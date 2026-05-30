import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass


@dataclass
class RunResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def success(self) -> bool:
        return self.returncode == 0


# 생성된 툴 코드를 격리 subprocess에서 실행하기 위한 래퍼 템플릿.
# Wrapper template that runs generated tool code in an isolated subprocess.
_RUNNER_TEMPLATE = """\
import sys as _sys

{tool_code}

if __name__ == "__main__":
    _input = {input_repr}
    try:
        _result = run(_input)
        if _result is None:
            print("(완료)")
        else:
            print(str(_result), end="")
    except Exception:
        import traceback
        traceback.print_exc()
        _sys.exit(1)
"""


def execute(tool_code: str, input_data: str = "", timeout: int = 30) -> RunResult:
    """격리된 subprocess에서 tool_code의 run(input_data) 함수를 실행한다.
    stdout, stderr, returncode를 반환한다.
    Execute tool_code's run(input_data) function in an isolated subprocess.
    Returns stdout, stderr, and returncode."""
    script = _RUNNER_TEMPLATE.format(
        tool_code=tool_code,
        input_repr=repr(input_data),
    )

    # 임시 파일에 스크립트를 기록하고 subprocess로 실행한 뒤 삭제한다.
    # Write the script to a temp file, run it as a subprocess, then delete it.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(script)
        tmp = f.name

    try:
        proc = subprocess.run(
            [sys.executable, tmp],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return RunResult(
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return RunResult(
            stdout="",
            stderr=f"실행 시간 초과 ({timeout}초).",
            returncode=-1,
        )
    finally:
        os.unlink(tmp)
