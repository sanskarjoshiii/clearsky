"""Farmer agent: Strands Agents SDK on Amazon Bedrock (IMPLEMENTATION.md §7).

One agent per inbound message (stateless Lambda). History comes from the Conversations table.
Tools are created inside `build_agent` and close over the verified sender phone, so the model can
never read or change another farmer's data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any, cast

from pydantic import BaseModel
from strands import Agent, tool
from strands.models.model import Model
from strands.types.content import Message

from clearsky import clock
from clearsky.agent import llm, memory, prompts, rules
from clearsky.agent import tools as impl
from clearsky.agent.llm import LLMConfigError
from clearsky.logging import get_logger, mask_phone

log = get_logger(child="agent")

FALLBACK_REPLY = "Maaf kijiye, abhi dikkat aa rahi hai. Thodi der mein dobara koshish karein. 🙏"


AgentConfigError = LLMConfigError


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]
    result: dict[str, Any]


class AgentReply(BaseModel):
    text: str
    booking: dict[str, Any] | None = None  # last successful book_pickup / reschedule result
    tool_calls: list[ToolCall] = []
    latency_ms: int = 0
    error: str | None = None


@dataclass
class TurnContext:
    calls: list[ToolCall] = field(default_factory=list)
    booking: dict[str, Any] | None = None

    def record(self, name: str, args: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(ToolCall(name=name, args=args, result=result))
        if name in ("book_pickup", "reschedule") and result.get("ok") and result.get("booking_id"):
            self.booking = result
        return result


def default_model() -> Model:
    """The configured LLM (LLM_PROVIDER). Raises AgentConfigError with a fix-it message."""
    return llm.build_model()


def build_tools(phone: str, ctx: TurnContext) -> list[Any]:
    """The agent's tools, bound to `phone`. The phone number is never an LLM-visible argument."""

    @tool
    def get_my_profile() -> dict[str, Any]:
        """Get this farmer's profile, fields and bookings. Returns registered=false for a new farmer."""
        return ctx.record("get_my_profile", {}, impl.get_my_profile(phone))

    @tool
    def resolve_village(name: str) -> dict[str, Any]:
        """Find the village the farmer means. Returns up to 3 matches with village_id and score (0-100).

        Args:
            name: Village name exactly as the farmer wrote it (any script or spelling).
        """
        return ctx.record("resolve_village", {"name": name}, impl.resolve_village(name))

    @tool
    def register_farmer(name: str, village_id: str, language: str = "hi") -> dict[str, Any]:
        """Register (or update) this farmer.

        Args:
            name: Farmer's name.
            village_id: village_id from resolve_village.
            language: Farmer's language: "hi" (Hindi), "pa" (Punjabi) or "en" (English).
        """
        args = {"name": name, "village_id": village_id, "language": language}
        return ctx.record("register_farmer", args, impl.register_farmer(phone, name, village_id, language))

    @tool
    def register_field(
        acres: float, harvest_date: str, village_id: str, sowing_date: str = ""
    ) -> dict[str, Any]:
        """Register a paddy field for this farmer. Call book_pickup right after with the returned field_id.

        Args:
            acres: Paddy area in acres (0.5 to 100).
            harvest_date: Harvest (katai) date as YYYY-MM-DD.
            village_id: village_id from resolve_village.
            sowing_date: Optional planned wheat sowing date as YYYY-MM-DD; empty if not given.
        """
        args = {
            "acres": acres,
            "harvest_date": harvest_date,
            "village_id": village_id,
            "sowing_date": sowing_date,
        }
        result = impl.register_field(phone, acres, harvest_date, village_id, sowing_date or None)
        return ctx.record("register_field", args, result)

    @tool
    def book_pickup(field_id: str) -> dict[str, Any]:
        """Book the nearest free baler for a field before its sowing deadline.

        Args:
            field_id: field_id from register_field or get_my_profile.
        """
        return ctx.record("book_pickup", {"field_id": field_id}, impl.book_pickup(phone, field_id))

    @tool
    def get_my_bookings() -> dict[str, Any]:
        """List this farmer's current pickup bookings."""
        return ctx.record("get_my_bookings", {}, impl.get_my_bookings(phone))

    @tool
    def confirm_harvest(field_id: str) -> dict[str, Any]:
        """Record that the farmer confirmed the harvest is done (or happening as planned).

        Args:
            field_id: field_id of the field.
        """
        return ctx.record("confirm_harvest", {"field_id": field_id}, impl.confirm_harvest(phone, field_id))

    @tool
    def reschedule(field_id: str, new_harvest_date: str) -> dict[str, Any]:
        """Change a field's harvest date: cancels the old booking and books again.

        Args:
            field_id: field_id of the field.
            new_harvest_date: New harvest date as YYYY-MM-DD.
        """
        args = {"field_id": field_id, "new_harvest_date": new_harvest_date}
        return ctx.record("reschedule", args, impl.reschedule(phone, field_id, new_harvest_date))

    @tool
    def cancel_booking(booking_id: str) -> dict[str, Any]:
        """Cancel a pickup booking. Only when the farmer clearly asks to cancel.

        Args:
            booking_id: booking_id from get_my_bookings or get_my_profile.
        """
        return ctx.record(
            "cancel_booking", {"booking_id": booking_id}, impl.cancel_booking(phone, booking_id)
        )

    return [
        get_my_profile,
        resolve_village,
        register_farmer,
        register_field,
        book_pickup,
        get_my_bookings,
        confirm_harvest,
        reschedule,
        cancel_booking,
    ]


def build_agent(
    phone: str,
    history: list[dict[str, Any]],
    today: date,
    *,
    model: Model | None = None,
    ctx: TurnContext | None = None,
) -> Agent:
    return Agent(
        model=model or default_model(),
        system_prompt=prompts.farmer_system(today=today),
        tools=build_tools(phone, ctx or TurnContext()),
        messages=cast(list[Message], history),
        callback_handler=None,
    )


def run_turn(phone: str, text: str, *, today: date | None = None, model: Model | None = None) -> AgentReply:
    """Handle one inbound farmer message end to end: load history, run the agent, save both turns.

    With an explicit `model` (tests) or LLM_PROVIDER≠rules, the Strands agent answers. If that LLM
    call fails (outage, throttling, bad key) the deterministic rules bot answers instead, so a farmer
    always gets a useful reply. LLM_PROVIDER=rules uses the rules bot directly.
    """
    today = today or clock.today()
    use_llm = model is not None or llm.provider() != "rules"
    ctx = TurnContext()
    agent = None
    if use_llm:
        history = memory.to_messages(memory.load_turns(phone))
        agent = build_agent(phone, history, today, model=model, ctx=ctx)  # raises AgentConfigError
    memory.save_turn(phone, "user", text)
    started = time.monotonic()
    error = None
    try:
        if agent is not None:
            reply = str(agent(text)).strip() or FALLBACK_REPLY
        else:
            reply = rules.reply(phone, text, today, ctx.record)
    except Exception as e:  # LLM outage/throttling → rules bot; rules failure → polite apology
        log.exception("agent failed", extra={"phone": mask_phone(phone), "llm": use_llm})
        error = type(e).__name__
        reply = FALLBACK_REPLY
        if agent is not None:
            try:
                reply = rules.reply(phone, text, today, ctx.record)
            except Exception:
                log.exception("rules fallback failed", extra={"phone": mask_phone(phone)})
    latency = int((time.monotonic() - started) * 1000)
    memory.save_turn(phone, "assistant", reply)
    log.info(
        "agent turn",
        extra={"phone": mask_phone(phone), "latency_ms": latency, "tools": [c.name for c in ctx.calls]},
    )
    return AgentReply(text=reply, booking=ctx.booking, tool_calls=ctx.calls, latency_ms=latency, error=error)
