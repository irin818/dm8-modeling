# tests/rf/

**验证对象：**RF 与零模型。

**科学不变量：**STA 使用训练窗口；零模型/可靠性与预测模型评分分开解释。

**测试文件：**test_rf.py；真实数据检查见 tests/integration/test_phase5.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
