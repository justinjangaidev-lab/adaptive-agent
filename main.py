#!/usr/bin/env python3
import os
import sys


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        sys.exit(f"오류: 환경 변수 {key} 가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return val


def _read_user_input(prompt: str) -> str:
    """
    멀티라인 입력을 지원하는 사용자 입력 읽기.
    빈 줄이 나오면 입력을 종료한다. 여러 줄 데이터는 마지막에 Enter를 두 번 눌러 제출.
    Read user input with multi-line support.
    Any blank line terminates input; paste multi-line data then press Enter twice.
    """
    sys.stdout.write(prompt)
    sys.stdout.flush()
    lines = []
    try:
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
    except EOFError:
        if not lines:
            raise
    return "\n".join(lines).strip()


def main() -> None:
    _load_env()

    provider = os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "openai":
        api_key  = _require("OPENAI_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1/chat/completions")
        model    = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    elif provider == "anthropic":
        api_key  = _require("ANTHROPIC_API_KEY")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com/v1/messages")
        model    = os.environ.get("LLM_MODEL", "claude-opus-4-8")
    else:
        sys.exit(f"지원하지 않는 LLM_PROVIDER: '{provider}'. 'openai' 또는 'anthropic' 을 사용하세요.")

    max_tokens    = int(os.environ.get("MAX_TOKENS", "4096"))
    generated_dir = os.environ.get("GENERATED_TOOLS_DIR", "./generated_tools")

    from agent import Agent
    from llm import LLMClient
    from memory import Memory

    llm    = LLMClient(api_key=api_key, model=model, base_url=base_url, max_tokens=max_tokens, provider=provider)
    memory = Memory(generated_tools_dir=generated_dir)
    agent  = Agent(llm=llm, memory=memory, input_fn=_read_user_input)

    print(f"Adaptive AI Agent  [{provider} / {model}]")
    print("태스크를 입력하세요. 종료하려면 'exit' 또는 Ctrl+D.")
    print("멀티라인 입력: 내용 입력 후 빈 줄(Enter 두 번)로 제출.")
    print("─" * 60)

    while True:
        try:
            user_input = _read_user_input("\nYou: ")
        except (KeyboardInterrupt, EOFError):
            print("\n종료합니다.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "종료"):
            print("종료합니다.")
            break

        agent.run_turn(user_input)
        agent.offer_tool_save()


if __name__ == "__main__":
    main()
