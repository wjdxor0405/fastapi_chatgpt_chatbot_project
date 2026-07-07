# app/schemas.py
# ------------------------------------------------------------
# 이 파일은 FastAPI 요청(Request)과 응답(Response)의 데이터 형식을 정의합니다.
# Pydantic 모델을 사용하면 잘못된 데이터가 들어왔을 때 FastAPI가 자동으로 검증합니다.
# ------------------------------------------------------------

# typing 모듈에서 List, Optional 타입을 가져옵니다.
# List는 여러 개의 데이터를 담는 리스트 자료형의 내부 타입을 명확히 표현할 때 사용합니다.
# Optional은 값이 있을 수도 있고 없을(None) 수도 있는 선택 항목을 표현할 때 사용합니다.
from typing import List, Optional

# pydantic의 BaseModel과 Field를 가져옵니다.
# BaseModel은 데이터 검증 모델의 기본 클래스입니다.
# Field는 각 필드의 설명, 기본값, 길이 제한 등을 지정할 때 사용합니다.
from pydantic import BaseModel, Field


# 채팅 메시지 1개의 구조를 정의하는 클래스입니다.
# 사용자의 메시지와 챗봇의 메시지를 같은 형식으로 다루기 위해 사용합니다.
class ChatMessage(BaseModel):
    # role은 메시지를 보낸 주체를 의미합니다.
    # OpenAI Chat Completions API에서는 일반적으로 system, user, assistant 역할을 사용합니다.
    role: str = Field(
        ...,                                      # ...은 필수 입력값이라는 뜻입니다.
        description="메시지 역할: system, user, assistant 중 하나",
        examples=["user"],
    )

    # content는 실제 메시지 내용입니다.
    # min_length=1을 지정하여 빈 문자열이 들어오지 않도록 검증합니다.
    content: str = Field(
        ...,
        min_length=1,
        description="메시지 본문",
        examples=["FastAPI가 무엇인가요?"],
    )


# 클라이언트가 /api/chat 엔드포인트로 보낼 요청 데이터 구조입니다.
class ChatRequest(BaseModel):
    # message는 사용자가 새로 입력한 질문입니다.
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="사용자가 입력한 새 질문",
        examples=["파이썬 FastAPI의 장점을 알려줘"],
    )

    # history는 이전 대화 내역입니다.
    # 기본값을 빈 리스트로 두어 첫 질문에서도 오류 없이 처리되게 합니다.
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="이전 대화 내역",
    )

    # ----------------------------------------------------------------
    # 아래 항목들은 모두 선택(Optional) 항목입니다.
    # 값을 보내지 않으면(None) 서버의 기본값이 사용됩니다.
    # ----------------------------------------------------------------

    # system_instruction은 챗봇의 역할과 답변 스타일을 지정하는 지시문입니다.
    # 예: "너는 친절한 파이썬 강사다." 처럼 대화 전체의 성격을 정할 수 있습니다.
    system_instruction: Optional[str] = Field(
        default=None,
        max_length=8000,
        description="챗봇의 역할과 답변 규칙을 지정하는 system 지시문 (미지정 시 서버 기본값 사용)",
        examples=["너는 초보자에게 친절하게 설명하는 파이썬 강사다."],
    )

    # model은 사용할 OpenAI 모델명입니다.
    # 예: gpt-4o-mini, gpt-4o, gpt-5, o3-mini 등.
    model: Optional[str] = Field(
        default=None,
        max_length=100,
        description="사용할 OpenAI 모델명 (미지정 시 서버 기본 모델 사용)",
        examples=["gpt-4o-mini"],
    )

    # temperature는 답변의 창의성 정도입니다. 0에 가까울수록 일관적이고, 값이 클수록 다양해집니다.
    # gpt-5 / o 계열 모델은 기본값 외의 temperature를 지원하지 않아, 서버가 자동으로 제외합니다.
    temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="답변의 무작위성 (0~2). gpt-5/o 계열에서는 자동 무시됨",
        examples=[0.7],
    )

    # top_p는 확률 상위 토큰만 선택하는 누적 확률 임계값입니다(0~1).
    # temperature와 마찬가지로 gpt-5 / o 계열에서는 자동으로 제외됩니다.
    top_p: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="누적 확률 기반 샘플링 값 (0~1). gpt-5/o 계열에서는 자동 무시됨",
        examples=[1.0],
    )

    # max_output_tokens는 모델이 생성할 답변의 최대 토큰 수입니다.
    # 내부적으로 모델 종류에 따라 max_tokens 또는 max_completion_tokens 로 변환됩니다.
    max_output_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        le=32000,
        description="생성할 답변의 최대 토큰 수",
        examples=[1024],
    )


# 서버가 클라이언트에게 돌려줄 응답 데이터 구조입니다.
class ChatResponse(BaseModel):
    # reply는 ChatGPT 또는 데모 응답이 생성한 답변입니다.
    reply: str = Field(
        ...,
        description="챗봇 답변",
        examples=["FastAPI는 파이썬 기반의 빠른 웹 API 프레임워크입니다."],
    )

    # used_demo_mode는 실제 OpenAI API를 호출했는지, 데모 응답을 사용했는지 알려줍니다.
    # API 키가 없으면 True가 됩니다.
    used_demo_mode: bool = Field(
        default=False,
        description="OPENAI_API_KEY가 없어서 데모 응답을 사용했는지 여부",
    )

    # model은 실제로 응답을 생성하는 데 사용된 모델명입니다.
    # 어떤 모델이 쓰였는지 프론트엔드에서 확인/표시할 수 있도록 함께 반환합니다.
    model: Optional[str] = Field(
        default=None,
        description="실제 사용된 모델명 (데모 모드에서는 None)",
    )

    # adjusted_params는 모델 호환성 때문에 서버가 자동으로 제외/변경한 파라미터 목록입니다.
    # 예: gpt-5/o 계열에서 temperature가 제거되면 ["temperature"] 가 들어갑니다.
    adjusted_params: List[str] = Field(
        default_factory=list,
        description="모델 호환성 때문에 자동으로 제외되거나 변경된 파라미터 목록",
    )
