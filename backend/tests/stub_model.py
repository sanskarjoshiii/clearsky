"""A scripted Strands model for tests: emits Bedrock-style stream events, never calls AWS."""

from __future__ import annotations

import ast
import itertools
import json
from collections.abc import AsyncGenerator, Callable
from typing import Any

from strands.models.model import Model

Step = dict[str, Any] | Callable[[list[dict[str, Any]]], dict[str, Any]]
_ids = itertools.count(1)


def say(text: str) -> dict[str, Any]:
    return {"text": text}


def call(tool_name: str, /, **args: Any) -> dict[str, Any]:
    return {"tools": [(tool_name, args)]}


def last_tool_result(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """The most recent toolResult payload as a dict (Strands may wrap it as json or text)."""
    for msg in reversed(messages):
        for block in reversed(msg.get("content", [])):
            tr = block.get("toolResult")
            if not tr:
                continue
            for c in tr.get("content", []):
                if "json" in c:
                    return dict(c["json"])
                if "text" in c:
                    try:
                        return dict(json.loads(c["text"]))
                    except ValueError:
                        return dict(ast.literal_eval(c["text"]))
    raise AssertionError("no tool result in messages")


class ScriptedModel(Model):
    def __init__(self, steps: list[Step]):
        self.steps = list(steps)
        self.seen: list[dict[str, Any]] = []

    def update_config(self, **model_config: Any) -> None:
        return None

    def get_config(self) -> dict[str, Any]:
        return {}

    def structured_output(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def stream(
        self,
        messages: list[Any],
        tool_specs: list[Any] | None = None,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        self.seen.append({"messages": messages, "tool_specs": tool_specs, "system_prompt": system_prompt})
        if not self.steps:
            raise AssertionError("script exhausted")
        step = self.steps.pop(0)
        if callable(step):
            step = step(messages)
        yield {"messageStart": {"role": "assistant"}}
        if "tools" in step:
            for name, args in step["tools"]:
                yield {
                    "contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{next(_ids)}", "name": name}}}
                }
                yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
                yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": step["text"]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}


class FailingModel(ScriptedModel):
    def __init__(self) -> None:
        super().__init__([])

    async def stream(self, *args: Any, **kwargs: Any) -> AsyncGenerator[dict[str, Any], None]:
        raise RuntimeError("bedrock throttled")
        yield {}  # pragma: no cover
