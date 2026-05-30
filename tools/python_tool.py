from sandbox import RunResult, execute
from .base import BuiltinTool, ToolResult


class PythonExecutorTool(BuiltinTool):
    """sandbox를 통해 동적으로 생성된 Python 코드를 실행한다.
    Executes dynamically generated Python code via the sandbox.
    코드는 반드시 run(input_data: str) -> str 함수를 정의해야 한다.
    The code must define a run(input_data: str) -> str function."""

    name = "python_executor"
    description = "동적으로 생성된 Python 코드를 격리 서브프로세스에서 실행합니다."

    def run(self, input_data: str) -> ToolResult:
        # 직접 호출하지 말고 sandbox.execute()를 사용할 것.
        # Do not call directly — use sandbox.execute(tool_code, input_data) instead.
        raise NotImplementedError("Use sandbox.execute(tool_code, input_data) directly.")

    @staticmethod
    def execute(tool_code: str, input_data: str = "", timeout: int = 30) -> RunResult:
        return execute(tool_code, input_data, timeout)
