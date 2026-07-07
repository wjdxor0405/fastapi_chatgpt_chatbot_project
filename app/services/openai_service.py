# app/services/openai_service.py
# ------------------------------------------------------------
# 이 파일은 OpenAI API 호출 로직을 담당합니다.
# 라우터(main.py)에 모든 코드를 몰아넣지 않고 서비스 파일로 분리하면 유지보수가 쉬워집니다.
#
# 이 서비스가 처리하는 핵심 기능:
#   1) 이전 대화 기록(history)을 포함한 문맥 유지
#   2) system instruction(지시문) 설정
#   3) model / temperature / top_p / max_output_tokens 설정
#   4) gpt-5 · o 계열 모델의 temperature/top_p 미지원 오류 자동 회피
# ------------------------------------------------------------

# os 모듈은 환경 변수 값을 읽을 때 사용합니다.
# API 키는 코드에 직접 작성하면 유출 위험이 있으므로 환경 변수로 관리합니다.
import os

# re 모듈은 모델명이 gpt-5 / o 계열인지 정규식으로 판별할 때 사용합니다.
import re

# typing 모듈에서 필요한 타입들을 가져옵니다.
from typing import Any, Dict, List, Optional, Tuple

# dotenv의 load_dotenv 함수를 가져옵니다.
# .env 파일에 저장된 OPENAI_API_KEY 값을 파이썬 환경 변수로 불러오기 위해 사용합니다.
from dotenv import load_dotenv

# OpenAI 공식 파이썬 SDK를 가져옵니다.
# OpenAI 클래스로 API를 호출하고, BadRequestError로 400 오류를 구분해서 처리합니다.
from openai import OpenAI, BadRequestError

# 앞에서 정의한 ChatMessage 모델을 가져옵니다.
# 요청으로 전달된 대화 기록을 타입 힌트로 사용합니다.
from app.schemas import ChatMessage

# 프로젝트 루트에 있는 .env 파일을 읽습니다.
# .env 파일이 없어도 오류를 발생시키지 않으므로 개발과 배포 환경 모두에서 사용할 수 있습니다.
load_dotenv()

# 기본 모델명을 환경 변수에서 읽습니다.
# 환경 변수 OPENAI_MODEL이 없으면 gpt-4o-mini를 기본값으로 사용합니다.
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 기본 system 지시문을 환경 변수에서 읽습니다.
# 요청에서 system_instruction을 보내지 않으면 이 문장이 사용됩니다.
DEFAULT_SYSTEM_INSTRUCTION = os.getenv(
    "OPENAI_SYSTEM_INSTRUCTION",
    "너는 한국어로 친절하고 정확하게 답변하는 FastAPI 기반 ChatGPT 챗봇이다.",
)

# OpenAI API 키를 환경 변수에서 읽습니다.
# 이 값이 없으면 실제 API 호출 대신 데모 응답을 반환합니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API 키가 있을 때만 OpenAI 클라이언트를 생성합니다.
# 키가 없는데 클라이언트를 무조건 만들면 실행 환경에 따라 오류가 발생할 수 있습니다.
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# gpt-5 계열 및 o 계열(o1, o3, o4 ...) 모델명을 판별하기 위한 정규식입니다.
# 이 계열의 추론(reasoning) 모델들은 temperature / top_p 를 기본값 외의 값으로 지정하면 오류가 납니다.
# 또한 max_tokens 대신 max_completion_tokens 파라미터를 사용해야 합니다.
_REASONING_MODEL_PATTERN = re.compile(r"^(o\d|gpt-5)", re.IGNORECASE)


def _is_reasoning_model(model: str) -> bool:
    """모델명이 gpt-5 / o 계열인지 판별합니다.

    예) "o1", "o1-mini", "o3-mini", "o4-mini", "gpt-5", "gpt-5-mini" → True
        "gpt-4o", "gpt-4o-mini", "gpt-4.1" → False
    """
    # 모델명 앞뒤 공백을 제거한 뒤 정규식으로 매칭합니다.
    return bool(_REASONING_MODEL_PATTERN.match((model or "").strip()))


def _build_messages(
    system_instruction: str,
    history: List[ChatMessage],
    message: str,
) -> List[Dict[str, str]]:
    """system 지시문 + 이전 대화 기록 + 새 질문을 OpenAI 메시지 형식으로 조립합니다."""
    # 첫 번째 system 메시지로 챗봇의 역할과 답변 스타일을 지정합니다.
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_instruction}
    ]

    # 클라이언트에서 전달한 이전 대화 내역을 OpenAI API 형식으로 변환합니다.
    for item in history:
        # 허용된 role만 API 메시지에 추가합니다.
        # 잘못된 role이 들어오면 OpenAI API 오류가 발생할 수 있으므로 필터링합니다.
        # history 안의 system 메시지는 중복을 피하기 위해 제외하고, user/assistant만 사용합니다.
        if item.role in {"user", "assistant"}:
            messages.append({"role": item.role, "content": item.content})

    # 사용자가 방금 입력한 새 질문을 메시지 목록의 마지막에 추가합니다.
    messages.append({"role": "user", "content": message})

    return messages


def _create_with_fallback(
    params: Dict[str, Any],
    adjusted: List[str],
    max_retries: int = 4,
) -> str:
    """OpenAI API를 호출하되, 파라미터 미지원(400) 오류가 나면 문제 파라미터를 자동으로
    제거/변환한 뒤 다시 시도합니다.

    사전 판별(_is_reasoning_model)로 대부분 걸러지지만, 새 모델이 나와 규칙이 바뀌더라도
    이 방어 로직 덕분에 temperature/top_p/max_tokens 관련 오류를 스스로 회피할 수 있습니다.
    """
    attempt = 0

    while True:
        try:
            # 실제 OpenAI Chat Completions API를 호출합니다.
            completion = client.chat.completions.create(**params)

            # 응답 객체에서 첫 번째 답변 메시지 내용을 꺼냅니다.
            return completion.choices[0].message.content or "응답 내용이 비어 있습니다."

        except BadRequestError as exc:
            # 400(잘못된 요청) 오류의 메시지를 소문자로 만들어 어떤 파라미터가 문제인지 확인합니다.
            attempt += 1
            if attempt > max_retries:
                # 재시도 한도를 넘으면 더 이상 손대지 않고 그대로 오류를 올립니다.
                raise

            msg = str(exc).lower()
            changed = False

            # (1) temperature 미지원 → 제거하고 재시도
            if "temperature" in msg and "temperature" in params:
                params.pop("temperature", None)
                if "temperature" not in adjusted:
                    adjusted.append("temperature")
                changed = True

            # (2) top_p 미지원 → 제거하고 재시도
            if "top_p" in msg and "top_p" in params:
                params.pop("top_p", None)
                if "top_p" not in adjusted:
                    adjusted.append("top_p")
                changed = True

            # (3) max_tokens 미지원 → max_completion_tokens 로 변환하고 재시도
            if (
                "max_tokens" in msg
                and "max_tokens" in params
                and "max_completion_tokens" not in params
            ):
                params["max_completion_tokens"] = params.pop("max_tokens")
                if "max_tokens→max_completion_tokens" not in adjusted:
                    adjusted.append("max_tokens→max_completion_tokens")
                changed = True

            # 우리가 조정할 수 있는 항목이 없으면(다른 원인의 오류이면) 그대로 올립니다.
            if not changed:
                raise


def generate_chat_reply(
    message: str,
    history: List[ChatMessage],
    *,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_output_tokens: Optional[int] = None,
) -> Tuple[str, bool, Dict[str, Any]]:
    """사용자 질문과 이전 대화 내역을 받아 챗봇 답변을 생성합니다.

    반환값: (답변 문자열, 데모모드 여부, 메타정보 dict)
      - 메타정보 dict = {"model": 실제_사용_모델, "adjusted_params": 자동_조정된_파라미터_목록}
    """
    # 사용할 모델과 system 지시문을 결정합니다. 값이 없으면 서버 기본값을 사용합니다.
    used_model = (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    system_text = (system_instruction or "").strip() or DEFAULT_SYSTEM_INSTRUCTION

    # API 키가 없으면 실제 ChatGPT API를 호출할 수 없습니다.
    # 수업 또는 화면 테스트가 가능하도록 데모 응답을 반환합니다.
    if client is None:
        # 데모 모드 안내 문장을 생성합니다. 설정값이 어떻게 전달됐는지도 함께 보여줍니다.
        demo_reply = (
            "현재 OPENAI_API_KEY가 설정되어 있지 않아 데모 모드로 응답합니다. "
            "실제 ChatGPT 답변을 받으려면 프로젝트 루트의 .env 파일에 "
            "OPENAI_API_KEY 값을 설정하세요.\n\n"
            f"요청 모델: {used_model}\n"
            f"system 지시문: {system_text}\n"
            f"temperature: {temperature}, top_p: {top_p}, "
            f"max_output_tokens: {max_output_tokens}\n\n"
            f"입력한 질문: {message}"
        )
        # (답변, 데모모드=True, 메타정보) 형태로 반환합니다.
        return demo_reply, True, {"model": None, "adjusted_params": []}

    # system 지시문 + 대화 기록 + 새 질문을 하나의 메시지 목록으로 만듭니다.
    messages = _build_messages(system_text, history, message)

    # 이 모델이 gpt-5 / o 계열(추론 모델)인지 미리 판별합니다.
    reasoning = _is_reasoning_model(used_model)

    # 자동으로 제외/변경된 파라미터를 기록할 목록입니다.
    adjusted: List[str] = []

    # API 호출에 사용할 파라미터를 조립합니다.
    params: Dict[str, Any] = {"model": used_model, "messages": messages}

    # ----- temperature 처리 -----
    if temperature is not None:
        if reasoning:
            # gpt-5 / o 계열은 지정 temperature를 지원하지 않으므로 아예 전달하지 않습니다.
            adjusted.append("temperature")
        else:
            params["temperature"] = temperature

    # ----- top_p 처리 -----
    if top_p is not None:
        if reasoning:
            # gpt-5 / o 계열은 지정 top_p도 지원하지 않으므로 전달하지 않습니다.
            adjusted.append("top_p")
        else:
            params["top_p"] = top_p

    # ----- 최대 토큰 수 처리 -----
    if max_output_tokens is not None:
        if reasoning:
            # gpt-5 / o 계열은 max_tokens 대신 max_completion_tokens를 사용합니다.
            params["max_completion_tokens"] = max_output_tokens
        else:
            params["max_tokens"] = max_output_tokens

    # 실제 API를 호출합니다. 혹시 미지원 파라미터 오류가 나면 내부에서 자동으로 회피/재시도합니다.
    reply = _create_with_fallback(params, adjusted)

    # (답변, 데모모드=False, 메타정보) 형태로 반환합니다.
    return reply, False, {"model": used_model, "adjusted_params": adjusted}
