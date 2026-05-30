# Adaptive AI Agent

자연어 요청을 받아 필요한 Python 툴을 스스로 생성·실행하여 문제를 해결하는 CLI 기반 AI Agent입니다.

*A CLI-based AI agent that receives natural language requests, dynamically generates the required Python tools, executes them, and returns the result.*

---

## 실행 방법 / Quick Start

### 1. 의존성 설치 / Install dependencies

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 / Configure environment

```bash
cp .env.example .env
# .env 파일을 열어 API 키와 설정을 입력하세요
# Open .env and fill in your API key and settings
```

| 변수 / Variable | 기본값 / Default | 설명 / Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` 또는 `anthropic` / or `anthropic` |
| `OPENAI_API_KEY` | — | OpenAI 사용 시 필수 / Required when using OpenAI |
| `ANTHROPIC_API_KEY` | — | Anthropic 사용 시 필수 / Required when using Anthropic |
| `LLM_MODEL` | 프로바이더 기본값 / provider default | 모델명 오버라이드 / Model name override |
| `LLM_BASE_URL` | 프로바이더 기본값 / provider default | API 엔드포인트 (Ollama 등) / API endpoint (for Ollama, etc.) |
| `MAX_TOKENS` | `4096` | LLM 호출당 최대 토큰 / Max tokens per LLM call |
| `GENERATED_TOOLS_DIR` | `./generated_tools` | 생성된 툴 저장 경로 / Directory for persisted tools |

#### 로컬 모델 (Ollama) 예시 / Local model (Ollama) example

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=ollama
LLM_MODEL=qwen2.5-coder:7b
LLM_BASE_URL=http://localhost:11434/v1/chat/completions
```

### 3. 실행 / Run

```bash
python main.py
```

---

## 프로젝트 구조 / Project Structure

```
├── main.py                  # CLI 진입점 및 환경 변수 로딩 / CLI entry point & env loading
├── agent.py                 # 핵심 에이전트 루프 / Core agent loop
├── llm.py                   # LLM API 직접 HTTP 호출 / Direct LLM HTTP calls (no SDK)
├── prompts.py               # 시스템 프롬프트 및 JSON 응답 형식 / System prompt & JSON format
├── sandbox.py               # 생성 코드 격리 실행 / Isolated code execution (subprocess)
├── memory.py                # 대화 컨텍스트 + 툴 레지스트리 / Conversation history & tool registry
├── tools/
│   ├── base.py              # 내장 툴 추상 클래스 / BuiltinTool ABC
│   ├── file_tools.py        # read_file, write_file, list_files
│   ├── python_tool.py       # sandbox 실행 래퍼 / sandbox execution wrapper
│   └── memory_tool.py       # 생성 툴 목록 조회·로드 / list & load generated tools
├── generated_tools/         # 사용자 승인 툴 저장 위치 / Persisted tool storage
├── requirements.txt
└── .env.example
```

---

## 사용 예시 / Example Interactions

### 예시 1 — 데이터 분석 / Data Analysis

```
$ python main.py
Adaptive AI Agent  [openai / openai/gpt-4o-mini]
태스크를 입력하세요. 종료하려면 'exit' 또는 Ctrl+D.
멀티라인 입력: 내용 입력 후 빈 줄(Enter 두 번)로 제출.
────────────────────────────────────────────────────────────

You: 아래 JSON 데이터에서 체력(hp)이 100 이상인 몬스터의 이름과 평균 hp를 알려줘.
     [{"name":"Goblin","hp":80},{"name":"Orc","hp":150},{"name":"Dragon","hp":300}]

  [생각] I need to filter monsters with hp >= 100 and calculate average hp.

  → 툴 생성: filter_monsters_by_hp
     Filters monsters with hp >= 100 and calculates average hp.
    1 | import json
    2 | def run(input_data: str) -> str:
    3 |     monsters = json.loads(input_data)
    4 |     filtered = [m for m in monsters if m['hp'] >= 100]
    5 |     names = [m['name'] for m in filtered]
    6 |     avg = sum(m['hp'] for m in filtered) / len(filtered) if filtered else 0
    7 |     return json.dumps({'names': names, 'average_hp': avg})
  ✓  {"names": ["Orc", "Dragon"], "average_hp": 225.0}

Agent: 조건을 만족하는 몬스터는 Orc와 Dragon이며, 평균 hp는 225.0입니다.
       (Monsters with hp ≥ 100 are Orc and Dragon. Average hp: 225.0)
```

### 예시 2 — 툴 실패 및 자가 수정 / Self-Correction on Failure

미설치 라이브러리(`polars`)를 요청하여 `ImportError`를 유발한 뒤, 표준 라이브러리로 자동 수정하는 과정입니다.

*Requesting an uninstalled library (`polars`) triggers an `ImportError`. The agent automatically rewrites the code using the standard library.*

```
You: polars를 사용해서 아래 JSON의 score 평균을 구해줘:
     [{"name":"Alice","score":90},{"name":"Bob","score":70},{"name":"Charlie","score":85}]

  [생각] I'll use Polars to compute the average score.

  → 툴 생성: calculate_average_score
    1 | import polars as pl
    2 | def run(input_data: str) -> str:
    3 |     df = pl.read_json(input_data)
    4 |     return str(df['score'].mean())
  ✗  실패 (시도 1/3) / Failed (attempt 1/3)
     ModuleNotFoundError: No module named 'polars'

  [생각] Polars is not available. Switching to standard Python + json.

  → 툴 수정: calculate_average_score
    1 | import json
    2 | def run(input_data: str) -> str:
    3 |     data = json.loads(input_data)
    4 |     avg = sum(d['score'] for d in data) / len(data)
    5 |     return str(round(avg, 2))
  ✓  81.67

Agent: 세 사람의 평균 점수는 81.67점입니다. (Average score: 81.67)
```

### 예시 3 — 모호한 요청 → 사용자 명확화 / Ambiguous Request → Clarification

```
You: 데이터 정리해줘.
     (Clean the data.)

  [생각] 요청이 모호하다. 어떤 데이터인지 물어봐야 한다.
         (Request is ambiguous. Need to ask for clarification.)

Agent: 정리할 데이터의 종류와 형식을 알려주시겠어요?
       (Could you specify what data to clean and how?)

You: 아래 CSV에서 중복 행을 제거하고 날짜 기준으로 정렬해줘:
     name,date,score
     Alice,2024-01-15,90
     Bob,2024-01-10,85
     Alice,2024-01-15,90

  → 툴 생성: deduplicate_and_sort_csv
    1 | import json
    2 | from io import StringIO
    3 | import csv
    4 | def run(input_data: str) -> str:
    5 |     reader = csv.DictReader(StringIO(input_data))
    6 |     rows = list({tuple(r.items()): r for r in reader}.values())
    7 |     rows.sort(key=lambda r: r['date'])
    8 |     out = StringIO()
    9 |     writer = csv.DictWriter(out, fieldnames=rows[0].keys())
   10 |     writer.writeheader(); writer.writerows(rows)
   11 |     return out.getvalue()
  ✓  name,date,score
     Bob,2024-01-10,85
     Alice,2024-01-15,90

Agent: 중복이 제거되고 날짜 순으로 정렬된 결과를 반환합니다.
       (Duplicates removed and sorted by date.)
```

### 예시 4 — 툴 저장 및 재사용 / Tool Save & Reuse

**저장 (y) / Save (y)**

```
────────────────────────────────────────
생성된 툴: Filters monsters with hp >= 100 and calculates average hp.
이 툴을 저장해두면 다음 세션에서도 사용할 수 있습니다. 저장할까요? (y/n): y
  툴 이름 [filter_monsters_by_hp]: hp_filter
  ✓ 저장 완료 → generated_tools/hp_filter.py
```

**폐기 (n) / Discard (n)**

```
────────────────────────────────────────
생성된 툴: Calculates the square root of a number.
이 툴을 저장해두면 다음 세션에서도 사용할 수 있습니다. 저장할까요? (y/n): n
  → 저장하지 않고 폐기합니다. (Discarded without saving.)
```

---

## 에이전트 동작 흐름 / Agent Flow

```
사용자 입력 / User input
    ↓
LLM 호출 → JSON 응답 파싱 / LLM call → JSON response parsing
    ↓
action 분기 / Action dispatch
    ├─ ask_user     → 사용자 재질문 → 루프 재시작
    │                 Ask user for clarification → restart loop
    ├─ create_tool  → Python 코드 생성 → sandbox 실행
    │                 Generate Python code → execute in sandbox
    │   ├─ 성공 / success → 결과를 컨텍스트에 추가 → 루프 계속
    │   └─ 실패 / failure → 에러를 컨텍스트에 추가 → revise_tool (최대 3회 / max 3)
    ├─ revise_tool  → 수정 코드로 재실행 / Re-execute with corrected code
    ├─ run_tool     → 저장된 툴 로드 후 실행 / Load & run a saved tool
    ├─ run_builtin  → 내장 툴 실행 / Run a built-in tool (read_file, etc.)
    └─ final_answer → 최종 응답 출력 → 툴 저장 여부 확인
                      Print final answer → Offer tool save (y/n)
```

### 생성 툴 코드 인터페이스 / Generated Tool Interface

모든 동적 생성 툴은 아래 형식을 따릅니다.
*All dynamically generated tools must follow this interface.*

```python
def run(input_data: str) -> str:
    # input_data를 파싱하여 처리 (JSON, CSV, 평문 등)
    # Parse input_data as needed (JSON, CSV, plain text, ...)
    # ...
    return result_string  # 반드시 문자열 반환 / must return a string
```

---

## 설계 결정 사항 / Design Decisions

### Agent 프레임워크 미사용 / No Agent Framework

LangChain, AutoGen, Claude SDK 등 에이전트 추상화 라이브러리를 사용하지 않았습니다.
LLM API는 `httpx`를 이용한 직접 HTTP POST 요청으로 호출하고, 에이전트 루프 전체를 수동으로 구현했습니다.

*No agent abstraction libraries (LangChain, AutoGen, Claude SDK, etc.) are used. LLM API calls are plain `httpx.post` requests, and the entire agent loop is implemented manually. Every step of the loop is explicit and traceable in code.*

### JSON 기반 LLM 응답 / JSON-Driven LLM Responses

OpenAI의 function calling 대신, LLM이 항상 구조화된 JSON 객체로 응답하도록 시스템 프롬프트를 설계했습니다.
JSON에는 `thought`(추론), `action`(다음 행동), `tool_code`(생성 코드), `tool_input`(입력 데이터) 등의 필드가 포함됩니다.
이 방식은 어떤 OpenAI 호환 엔드포인트에서도 동작하며, 에이전트 내부 추론 과정이 투명하게 기록됩니다.

*Instead of OpenAI function calling, the system prompt instructs the LLM to always return a structured JSON object containing `thought`, `action`, `tool_code`, `tool_input`, etc. This works with any OpenAI-compatible endpoint and keeps the agent's internal reasoning fully transparent.*

### `run(input_data: str) -> str` 통일 인터페이스 / Unified Tool Interface

모든 동적 생성 툴은 동일한 함수 시그니처를 따릅니다.
sandbox는 이 인터페이스만 가정하고 실행하므로, LLM이 생성하는 코드와 실행 환경 간의 결합이 최소화됩니다.

*All dynamically generated tools share the same function signature. The sandbox only assumes this interface, minimizing coupling between LLM-generated code and the execution environment.*

### subprocess 격리 실행 / Subprocess Isolation

생성된 코드는 `tempfile` + `subprocess.run`으로 완전히 별도 프로세스에서 실행됩니다.
메인 프로세스의 네임스페이스 오염을 방지하고, 타임아웃을 안정적으로 강제할 수 있습니다.

*Generated code runs in a fresh subprocess via `tempfile` + `subprocess.run`. This prevents namespace pollution in the main process and enables clean timeout enforcement.*

### 자가 수정 루프 (최대 3회) / Self-Correction Loop (max 3 retries)

실행 실패 시 `stderr`와 traceback이 그대로 LLM 컨텍스트에 추가됩니다.
LLM은 `revise_tool` 액션으로 수정된 코드를 생성하며, 재시도는 최대 3회(`MAX_RETRIES = 3`)로 제한합니다.

*On failure, the full `stderr` and traceback are appended to the LLM context. The LLM selects `revise_tool` to generate corrected code. Retries are capped at 3 (`MAX_RETRIES = 3`) to prevent infinite loops.*

### Human-in-the-loop

모호한 요청 시 LLM이 `ask_user` 액션을 선택하여 CLI로 사용자에게 직접 질문합니다.
사용자 응답은 컨텍스트에 추가되어 루프가 자연스럽게 이어집니다.
툴 실행 성공 후에는 저장 여부를 `y/n`으로 확인합니다.

*For ambiguous requests, the LLM selects `ask_user` and the agent pauses to collect input from the user via CLI. The response is added to context and the loop continues seamlessly. After a successful tool execution, the agent asks the user whether to persist the tool.*

### 생성 툴 영속성 / Tool Persistence

사용자가 저장을 승인한 툴은 `generated_tools/{name}.py`에 코드가 저장되고, `_registry.json`에 메타데이터가 기록됩니다.
다음 세션에서 저장된 툴 목록이 시스템 프롬프트에 자동 주입되어 `run_tool` 액션으로 재사용됩니다.

*Tools approved by the user are saved as `generated_tools/{name}.py` with metadata in `_registry.json`. On the next session, the tool list is automatically injected into the system prompt, enabling reuse via the `run_tool` action.*

---

## 한계 및 개선 가능 방향 / Limitations & Possible Improvements

### 한계 / Limitations

- **샌드박스 격리 없음 / No sandbox isolation** — 생성된 코드가 현재 사용자 권한으로 실행됩니다. 프로덕션 환경에는 부적합합니다. *(Generated code runs with the current user's permissions. Not suitable for production with untrusted input.)*
- **컨텍스트 무한 증가 / Unbounded context** — 긴 세션에서 대화 히스토리가 누적되어 모델 컨텍스트 한도에 도달할 수 있습니다. *(Long sessions accumulate history and may hit the model's context limit.)*
- **전체 히스토리 전달 / Full history per call** — 각 스텝마다 전체 히스토리를 LLM에 전달하므로, 히스토리가 길어질수록 비용과 지연이 증가합니다. *(Every step sends the full history to the LLM — cost and latency grow with session length.)*
- **툴 재사용 한계 / Hardcoded tool data** — 저장된 툴은 생성 당시의 데이터를 하드코딩하는 경우가 많아, 새 데이터에 적용하려면 코드 수정이 필요합니다. *(Saved tools often hardcode data from when they were created; applying them to new data requires rewriting.)*
- **모델 의존적 코드 품질 / Model-dependent quality** — 소형 모델은 잘못된 코드를 더 자주 생성하여 자가 수정 횟수가 늘어납니다. *(Smaller models generate incorrect code more often, requiring more self-correction iterations.)*

### 개선 가능 방향 / Possible Improvements

- **컨테이너 샌드박스 / Container sandbox** — Docker 또는 WebAssembly 환경에서 생성 코드를 실행하여 보안 강화 *(Run generated code inside Docker or WebAssembly for proper isolation)*
- **컨텍스트 압축 / Context compression** — 오래된 대화 턴을 요약하여 긴 세션 지원 *(Summarize older turns to extend effective session length)*
- **스트리밍 출력 / Streaming output** — LLM 응답과 코드 실행 결과를 실시간으로 출력 *(Stream LLM responses and execution output in real time)*
- **파라미터화된 툴 / Parameterized tools** — 툴 저장 시 데이터를 분리하여 다양한 입력에 재사용 가능하도록 설계 *(Decouple data from logic at save time so tools generalize to new inputs)*
- **병렬 툴 실행 / Parallel tool execution** — 독립적인 툴 여러 개를 동시에 실행하여 성능 개선 *(Execute independent tools concurrently)*
- **툴 버전 관리 / Tool versioning** — 생성된 툴의 수정 이력 추적 및 롤백 *(Track revision history and allow rollback of generated tools)*
- **멀티모달 입력 / Multimodal input** — 이미지, PDF 등 비텍스트 입력 지원 *(Support image, PDF, and other non-text inputs)*

---

## 구현 기능 체크리스트 / Feature Checklist

| 기능 / Feature | 구현 위치 / Location | 상태 / Status |
|---|---|---|
| CLI 기반 에이전트 / CLI-based agent | `main.py` | ✅ |
| 에이전트 프레임워크 미사용 (직접 HTTP) / No agent framework | `llm.py` | ✅ |
| 자연어 태스크 분석 / Natural language task analysis | `agent.py`, `prompts.py` | ✅ |
| 동적 Python 툴 생성 / Dynamic tool generation | `agent.py` `create_tool` | ✅ |
| subprocess 격리 실행 / Subprocess isolation | `sandbox.py` | ✅ |
| stdout / stderr / returncode 관찰 / Execution observation | `sandbox.py` `RunResult` | ✅ |
| 오류 기반 자가 수정 / Error-driven self-correction | `agent.py` `revise_tool` | ✅ |
| 최대 3회 재시도 / Max 3 retries | `agent.py` `MAX_RETRIES` | ✅ |
| 모호한 요청 명확화 / Ambiguity clarification | `agent.py` `ask_user` | ✅ |
| 대화 히스토리 / Conversation history | `memory.py` | ✅ |
| 실행 히스토리 / Execution history | `memory.py` `add_tool_result` | ✅ |
| 툴 저장 여부 사용자 확인 / User-confirmed tool save | `agent.py` `offer_tool_save` | ✅ |
| 저장 툴 재사용 / Saved tool reuse | `memory.py`, `generated_tools/` | ✅ |
| JSON 응답 파싱 + 폴백 / JSON parsing with fallback | `agent.py` `_parse_json` | ✅ |
| 내장 툴 (read/write/list) / Built-in file tools | `tools/file_tools.py` | ✅ |
