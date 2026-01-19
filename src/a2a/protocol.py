from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class AgentMessage(BaseModel):
    role: str
    content: str

class AgentTask(BaseModel):
    task_id: str
    input: str
    additional_input: Optional[Dict[str, Any]] = None

class AgentStep(BaseModel):
    task_id: str
    step_id: str
    input: Optional[str] = None
    output: Optional[str] = None
    is_last: bool = False

# 符合 OpenAI 兼容协议但经过 A2A 封装的模型
class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[AgentMessage]
    stream: bool = False
