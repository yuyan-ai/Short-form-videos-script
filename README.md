# 短视频脚本 Agent

Python + LangGraph 的短视频脚本原型。Mock 模式无需 Key，live 模式使用配置的真实模型接口。

## 安装与运行（PowerShell）

需要 Python 3.10+。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/overlong.json
.\.venv\Scripts\python.exe -m pytest -q
```

`--mode mock` 为默认模式；`--mode live` 调用真实模型。完成返回退出码 0，缺信息、失败、预算耗尽返回 2。输出目录在命令返回的 output 中。

## 已提供

- 虚构产品“轻剪”的三条合成素材：支持字幕、支持竖屏预览、支持保存脚本草稿。
- 品牌禁用词、中性脚本表达白名单、事实引用检查。
- 五组输入：normal、overlong、no_material、missing_info、tool_failure。
- LangGraph 输入校验、决策、执行循环；次数上限及明确状态。
- 时长逐镜估算；改稿使旧检查失效；交付前检查当前版本。
- 每次导出 input.json、result.json、checks.json、trace.jsonl、manifest.json、script.md。

## 当前边界

Mock 模式使用固定策略和模板，不代表模型 ReAct 能力。live 模式由模型输出经 Pydantic 校验的动作，支持检索查询改写、完整写稿与改稿、检查、补充信息和结束。尚未配置供应商并执行真实模型评估，因此没有真实模型效果证据。开放式自然语言事实审核尚未实现。

素材全部合成，不能作为真实产品宣传依据。时长按每秒4个字/字符估算，并加入画面最低时长和停顿，未做录音校准。规则检查使用严格白名单，无法审核任意改写。

业务工具已拆分至 tools/retrieval.py、tools/duration.py、tools/rules.py；完成门禁位于 policy.py，runtime.py 负责图与节点。其余预留模块后续按设计拆分。模型通过 HTTPX 接入 Chat Completions 兼容接口，供应商兼容性需接入后验证。不应在代码中写入密钥。

## 文档

- [原始需求](require.md)
- [实现范围](docs/01-requirements.md)
- [目标设计](docs/02-solution.md)
- [验证与限制](docs/03-evaluation.md)
- [AI 使用](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)

LangGraph 参考：https://docs.langchain.com/oss/python/langgraph/quickstart

## 配置真实模型

在项目根目录 `.env` 填写以下三项（已创建占位文件；如丢失则复制 `.env.example`）：

```dotenv
LLM_API_KEY=你的密钥
LLM_BASE_URL=供应商提供的HTTPS基础地址
LLM_MODEL=供应商提供的模型标识
LLM_TIMEOUT_SECONDS=45
```

基础地址通常包含 `/v1`，但必须以供应商文档为准；程序自动追加 `/chat/completions`。当前仅支持 Bearer 鉴权及 `choices[0].message.content` 文本响应格式。不同协议需要新增适配器。不要在 `.env.example` 填真实密钥。`.env` 已被 Git 忽略，进程环境变量优先于文件。

```powershell
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json --mode live --max-steps 12
```

live 会将输入、命中素材、规则及当前执行历史发送到所配置的服务。程序不自动回退为 Mock。模型接口失败时导出失败状态；非法JSON消耗一次调用预算并反馈给模型；业务工具异常也反馈模型选择下一步。总时间预算默认180秒，在调用前后检查；正在进行的HTTP请求以单次超时为界，不会被总预算即时取消。

19项测试包含HTTP模拟接入、查询改写、改稿重检、拒绝提前完成、非法输出预算、鉴权失败及超时处理，均不是供应商实际联网测试。已验证依赖版本见 `requirements-lock.txt`。


## 质量检查第二版（2026-10-30）

- 组合关键词检索按事实命中加权排序，产品名称作为次要信号，不搜索JSON字段名。
- 每条引用必须在同一镜头的画面、旁白或字幕中原样出现；禁止无关挂引用，至少有一条展示的产品事实。
- 重复旁白/字幕和每镜超过3秒的额外画面停留会阻止完成。阈值可在 data/brand_rules.json 调整；这是可配置的编辑标准，不是通用视频制作标准。
- 字幕与旁白分别估时，取较大值安排画面，避免短旁白掩盖长字幕；二者不直接相加。
- 报告绑定草稿、素材与规则快照。规则修改后必须重新检查。
- 结果显示总时长、旁白时间和额外画面停留。目标时长按上限处理，不要求填满。
- 当前30项测试通过。原始运行记录保留，不会改写旧报告；旧版通过不意味着通过新版规则。

白名单仍限制写作自由：新增少量审核过的中性过渡表达，但不宣称能自动审核任意自然语言。真实模型可能因反复改稿耗尽预算，系统将明确返回未完成。
