# tests/evaluation/

**验证对象：**纯指标和成对评估。

**科学不变量：**Pearson r、R² 与 normalized MSE 对同一目标/同一 fold 解释；避免把 ROI 当独立 fly。

**测试文件：**test_metrics.py；整合评估见 tests/integration/test_phase5.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
