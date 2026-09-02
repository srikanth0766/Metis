"""
AI Recovery Agent — Groq-backed conversation loop.

Flow:
    customer message
        → Groq (Llama 3.3 70B)
        → tool selection
        → policy validation (inside ToolExecutor)
        → tool execution
        → result injected back to Groq
        → final reply

The agent loop is intentionally simple Python — no agent framework dependency.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.system_prompt import SYSTEM_PROMPT
from app.agent.tools import TOOL_SCHEMAS, ToolExecutor
from app.core.config import get_settings
from app.models.models import AgentRunStatus

logger = logging.getLogger(__name__)

settings = get_settings()

MAX_TOOL_ROUNDS = 8  # safety cap — prevents infinite loops


class AgentRunner:
    """
    Runs a full recovery conversation for one AgentRun.

    Usage:
        runner = AgentRunner(db, run_id, context)
        reply = await runner.step(customer_message)
    """

    def __init__(
        self,
        db: AsyncSession,
        run_id: str,
        context: dict[str, Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> None:
        self.db = db
        self.run_id = run_id
        self.context = context
        self.history: list[dict[str, Any]] = conversation_history or []
        self._client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self._executor = ToolExecutor(db=db, context=context)

    async def step(self, customer_message: str) -> tuple[str, AgentRunStatus]:
        """
        Process one customer message turn.

        Returns:
            (agent_reply: str, new_status: AgentRunStatus)
        """
        self.history.append({"role": "user", "content": customer_message})

        context_str = (
            f"\n\nCURRENT SESSION CONTEXT:\n"
            f"- Case ID: {self.context.get('case_id')}\n"
            f"- Customer ID: {self.context.get('customer_id')}\n"
            f"- Payment ID: {self.context.get('payment_id')}\n"
            f"- Merchant ID: {self.context.get('merchant_id')}\n"
            f"- Amount: {self.context.get('amount')}\n"
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_str}] + self.history

        tool_rounds = 0
        while tool_rounds < MAX_TOOL_ROUNDS:
            response = await self._client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=1024,
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls":
                tool_calls = choice.message.tool_calls or []
                messages.append(choice.message)  # type: ignore[arg-type]

                for tc in tool_calls:
                    arguments = json.loads(tc.function.arguments)
                    tool_name = tc.function.name

                    logger.info("Agent calling tool: %s(%s)", tool_name, arguments)
                    raw_result = await self._executor.execute(tool_name, arguments)
                    result = self._clean(raw_result)

                    await self._persist_tool_call(tool_name, arguments, result)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        }
                    )

                    # Detect escalation
                    if tool_name == "escalate_to_human":
                        reply = "I'm connecting you with one of our specialists who can help further."
                        self.history.append({"role": "assistant", "content": reply})
                        return reply, AgentRunStatus.ESCALATED

                tool_rounds += 1
                continue

            # finish_reason == "stop" — we have the final reply
            reply: str = choice.message.content or ""
            self.history.append({"role": "assistant", "content": reply})
            return reply, AgentRunStatus.RUNNING

        # Exceeded max tool rounds — safety fallback
        logger.warning("Agent exceeded max tool rounds for run %s — escalating.", self.run_id)
        fallback = "I need to connect you with a specialist to resolve this. Please hold on."
        self.history.append({"role": "assistant", "content": fallback})
        return fallback, AgentRunStatus.ESCALATED

    @staticmethod
    def _clean(val: Any) -> Any:
        if isinstance(val, Decimal):
            return float(val)
        if hasattr(val, "isoformat"):
            return val.isoformat()
        if isinstance(val, dict):
            return {k: AgentRunner._clean(v) for k, v in val.items()}
        if isinstance(val, list):
            return [AgentRunner._clean(v) for v in val]
        return val

    async def _persist_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        """Write tool call to agent_tool_calls for audit trail."""
        from app.models.models import AgentToolCall

        policy_status = "BLOCKED" if result.get("policy_blocked") else "ALLOWED"
        tc = AgentToolCall(
            run_id=self.run_id,
            tool_name=tool_name,
            arguments=self._clean(arguments),
            result=self._clean(result),
            policy_status=policy_status,
        )
        self.db.add(tc)
        await self.db.flush()
