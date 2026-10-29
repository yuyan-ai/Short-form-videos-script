"""离线原型命令行入口。"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from .runtime import run
from .export import export_run


def main():
    parser = argparse.ArgumentParser(description="短视频脚本离线流程演示，无需 API Key")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--mode", choices=["mock"], default="mock")
    parser.add_argument("--output", type=Path, default=Path("examples/runs"))
    parser.add_argument("--max-steps", type=int, default=10)
    args = parser.parse_args()
    try:
        request = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(request, dict):
            raise ValueError("输入 JSON 必须为对象")
        state = run(request, args.max_steps)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"输入或运行错误：{exc}\n")
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = args.output / run_id
    export_run(directory, request, state)
    print(json.dumps({"status": state["status"], "output": str(directory.resolve())}, ensure_ascii=False))
    return 0 if state["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
