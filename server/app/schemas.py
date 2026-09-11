"""Pydantic 请求/响应模型。"""
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="终端名称")

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("终端名称不能为空")
        return v


class TerminalInfo(BaseModel):
    code: str
    name: str
    inbox_token: str


class UnregisterRequest(BaseModel):
    """客户端自助注销：终端编码 + 消息中心令牌。"""
    code: str = Field(..., min_length=6, max_length=6)
    token: str = Field(..., min_length=8)


class MessagePushRequest(BaseModel):
    """第三方推送消息请求体：terminal_code 单发 / terminal_codes 群发。"""
    terminal_code: Optional[str] = None
    terminal_codes: Optional[List[str]] = None
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=20000)
    sender: str = Field("未命名", max_length=50)

    @field_validator("title", "sender")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    def target_codes(self) -> List[str]:
        codes: List[str] = []
        if self.terminal_code:
            codes.append(self.terminal_code.strip())
        if self.terminal_codes:
            codes.extend(c.strip() for c in self.terminal_codes if c.strip())
        # 去重且保序
        return list(dict.fromkeys(codes))


class PushResultItem(BaseModel):
    terminal_code: str
    message_id: Optional[int] = None
    delivered: bool = False
    error: Optional[str] = None


class PushResponse(BaseModel):
    total: int
    delivered: int
    results: List[PushResultItem]


class LoginRequest(BaseModel):
    password: str


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class AdminPushRequest(BaseModel):
    """管理后台直接发送（测试）消息。"""
    terminal_codes: List[str] = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field("", max_length=20000)
    sender: str = Field("管理后台", max_length=50)


class TerminalCreateRequest(BaseModel):
    """管理后台手动创建终端。"""
    name: str = Field(..., min_length=1, max_length=50)
