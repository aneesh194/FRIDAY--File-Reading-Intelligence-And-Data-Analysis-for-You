import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_engine import llm, MODEL_PATH, MODEL_FAMILY, _get_stop_tokens, llm_lock

app = FastAPI(title="FRIDAY AI API Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: str = "friday"
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

def format_openai_chunk(content: str, finish_reason: Optional[str] = None) -> str:
    chunk = {
        "id": "chatcmpl-friday",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "friday",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason
            }
        ]
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

def build_prompt_from_messages(messages: List[ChatMessage]) -> str:
    """Translate OpenAI-style messages into the correct model-family chat template."""
    prompt_str = ""
    system_content = "You are FRIDAY AI — a highly intelligent technical companion and advanced file analysis assistant."
    
    # Extract system instruction if present, or use default
    chat_messages = []
    for msg in messages:
        if msg.role == "system":
            system_content = msg.content
        else:
            chat_messages.append(msg)
            
    if MODEL_FAMILY == "llama3":
        prompt_str += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_content}<|eot_id|>"
        for msg in chat_messages:
            role = "user" if msg.role == "user" else "assistant"
            prompt_str += f"<|start_header_id|>{role}<|end_header_id|>\n\n{msg.content}<|eot_id|>"
        prompt_str += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        
    elif MODEL_FAMILY == "mistral":
        prompt_str += f"<s>[INST] {system_content}\n\n"
        for i, msg in enumerate(chat_messages):
            if msg.role == "user":
                if i > 0:
                    prompt_str += f" [INST] {msg.content} [/INST]"
                else:
                    prompt_str += f"{msg.content} [/INST]"
            else:
                prompt_str += f" {msg.content}</s>"
                
    elif MODEL_FAMILY == "phi3":
        prompt_str += f"<|system|>\n{system_content}<|end|>\n"
        for msg in chat_messages:
            role = "user" if msg.role == "user" else "assistant"
            prompt_str += f"<{role}>\n{msg.content}<|end|>\n"
        prompt_str += "<|assistant|>\n"
        
    elif MODEL_FAMILY == "qwen":
        prompt_str += f"<|im_start|>system\n{system_content}<|im_end|>\n"
        for msg in chat_messages:
            role = "user" if msg.role == "user" else "assistant"
            prompt_str += f"<|im_start|>{role}\n{msg.content}<|im_end|>\n"
        prompt_str += "<|im_start|>assistant\n"
        
    else:  # deepseek / generic
        prompt_str += f"{system_content}\n\n"
        for msg in chat_messages:
            if msg.role == "user":
                prompt_str += f"### Instruction:\n{msg.content}\n\n"
            else:
                prompt_str += f"### Response:\n{msg.content}\n\n"
        prompt_str += "### Response:\n"
        
    return prompt_str

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    prompt = build_prompt_from_messages(request.messages)
    stop_tokens = _get_stop_tokens()
    
    if not request.stream:
        # Serialized synchronous request running in executor
        loop = asyncio.get_event_loop()
        def locked_call():
            with llm_lock:
                return llm(
                    prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    repeat_penalty=1.15,
                    stop=stop_tokens
                )
        try:
            response = await loop.run_in_executor(None, locked_call)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
        content = response["choices"][0]["text"].strip()
        
        # Clean <think> tags natively if returned
        import re
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        if '</think>' in content:
            content = content.split('</think>')[-1].strip()
            
        return {
            "id": "chatcmpl-friday",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "friday",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": response.get("usage", {})
        }
        
    else:
        # Streaming response using Server-Sent Events (SSE) and an async queue
        async def stream_generator():
            queue = asyncio.Queue()
            loop = asyncio.get_event_loop()
            
            def producer():
                try:
                    with llm_lock:
                        stream = llm(
                            prompt,
                            max_tokens=request.max_tokens,
                            temperature=request.temperature,
                            repeat_penalty=1.15,
                            stop=stop_tokens,
                            stream=True
                        )
                        for chunk in stream:
                            token = chunk["choices"][0]["text"]
                            loop.call_soon_threadsafe(queue.put_nowait, token)
                    loop.call_soon_threadsafe(queue.put_nowait, None)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, e)
            
            # Start background thread execution to preserve server concurrency
            asyncio.create_task(loop.run_in_executor(None, producer))
            
            try:
                consecutive_ticks = 0
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                        
                    token = item
                    if "```" in token:
                        consecutive_ticks += 1
                    else:
                        if token.strip():
                            consecutive_ticks = 0
                            
                    if consecutive_ticks > 3:
                        yield format_openai_chunk("", "stop")
                        break
                        
                    yield format_openai_chunk(token)
                    
                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"[Error in Streaming] {e}")
                yield format_openai_chunk(f"\n[Error: {e}]", "stop")
                yield "data: [DONE]\n\n"
                
        return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "friday",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "friday"
            }
        ]
    }

def start_server(port: int = 8000):
    import uvicorn
    print(f"[FRIDAY AI] Launching Local API Server on http://localhost:{port}/v1", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    start_server()
