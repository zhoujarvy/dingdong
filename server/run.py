"""读取 config.json 后启动 uvicorn。"""
import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=config.get("host"),
        port=int(config.get("port")),
    )
