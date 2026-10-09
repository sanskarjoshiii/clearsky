"""Phase 3: the agent loop with a scripted model (no Bedrock), memory, and failure handling."""

from __future__ import annotations

from typing import Any

import pytest

from clearsky.agent import memory
from clearsky.agent.agent import FALLBACK_REPLY, AgentConfigError, run_turn
from clearsky.agent.prompts import farmer_system
from clearsky.models import ConversationTurn, FieldStatus
from clearsky.repo import BookingsRepo, ConversationsRepo, FarmersRepo, FieldsRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests.conftest import TODAY
from tests.stub_model import FailingModel, ScriptedModel, call, last_tool_result, say

PHONE = "+919900000077"
MSG = "Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet."


@pytest.fixture
def seeded(ddb: None) -> None:
    load(generate(42), prebook=False)


def _booking_script() -> list[Any]:
    def register_farmer(msgs: list[dict[str, Any]]) -> dict[str, Any]:
        vid = last_tool_result(msgs)["matches"][0]["village_id"]
        return call("register_farmer", name="Gurpreet", village_id=vid, language="hi")

    def register_field(msgs: list[dict[str, Any]]) -> dict[str, Any]:
        vid = last_tool_result(msgs)["village_id"]
        return call("register_field", acres=8, harvest_date="2026-10-24", village_id=vid)

    def book(msgs: list[dict[str, Any]]) -> dict[str, Any]:
        return call("book_pickup", field_id=last_tool_result(msgs)["field_id"])

    def confirm(msgs: list[dict[str, Any]]) -> dict[str, Any]:
        r = last_tool_result(msgs)
        # what a model following the prompt says for status "offered": sent, not confirmed
        assert r["status"] == "offered" and r["confirmed"] is False
        return say(
            f"Gurpreet ji, {r['pickup_date']} ke liye request baler ko bhej di hai. Confirm hote hi batayenge."
        )

    return [
        call("get_my_profile"),
        call("resolve_village", name="Bhawanigarh"),
        register_farmer,
        register_field,
        book,
        confirm,
    ]


def test_full_booking_in_one_turn(seeded: None) -> None:
    model = ScriptedModel(_booking_script())
    reply = run_turn(PHONE, MSG, model=model)

    assert reply.error is None
    assert "2026-10-25" in reply.text
    assert reply.booking is not None and reply.booking["pickup_date"] == "2026-10-25"
    assert reply.booking["status"] == "offered"
    assert [c.name for c in reply.tool_calls] == [
        "get_my_profile",
        "resolve_village",
        "register_farmer",
        "register_field",
        "book_pickup",
    ]
    farmer = FarmersRepo().get(PHONE)
    assert farmer is not None and farmer.name == "Gurpreet" and farmer.village_id == "V002"
    fields = FieldsRepo().by_farmer(PHONE)
    assert len(fields) == 1 and fields[0].status == FieldStatus.BOOKED
    assert BookingsRepo().get(str(fields[0].booking_id)) is not None
    turns = ConversationsRepo().last(PHONE, 10)
    assert [(t.role, t.text) for t in turns] == [("user", MSG), ("assistant", reply.text)]
    # the system prompt carries today's date
    assert "2026-10-20" in model.seen[0]["system_prompt"]


def test_second_turn_gets_history(seeded: None) -> None:
    run_turn(PHONE, MSG, model=ScriptedModel(_booking_script()))
    model = ScriptedModel([say("Aapka khet 25 Oct ko saaf hoga.")])
    run_turn(PHONE, "kab aayega baler?", model=model)
    msgs = model.seen[0]["messages"]
    assert msgs[0]["role"] == "user" and msgs[0]["content"][0]["text"] == MSG
    assert msgs[1]["role"] == "assistant"
    assert msgs[-1]["content"][0]["text"] == "kab aayega baler?"


def test_off_topic_reply_makes_no_tool_calls(seeded: None) -> None:
    reply = run_turn(
        PHONE,
        "cricket score?",
        model=ScriptedModel([say("Maaf kijiye, main sirf parali pickup mein madad karta hoon.")]),
    )
    assert reply.tool_calls == [] and reply.booking is None


def test_model_failure_falls_back_to_rules_bot(seeded: None) -> None:
    reply = run_turn(PHONE, MSG, model=FailingModel())
    assert reply.error == "RuntimeError"
    assert reply.text.startswith("📨") and reply.booking is not None  # rules bot still sent the request
    assert reply.text != FALLBACK_REPLY
    assert [t.role for t in ConversationsRepo().last(PHONE, 10)] == ["user", "assistant"]


@pytest.mark.parametrize(
    ("env", "needs"),
    [
        ({"LLM_PROVIDER": "bedrock"}, "BEDROCK_MODEL_ID"),
        ({"LLM_PROVIDER": "openai"}, "LLM_MODEL_ID"),
        ({"LLM_PROVIDER": "openai", "LLM_MODEL_ID": "team-model"}, "LLM_API_KEY"),
        ({"LLM_PROVIDER": "nope"}, "LLM_PROVIDER"),
    ],
)
def test_misconfigured_llm_is_a_config_error(
    seeded: None, monkeypatch: pytest.MonkeyPatch, env: dict[str, str], needs: str
) -> None:
    import clearsky.config as cfg

    monkeypatch.setattr(cfg, "_dotenv_value", lambda name: None)
    monkeypatch.setattr(cfg, "_ssm_value", lambda path: None)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    cfg.reset_settings()
    with pytest.raises(AgentConfigError, match=needs):
        run_turn(PHONE, MSG)


def test_to_messages_alternates_and_starts_with_user() -> None:
    def t(role: str, text: str, i: int) -> ConversationTurn:
        return ConversationTurn(phone=PHONE, ts=f"2026-10-20T10:00:{i:02d}", role=role, text=text)

    turns = [
        t("assistant", "old reminder", 0),
        t("user", "hi", 1),
        t("user", "8 acre", 2),
        t("assistant", "Gaon?", 3),
        t("user", "", 4),
        t("user", "unanswered", 5),
    ]
    msgs = memory.to_messages(turns)
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"][0]["text"] == "hi\n8 acre"


def test_system_prompt_rules() -> None:
    p = farmer_system(TODAY)
    assert "2026-10-20 (Tuesday)" in p
    for rule in (
        "ONLY talk to farmers",
        "book_pickup",
        "Never invent",
        "40 words",
        "Off-topic",
        "NEVER say the pickup is confirmed",
    ):
        assert rule in p
