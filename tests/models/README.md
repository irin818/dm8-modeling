# tests/models/

**验证对象：**旧单 fly 模型、CNN 和五 fly 模型。

**科学不变量：**保存模型可重播；验证调参和测试评分分离；共同刺激 split 不跨 fly 泄漏。

**测试文件：**test_legacy_models.py、test_cnn.py；共享模型真实/合成检查见 tests/integration/test_phase5.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
