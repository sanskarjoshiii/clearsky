"""Phase 0: check AWS readiness for every service ClearSky needs. Prints a ✅/❌ table.

All checks are read-only and free, except `--invoke-llm`, which sends one tiny prompt to the
configured LLM (a few tokens, billed). Usage:  uv run python scripts/check_aws.py [--invoke-llm]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Callable

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from clearsky.config import get_settings

Row = tuple[str, bool, str]


def _try(name: str, fn: Callable[[], str]) -> Row:
    try:
        return (name, True, fn())
    except (ClientError, BotoCoreError, RuntimeError, KeyError, Exception) as e:
        return (name, False, str(e).splitlines()[0][:140])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--invoke-llm", action="store_true", help="send one tiny billed prompt to the configured LLM"
    )
    args = p.parse_args()
    s = get_settings()
    region = s.aws_region
    rows: list[Row] = []

    def identity() -> str:
        ident = boto3.client("sts", region_name=region).get_caller_identity()
        return f"account {ident['Account']} as {ident['Arn'].split('/')[-1]}"

    rows.append(_try("AWS credentials", identity))
    rows.append(("Region", True, region))

    def llm_config() -> str:
        from clearsky.agent import llm

        p = llm.provider()
        if p == "rules":
            return "rules bot (no LLM needed); set LLM_PROVIDER to use an LLM"
        if p == "bedrock":
            if not s.bedrock_model_id:
                raise RuntimeError("BEDROCK_MODEL_ID not set (team must choose one)")
            client = boto3.client("bedrock", region_name=region)
            mid = s.bedrock_model_id
            if mid.split(".")[0] in ("global", "apac", "in", "us", "eu"):
                prof = client.get_inference_profile(inferenceProfileIdentifier=mid)
                return f"bedrock inference profile {prof['inferenceProfileId']} ({prof['status']})"
            model = client.get_foundation_model(modelIdentifier=mid)["modelDetails"]
            return f"bedrock model {model['modelId']}"
        llm.build_model()  # raises with a fix-it message if the model id or key is missing
        return f"{llm.describe()} (key present)"

    rows.append(_try("LLM provider", llm_config))

    if args.invoke_llm:

        def ping() -> str:
            from strands import Agent

            from clearsky.agent import llm

            agent = Agent(model=llm.build_model(), callback_handler=None)
            return "reply: " + str(agent("Reply with the single word: pong")).strip()[:40]

        rows.append(_try("LLM invoke (billed)", ping))
    else:
        rows.append(("LLM invoke", True, "skipped (pass --invoke-llm to send one tiny billed prompt)"))

    def transcribe() -> str:
        if s.stt_provider != "transcribe":
            return f"not used (STT_PROVIDER={s.stt_provider})"
        boto3.client("transcribe", region_name=region).list_transcription_jobs(MaxResults=1)
        return f"reachable; language {s.transcribe_language}"

    rows.append(_try("Transcribe", transcribe))

    def polly() -> str:
        # Kajal/Aditi are listed as en-IN voices with hi-IN as an additional (bilingual) language.
        voices = boto3.client("polly", region_name=region).describe_voices(
            IncludeAdditionalLanguageCodes=True
        )["Voices"]
        v = next((v for v in voices if v["Id"] == s.polly_voice), None)
        langs = [v["LanguageCode"], *v.get("AdditionalLanguageCodes", [])] if v else []
        if v is None or "hi-IN" not in langs:
            raise RuntimeError(f"voice {s.polly_voice} not available for hi-IN")
        if s.polly_engine not in v.get("SupportedEngines", []):
            raise RuntimeError(f"{s.polly_voice} lacks engine {s.polly_engine}: {v.get('SupportedEngines')}")
        return f"{s.polly_voice} ({s.polly_engine})"

    rows.append(_try("Polly hi-IN voice", polly))

    def location() -> str:
        loc = boto3.client("location", region_name=region)
        maps = loc.list_maps(MaxResults=10).get("Entries", [])
        idx = loc.list_place_indexes(MaxResults=10).get("Entries", [])
        return f"reachable; {len(maps)} map(s), {len(idx)} place index(es)"

    rows.append(_try("Location Service", location))
    # Not a blocker: make.ps1 runs SAM through `uv tool run --from aws-sam-cli sam` when it isn't installed.
    rows.append(("SAM CLI", True, shutil.which("sam") or "not on PATH; make.ps1 runs it via uv tool run"))
    rows.append(("Python", sys.version_info[:2] == (3, 12), sys.version.split()[0]))

    width = max(len(r[0]) for r in rows)
    for name, ok, detail in rows:
        print(f"{'✅' if ok else '❌'}  {name.ljust(width)}  {detail}")
    return 0 if all(ok for _, ok, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
