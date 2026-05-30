import json
import re

from llm import LLMClient
from memory import Memory
from prompts import build_system_prompt
from sandbox import execute
from tools import ListFilesTool, ReadFileTool, WriteFileTool

MAX_RETRIES = 3


# ── JSON 파싱 / JSON parsing ──────────────────────────────────────────────────

def _parse_json(text: str) -> dict | None:
    """LLM 응답을 JSON으로 파싱한다. 마크다운 펜스와 부분 래핑을 처리한다.
    Parse LLM response as JSON. Handles markdown fences and partial wrapping."""
    text = text.strip()

    # 1. 직접 파싱 시도 / Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. ```json ... ``` 또는 ``` ... ``` 에서 추출 / Extract from ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 가장 바깥쪽 { ... } 탐색 / Find outermost { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


# ── 출력 헬퍼 / Display helpers ───────────────────────────────────────────────

def _print_code(code: str, label: str = "", max_lines: int = 40) -> None:
    if label:
        print(f"     {label}")
    lines = code.splitlines()
    for i, line in enumerate(lines[:max_lines], 1):
        print(f"  {i:3d} | {line}")
    if len(lines) > max_lines:
        print(f"       ... ({len(lines) - max_lines}줄 더)")


def _truncate(text: str, n: int = 300) -> str:
    text = text.strip()
    return text[:n] + " ..." if len(text) > n else text


# ── 에이전트 / Agent ──────────────────────────────────────────────────────────

class Agent:
    """
    핵심 에이전트 루프. / Core agent loop.

    턴당 흐름 / Flow per turn:
        생각 → (툴 생성 | 툴 수정 | 툴 실행 | 사용자 질문) → 최종 응답
        think → (create_tool | revise_tool | run_tool | ask_user) → final_answer

    LLM은 항상 다음 액션을 지정하는 JSON 객체를 반환한다.
    The LLM always returns a JSON object specifying the next action.
    툴 코드는 반드시 구현해야 한다: def run(input_data: str) -> str
    Tool code must implement:  def run(input_data: str) -> str
    """

    def __init__(self, llm: LLMClient, memory: Memory, input_fn=None):
        self.llm = llm
        self.memory = memory
        self._input = input_fn or (lambda prompt: input(prompt))
        self._builtin: dict = {
            t.name: t for t in [ReadFileTool(), WriteFileTool(), ListFilesTool()]
        }
        self._pending_saves: list[dict] = []

    # ── 공개 API / public API ─────────────────────────────────────────────────

    def run_turn(self, user_input: str) -> str:
        """사용자 입력 한 턴을 처리하고 최종 응답 문자열을 반환한다.
        Process one user turn and return the final answer string."""
        self.memory.add_user(user_input)
        self._pending_saves = []
        retries = 0

        while True:
            system = build_system_prompt(self.memory.list_tools())

            try:
                raw = self.llm.chat(self.memory.messages, system)
            except Exception as exc:
                return f"LLM 호출 오류: {exc}"

            self.memory.add_assistant(raw)
            parsed = _parse_json(raw)

            if parsed is None:
                # 폴백: 전체 응답을 최종 답변으로 처리 / Fallback: treat the whole response as a final answer
                print(f"\nAgent: {raw}")
                return raw

            thought = parsed.get("thought", "")
            action = parsed.get("action", "final_answer")
            message = parsed.get("message", "")

            if thought:
                print(f"\n  [생각] {thought}")

            # ── 사용자 질문 / ask_user ────────────────────────────────────────
            if action == "ask_user":
                print(f"\nAgent: {message}")
                try:
                    clarification = self._input("You: ").strip()
                except EOFError:
                    clarification = ""
                self.memory.add_user(clarification)
                retries = 0
                continue

            # ── 툴 생성 / 수정 / create_tool / revise_tool ────────────────────
            if action in ("create_tool", "revise_tool"):
                tool_name = parsed.get("tool_name", "unnamed_tool")
                tool_desc = parsed.get("tool_description", "")
                tool_code = parsed.get("tool_code", "")
                tool_input = parsed.get("tool_input", "")

                verb = "생성" if action == "create_tool" else "수정"
                print(f"\n  → 툴 {verb}: {tool_name}")
                _print_code(tool_code, tool_desc)

                result = execute(tool_code, tool_input)

                if result.success:
                    out = result.stdout.strip() or "(출력 없음)"
                    print(f"  ✓  {_truncate(out, 200)}")
                    self.memory.add_tool_result(tool_name, output=result.stdout)
                    self._pending_saves.append(
                        {"name": tool_name, "description": tool_desc, "code": tool_code}
                    )
                    retries = 0
                else:
                    retries += 1
                    print(f"  ✗  실패 (시도 {retries}/{MAX_RETRIES})")
                    print(f"     {_truncate(result.stderr, 300)}")
                    self.memory.add_tool_result(tool_name, error=result.stderr)

                    if retries >= MAX_RETRIES:
                        msg = f"최대 재시도 횟수({MAX_RETRIES})를 초과했습니다. 태스크를 완료할 수 없습니다."
                        print(f"\nAgent: {msg}")
                        return msg
                continue

            # ── 저장된 툴 실행 / run_tool ─────────────────────────────────────
            if action == "run_tool":
                tool_name = parsed.get("tool_name", "")
                tool_input = parsed.get("tool_input", "")

                tool = self.memory.load_tool(tool_name)
                if tool is None:
                    self.memory.add_tool_result(
                        tool_name, error=f"툴 '{tool_name}'을 찾을 수 없습니다."
                    )
                    retries += 1
                    if retries >= MAX_RETRIES:
                        return f"툴 '{tool_name}'을 찾을 수 없습니다."
                    continue

                print(f"\n  → 저장된 툴 실행: {tool_name}")
                result = execute(tool["code"], tool_input)

                if result.success:
                    out = result.stdout.strip() or "(출력 없음)"
                    print(f"  ✓  {_truncate(out, 200)}")
                    self.memory.add_tool_result(tool_name, output=result.stdout)
                    retries = 0
                else:
                    retries += 1
                    print(f"  ✗  실패 (시도 {retries}/{MAX_RETRIES})")
                    self.memory.add_tool_result(tool_name, error=result.stderr)
                    if retries >= MAX_RETRIES:
                        return "저장된 툴 실행에 실패했습니다."
                continue

            # ── 내장 툴 실행 / run_builtin ────────────────────────────────────
            if action == "run_builtin":
                tool_name = parsed.get("tool_name", "")
                tool_input = parsed.get("tool_input", "")
                builtin = self._builtin.get(tool_name)
                if builtin is None:
                    self.memory.add_tool_result(
                        tool_name, error=f"내장 툴 '{tool_name}'이 없습니다."
                    )
                    continue
                print(f"\n  → 내장 툴: {tool_name}")
                result = builtin.run(tool_input)
                status = "✓" if result.success else "✗"
                print(f"  {status}  {_truncate(result.output, 200)}")
                if result.success:
                    self.memory.add_tool_result(tool_name, output=result.output)
                else:
                    self.memory.add_tool_result(tool_name, error=result.output)
                continue

            # ── 최종 응답 / final_answer ──────────────────────────────────────
            if action == "final_answer":
                if message:
                    print(f"\nAgent: {message}")
                return message

            # 알 수 없는 액션 → 오류 처리 / Unknown action — treat as error
            retries += 1
            self.memory.add_user(
                f"[ERROR] 알 수 없는 action: '{action}'. "
                "유효한 JSON으로 다시 응답해 주세요."
            )
            if retries >= MAX_RETRIES:
                return "응답을 처리할 수 없습니다."

    def offer_tool_save(self) -> None:
        """run_turn() 이후 사용자에게 생성된 툴 저장 여부를 묻는다.
        After run_turn(), offer the user a chance to persist generated tools."""
        if not self._pending_saves:
            return

        print("\n" + "─" * 40)
        count = len(self._pending_saves)

        try:
            if count == 1:
                item = self._pending_saves[0]
                print(f"생성된 툴: {item['description'] or item['name']}")
                ans = input(
                    "이 툴을 저장해두면 다음 세션에서도 사용할 수 있습니다. 저장할까요? (y/n): "
                ).strip().lower()
                if ans == "y":
                    self._do_save(item)
                else:
                    print("  → 저장하지 않고 폐기합니다.")
            else:
                print(f"이번 턴에서 {count}개의 툴을 생성했습니다:")
                for i, item in enumerate(self._pending_saves, 1):
                    print(f"  {i}. {item['description'] or item['name']}")
                ans = input("저장할 툴이 있나요? (y/n): ").strip().lower()
                if ans == "y":
                    choice = input(f"번호를 선택하세요 (1-{count} 또는 'all'): ").strip()
                    if choice == "all":
                        for item in self._pending_saves:
                            self._do_save(item)
                    else:
                        idx = int(choice) - 1
                        self._do_save(self._pending_saves[idx])
        except (EOFError, ValueError, IndexError):
            pass

    def _do_save(self, item: dict) -> None:
        try:
            default = item["name"]
            name = input(f"  툴 이름 [{default}]: ").strip() or default
        except EOFError:
            name = item["name"]
        name = name.replace(" ", "_")
        path = self.memory.save_tool(name, item["description"], item["code"])
        print(f"  ✓ 저장 완료 → {path}")
