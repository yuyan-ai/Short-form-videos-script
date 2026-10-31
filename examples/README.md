# 演示输入与实际运行记录

inputs 下包含五个可运行的离线输入：

- normal：有素材且时长通过。
- overlong：初稿增加画面停留导致超时，Mock 压缩后重检。
- no_material：未知产品没有命中素材，返回 needs_input。
- missing_info：缺少 audience，返回 needs_input。
- tool_failure：显式注入检索工具错误，返回 failed。

demo_scenario 是离线演示开关，不是产品事实。Mock Trace 的 actor 标记 deterministic_mock；Live 标记 live_model。

runs 中包含程序实际执行的 Mock 和 Live 记录，以 manifest.json 的 mode 区分。Mock 记录不证明真实模型能自主决策。异常输入的非零退出码是预期行为。
