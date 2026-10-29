# 短视频脚本 Agent

基于 Python + LangGraph 的短视频脚本项目。

当前已建立目录与文件骨架，业务逻辑、模型接入和测试尚未实现。

## 项目入口

- 原始需求：`require.md`
- 框架设计：`docs/02-solution.md`
- 业务代码：`src/short_video_agent/`
- 测试：`tests/`
- 合成素材与规则：`data/`
- 示例输入与运行记录：`examples/`

## 开发环境

建议使用 Python 3.11 或更新版本。PowerShell 安装步骤：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

依赖尚未锁定或验证；安装命令仅用于准备开发环境。目前没有可运行的 Agent，也没有实际执行结果。
