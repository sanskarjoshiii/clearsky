"""Talk to the farmer agent from the terminal (no WhatsApp needed).

  uv run python scripts/chat_cli.py --local --phone +919900000001 --today 2026-10-20 --debug
  --local       in-process mock DynamoDB loaded with the seed (no deploy needed; Bedrock is still real)
  --today       simulated date (default: the clock, or 2026-10-20 with --local)
  --debug       print every tool call and result
  --transcript  append the session to a Markdown file (e.g. docs/agent_transcripts.md)
  --model-id    override BEDROCK_MODEL_ID for this session
Type /quit to exit, /reset to forget the conversation history for this phone.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--phone", default="+919900000001", help="sender phone (E.164); use a test number")
    p.add_argument("--today", type=date.fromisoformat, default=None)
    p.add_argument("--local", action="store_true")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--transcript", type=Path, default=None)
    p.add_argument("--title", default="", help="heading for the transcript section")
    p.add_argument("--model-id", default=None)
    p.add_argument("-m", "--message", action="append", default=[], help="send these messages, then exit")
    args = p.parse_args()

    if args.model_id:
        os.environ["BEDROCK_MODEL_ID"] = args.model_id
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # Devanagari/Gurmukhi on Windows consoles

    from clearsky import clock
    from clearsky.config import get_settings, reset_settings

    reset_settings()
    server = None
    if args.local:
        from clearsky.local import start_local_dynamodb

        server, summary = start_local_dynamodb()
        print(f"[local] mock DynamoDB ready, seed loaded: {summary}")
        args.today = args.today or date(2026, 10, 20)
    if args.today:
        clock.set_override(args.today)

    from clearsky.agent.agent import AgentConfigError, run_turn
    from clearsky.agent.prompts import BOT_NAME
    from clearsky.repo import ConversationsRepo
    from clearsky.repo.base import table

    s = get_settings()
    print(
        f"{BOT_NAME} chat · phone {args.phone} · today {clock.today()} · model {s.bedrock_model_id or '(unset)'}"
    )
    log: list[str] = []

    def handle(text: str) -> bool:
        if text in ("/quit", "/exit"):
            return False
        if text == "/reset":
            t = table("Conversations")
            for turn in ConversationsRepo().last(args.phone, 1000):
                t.delete_item(Key={"phone": args.phone, "ts": turn.ts})
            print("(history cleared)")
            return True
        try:
            reply = run_turn(args.phone, text)
        except AgentConfigError as e:
            print(f"❌ {e}  (pass --model-id or set BEDROCK_MODEL_ID in .env)")
            return False
        if args.debug:
            for c in reply.tool_calls:
                print(
                    f"  ⚙ {c.name}({json.dumps(c.args, ensure_ascii=False)}) → "
                    f"{json.dumps(c.result, ensure_ascii=False, default=str)[:300]}"
                )
        print(f"🌾 {reply.text}   ({reply.latency_ms} ms)")
        log.extend([f"**Farmer:** {text}", f"**ClearSky:** {reply.text}"])
        if reply.tool_calls:
            log.append("<sub>tools: " + ", ".join(c.name for c in reply.tool_calls) + "</sub>")
        return True

    try:
        if args.message:
            for m in args.message:
                print(f"👨‍🌾 {m}")
                if not handle(m):
                    break
        else:
            while True:
                try:
                    text = input("👨‍🌾 ").strip()
                except EOFError:
                    break
                if text and not handle(text):
                    break
    finally:
        if args.transcript and log:
            args.transcript.parent.mkdir(parents=True, exist_ok=True)
            with args.transcript.open("a", encoding="utf-8") as fh:
                fh.write(
                    f"\n## {args.title or 'Session'} (today {clock.today()}, model {s.bedrock_model_id})\n\n"
                )
                fh.write("\n\n".join(log) + "\n")
            print(f"(transcript appended to {args.transcript})")
        if server is not None:
            server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
