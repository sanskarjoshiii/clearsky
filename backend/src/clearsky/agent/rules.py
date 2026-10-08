"""Deterministic farmer bot (LLM_PROVIDER=rules).

A slot-filling state machine over the same tools the LLM agent uses, so the WhatsApp → booking loop
works with no LLM at all (offline dev, demos, and a fallback if the LLM provider is down).

Slots: name, village, acres, harvest date. Details are gathered from every user turn since the last
booking/cancel confirmation, so a farmer can answer across several messages. Replies follow the
farmer's script: Devanagari → Hindi, Gurmukhi → Punjabi, English words → English, else Hinglish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from clearsky.agent import tools
from clearsky.agent.memory import load_turns
from clearsky.domain.villages import resolve
from clearsky.repo import FarmersRepo, FieldsRepo

# ------------------------------------------------------------------ language

HI, HINGLISH, PA, EN = "hi", "hinglish", "pa", "en"
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_GURMUKHI = re.compile(r"[਀-੿]")
_ENGLISH_HINTS = {
    "my",
    "the",
    "is",
    "will",
    "harvest",
    "please",
    "when",
    "what",
    "name",
    "village",
    "field",
    "hello",
    "hi",
    "book",
    "yes",
    "no",
    "cancel",
    "on",
    "of",
    "and",
    "i",
    "am",
    "acres",
}
_HINGLISH_HINTS = {
    "mera",
    "meri",
    "hai",
    "ko",
    "ka",
    "ki",
    "naam",
    "katega",
    "katai",
    "dhaan",
    "gaon",
    "pind",
    "kal",
    "parso",
    "haan",
    "nahi",
    "kab",
    "tareekh",
    "tarikh",
    "ji",
    "aur",
    "sat",
    "sri",
    "akal",
}


def detect_language(text: str) -> str:
    if _DEVANAGARI.search(text):
        return HI
    if _GURMUKHI.search(text):
        return PA
    words = set(re.findall(r"[a-z]+", text.lower()))
    if words & _HINGLISH_HINTS:
        return HINGLISH
    if words & _ENGLISH_HINTS:
        return EN
    return HINGLISH


# ------------------------------------------------------------------ replies

_MONTHS = {
    EN: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    HINGLISH: ["Jan", "Feb", "March", "April", "May", "June", "July", "Aug", "Sep", "Oct", "Nov", "Dec"],
    HI: ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"],
    PA: ["ਜਨਵਰੀ", "ਫ਼ਰਵਰੀ", "ਮਾਰਚ", "ਅਪ੍ਰੈਲ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾਈ", "ਅਗਸਤ", "ਸਤੰਬਰ", "ਅਕਤੂਬਰ", "ਨਵੰਬਰ", "ਦਸੰਬਰ"],
}

MSG: dict[str, dict[str, str]] = {
    "intro": {
        HINGLISH: "Sat Sri Akal ji 🌾 Main ClearSky hoon. Parali jalane ki zaroorat nahi: hum baler bhej kar khet saaf karwate hain. Apna naam, gaon, kitne acre aur katai ki tareekh bataiye.",
        HI: "सत श्री अकाल जी 🌾 मैं ClearSky हूँ। पराली जलाने की ज़रूरत नहीं: हम बेलर भेजकर खेत साफ़ करवाते हैं। अपना नाम, गाँव, कितने एकड़ और कटाई की तारीख बताइए।",
        PA: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਜੀ 🌾 ਮੈਂ ClearSky ਹਾਂ। ਪਰਾਲੀ ਸਾੜਨ ਦੀ ਲੋੜ ਨਹੀਂ: ਅਸੀਂ ਬੇਲਰ ਭੇਜ ਕੇ ਖੇਤ ਸਾਫ਼ ਕਰਵਾਉਂਦੇ ਹਾਂ। ਆਪਣਾ ਨਾਂ, ਪਿੰਡ, ਕਿੰਨੇ ਏਕੜ ਅਤੇ ਕਟਾਈ ਦੀ ਤਾਰੀਖ ਦੱਸੋ।",
        EN: "Hello 🌾 I'm ClearSky. No need to burn straw: we send a baler to clear your field. Please tell me your name, village, how many acres, and the harvest date.",
    },
    "ask_name": {
        HINGLISH: "Aapka naam kya hai ji?",
        HI: "आपका नाम क्या है जी?",
        PA: "ਤੁਹਾਡਾ ਨਾਂ ਕੀ ਹੈ ਜੀ?",
        EN: "What is your name?",
    },
    "ask_village": {
        HINGLISH: "Aapka khet kis gaon mein hai?",
        HI: "आपका खेत किस गाँव में है?",
        PA: "ਤੁਹਾਡਾ ਖੇਤ ਕਿਹੜੇ ਪਿੰਡ ਵਿੱਚ ਹੈ?",
        EN: "Which village is your field in?",
    },
    "ask_acres": {
        HINGLISH: "Kitne acre mein dhaan hai?",
        HI: "कितने एकड़ में धान है?",
        PA: "ਕਿੰਨੇ ਏਕੜ ਵਿੱਚ ਝੋਨਾ ਹੈ?",
        EN: "How many acres of paddy?",
    },
    "ask_date": {
        HINGLISH: "Katai kis tareekh ko hogi?",
        HI: "कटाई किस तारीख को होगी?",
        PA: "ਕਟਾਈ ਕਿਸ ਤਾਰੀਖ ਨੂੰ ਹੋਵੇਗੀ?",
        EN: "On which date will you harvest?",
    },
    "village_pick": {
        HINGLISH: "Kaunsa gaon? {options}",
        HI: "कौन सा गाँव? {options}",
        PA: "ਕਿਹੜਾ ਪਿੰਡ? {options}",
        EN: "Which village? {options}",
    },
    "village_unknown": {
        HINGLISH: "'{name}' gaon nahi mila. Paas ke bade gaon ya sheher ka naam bataiye.",
        HI: "'{name}' गाँव नहीं मिला। पास के बड़े गाँव या शहर का नाम बताइए।",
        PA: "'{name}' ਪਿੰਡ ਨਹੀਂ ਮਿਲਿਆ। ਨੇੜੇ ਦੇ ਵੱਡੇ ਪਿੰਡ ਜਾਂ ਸ਼ਹਿਰ ਦਾ ਨਾਂ ਦੱਸੋ।",
        EN: "I couldn't find '{name}'. Please tell me a nearby bigger village or town.",
    },
    "booked": {
        HINGLISH: "✅ {name} ji, {acres} acre ka khet {date} ko saaf hoga. Baler: {operator}. {money}",
        HI: "✅ {name} जी, {acres} एकड़ का खेत {date} को साफ़ होगा। बेलर: {operator}। {money}",
        PA: "✅ {name} ਜੀ, {acres} ਏਕੜ ਦਾ ਖੇਤ {date} ਨੂੰ ਸਾਫ਼ ਹੋਵੇਗਾ। ਬੇਲਰ: {operator}। {money}",
        EN: "✅ {name}, your {acres}-acre field will be cleared on {date}. Baler: {operator}. {money}",
    },
    "free": {HINGLISH: "Koi kharcha nahi.", HI: "कोई खर्चा नहीं।", PA: "ਕੋਈ ਖ਼ਰਚਾ ਨਹੀਂ।", EN: "Free of cost."},
    "payout": {
        HINGLISH: "Aapko lagbhag ₹{amount} milenge (anumaan).",
        HI: "आपको लगभग ₹{amount} मिलेंगे (अनुमान)।",
        PA: "ਤੁਹਾਨੂੰ ਲਗਭਗ ₹{amount} ਮਿਲਣਗੇ (ਅੰਦਾਜ਼ਾ)।",
        EN: "You will get about ₹{amount} (estimate).",
    },
    "no_slot": {
        HINGLISH: "Maaf kijiye, abhi koi baler khali nahi hai. Officer ko bata diya hai, jaldi sampark hoga. 🙏",
        HI: "माफ़ कीजिए, अभी कोई बेलर खाली नहीं है। अफ़सर को बता दिया है, जल्दी संपर्क होगा। 🙏",
        PA: "ਮਾਫ਼ ਕਰਨਾ, ਹੁਣੇ ਕੋਈ ਬੇਲਰ ਖਾਲੀ ਨਹੀਂ। ਅਫ਼ਸਰ ਨੂੰ ਦੱਸ ਦਿੱਤਾ ਹੈ, ਜਲਦੀ ਸੰਪਰਕ ਹੋਵੇਗਾ। 🙏",
        EN: "Sorry, no baler is free right now. An officer has been informed and will follow up. 🙏",
    },
    "bad_input": {
        HINGLISH: "{problem} Dobara bataiye.",
        HI: "{problem} दोबारा बताइए।",
        PA: "{problem} ਦੁਬਾਰਾ ਦੱਸੋ।",
        EN: "{problem} Please tell me again.",
    },
    "status": {
        HINGLISH: "Aapki booking: {items}",
        HI: "आपकी बुकिंग: {items}",
        PA: "ਤੁਹਾਡੀ ਬੁਕਿੰਗ: {items}",
        EN: "Your bookings: {items}",
    },
    "no_bookings": {
        HINGLISH: "Abhi koi booking nahi hai. Acre aur katai ki tareekh bataiye.",
        HI: "अभी कोई बुकिंग नहीं है। एकड़ और कटाई की तारीख बताइए।",
        PA: "ਹੁਣੇ ਕੋਈ ਬੁਕਿੰਗ ਨਹੀਂ। ਏਕੜ ਅਤੇ ਕਟਾਈ ਦੀ ਤਾਰੀਖ ਦੱਸੋ।",
        EN: "You have no bookings yet. Tell me your acres and harvest date.",
    },
    "cancelled": {
        HINGLISH: "❌ Booking radd kar di gayi hai.",
        HI: "❌ बुकिंग रद्द कर दी गई है।",
        PA: "❌ ਬੁਕਿੰਗ ਰੱਦ ਕਰ ਦਿੱਤੀ ਗਈ ਹੈ।",
        EN: "❌ Your booking has been cancelled.",
    },
    "harvest_confirmed": {
        HINGLISH: "👍 Shukriya ji, katai note kar li. Baler tay samay par aayega.",
        HI: "👍 शुक्रिया जी, कटाई नोट कर ली। बेलर तय समय पर आएगा।",
        PA: "👍 ਧੰਨਵਾਦ ਜੀ, ਕਟਾਈ ਨੋਟ ਕਰ ਲਈ। ਬੇਲਰ ਸਮੇਂ ਸਿਰ ਆਵੇਗਾ।",
        EN: "👍 Thanks, harvest noted. The baler will come as scheduled.",
    },
    "ask_new_date": {
        HINGLISH: "Theek hai. Nayi katai ki tareekh bataiye.",
        HI: "ठीक है। नई कटाई की तारीख बताइए।",
        PA: "ਠੀਕ ਹੈ। ਨਵੀਂ ਕਟਾਈ ਦੀ ਤਾਰੀਖ ਦੱਸੋ।",
        EN: "OK. Please tell me the new harvest date.",
    },
    "off_topic": {
        HINGLISH: "Maaf kijiye, main sirf parali pickup mein madad karta hoon. Kitne acre aur katai kab hai?",
        HI: "माफ़ कीजिए, मैं सिर्फ़ पराली पिकअप में मदद करता हूँ। कितने एकड़ और कटाई कब है?",
        PA: "ਮਾਫ਼ ਕਰਨਾ, ਮੈਂ ਸਿਰਫ਼ ਪਰਾਲੀ ਪਿਕਅੱਪ ਵਿੱਚ ਮਦਦ ਕਰਦਾ ਹਾਂ। ਕਿੰਨੇ ਏਕੜ ਅਤੇ ਕਟਾਈ ਕਦੋਂ ਹੈ?",
        EN: "Sorry, I can only help with straw pickup. How many acres, and when is the harvest?",
    },
}

_ASK_SLOT = {
    key: slot
    for slot, key in (
        ("name", "ask_name"),
        ("village", "ask_village"),
        ("acres", "ask_acres"),
        ("date", "ask_date"),
        ("date", "ask_new_date"),
        ("village", "village_pick"),
        ("village", "village_unknown"),
    )
}


def t(key: str, lang: str, **kw: Any) -> str:
    return MSG[key][lang].format(**kw)


def fmt_date(d: date, lang: str) -> str:
    return f"{d.day} {_MONTHS[lang][d.month - 1]}"


def asked_slot(assistant_text: str | None) -> str | None:
    """Which slot the bot's previous message asked for (by matching the question templates)."""
    if not assistant_text:
        return None
    for key, slot in _ASK_SLOT.items():
        for template in MSG[key].values():
            stem = template.split("{")[0].strip("'\" ")
            if stem and assistant_text.startswith(stem[:18]):
                return slot
    return None


# ------------------------------------------------------------------ parsing

_DIGITS = str.maketrans("०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯", "01234567890123456789")
_ACRE_WORDS = r"(?:acres?|ekad|ekar|ekr|killa|kille|kila|kile|एकड़|एकड|किल्ले|किल्ला|ਏਕੜ|ਕਿੱਲੇ|ਕਿੱਲਾ)"
_ACRES_RE = re.compile(rf"(\d+(?:\.\d+)?)\s*{_ACRE_WORDS}", re.I)
_MONTH_WORDS = {
    "sep": 9,
    "sept": 9,
    "september": 9,
    "सितंबर": 9,
    "ਸਤੰਬਰ": 9,
    "oct": 10,
    "october": 10,
    "अक्टूबर": 10,
    "ਅਕਤੂਬਰ": 10,
    "nov": 11,
    "november": 11,
    "नवंबर": 11,
    "ਨਵੰਬਰ": 11,
}
_DAY_MONTH_RE = re.compile(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s+(" + "|".join(_MONTH_WORDS) + r")\b", re.I)
_MONTH_DAY_RE = re.compile(r"\b(" + "|".join(_MONTH_WORDS) + r")\s+(\d{1,2})\b", re.I)
_TAREEKH_RE = re.compile(
    r"(\d{1,2})\s*(?:st|nd|rd|th)?\s*(?:tareekh|tarikh|tarik|tareek|tareeq|तारीख़?|ਤਾਰੀਖ|date)", re.I
)
_ISO_RE = re.compile(r"\b(20\d\d)-(\d{1,2})-(\d{1,2})\b")
_SLASH_RE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?\b")
_RELATIVE = [
    (re.compile(r"\b(?:aaj|today)\b|आज|ਅੱਜ", re.I), 0),
    (re.compile(r"\b(?:parso|parson|parsoon)\b|परसों|ਪਰਸੋਂ", re.I), 2),
    (re.compile(r"\b(?:kal|tomorrow)\b|कल|ਕੱਲ੍ਹ|ਭਲਕੇ", re.I), 1),
    (re.compile(r"\b(?:agle hafte|next week)\b|अगले हफ़्ते|अगले हफ्ते|ਅਗਲੇ ਹਫ਼ਤੇ", re.I), 7),
]
_NAME_RE = re.compile(
    r"(?:mera naam|my name is|naam|name|i am|i'm|मेरा नाम|नाम|ਮੇਰਾ ਨਾਂ|ਮੇਰਾ ਨਾਮ|ਨਾਂ|ਨਾਮ)\s*(?:hai|है|ਹੈ|is)?\s*[:\-]?\s*"
    r"([A-Za-zऀ-ॿ਀-੿]+(?:\s+[A-Za-zऀ-ॿ਀-੿]+)?)",
    re.I,
)
_NAME_TAIL = {"hai", "है", "ਹੈ", "ji", "जी", "ਜੀ", "aur", "and", "mera", "meri", "village", "gaon", "pind"}
_YES = re.compile(
    r"^\s*(?:haan|haa|ha|han|yes|yeah|ok|okay|ji haan|ji|हाँ|हां|जी हाँ|ਹਾਂ|ਹਾਂ ਜੀ)\s*[.!]*\s*$", re.I
)
_NO = re.compile(r"\b(?:nahi|nahin|nhi|no|not)\b|नहीं|ਨਹੀਂ", re.I)
_CANCEL = re.compile(r"\b(?:cancel|radd|rad karo|band karo)\b|रद्द|ਰੱਦ", re.I)
_STATUS = re.compile(r"\b(?:status|kab|when|booking|kab aayega|kab ayega)\b|कब|ਕਦੋਂ|ਬੁਕਿੰਗ|बुकिंग", re.I)
_GREETING = re.compile(
    r"^\s*(?:hi|hello|hey|namaste|namaskar|sat sri akal|sasriakal|नमस्ते|सत श्री अकाल|ਸਤ ਸ੍ਰੀ ਅਕਾਲ)\W*$", re.I
)
# Words that are never village names (Hinglish filler around the details).
_NOT_VILLAGE = {
    "mera",
    "meri",
    "mere",
    "hai",
    "ko",
    "ka",
    "ki",
    "ke",
    "mein",
    "me",
    "dhaan",
    "dhan",
    "paddy",
    "katega",
    "katai",
    "kategi",
    "hogi",
    "hoga",
    "acre",
    "acres",
    "tareekh",
    "tarikh",
    "naam",
    "name",
    "khet",
    "field",
    "gaon",
    "pind",
    "village",
    "my",
    "is",
    "the",
    "will",
    "be",
    "harvest",
    "harvested",
    "on",
    "in",
    "of",
    "and",
    "aur",
    "ji",
    "kal",
    "aaj",
    "parso",
    "haan",
    "nahi",
    "please",
    "book",
    "karo",
    "oct",
    "nov",
    "october",
    "november",
    "date",
    "main",
    "hoon",
    "hu",
    "hum",
    "from",
    "at",
    "am",
    "i",
    "sat",
    "sri",
    "akal",
    "hello",
    "namaste",
    "jhona",
    "मेरा",
    "मेरी",
    "है",
    "को",
    "का",
    "की",
    "में",
    "धान",
    "कटेगा",
    "कटाई",
    "तारीख",
    "एकड़",
    "खेत",
    "गाँव",
    "गांव",
    "पिंड",
    "नाम",
    "होगी",
    "और",
    "जी",
    "ਮੇਰਾ",
    "ਮੇਰੀ",
    "ਹੈ",
    "ਨੂੰ",
    "ਦਾ",
    "ਦੀ",
    "ਵਿੱਚ",
    "ਝੋਨਾ",
    "ਕਟਾਈ",
    "ਤਾਰੀਖ",
    "ਏਕੜ",
    "ਖੇਤ",
    "ਪਿੰਡ",
    "ਨਾਂ",
    "ਨਾਮ",
    "ਹੋਵੇਗੀ",
    "ਅਤੇ",
    "ਜੀ",
}


def _to_date(day: int, month: int, today: date, year: int | None = None) -> date | None:
    try:
        return date(year or today.year, month, day)
    except ValueError:
        return None


def parse_date(text: str, today: date, bare_number_is_day: bool = False) -> date | None:
    s = text.translate(_DIGITS)
    if m := _ISO_RE.search(s):
        return _to_date(int(m.group(3)), int(m.group(2)), today, int(m.group(1)))
    if m := _DAY_MONTH_RE.search(s):
        return _to_date(int(m.group(1)), _MONTH_WORDS[m.group(2).lower()], today)
    if m := _MONTH_DAY_RE.search(s):
        return _to_date(int(m.group(2)), _MONTH_WORDS[m.group(1).lower()], today)
    day: int | None = None
    if m := _TAREEKH_RE.search(s):
        day = int(m.group(1))
    elif (m := _SLASH_RE.search(s)) and not _ACRES_RE.search(s[m.start() : m.end() + 8]):
        y = int(m.group(3)) if m.group(3) else None
        if y is not None and y < 100:
            y += 2000
        return _to_date(int(m.group(1)), int(m.group(2)), today, y)
    for pattern, offset in _RELATIVE:
        if pattern.search(s):
            return today + timedelta(days=offset)
    if day is None and bare_number_is_day and (m := re.fullmatch(r"\s*(\d{1,2})\s*", _ACRES_RE.sub(" ", s))):
        day = int(m.group(1))
    if day is None:
        return None
    d = _to_date(day, today.month, today)
    if d is None or d < today - timedelta(days=15):  # "5 tareekh" late in the month means next month
        nm = today.replace(day=1) + timedelta(days=32)
        d = _to_date(day, nm.month, today, nm.year)
    return d


def parse_acres(text: str, bare_number_is_acres: bool = False) -> float | None:
    s = text.translate(_DIGITS)
    if m := _ACRES_RE.search(s):
        return float(m.group(1))
    if bare_number_is_acres and (m := re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*", s)):
        return float(m.group(1))
    return None


def parse_name(text: str, bare_text_is_name: bool = False) -> str | None:
    if m := _NAME_RE.search(text):
        words = [w for w in m.group(1).split() if w.lower() not in _NAME_TAIL]
        if words:
            return " ".join(w.capitalize() if w.isascii() else w for w in words)
    if bare_text_is_name:
        words = re.findall(r"[A-Za-zऀ-ॿ਀-੿]+", text)
        words = [w for w in words if w.lower() not in _NAME_TAIL]
        if 1 <= len(words) <= 3 and not re.search(r"\d", text):
            return " ".join(w.capitalize() if w.isascii() else w for w in words)
    return None


def find_village(text: str, *, answer_to_question: bool = False) -> tuple[str | None, list[str], str | None]:
    """(village_id, ambiguous option names, unknown phrase). Scans 1–3 word windows of the text."""
    cleaned = _NAME_RE.sub(" ", text.translate(_DIGITS))
    cleaned = _ACRES_RE.sub(" ", cleaned)
    words = re.findall(r"[A-Za-zऀ-ॿ਀-੿]+", cleaned)
    words = [w for w in words if w.lower() not in _NOT_VILLAGE and len(w) >= 3]
    best: tuple[float, str, str] | None = None
    options: list[str] = []
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            matches = resolve(phrase)
            if not matches:
                continue
            top = matches[0]
            if top.score >= 88 and (best is None or top.score > best[0]):
                best = (top.score, top.village_id, phrase)
                close = [m.name for m in matches[1:] if top.score - m.score < 3 and m.score >= 88]
                options = [top.name, *close] if close else []
    if best:
        return (None if options else best[1]), options, None
    if answer_to_question and words:
        return None, [], " ".join(words[:3])
    return None, [], None


# ------------------------------------------------------------------ the bot


@dataclass
class Draft:
    name: str | None = None
    village_id: str | None = None
    acres: float | None = None
    harvest: date | None = None
    village_options: list[str] = field(default_factory=list)
    village_unknown: str | None = None

    def absorb(self, text: str, asked: str | None, today: date) -> None:
        if name := parse_name(text, bare_text_is_name=asked == "name"):
            self.name = name
        if (acres := parse_acres(text, bare_number_is_acres=asked == "acres")) is not None:
            self.acres = acres
        if d := parse_date(text, today, bare_number_is_day=asked == "date"):
            self.harvest = d
        if asked == "name" and self.name and parse_acres(text) is None and parse_date(text, today) is None:
            return  # a bare name answer is not a village
        vid, options, unknown = find_village(text, answer_to_question=asked == "village")
        if vid:
            self.village_id, self.village_options, self.village_unknown = vid, [], None
        elif options:
            self.village_options, self.village_unknown = options, None
        elif unknown:
            self.village_unknown = unknown


def _build_draft(phone: str, text: str, today: date) -> tuple[Draft, str | None]:
    """Replay user turns since the last ✅/❌ confirmation, then the new message."""
    turns = load_turns(phone, 20)
    start = 0
    for i, tn in enumerate(turns):
        if tn.role == "assistant" and tn.text.startswith(("✅", "❌")):
            start = i + 1
    draft = Draft()
    last_assistant: str | None = None
    for tn in turns[start:]:
        if tn.role == "assistant":
            last_assistant = tn.text
        else:
            draft.absorb(tn.text, asked_slot(last_assistant), today)
    # the newest assistant turn overall decides what the current message answers
    for tn in reversed(turns):
        if tn.role == "assistant":
            last_assistant = tn.text
            break
    asked = asked_slot(last_assistant)
    draft.absorb(text, asked, today)
    return draft, last_assistant


def _money(result: dict[str, Any], lang: str) -> str:
    if result.get("free_clearance"):
        return t("free", lang)
    return t("payout", lang, amount=f"{int(result.get('farmer_payout_inr', 0)):,}")


def _upcoming_field(phone: str, today: date) -> Any:
    open_fields = [
        f for f in FieldsRepo().by_farmer(phone) if f.status.value in ("REGISTERED", "HARVESTED", "BOOKED")
    ]
    if not open_fields:
        return None
    return min(open_fields, key=lambda f: abs((f.harvest_date - today).days))


def reply(phone: str, text: str, today: date, record: Any) -> str:
    """One bot turn. `record(name, args, result)` logs tool calls (agent.TurnContext.record)."""

    def call(name: str, fn: Any, *args: Any) -> dict[str, Any]:
        result: dict[str, Any] = fn(*args)
        record(name, {"args": [a for a in args if a != phone]}, result)
        return result

    farmer = FarmersRepo().get(phone)
    lang = detect_language(text)
    if farmer is not None and lang == HINGLISH and not re.search(r"[a-z]{3,}", text.lower()):
        lang = {"hi": HINGLISH, "pa": PA, "en": EN}.get(farmer.language.value, HINGLISH)

    if _GREETING.match(text):
        return t("intro", lang)

    if _CANCEL.search(text):
        bookings = call("get_my_bookings", tools.get_my_bookings, phone)["bookings"]
        confirmed = [b for b in bookings if b["status"] == "CONFIRMED"]
        if not confirmed:
            return t("no_bookings", lang)
        call("cancel_booking", tools.cancel_booking, phone, confirmed[-1]["booking_id"])
        return t("cancelled", lang)

    draft, last_assistant = _build_draft(phone, text, today)
    nothing_new = (
        draft.acres is None and draft.harvest is None and draft.village_id is None and not draft.name
    )

    if _YES.match(text):
        f = _upcoming_field(phone, today)
        if f is not None and not f.harvest_confirmed:
            call("confirm_harvest", tools.confirm_harvest, phone, f.field_id)
            if f.status.value != "BOOKED":
                booked = call("book_pickup", tools.book_pickup, phone, f.field_id)
                if booked.get("ok"):
                    return _booked_text(booked, farmer.name if farmer else "", f.acres, lang)
            return t("harvest_confirmed", lang)

    if _NO.search(text) and nothing_new and _upcoming_field(phone, today) is not None:
        return t("ask_new_date", lang)

    if (
        asked_slot(last_assistant) == "date"
        and last_assistant
        and last_assistant.startswith(MSG["ask_new_date"][lang][:8])
    ):
        f = _upcoming_field(phone, today)
        if f is not None and draft.harvest:
            moved = call("reschedule", tools.reschedule, phone, f.field_id, draft.harvest.isoformat())
            return _result_text(moved, farmer.name if farmer else "", f.acres, lang)

    if _STATUS.search(text) and nothing_new:
        bookings = [
            b
            for b in call("get_my_bookings", tools.get_my_bookings, phone)["bookings"]
            if b["status"] == "CONFIRMED"
        ]
        if not bookings:
            return t("no_bookings", lang)
        items = ", ".join(
            fmt_date(date.fromisoformat(b["pickup_date"]), lang) + f" ({b['acres']:g})" for b in bookings
        )
        return t("status", lang, items=items)

    if nothing_new and draft.village_unknown is None and not draft.village_options:
        if farmer is None and last_assistant is None:
            return t("intro", lang)
        if asked_slot(last_assistant) is None:
            return t("off_topic", lang)

    # fill from the profile of a registered farmer
    name = draft.name or (farmer.name if farmer else None)
    village_id = draft.village_id or (farmer.village_id if farmer else None)

    if not name:
        return t("ask_name", lang)
    if not village_id:
        if draft.village_options:
            return t("village_pick", lang, options=" / ".join(draft.village_options))
        if draft.village_unknown:
            return t("village_unknown", lang, name=draft.village_unknown)
        return t("ask_village", lang)
    if draft.acres is None:
        return t("ask_acres", lang)
    if draft.harvest is None:
        return t("ask_date", lang)

    language = {HI: "hi", HINGLISH: "hi", PA: "pa", EN: "en"}[lang]
    if farmer is None or farmer.name != name or (draft.village_id and farmer.village_id != draft.village_id):
        reg = call("register_farmer", tools.register_farmer, phone, name, village_id, language)
        if not reg.get("ok"):
            return t("bad_input", lang, problem=reg.get("message", ""))
    fld = call(
        "register_field", tools.register_field, phone, draft.acres, draft.harvest.isoformat(), village_id
    )
    if not fld.get("ok"):
        return t("bad_input", lang, problem=fld.get("message", ""))
    booked = call("book_pickup", tools.book_pickup, phone, fld["field_id"])
    return _result_text(booked, name, draft.acres, lang)


def _result_text(result: dict[str, Any], name: str, acres: float, lang: str) -> str:
    if result.get("ok") and result.get("pickup_date"):
        return _booked_text(result, name, acres, lang)
    if result.get("error") == "no_slot":
        return t("no_slot", lang)
    return t("bad_input", lang, problem=result.get("message", ""))


def _booked_text(result: dict[str, Any], name: str, acres: float, lang: str) -> str:
    return t(
        "booked",
        lang,
        name=name,
        acres=f"{acres:g}",
        date=fmt_date(date.fromisoformat(result["pickup_date"]), lang),
        operator=result.get("operator_name") or "-",
        money=_money(result, lang),
    )
