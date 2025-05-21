from typing import List, Optional
from pydantic import BaseModel, Field, validator
import os


class MountRequest(BaseModel):
    """工作区挂载请求模型"""

    user_id: str = Field(..., description="用户ID")
    workspace_id: str = Field(..., description="工作区ID")
    local_path: str = Field(..., description="本地文件夹绝对路径")
    description: Optional[str] = Field(None, description="挂载描述信息")

    @validator('user_id')
    def validate_user_id(cls, v):
        """验证用户ID格式"""
        if not v or not v.strip():
            raise ValueError("用户ID不能为空")
        return v

    @validator('workspace_id')
    def validate_workspace_id(cls, v):
        """验证工作区ID格式"""
        if not v or not v.strip():
            raise ValueError("工作区ID不能为空")
        return v


class MountResponse(BaseModel):
    """挂载响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    data: Optional[dict] = Field(None, description="挂载详情数据")


class MountInfo(BaseModel):
    """挂载信息模型"""

    user_id: str = Field(..., description="用户ID")
    workspace_id: str = Field(..., description="工作区ID")
    local_path: str = Field(..., description="本地文件夹绝对路径")
    container_path: str = Field(..., description="容器内映射路径")
    description: Optional[str] = Field(None, description="挂载描述信息")
    created_at: str = Field(..., description="创建时间")


class MountListResponse(BaseModel):
    """挂载列表响应模型"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
    data: List[MountInfo] = Field([], description="挂载列表数据")
