# tests/workspace/

**验证对象：**工作流入口和阶段 receipt。

**科学不变量：**前置 manifest 缺失/哈希变化必须失败；仓库及实验清单不触碰原文件。

**测试文件：**test_workflow.py；实验清单另见 tests/integration/test_workspace_audit.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
