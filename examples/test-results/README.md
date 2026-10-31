# 自动化测试报告

执行日期：2026-10-31。结果：40 passed，耗时3.74秒。

执行命令（PowerShell，在仓库根目录）：

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=examples/test-results/pytest.xml 2>&1 | Tee-Object -FilePath examples/test-results/pytest.txt
```

- pytest.txt：本次实际终端输出。
- pytest.xml：JUnit格式，每个用例的执行结果。

不需要调用真实模型。HTTP模型接入测试使用模拟响应，不能作为真实模型能力证据。真实服务记录另见 [验收索引](../../docs/06-acceptance.md)。
