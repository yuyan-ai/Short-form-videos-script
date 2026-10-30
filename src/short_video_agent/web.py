"""仅供本机使用的工作台：静态页面 + 后台任务，不暴露.env或任意文件。"""
import argparse
import json
import mimetypes
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from uuid import uuid4

from .runtime import ROOT, Request, run
from .export import export_run
from .config import ModelConfig
from .models.live import LiveModel


class Jobs:
    def __init__(self, runner=run, output=None):
        self.runner = runner
        self.output = output or ROOT / "examples/runs"
        self.items = {}
        self.lock = Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)

    def submit(self, request, mode, max_steps):
        # 先验证输入；配置检查不返回密钥。
        request = Request(**request).model_dump()
        model = LiveModel(ModelConfig.from_env(ROOT / ".env")) if mode == "live" else None
        with self.lock:
            if any(j["status"] == "running" for j in self.items.values()):
                raise RuntimeError("已有任务运行，请等待完成")
            job_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
            # 只保留最近50条会话记录，文件仍保存在runs目录。
            if len(self.items) >= 50:
                self.items.pop(next(iter(self.items)))
            self.items[job_id] = {"id": job_id, "status": "running", "mode": mode}
        self.pool.submit(self.execute, job_id, request, mode, max_steps, model)
        return job_id

    def execute(self, job_id, request, mode, max_steps, model):
        try:
            state = self.runner(request, max_steps=max_steps, model=model)
            directory = self.output / job_id
            export_run(directory, request, state)
            result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            job = {"id": job_id, "status": state["status"], "mode": mode,
                   "result": result, "trace": state["trace"],
                   "markdown": (directory / "script.md").read_text(encoding="utf-8")}
        except Exception:
            job = {"id": job_id, "status": "failed", "mode": mode,
                   "error": "任务执行或导出失败，请通过CLI排查；原始错误未向浏览器公开"}
        with self.lock:
            self.items[job_id] = job

    def get(self, job_id):
        with self.lock:
            return self.items.get(job_id)


def handler_for(jobs):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, value, content_type="application/json; charset=utf-8"):
            data = json.dumps(value, ensure_ascii=False).encode() if isinstance(value, dict) else value
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def local_request(self):
            host = self.headers.get("Host", "")
            allowed = f"127.0.0.1:{self.server.server_port}"
            return host == allowed and self.headers.get("Origin", "http://" + allowed) == "http://" + allowed

        def do_GET(self):
            if not self.local_request():
                return self.send(403, {"error": "只接受本地同源请求"})
            if self.path == "/api/materials":
                data = json.loads((ROOT / "data/materials.json").read_text(encoding="utf-8-sig"))
                return self.send(200, {"materials": data})
            match = re.fullmatch(r"/api/jobs/([a-zA-Z0-9-]+)", self.path)
            if match:
                job = jobs.get(match[1])
                return self.send(200 if job else 404, job or {"error": "任务不存在或服务已重启"})
            static = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
            if self.path in static:
                file = ROOT / "frontend" / static[self.path]
                return self.send(200, file.read_bytes(), (mimetypes.guess_type(file.name)[0] or "text/plain") + "; charset=utf-8")
            self.send(404, {"error": "页面不存在"})

        def do_POST(self):
            if not self.local_request():
                return self.send(403, {"error": "只接受本地同源请求"})
            if self.path != "/api/jobs":
                return self.send(404, {"error": "接口不存在"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 32000:
                    raise ValueError("请求大小不合法")
                body = json.loads(self.rfile.read(size))
                mode = body.get("mode", "mock")
                steps = body.get("max_steps", 12)
                if mode not in ("mock", "live") or type(steps) is not int or not 1 <= steps <= 30:
                    raise ValueError("模式或调用上限不合法")
                job_id = jobs.submit(body["request"], mode, steps)
                self.send(202, {"id": job_id})
            except RuntimeError as exc:
                self.send(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError):
                self.send(400, {"error": "请检查必填信息、时长及模型配置。live需要在后端.env配置三项LLM变量"})
    return Handler


def main():
    parser = argparse.ArgumentParser(description="本地短视频脚本工作台")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    jobs = Jobs()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(jobs))
    print(f"工作台 http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        jobs.pool.shutdown(wait=True)


if __name__ == "__main__":
    main()
