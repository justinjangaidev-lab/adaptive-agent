from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BuiltinTool, ToolResult

if TYPE_CHECKING:
    from memory import Memory


class ListGeneratedToolsTool(BuiltinTool):
    name = "list_generated_tools"
    description = "저장된 동적 생성 툴 목록을 반환합니다."

    def __init__(self, memory: "Memory"):
        self._memory = memory

    def run(self, input_data: str = "") -> ToolResult:
        tools = self._memory.list_tools()
        if not tools:
            return ToolResult(success=True, output="저장된 툴이 없습니다.")
        lines = [f"저장된 툴 {len(tools)}개:"]
        for t in tools:
            lines.append(f"  • {t['name']}: {t['description']}")
        return ToolResult(success=True, output="\n".join(lines))


class LoadGeneratedToolTool(BuiltinTool):
    name = "load_generated_tool"
    description = "이름으로 저장된 툴의 코드를 불러옵니다."

    def __init__(self, memory: "Memory"):
        self._memory = memory

    def run(self, input_data: str) -> ToolResult:
        name = input_data.strip()
        tool = self._memory.load_tool(name)
        if tool is None:
            return ToolResult(success=False, output=f"툴 '{name}' 을 찾을 수 없습니다.")
        return ToolResult(success=True, output=tool["code"])
