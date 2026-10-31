# 短视频脚本 Agent

基于 Python 和 LangGraph 的短视频脚本生成项目。输入主题、受众、平台和时长上限，结合本地产品素材生成分镜、旁白和字幕，并检查事实引用与预计时长。

提供 CLI 和本地 Web 界面。可以不配置密钥运行 Mock，也可以接入兼容 Chat Completions 的模型服务。

## 功能

- 按关键词检索产品素材，在分镜中标注来源 ID。
- 根据主题、受众和风格生成脚本，支持导入已有脚本改写。
- 逐镜估算时长；超出上限后，模型可压缩脚本并重新检查。
- 检查事实引用、品牌禁用词和画面停留；原创文案另发一次模型请求审核。
- 保存脚本、检查报告和执行记录，方便回看每一步的动作及结果。

## 快速开始

需要 Python 3.10+。以下命令在项目根目录执行，使用 PowerShell。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json
```

默认使用 Mock，无需密钥或模型联网。它使用固定模板，适合检查安装和执行流程，不用于评估模型的写作能力。

运行结束后，终端会打印任务状态和输出目录。成功退出码为 `0`；需要补充信息、执行失败或预算耗尽时为 `2`。

### Web 界面

```powershell
.\.venv\Scripts\python.exe -m short_video_agent.web
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)，填写输入并提交任务。页面可查看分镜、检查结果和执行记录，也可下载 Markdown 与 JSON。

端口占用时使用 `--port 8001`。前端无需 Node.js；Live 模式使用后端的模型配置，不在页面填写密钥。按 `Ctrl+C` 停止服务。

## 接入模型

首次配置时，将 [.env.example](.env.example) 复制为项目根目录的 `.env`，填写供应商提供的参数：

```dotenv
LLM_API_KEY=你的密钥
LLM_BASE_URL=https://供应商地址/v1
LLM_MODEL=模型名称
LLM_TIMEOUT_SECONDS=45
```

`LLM_BASE_URL` 需使用 HTTPS，不包含 `/chat/completions`，程序会自动追加该路径。当前支持 Bearer 鉴权及 `choices[0].message.content` 文本响应格式。进程环境变量优先于 `.env`；`.env` 已加入 Git 忽略规则。

```powershell
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json --mode live --max-steps 20
```

Live 会将输入、检索素材、品牌规则和执行历史发送给配置的模型服务，可能产生调用费用。连接失败时返回失败状态，不会自动切换到 Mock。

## 输入与输出

输入文件示例：

```json
{
  "topic": "介绍轻剪字幕功能",
  "audience": "短视频创作者",
  "platform": "抖音",
  "target_seconds": 30,
  "style": "清晰自然",
  "product_id": "qingjian",
  "query": "字幕"
}
```

`topic`、`audience`、`platform` 和 `target_seconds` 为必填项。目标时长按上限处理，不要求填满。产品素材在 [data/materials.json](data/materials.json)，品牌规则在 [data/brand_rules.json](data/brand_rules.json)。

每次运行默认保存到 `examples/runs/<run_id>/`：

| 文件 | 内容 |
| --- | --- |
| `script.md` | 可编辑的分镜脚本、引用和时长 |
| `result.json` | 脚本、任务状态、检查结果和风险提示 |
| `input.json` | 本次输入 |
| `checks.json` | 规则检查报告 |
| `trace.jsonl` | 动作参数、工具结果和简短决策依据 |
| `manifest.json` | 模型标识、素材和规则快照 |

可用 `--output` 指定其他输出目录。任务状态包括 `completed`、`needs_input`、`failed` 和 `budget_exceeded`。

### 修改已有脚本

使用 `--draft` 导入待改脚本：

```powershell
.\.venv\Scripts\python.exe -m short_video_agent.cli --input examples/inputs/normal.json --draft examples/inputs/revise_draft.json --mode live --max-steps 20
```

草稿 JSON 只包含 `title` 和 `scenes`，结构参考 [示例草稿](examples/inputs/revise_draft.json)，不要附带 `revision` 或旧检查报告。导入稿会重新估时，并在执行记录中标为用户提供。

## 执行流程

LangGraph 负责输入校验和决策循环。Live 模式下，模型选择检索、保存草稿、估时、检查、请求补充或结束等动作；工具结果会反馈给下一轮决策。无素材时可改写查询，超时或检查不通过时可改稿重检，也可说明无法满足要求。

只有当前草稿的时长和规则检查均通过，任务才能完成。修改草稿会使旧报告失效；报告同时绑定素材和规则快照。原创文案的模型审核通过，也不能绕过引用等确定性检查。

CLI 默认动作预算为 `10`，可通过 `--max-steps` 调整；原创审核额外占一次预算。Live 总时间预算默认为 180 秒，在请求前后检查，正在进行的请求仍受单次超时限制。

## 测试与运行记录

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前包含 40 项测试，覆盖正常生成、缺少信息、无素材、工具失败、超时改稿、检查失效、审核拒绝及预算限制。测试中的 HTTP 模拟与真实服务运行分开记录。

[examples/inputs](examples/inputs) 提供五类流程输入和一份待修改草稿。[验证报告](docs/03-evaluation.md) 记录测试结果及真实模型运行，包括查询改写、结构错误恢复、脚本压缩和未完成案例。已验证的依赖版本见 [requirements-lock.txt](requirements-lock.txt)。

## 已知限制

- 示例产品“轻剪”及其素材均为合成数据，不能作为真实产品宣传依据。
- 时长按每秒 4 个字或字符估算，结合字幕阅读、最低画面时长和停顿计算，未做录音校准。
- 原创文案由同一模型的额外请求审核，可能漏判，仍需人工核查。Mock 只验证流程，不验证主题和风格适配。
- 本地 Web 服务一次执行一个任务，不支持取消、上传素材或在页面直接编辑脚本。任务索引保存在内存，重启后清空；导出文件仍保留。
- Web 服务仅监听本机，用于本地开发，尚未做生产部署和并发压力测试。

## 项目结构

```text
src/short_video_agent/   # 决策循环、模型接入、工具和运行入口
frontend/               # 本地 Web 界面
data/                   # 合成素材与品牌规则
tests/                  # 自动化测试
examples/               # 示例输入、输出与执行记录
docs/                   # 需求、设计和评估文档
```

## 相关文档

- [原始需求](require.md)
- [需求与范围](docs/01-requirements.md)
- [实现方案与设计取舍](docs/02-solution.md)
- [测试结果与真实运行记录](docs/03-evaluation.md)
- [AI 辅助记录](docs/04-ai-usage.md)
- [项目复盘](docs/05-retrospective.md)
