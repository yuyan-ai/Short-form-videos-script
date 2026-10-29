# 短视频脚本 Agent

Python + LangGraph 的离线可运行原型。无需 API Key。

## 安装与运行（PowerShell）

需要 Python 3.10+。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/overlong.json
.\.venv\Scripts\python.exe -m pytest -q
```

`--mode mock` 为默认模式，目前仅支持 Mock。完成返回退出码 0，缺信息、失败、预算耗尽返回 2。输出目录在命令返回的 output 中。

## 已提供

- 虚构产品“轻剪”的三条合成素材：支持字幕、支持竖屏预览、支持保存脚本草稿。
- 品牌禁用词、中性脚本表达白名单、事实引用检查。
- 五组输入：normal、overlong、no_material、missing_info、tool_failure。
- LangGraph 输入校验、决策、执行循环；次数上限及明确状态。
- 时长逐镜估算；改稿使旧检查失效；交付前检查当前版本。
- 每次导出 input.json、result.json、checks.json、trace.jsonl、manifest.json、script.md。

## 当前边界

这是初始离线原型。决策使用固定 Mock 策略，写稿使用模板，不代表真实模型 ReAct 能力。真实模型适配、查询改写和开放式自然语言事实审查尚未实现，不满足最终真实模型验收。

素材全部合成，不能作为真实产品宣传依据。时长按每秒4个字/字符估算，并加入画面最低时长和停顿，未做录音校准。规则检查使用严格白名单，无法审核任意改写。

当前核心逻辑集中于 runtime.py，cli.py 和 export.py 已独立；其余预留模块后续按设计拆分。尚无模型供应商依赖或 Key 配置，不应在代码中写入密钥。

## 文档

- [原始需求](require.md)
- [实现范围](docs/01-requirements.md)
- [目标设计](docs/02-solution.md)
- [验证与限制](docs/03-evaluation.md)
- [AI 使用](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)

LangGraph 参考：https://docs.langchain.com/oss/python/langgraph/quickstart
