import json
from pathlib import Path

from .base import BuiltinTool, ToolResult


class ReadFileTool(BuiltinTool):
    name = "read_file"
    description = "로컬 파일의 텍스트 내용을 읽습니다. input: 파일 경로"

    def run(self, input_data: str) -> ToolResult:
        path = input_data.strip()
        try:
            content = Path(path).read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except Exception as exc:
            return ToolResult(success=False, output=f"파일 읽기 실패 '{path}': {exc}")


class WriteFileTool(BuiltinTool):
    name = "write_file"
    description = "로컬 파일에 텍스트를 씁니다. input: JSON {\"path\":\"...\",\"content\":\"...\"}"

    def run(self, input_data: str) -> ToolResult:
        try:
            data = json.loads(input_data)
            path = data["path"]
            content = data["content"]
            Path(path).write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"'{path}' 에 {len(content)}자 기록 완료.")
        except Exception as exc:
            return ToolResult(success=False, output=f"파일 쓰기 실패: {exc}")


class ListFilesTool(BuiltinTool):
    name = "list_files"
    description = "디렉토리의 파일 목록을 반환합니다. input: 디렉토리 경로 (기본값 '.')"

    def run(self, input_data: str) -> ToolResult:
        directory = input_data.strip() or "."
        try:
            files = sorted(Path(directory).iterdir())
            if not files:
                return ToolResult(success=True, output="파일 없음.")
            lines = [str(f) for f in files]
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as exc:
            return ToolResult(success=False, output=f"디렉토리 조회 실패: {exc}")
