# 验收材料索引

题目：短视频脚本 Agent。

## 功能与运行证据

以下路径均相对于仓库根目录。每个运行目录包含input.json、result.json、checks.json、trace.jsonl、manifest.json和script.md。

| 考核项 | 实际记录目录 | 结果与边界 |
| --- | --- | --- |
| 正常生成 | [20261030-214720-59de406b](../examples/runs/20261030-214720-59de406b) | Mock完成，3镜头、9.75秒；仅验证流程 |
| 缺关键信息 | [20261029-184734-9c0f5970](../examples/runs/20261029-184734-9c0f5970) | 缺少audience，needs_input；输入校验前退出，Trace为空 |
| 无素材 | [20261029-184732-11181ea5](../examples/runs/20261029-184732-11181ea5) | Mock检索无结果，needs_input |
| 工具失败 | [20261029-184737-c661b39e](../examples/runs/20261029-184737-c661b39e) | Mock注入工具故障，failed |
| 超时后修正与重检 | [20261030-205518-b25d9aa3](../examples/runs/20261030-205518-b25d9aa3) | Mock压缩后重检，completed |
| 模型路径一：空检索后改写查询 | [20261029-192730-6ac7b49b](../examples/runs/20261029-192730-6ac7b49b) | Live多次检索后命中P01并完成；旧版成稿后被新版规则拒绝，不作为当前质量通过证据 |
| 模型路径二：结构错误反馈后调整 | [20261030-205515-30f83875](../examples/runs/20261030-205515-30f83875) | Live非法结构输出后返回合法动作，completed、22.75秒 |
| Live修改用户超时稿 | [20261031-131035-e68839aa](../examples/runs/20261031-131035-e68839aa) | 修改为28秒且审核通过；首稿来自用户，当次Trace未附首稿估时报告 |
| 模型路径三：超时观察与引用错误后修改 | [20261031-153621-1799c0bf](../examples/runs/20261031-153621-1799c0bf) | 初始观察39.5秒，模型改至20.5秒，再按引用错误改至18.5秒；最终审核错误且预算耗尽，未宣称完成 |

五类必须场景均有实际程序记录；其中离线异常演示不证明模型决策能力。模型决策证据另列Live路径，没有将Mock当作ReAct证据。

## 自动化测试

- [文本报告](../examples/test-results/pytest.txt)
- [JUnit XML](../examples/test-results/pytest.xml)
- [测试说明及复现命令](../examples/test-results/README.md)

测试覆盖正常、缺信息、无素材、工具异常、超时修改、无法满足时长、预算耗尽、旧报告失效、事实引用、原创审核和本地HTTP接口。具体断言见tests/。

## 文档对应

| 规范 | 文件 |
| --- | --- |
| 环境、安装、运行 | [README](../README.md) |
| 用户、目标、范围、验收场景 | [需求](01-requirements.md) |
| 流程、动态决策、版本职责及取舍 | [方案](02-solution.md) |
| 实际结果、失败及限制 | [评估](03-evaluation.md) |
| AI范围、个人贡献、3小时用时 | [AI与个人贡献](04-ai-usage.md) |
| 难点、学习收获、下一步 | [复盘](05-retrospective.md) |

## 最终提交信息

- 题目名称：短视频脚本 Agent。
- 题号：4。
- GitHub：[yuyan-ai/Short-form-videos-script](https://github.com/yuyan-ai/Short-form-videos-script)。
- 最终commit SHA：7942b0a67053f81e72636a3f51f4ede116ba6597。
- 实际投入时间：3小时（作者自述）。
