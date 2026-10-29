# 初版评估

实际执行环境：Python 3.10.9，Windows，LangGraph 1.2.18，Pydantic 2.14.1。依赖快照见 requirements-lock.txt。

执行 `.\.venv\Scripts\python.exe -m pytest -q`：11 passed。
覆盖五类场景、超时长修正后的重新检查、无法满足时长、预算耗尽、旧报告失效、无依据数字及错误引用。

| 场景 | 实际状态 | 时长估算历史（秒） | 运行结果 |
| --- | --- | --- | --- |
| normal | completed | [9.75] | [20261029-184727-eeca460e](../examples/runs/20261029-184727-eeca460e/result.json) |
| overlong | completed | [39.5, 9.75] | [20261029-184730-d26c1211](../examples/runs/20261029-184730-d26c1211/result.json) |
| no_material | needs_input | [] | [20261029-184732-11181ea5](../examples/runs/20261029-184732-11181ea5/result.json) |
| missing_info | needs_input | [] | [20261029-184734-9c0f5970](../examples/runs/20261029-184734-9c0f5970/result.json) |
| tool_failure | failed | [] | [20261029-184737-c661b39e](../examples/runs/20261029-184737-c661b39e/result.json) |

以上为真实执行的离线程序结果。动作来自固定 Mock 策略，不是实际 LLM 决策；不能作为最终 ReAct 通过证据。后续需要真实模型接入、结构化动作校验、查询改写及工具错误反馈后的模型决策。当前工具故障直接终止。

当前素材为合成资料，模板草稿仅演示已有事实。时长采用简单估算，不是录音结果。规则检查采用白名单，无法覆盖自由自然语言事实审核。目标设计中的总期限、模型调用预算与供应商接入尚未实现，当前仅有离线动作次数上限及图递归兜底。
