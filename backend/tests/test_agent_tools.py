import pytest

from app.agent.tools import ToolExecutor


@pytest.mark.asyncio
async def test_unknown_agent_tool_is_rejected_without_execution():
    result = await ToolExecutor(db=None, context={}).execute("invent_discount", {})
    assert "not available" in result["error"]
