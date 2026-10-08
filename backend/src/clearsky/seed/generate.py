"""Deterministic demo seed for Sangrur district (IMPLEMENTATION.md §14).

PROPOSED village list, pending team confirmation. Every coordinate is an approximation (town
coordinates plus small offsets for villages) and is flagged `approx=true` until geocoded with
Amazon Location. Buyers are fictional. Farmers are synthetic (`synthetic=true`): their phone numbers
are placeholders and must never receive real WhatsApp messages. Balers have no operator phone.
"""

from __future__ import annotations

import json
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from clearsky.config import REPO_ROOT
from clearsky.domain.geo import jitter_point, offset_point
from clearsky.models import Baler, Buyer, BuyerType, Farmer, Field, FieldStatus, Language, Village
from clearsky.models.dynamo import from_dynamo

SEED_DIR = REPO_ROOT / "data" / "seed"
DEFAULT_SEED = 42
REFERENCE_DATE = date(2026, 10, 20)  # demo "today" the seed is built around (runbook starts here)
DISTRICT = "Sangrur"

# (village_id, name, name_hi, name_pa, aliases, block, lat, lng) — approximate town centres.
TOWNS: list[tuple[str, str, str, str, list[str], str, float, float]] = [
    ("V001", "Sangrur", "संगरूर", "ਸੰਗਰੂਰ", ["sangroor", "sangrur city"], "Sangrur", 30.2458, 75.8421),
    (
        "V002",
        "Bhawanigarh",
        "भवानीगढ़",
        "ਭਵਾਨੀਗੜ੍ਹ",
        ["bhavanigarh", "bhawanigadh", "bhawani garh"],
        "Bhawanigarh",
        30.2660,
        76.0390,
    ),
    ("V003", "Sunam", "सुनाम", "ਸੁਨਾਮ", ["sunaam", "sunam udham singh wala"], "Sunam", 30.1290, 75.7990),
    ("V004", "Dhuri", "धूरी", "ਧੂਰੀ", ["dhoori"], "Dhuri", 30.3690, 75.8680),
    ("V005", "Dirba", "दिड़बा", "ਦਿੜ੍ਹਬਾ", ["dirbha", "dhirba", "dirba mandi"], "Dirba", 30.0730, 75.9990),
    (
        "V006",
        "Lehragaga",
        "लहरागागा",
        "ਲਹਿਰਾਗਾਗਾ",
        ["lehra gaga", "lehra", "lehragagga"],
        "Lehragaga",
        29.9470,
        75.9670,
    ),
    ("V007", "Moonak", "मूनक", "ਮੂਣਕ", ["munak", "moonak mandi"], "Moonak", 29.8300, 76.1000),
    ("V008", "Longowal", "लोंगोवाल", "ਲੌਂਗੋਵਾਲ", ["longoval", "longowaal"], "Sunam", 30.2130, 75.6840),
    ("V009", "Cheema", "चीमा", "ਚੀਮਾ", ["cheema mandi", "chima"], "Sunam", 30.1720, 75.6250),
    ("V010", "Khanauri", "खनौरी", "ਖਨੌਰੀ", ["khanori", "khanauri mandi"], "Moonak", 29.8230, 76.3130),
]

# (village_id, name, name_hi, name_pa, aliases, block, anchor village_id, km north, km east)
VILLAGES: list[tuple[str, str, str, str, list[str], str, str, float, float]] = [
    ("V011", "Balad Kalan", "बलद कलां", "ਬਲਦ ਕਲਾਂ", ["balad", "balad kalan"], "Bhawanigarh", "V002", 4, -3),
    ("V012", "Gharachon", "घराचों", "ਘਰਾਚੋਂ", ["gharacho", "gharachon"], "Bhawanigarh", "V002", -5, 2),
    ("V013", "Phagguwala", "फग्गूवाला", "ਫੱਗੂਵਾਲਾ", ["phaguwala", "fagguwala"], "Bhawanigarh", "V002", 3, 5),
    ("V014", "Kakra", "काकड़ा", "ਕਾਕੜਾ", ["kakda", "kakra"], "Bhawanigarh", "V002", -2, -6),
    ("V015", "Nadampur", "नदामपुर", "ਨਦਾਮਪੁਰ", ["nadampur"], "Bhawanigarh", "V002", 6, 2),
    ("V016", "Jhaneri", "झनेड़ी", "ਝਨੇੜੀ", ["jhaneri", "jhanedi"], "Bhawanigarh", "V002", 1, 7),
    ("V017", "Balian", "बालियां", "ਬਾਲੀਆਂ", ["baliyan", "balian"], "Sangrur", "V001", 3, 4),
    ("V018", "Ghabdan", "घाबदां", "ਘਾਬਦਾਂ", ["ghabdan", "ghabdaan"], "Sangrur", "V001", 5, -3),
    ("V019", "Ubhawal", "उभावाल", "ਉਭਾਵਾਲ", ["ubhawal", "ubhaval"], "Sangrur", "V001", -4, 3),
    ("V020", "Badrukhan", "बडरुखां", "ਬਡਰੁੱਖਾਂ", ["badrukhan", "badrukhaan"], "Sangrur", "V001", -3, -4),
    ("V021", "Mangwal", "मंगवाल", "ਮੰਗਵਾਲ", ["mangwal", "mangval"], "Sangrur", "V001", 2, -5),
    ("V022", "Mehlan", "महलां", "ਮਹਿਲਾਂ", ["mehlan", "mahlan", "mehlan chowk"], "Sangrur", "V001", -5, -2),
    ("V023", "Ugrahan", "उगराहां", "ਉਗਰਾਹਾਂ", ["ugrahan", "ugraha"], "Sunam", "V003", 3, 3),
    ("V024", "Sheron", "शेरों", "ਸ਼ੇਰੋਂ", ["sheron", "shero"], "Sunam", "V003", -4, -3),
    ("V025", "Chhajli", "छाजली", "ਛਾਜਲੀ", ["chajli", "chhajli"], "Sunam", "V003", -6, 6),
    ("V026", "Jakhepal", "जखेपल", "ਜਖੇਪਲ", ["jakhepal", "jakhepall"], "Sunam", "V003", -7, 1),
    ("V027", "Benra", "बेनड़ा", "ਬੇਨੜਾ", ["benda", "benra"], "Dhuri", "V004", 3, -2),
    ("V028", "Ghanauri Kalan", "घनौरी कलां", "ਘਨੌਰੀ ਕਲਾਂ", ["ghanauri", "ghanori kalan"], "Dhuri", "V004", 5, 4),
    ("V029", "Bhalwan", "भलवान", "ਭਲਵਾਨ", ["bhalwan", "bhalvan"], "Dhuri", "V004", -3, 4),
    ("V030", "Lehal Kalan", "लेहल कलां", "ਲਹਿਲ ਕਲਾਂ", ["lehal", "lehal kalan"], "Lehragaga", "V006", 4, 3),
    ("V031", "Rogla", "रोगला", "ਰੋਗਲਾ", ["rogla"], "Dirba", "V005", 3, -3),
]

BALER_BASES = ["V002", "V011", "V001", "V018", "V003", "V024", "V004", "V005", "V006", "V007"]
OPERATOR_FIRST = [
    "Gurdeep",
    "Harpreet",
    "Jaswinder",
    "Kuldeep",
    "Manjit",
    "Paramjit",
    "Rajinder",
    "Sukhwinder",
    "Balwinder",
    "Hardeep",
    "Lakhwinder",
    "Satnam",
    "Amarjit",
    "Baljit",
    "Charanjit",
    "Davinder",
    "Gurmeet",
    "Iqbal",
    "Jagdeep",
    "Navdeep",
]
SURNAMES = ["Singh", "Sidhu", "Dhillon", "Gill", "Grewal", "Sandhu", "Brar", "Mann", "Cheema", "Virk"]

BUYERS: list[dict[str, Any]] = [
    # Fictional buyers with demo prices (₹/tonne). Never use real company names.
    {
        "buyer_id": "BY01",
        "name": "Demo Pellet Plant",
        "type": BuyerType.PELLET,
        "anchor": "V001",
        "off": (8, 6),
        "price_per_tonne": 1700.0,
        "demand_tonnes": 3000.0,
        "max_radius_km": 60.0,
    },
    {
        "buyer_id": "BY02",
        "name": "Demo CBG Plant",
        "type": BuyerType.CBG,
        "anchor": "V006",
        "off": (5, -6),
        "price_per_tonne": 1500.0,
        "demand_tonnes": 4000.0,
        "max_radius_km": 50.0,
    },
    {
        "buyer_id": "BY03",
        "name": "Demo Boiler Unit",
        "type": BuyerType.BOILER,
        "anchor": "V004",
        "off": (-4, 8),
        "price_per_tonne": 1900.0,
        "demand_tonnes": 1500.0,
        "max_radius_km": 40.0,
    },
]


def build_villages() -> list[Village]:
    out = [
        Village(
            village_id=vid,
            name=n,
            name_hi=hi,
            name_pa=pa,
            aliases=al,
            block=blk,
            district=DISTRICT,
            lat=lat,
            lng=lng,
            approx=True,
        )
        for vid, n, hi, pa, al, blk, lat, lng in TOWNS
    ]
    by_id = {v.village_id: v for v in out}
    for vid, n, hi, pa, al, blk, anchor, north, east in VILLAGES:
        a = by_id[anchor]
        lat, lng = offset_point(a.lat, a.lng, north, east)
        out.append(
            Village(
                village_id=vid,
                name=n,
                name_hi=hi,
                name_pa=pa,
                aliases=al,
                block=blk,
                district=DISTRICT,
                lat=lat,
                lng=lng,
                approx=True,
            )
        )
    return out


def build_balers(rng: random.Random, villages: dict[str, Village]) -> list[Baler]:
    balers = []
    for i, vid in enumerate(BALER_BASES, start=1):
        v = villages[vid]
        lat, lng = jitter_point(v.lat, v.lng, 1.0, rng)
        balers.append(
            Baler(
                baler_id=f"B{i:02d}",
                operator_name=f"{OPERATOR_FIRST[i - 1]} {rng.choice(SURNAMES)}",
                operator_phone=None,
                chc_name=f"{v.name} Custom Hiring Centre (demo)",
                base_village_id=vid,
                lat=lat,
                lng=lng,
                acres_per_day=float(rng.randint(12, 20)),
                radius_km=float(rng.randint(15, 25)),
                active=True,
            )
        )
    return balers


def build_buyers(villages: dict[str, Village]) -> list[Buyer]:
    out = []
    for b in BUYERS:
        a = villages[b["anchor"]]
        lat, lng = offset_point(a.lat, a.lng, *b["off"])
        out.append(
            Buyer(
                buyer_id=b["buyer_id"],
                name=b["name"],
                type=b["type"],
                lat=lat,
                lng=lng,
                price_per_tonne=b["price_per_tonne"],
                demand_tonnes=b["demand_tonnes"],
                max_radius_km=b["max_radius_km"],
            )
        )
    return out


def build_farmers_and_fields(
    rng: random.Random, villages: list[Village], n_fields: int, ref: date
) -> tuple[list[Farmer], list[Field], list[str], list[str]]:
    """Returns farmers, fields, field_ids to pre-book, and RED-candidate field_ids."""
    created = datetime.combine(ref - timedelta(days=10), time(9, 0))
    farmers: list[Farmer] = []
    fields: list[Field] = []
    prebook: list[str] = []
    red: list[str] = []
    n_red = 10
    for i in range(n_fields):
        v = villages[rng.randrange(len(villages))]
        phone = f"+9199999{i + 1:05d}"
        farmers.append(
            Farmer(
                phone=phone,
                name=f"{rng.choice(OPERATOR_FIRST)} {rng.choice(SURNAMES)}",
                village_id=v.village_id,
                language=rng.choice([Language.HINDI, Language.HINDI, Language.PUNJABI]),
                synthetic=True,
                created_at=created,
            )
        )
        acres = float(rng.randint(2, 15))
        lat, lng = jitter_point(v.lat, v.lng, 1.5, rng)
        if i < n_red:
            # Harvested 3–8 days ago, unbooked, farmer plans to sow soon → RED candidates for Phase 6.
            harvest = ref - timedelta(days=rng.randint(3, 8))
            deadline = ref + timedelta(days=rng.randint(3, 6))  # urgent but still bookable
            status, confirmed = FieldStatus.HARVESTED, True
            red.append(f"F-SEED-{i + 1:03d}")
        else:
            harvest = date(2026, 10, 15) + timedelta(days=rng.randint(0, 21))  # Oct 15 – Nov 5
            deadline = min(harvest + timedelta(days=20), date(2026, 11, 15))
            harvested = harvest <= ref
            status = FieldStatus.HARVESTED if harvested else FieldStatus.REGISTERED
            confirmed = harvest < ref
        field_id = f"F-SEED-{i + 1:03d}"
        fields.append(
            Field(
                field_id=field_id,
                phone=phone,
                village_id=v.village_id,
                acres=acres,
                lat=lat,
                lng=lng,
                harvest_date=harvest,
                sowing_deadline=deadline,
                harvest_confirmed=confirmed,
                status=status,
                source="seed",
                created_at=created,
                updated_at=created,
            )
        )
        if i >= n_red and rng.random() < 0.35:
            prebook.append(field_id)
    return farmers, fields, prebook, red


def generate(seed: int = DEFAULT_SEED, n_fields: int = 60, ref: date = REFERENCE_DATE) -> dict[str, Any]:
    rng = random.Random(seed)
    villages = build_villages()
    by_id = {v.village_id: v for v in villages}
    balers = build_balers(rng, by_id)
    buyers = build_buyers(by_id)
    farmers, fields, prebook, red = build_farmers_and_fields(rng, villages, n_fields, ref)
    dump = lambda ms: [m.model_dump(mode="json", exclude_none=True) for m in ms]  # noqa: E731
    return {
        "villages": dump(villages),
        "balers": dump(balers),
        "buyers": dump(buyers),
        "farmers": dump(farmers),
        "fields": dump(fields),
        "meta": {
            "seed": seed,
            "reference_date": ref.isoformat(),
            "district": DISTRICT,
            "prebook_field_ids": prebook,
            "red_candidate_field_ids": red,
            "notes": [
                "Village list is a proposal pending team confirmation; coordinates are approximate (approx=true).",
                "Buyers are fictional; prices are demo values.",
                "Farmers are synthetic placeholders (synthetic=true) and must never be messaged.",
            ],
        },
    }


def write(data: dict[str, Any], out_dir: Path = SEED_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rows in data.items():
        p = out_dir / f"{name}.json"
        p.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        paths.append(p)
    return paths


def read(in_dir: Path = SEED_DIR) -> dict[str, Any]:
    names = ["villages", "balers", "buyers", "farmers", "fields", "meta"]
    return {n: from_dynamo(json.loads((in_dir / f"{n}.json").read_text(encoding="utf-8"))) for n in names}
