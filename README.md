# FastAPI ChatGPT 챗봇 앱 프로젝트

## 1. 프로젝트 특징

- FastAPI로 백엔드 API 구현
- `/api/chat` 엔드포인트로 ChatGPT 응답 처리
- API 키를 프론트엔드 코드에 직접 넣지 않도록 `.env` 사용
- HTML/CSS/JavaScript 기반 floating chatbot UI 구현
- API 키가 없을 때도 화면 테스트가 가능한 데모 모드 제공
- Swagger 문서 자동 제공

### 주요 구현 기능

- **문맥 유지**: 이전 대화 기록(history)을 함께 전송하여 대화의 맥락을 이어서 답변.
- **System instruction 설정**: 챗봇의 역할과 답변 규칙을 요청마다 지정 가능.
  (미지정 시 `.env`의 `OPENAI_SYSTEM_INSTRUCTION` 또는 서버 기본값 사용)
- **생성 옵션 설정**: `model`, `temperature`, `top_p`, `max_output_tokens`를 UI 설정 패널 또는
  API 요청 본문에서 지정 가능.
- **gpt-5 / o 계열 자동 회피**: gpt-5·o 계열(추론) 모델은 지정 `temperature`/`top_p`를 지원하지
  않고 `max_tokens` 대신 `max_completion_tokens`를 사용. 서버가 모델명을 판별하여
  해당 파라미터를 자동으로 제외/변환하며, 예기치 못한 파라미터 오류가 나더라도 문제 파라미터를
  제거하고 자동 재시도. 조정된 항목은 응답의 `adjusted_params`로 안내.

### 설정 패널 사용법

챗봇 창 상단의 ⚙(설정) 버튼을 누르면 System instruction / Model / Temperature / Top&nbsp;p /
Max output tokens를 입력할 수 있습니다. 🗑 버튼으로 대화를 초기화할 수 있습니다.
값을 비워 두면 서버 기본값이 사용됩니다.

## 2. 프로젝트 구조

```text
fastapi_chatgpt_chatbot_project/
├─ app/
│  ├─ main.py                         # FastAPI 실행 파일
│  ├─ schemas.py                      # 요청/응답 데이터 모델
│  ├─ services/
│  │  └─ openai_service.py            # OpenAI API 호출 서비스
│  └─ static/
│     ├─ index.html                   # 챗봇 메인 화면
│     ├─ style.css                    # 챗봇 UI 스타일
│     └─ app.js                       # 챗봇 프론트엔드 동작
├─ .env.example                       # 환경 변수 예시
├─ .gitignore                         # Git 제외 파일 목록
├─ requirements.txt                   # 설치 패키지 목록
├─ run.bat                            # Windows 실행 스크립트
└─ README.md                          # 프로젝트 설명서
```

## 3. 실행 방법

### 3-1. 프로젝트 폴더로 이동

```bash
cd fastapi_chatgpt_chatbot_project
```

### 3-2. 가상환경 생성

```bash
python -m venv .venv
```

### 3-3. 가상환경 활성화

Windows CMD:

```bash
.venv\Scripts\activate
```

PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

### 3-4. 패키지 설치

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3-5. 환경 변수 파일 생성

`.env.example` 파일을 복사하여 `.env` 파일을 만듭니다.

```bash
copy .env.example .env
```

`.env` 파일을 열고 OpenAI API 키를 입력합니다.

```env
OPENAI_API_KEY=sk-본인의_API_키
OPENAI_MODEL=gpt-4o-mini
```

API 키를 입력하지 않으면 데모 모드로 실행됩니다.

### 3-6. 서버 실행

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

또는 Windows에서 다음 파일을 실행합니다.

```bash
run.bat
```

## 4. 접속 주소

챗봇 화면:

```text
http://127.0.0.1:8000
```

Swagger API 문서:

```text
http://127.0.0.1:8000/docs
```

서버 상태 확인:

```text
http://127.0.0.1:8000/api/health
```

## 5. Swagger 테스트 방법

1. 브라우저에서 `http://127.0.0.1:8000/docs` 접속
2. `POST /api/chat` 클릭
3. `Try it out` 클릭
4. Request body에 아래 예시 입력

```json
{
  "message": "FastAPI가 무엇인지 설명해줘",
  "history": [],
  "system_instruction": "너는 초보자에게 친절하게 설명하는 파이썬 강사다.",
  "model": "gpt-4o-mini",
  "temperature": 0.7,
  "top_p": 1.0,
  "max_output_tokens": 1024
}
```

`system_instruction`, `model`, `temperature`, `top_p`, `max_output_tokens`는 모두 선택
항목입니다. 생략하면 서버 기본값이 사용됩니다. gpt-5 · o 계열 모델을 지정하면 `temperature`와
`top_p`는 자동으로 무시되며, 응답의 `adjusted_params` 목록으로 어떤 값이 조정됐는지 확인할 수 있습니다.

5. `Execute` 클릭
6. `reply` 값으로 챗봇 답변 확인
