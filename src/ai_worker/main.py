"""Run the full OpenCV/YOLO API as a separate local worker service."""

import os

import uvicorn


def main():
    os.environ["CROWD_RUNTIME_MODE"] = "AI_WORKER"
    uvicorn.run(
        "src.api:app",
        host=os.getenv("AI_WORKER_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_WORKER_PORT", "8100")),
        reload=False,
    )


if __name__ == "__main__":
    main()
