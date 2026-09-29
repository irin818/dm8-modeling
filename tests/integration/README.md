# tests/integration/

**验证对象：**完整数据链与 Phase 5。

**科学不变量：**五 fly 原始记录、source SHA、共同 split、模型矩阵和旧 workspace 审计真实运行。

**测试文件：**test_phase5.py、test_workspace_audit.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
