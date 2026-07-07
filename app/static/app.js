// app/static/app.js
// ------------------------------------------------------------
// 챗봇 화면의 동작을 담당하는 JavaScript 파일입니다.
// 사용자의 입력을 FastAPI /api/chat 엔드포인트로 전송하고 응답을 화면에 출력합니다.
//
// 추가 기능:
//   - system instruction, model, temperature, top_p, max_output_tokens 설정 전송
//   - 이전 대화 기록(history)을 함께 보내 문맥 유지
//   - 서버가 gpt-5/o 계열 때문에 자동 제외한 파라미터를 화면에 안내
// ------------------------------------------------------------

// 챗봇 열기 버튼 요소를 가져옵니다.
const chatIcon = document.getElementById("chatIcon");

// 챗봇 모달 요소를 가져옵니다.
const chatModal = document.getElementById("chatModal");

// 챗봇 닫기 버튼 요소를 가져옵니다.
const closeChat = document.getElementById("closeChat");

// 설정 패널 열기/닫기 버튼과 패널 요소를 가져옵니다.
const toggleSettings = document.getElementById("toggleSettings");
const settingsPanel = document.getElementById("settingsPanel");

// 대화 초기화 버튼 요소를 가져옵니다.
const clearChat = document.getElementById("clearChat");

// 메시지 목록이 표시될 영역을 가져옵니다.
const chatMessages = document.getElementById("chatMessages");

// 메시지 입력 폼 요소를 가져옵니다.
const chatForm = document.getElementById("chatForm");

// 사용자가 질문을 입력하는 input 요소를 가져옵니다.
const messageInput = document.getElementById("messageInput");

// 설정 입력 요소들을 가져옵니다.
const systemInstructionInput = document.getElementById("systemInstruction");
const modelInput = document.getElementById("modelInput");
const temperatureInput = document.getElementById("temperatureInput");
const topPInput = document.getElementById("topPInput");
const maxTokensInput = document.getElementById("maxTokensInput");

// 이전 대화 내역을 저장하는 배열입니다.
// 서버에 함께 전달하면 문맥을 이어서 답변할 수 있습니다.
const history = [];

// 챗봇 버튼을 클릭하면 모달의 hidden 클래스를 제거하여 화면에 표시합니다.
chatIcon.addEventListener("click", () => {
    chatModal.classList.remove("hidden");
    messageInput.focus();
});

// 닫기 버튼을 클릭하면 모달에 hidden 클래스를 추가하여 화면에서 숨깁니다.
closeChat.addEventListener("click", () => {
    chatModal.classList.add("hidden");
});

// 설정 버튼을 클릭하면 설정 패널을 열거나 닫습니다.
toggleSettings.addEventListener("click", () => {
    settingsPanel.classList.toggle("hidden");
});

// 대화 초기화 버튼을 클릭하면 화면과 기록을 모두 비웁니다.
clearChat.addEventListener("click", () => {
    // 화면의 메시지를 모두 제거합니다.
    chatMessages.innerHTML = "";
    // 저장된 대화 기록 배열도 비웁니다.
    history.length = 0;
    // 입력창에 다시 포커스를 둡니다.
    messageInput.focus();
});

// 화면에 메시지 말풍선을 추가하는 함수입니다.
function addMessage(role, content) {
    // div 요소를 새로 생성합니다.
    const messageElement = document.createElement("div");

    // role에 따라 user 또는 assistant 스타일이 적용되도록 클래스를 지정합니다.
    messageElement.className = `message ${role}`;

    // textContent를 사용하여 사용자가 입력한 HTML이 실행되지 않도록 안전하게 출력합니다.
    messageElement.textContent = content;

    // 생성한 메시지 요소를 메시지 목록 영역에 추가합니다.
    chatMessages.appendChild(messageElement);

    // 새 메시지가 추가되면 스크롤을 가장 아래로 이동합니다.
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // 이후 내용을 교체할 수 있도록 생성한 요소를 반환합니다.
    return messageElement;
}

// 답변 아래에 작은 안내(사용 모델, 자동 제외된 파라미터)를 표시하는 함수입니다.
function addMeta(data) {
    // 표시할 안내 문구 조각들을 담을 배열입니다.
    const parts = [];

    // 데모 모드일 때는 안내를 표시합니다.
    if (data.used_demo_mode) {
        parts.push("데모 모드");
    }

    // 실제 사용된 모델명이 있으면 표시합니다.
    if (data.model) {
        parts.push(`모델: ${data.model}`);
    }

    // 서버가 호환성 때문에 자동으로 제외/변경한 파라미터가 있으면 표시합니다.
    if (Array.isArray(data.adjusted_params) && data.adjusted_params.length > 0) {
        parts.push(`자동 조정: ${data.adjusted_params.join(", ")}`);
    }

    // 표시할 내용이 없으면 아무것도 추가하지 않습니다.
    if (parts.length === 0) {
        return;
    }

    // 메타 정보 요소를 생성하여 메시지 목록에 추가합니다.
    const metaElement = document.createElement("div");
    metaElement.className = "message-meta";
    metaElement.textContent = parts.join(" · ");
    chatMessages.appendChild(metaElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 현재 설정 입력값을 읽어 요청 본문에 담을 객체로 만드는 함수입니다.
// 값이 비어 있으면 해당 항목을 아예 넣지 않아 서버 기본값이 사용되게 합니다.
function collectSettings() {
    // 결과를 담을 객체입니다.
    const settings = {};

    // system 지시문은 앞뒤 공백을 제거한 뒤 값이 있으면 넣습니다.
    const systemText = systemInstructionInput.value.trim();
    if (systemText) {
        settings.system_instruction = systemText;
    }

    // 모델명도 값이 있으면 넣습니다.
    const modelText = modelInput.value.trim();
    if (modelText) {
        settings.model = modelText;
    }

    // temperature는 숫자로 변환하여 유효할 때만 넣습니다.
    if (temperatureInput.value !== "") {
        const temperature = Number(temperatureInput.value);
        if (!Number.isNaN(temperature)) {
            settings.temperature = temperature;
        }
    }

    // top_p도 숫자로 변환하여 유효할 때만 넣습니다.
    if (topPInput.value !== "") {
        const topP = Number(topPInput.value);
        if (!Number.isNaN(topP)) {
            settings.top_p = topP;
        }
    }

    // 최대 토큰 수는 정수로 변환하여 유효할 때만 넣습니다.
    if (maxTokensInput.value !== "") {
        const maxTokens = parseInt(maxTokensInput.value, 10);
        if (!Number.isNaN(maxTokens)) {
            settings.max_output_tokens = maxTokens;
        }
    }

    return settings;
}

// 메시지 전송 폼이 제출될 때 실행되는 이벤트입니다.
chatForm.addEventListener("submit", async (event) => {
    // form의 기본 동작인 페이지 새로고침을 막습니다.
    event.preventDefault();

    // 입력값 앞뒤 공백을 제거합니다.
    const message = messageInput.value.trim();

    // 빈 문자열이면 서버로 전송하지 않습니다.
    if (!message) {
        return;
    }

    // 사용자 메시지를 화면에 먼저 출력합니다.
    addMessage("user", message);

    // 대화 기록에도 사용자 메시지를 저장합니다.
    history.push({ role: "user", content: message });

    // 입력창을 비워 다음 질문을 입력할 수 있게 합니다.
    messageInput.value = "";

    // 응답 대기 중임을 사용자에게 알려줍니다.
    const loadingMessage = addMessage("assistant", "답변을 생성하는 중입니다...");

    // 현재 설정값을 읽어옵니다.
    const settings = collectSettings();

    // try 블록에서 서버 API를 호출합니다.
    try {
        // 요청 본문을 구성합니다.
        // history는 방금 추가한 사용자 메시지를 제외하고 보냅니다(서버가 message로 따로 받기 때문).
        const requestBody = Object.assign(
            {
                message: message,
                history: history.slice(0, -1),
            },
            settings
        );

        // FastAPI의 /api/chat 엔드포인트에 POST 요청을 보냅니다.
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(requestBody),
        });

        // HTTP 응답이 실패 상태이면 오류를 발생시킵니다.
        if (!response.ok) {
            throw new Error(`서버 오류: ${response.status}`);
        }

        // 서버에서 받은 JSON 응답을 파싱합니다.
        const data = await response.json();

        // 대기 메시지 내용을 실제 답변으로 교체합니다.
        loadingMessage.textContent = data.reply;

        // 답변 아래에 사용 모델/자동 조정 안내를 표시합니다.
        addMeta(data);

        // 대화 기록에도 챗봇 답변을 저장합니다.
        history.push({ role: "assistant", content: data.reply });
    } catch (error) {
        // 오류가 발생하면 화면에 오류 안내를 표시합니다.
        loadingMessage.textContent = `오류가 발생했습니다. ${error.message}`;
    }
});
