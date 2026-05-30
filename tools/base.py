from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    output: str


class BuiltinTool(ABC):
    """내장 (비생성) 툴의 기반 클래스. / Base class for built-in (non-generated) tools."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, input_data: str) -> ToolResult:
        ...
