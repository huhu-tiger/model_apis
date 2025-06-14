import sys
import os
import logging
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import Mount
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles

from common.response import error_response,success_response
from pydantic import BaseModel, validator
import requests
from datetime import datetime

# 获取项目根目录的绝对路径
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"Project root directory: {project_root}")
download_dir = os.path.join(project_root,"public","download")
upload_dir = os.path.join(project_root,"public","upload")
os.makedirs(download_dir, exist_ok=True)
os.makedirs(upload_dir, exist_ok=True)
sys.path.append(project_root)




logger = logging.getLogger(__name__)
# 初始化应用
# setup_log(app_server=config.BaseConfig.SERVICE_NAME, level=logging.DEBUG)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # 启动时执行
#     await service_registration.register()
#     yield
#     # 关闭时执行
#     await service_registration.deregister()

app = FastAPI(docs_url=None, redoc_url=None)

# 挂载 public/upload/ 作为静态文件服务器路径
upload_static_path = os.path.join(project_root, "public", "upload")
app.mount("/upload", StaticFiles(directory=upload_static_path), name="upload")


# script_path = os.path.abspath(__file__)
# # 当前脚本所在目录
# script_dir  = os.path.dirname(script_path)
# app.mount("/static", StaticFiles(directory=os.path.join(script_dir,"static")), name="static")


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()



app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载路由表
# app.include_router(V1Router)

def print_routes(app: FastAPI):
    print("Registered Routes:")
    for route in app.routes:
        # 检查是否为 Mount 类型
        if isinstance(route, Mount):
            print(f"{route.path} -> Static (mounted at {route.name})")
        else:
            methods = ", ".join(route.methods)
            print(f"{route.path} -> {methods}")




class ChatCompletionRequest(BaseModel):
    model: str
    messages: list
    temperature: float = 1
    max_tokens: int = 256

    @validator('messages')
    def validate_messages(cls, v):
        required_roles = {'user', 'system'}
        for message in v:
            if not isinstance(message, dict):
                raise ValueError('消息必须为字典类型')
            if 'role' not in message or 'content' not in message:
                raise ValueError('消息必须包含 role 和 content 字段')
            if message['role'] not in required_roles:
                raise ValueError(f'role 必须为 {required_roles} 中的一个')
            # if message['role'] == 'system':
            #     if 'type' not in message or message['type'] not in ['audio_url', 'text']:
            #         raise ValueError('system 消息的 type 字段必须为 audio_url 或 text')
        return v


@app.post("/v1/chat/completions")
async def chat_completion(request: ChatCompletionRequest):
    try:
        logger.info(f"Received request: {request.messages}")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        # 查找 type 为 audio 的 URL
        audio_url =  ""
        audio_text = ""
        output_text = ""

        for message in request.messages:
            if message.get('role') == 'system' and len(message.get('content')) > 0:
                for content in message['content']:
                    if isinstance(content, dict) and content.get('type') == 'audio':
                        audio_url=content.get('url')
                    if isinstance(content, dict) and content.get('type') == 'audio':
                        audio_text=content.get('text')   
            if message.get('role') == 'user' and len(message.get('content')) > 0:
                output_text = message['content'][0]

        
        # 下载音频文件
        try:
            response = requests.get(audio_url)
            response.raise_for_status()
            
            # 获取文件扩展名
            ext = os.path.splitext(audio_url)[1]
            ext = ext if ext else '.wav'  # 默认扩展名为 .wav
            
            filename = f"{timestamp}{ext}"
            file_path = os.path.join(download_dir, filename)
            
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            print(f"Downloaded audio file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to download audio file from {audio_url}: {e}")
            raise BaseException(f"下载音频文件失败: {e}")
        
        # 这里添加实际的大模型调用逻辑
        response_data = {
            "id": timestamp,
            "object": timestamp,
            "created": 1677858242,
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "这是一个模拟的大模型响应。"
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        return success_response(data=response_data)
    except Exception as e:
        logger.error(f"大模型接口错误: {e}")
        return error_response(code=500, data="大模型接口调用失败")


if __name__ == "__main__":
    import uvicorn
    print_routes(app=app)
    uvicorn.run(app='main:app', host="0.0.0.0", port=int(os.getenv("port", 5788)))