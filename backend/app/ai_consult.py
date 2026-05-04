import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field


class DoctorAssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    prediction_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class UserConsultRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="user / assistant / ai")
    content: str = Field(default="", max_length=4000)


class PublicConsultRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: List[ChatHistoryMessage] = Field(default_factory=list)


class ImageConsultRequest(BaseModel):
    message: str = Field(default="", max_length=2000)
    image_base64: str = Field(..., description="Base64 encoded image data")
    history: List[ChatHistoryMessage] = Field(default_factory=list)


def ensure_api_key(api_key: str, detail: str) -> None:
    if not api_key:
        raise HTTPException(status_code=503, detail=detail)


def build_doctor_assistant_messages(
    message: str, context_chunks: List[str]
) -> List[Dict[str, str]]:
    system_prompt = (
        "你是骨龄辅助诊断AI，请输出临床可用、谨慎、结构化建议。"
        "请明确说明不确定性，不可替代医生最终判断。"
    )
    user_prompt = message.strip()
    if context_chunks:
        user_prompt = user_prompt + "\n\n" + "\n".join(context_chunks)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def build_consult_system_prompt(*, include_image: bool = False) -> str:
    prompt = (
        "你是一位友好、专业的骨龄与儿童生长发育健康顾问。"
        "你的角色是向患者及家长提供通俗易懂的健康科普解释，帮助他们理解骨龄概念、发育规律以及相关注意事项。"
        "请用温和、清晰、易理解的语言回答，避免使用晦涩的专业术语。"
        "对于需要临床检查或诊断的问题，请明确建议用户就诊，不替代医生专业判断。"
        "回答时请结构清晰，必要时使用条目列表。"
    )
    if include_image:
        prompt += "如果用户上传了X光片图片，请仔细观察并给出专业的解读建议。"
    return prompt


def _normalize_history_messages(
    history: List[ChatHistoryMessage],
) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    for item in history:
        role_raw = str(item.role).strip().lower()
        if role_raw in {"assistant", "ai"}:
            role = "assistant"
        elif role_raw == "user":
            role = "user"
        else:
            continue

        content = item.content.strip()
        if not content:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def build_consult_messages(
    *,
    system_prompt: str,
    message: str,
    history: List[ChatHistoryMessage],
    image_base64: Optional[str] = None,
) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(_normalize_history_messages(history))

    if image_base64 is None:
        text = message.strip()
        if not text:
            raise HTTPException(status_code=400, detail="message cannot be empty")
        messages.append({"role": "user", "content": text})
        return messages

    user_content: List[Dict[str, Any]] = []
    text = message.strip() or "请帮我分析这张图片"
    user_content.append({"type": "text", "text": text})

    image_data = image_base64
    if not image_data.startswith("data:"):
        image_data = f"data:image/jpeg;base64,{image_data}"
    user_content.append({"type": "image_url", "image_url": {"url": image_data}})

    messages.append({"role": "user", "content": user_content})
    return messages


def _sse_event(payload: Dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def stream_deepseek_chat(
    *,
    api_key: str,
    api_base: str,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    timeout_seconds: float,
    error_prefix: str,
):
    api_url = api_base.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }

    try:
        timeout = httpx.Timeout(timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                api_url,
                headers=headers,
                json=body,
            ) as resp:
                if resp.status_code >= 400:
                    error_text = (await resp.aread()).decode("utf-8", "ignore")[:400]
                    yield _sse_event({"error": f"{error_prefix}: {error_text}"})
                    return

                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield _sse_event({"content": content})
    except Exception as exc:
        yield _sse_event({"error": f"{error_prefix}: {exc}"})
