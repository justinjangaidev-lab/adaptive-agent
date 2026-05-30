import json
from datetime import datetime
from pathlib import Path


class Memory:
    """Conversation history and generated-tool registry."""

    def __init__(self, generated_tools_dir: str = "./generated_tools"):
        self.messages: list[dict] = []
        self._dir = Path(generated_tools_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._dir / "_registry.json"
        self._registry: dict = self._load_registry()

    # ── conversation ──────────────────────────────────────────────────────────

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_result(self, tool_name: str, output: str = "", error: str = "") -> None:
        if error:
            content = (
                f"[TOOL_RESULT] 툴 '{tool_name}' 실행 실패.\n"
                f"stderr:\n{error}"
            )
        else:
            content = (
                f"[TOOL_RESULT] 툴 '{tool_name}' 실행 성공.\n"
                f"출력:\n{output}"
            )
        self.messages.append({"role": "user", "content": content})

    # ── tool registry ─────────────────────────────────────────────────────────

    def save_tool(self, name: str, description: str, code: str) -> str:
        path = self._dir / f"{name}.py"
        path.write_text(code, encoding="utf-8")
        self._registry[name] = {
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "path": str(path),
        }
        self._persist_registry()
        return str(path)

    def load_tool(self, name: str) -> dict | None:
        if name not in self._registry:
            return None
        entry = self._registry[name]
        try:
            code = Path(entry["path"]).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        return {"name": name, "description": entry["description"], "code": code}

    def list_tools(self) -> list[dict]:
        return [
            {"name": v["name"], "description": v["description"]}
            for v in self._registry.values()
        ]

    def _load_registry(self) -> dict:
        if self._registry_path.exists():
            try:
                return json.loads(self._registry_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _persist_registry(self) -> None:
        self._registry_path.write_text(
            json.dumps(self._registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
