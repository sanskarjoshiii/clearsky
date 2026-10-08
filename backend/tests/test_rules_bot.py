"""The deterministic farmer bot (LLM_PROVIDER=rules): parsers and full conversations in 4 languages."""

from __future__ import annotations

from datetime import date

import pytest

from clearsky.agent import rules
from clearsky.agent.agent import run_turn
from clearsky.models import BookingStatus, FieldStatus
from clearsky.repo import BookingsRepo, FieldsRepo
from clearsky.seed.generate import generate
from clearsky.seed.load import load
from tests import factories as fx

TODAY = date(2026, 10, 20)


@pytest.fixture
def seeded(ddb: None) -> None:
    load(generate(42), prebook=False)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("24 tareekh ko katega", date(2026, 10, 24)),
        ("24 tarikh", date(2026, 10, 24)),
        ("२४ तारीख", date(2026, 10, 24)),
        ("੨੪ ਤਾਰੀਖ", date(2026, 10, 24)),
        ("harvest on 26 Oct", date(2026, 10, 26)),
        ("Nov 3", date(2026, 11, 3)),
        ("2026-10-28", date(2026, 10, 28)),
        ("28/10", date(2026, 10, 28)),
        ("kal", date(2026, 10, 21)),
        ("parso katai", date(2026, 10, 22)),
        ("कल", date(2026, 10, 21)),
        ("aaj", date(2026, 10, 20)),
        ("2 tareekh", date(2026, 11, 2)),  # early-month day already long past → next month
        ("8 acre", None),
    ],
)
def test_parse_date(text: str, expected: date | None) -> None:
    assert rules.parse_date(text, TODAY) == expected


def test_parse_date_bare_number_only_when_asked() -> None:
    assert rules.parse_date("25", TODAY) is None
    assert rules.parse_date("25", TODAY, bare_number_is_day=True) == date(2026, 10, 25)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("8 acre", 8.0),
        ("8acres", 8.0),
        ("2.5 ekad", 2.5),
        ("10 killa", 10.0),
        ("८ एकड़", 8.0),
        ("੫ ਏਕੜ", 5.0),
        ("24 tareekh", None),
    ],
)
def test_parse_acres(text: str, expected: float | None) -> None:
    assert rules.parse_acres(text) == expected


def test_parse_name() -> None:
    assert rules.parse_name("Naam Gurpreet.") == "Gurpreet"
    assert rules.parse_name("mera naam harjit singh hai") == "Harjit Singh"
    assert rules.parse_name("मेरा नाम गुरप्रीत है") == "गुरप्रीत"
    assert rules.parse_name("My name is Aman, village Sunam") == "Aman"
    assert rules.parse_name("Kuldeep", bare_text_is_name=True) == "Kuldeep"
    assert rules.parse_name("8 acre", bare_text_is_name=True) is None


def test_detect_language() -> None:
    assert rules.detect_language("मेरा नाम") == rules.HI
    assert rules.detect_language("ਮੇਰਾ ਨਾਂ") == rules.PA
    assert rules.detect_language("my name is Aman") == rules.EN
    assert rules.detect_language("mera naam Aman hai") == rules.HINGLISH


def test_one_message_booking_hinglish(seeded: None) -> None:
    reply = run_turn("+919900000101", "Mera 8 acre dhaan 24 tareekh ko katega, Bhawanigarh. Naam Gurpreet.")
    assert reply.text.startswith("✅ Gurpreet ji, 8 acre ka khet 25 Oct ko saaf hoga")
    assert reply.booking is not None and reply.booking["pickup_date"] == "2026-10-25"
    [f] = FieldsRepo().by_farmer("+919900000101")
    assert f.status == FieldStatus.BOOKED and f.village_id == "V002"


def test_multi_turn_conversation(seeded: None) -> None:
    phone = "+919900000102"
    assert run_turn(phone, "namaste").text.startswith("Sat Sri Akal")
    assert run_turn(phone, "mera naam Harjit hai").text == rules.t("ask_village", rules.HINGLISH)
    assert run_turn(phone, "Bhawanigarh").text == rules.t("ask_acres", rules.HINGLISH)
    assert run_turn(phone, "6").text == rules.t("ask_date", rules.HINGLISH)
    final = run_turn(phone, "kal")
    assert final.text.startswith("✅ Harjit ji, 6 acre ka khet 22 Oct")


def test_hindi_devanagari(seeded: None) -> None:
    reply = run_turn("+919900000103", "मेरा नाम गुरप्रीत है, भवानीगढ़, 8 एकड़, 24 तारीख")
    assert reply.text.startswith("✅ गुरप्रीत जी") and "25 अक्टूबर" in reply.text


def test_punjabi_gurmukhi(seeded: None) -> None:
    reply = run_turn("+919900000104", "ਮੇਰਾ ਨਾਂ ਹਰਜੀਤ, ਪਿੰਡ ਭਵਾਨੀਗੜ੍ਹ, 5 ਏਕੜ, 23 ਤਾਰੀਖ")
    assert reply.text.startswith("✅ ਹਰਜੀਤ ਜੀ") and "24 ਅਕਤੂਬਰ" in reply.text


def test_english(seeded: None) -> None:
    reply = run_turn("+919900000105", "My name is Aman, village Sunam, 10 acres, harvest on 26 Oct")
    assert reply.text.startswith("✅ Aman, your 10-acre field will be cleared on 27 Oct")


def test_status_off_topic_and_cancel(seeded: None) -> None:
    phone = "+919900000106"
    booked = run_turn(phone, "Naam Gurpreet, Bhawanigarh, 8 acre, 24 tareekh")
    assert booked.text.startswith("✅")
    assert run_turn(phone, "kab aayega baler?").text.startswith("Aapki booking: 25 Oct")
    assert run_turn(phone, "cricket score?").text == rules.t("off_topic", rules.HINGLISH)
    assert run_turn(phone, "booking cancel karo").text.startswith("❌")
    [bk] = BookingsRepo().list_all()
    assert bk.status == BookingStatus.CANCELLED


def test_first_contact_off_topic_gets_intro(seeded: None) -> None:
    assert run_turn("+919900000107", "cricket score kya hai").text.startswith("Sat Sri Akal")


def test_unknown_village_is_asked_again(seeded: None) -> None:
    phone = "+919900000108"
    assert run_turn(phone, "naam Raju, 5 acre, kal").text == rules.t("ask_village", rules.HINGLISH)
    assert "'Mumbai'" in run_turn(phone, "Mumbai").text
    assert run_turn(phone, "Sunam").text.startswith("✅ Raju ji, 5 acre")


def test_yes_after_reminder_confirms_and_books(ddb: None) -> None:
    load(generate(42), prebook=False)
    fx.farmer("+919900000109", village_id="V002", name="Balwinder")
    fx.field(
        "FR1", phone="+919900000109", village_id="V002", harvest=date(2026, 10, 21), lat=30.266, lng=76.039
    )
    reply = run_turn("+919900000109", "haan")
    f = FieldsRepo().get("FR1")
    assert f is not None and f.harvest_confirmed and f.status == FieldStatus.BOOKED
    assert reply.text.startswith("✅ Balwinder ji")


def test_no_then_new_date_reschedules(seeded: None) -> None:
    phone = "+919900000110"
    run_turn(phone, "Naam Gurpreet, Bhawanigarh, 8 acre, 24 tareekh")
    assert run_turn(phone, "nahi").text == rules.t("ask_new_date", rules.HINGLISH)
    moved = run_turn(phone, "28 tareekh")
    assert moved.text.startswith("✅") and "29 Oct" in moved.text
