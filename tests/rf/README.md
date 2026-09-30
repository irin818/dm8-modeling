# tests/rf/

**验证对象：**RF 与零模型。

**科学不变量：**STA 使用训练窗口；零模型/可靠性与预测模型评分分开解释。

**测试文件：**`test_rf.py` 保留历史 STA/零模型回归；`test_phase6.py` 检查 raw 不变、Li-style 可复现、causal past-only、TRAIN/TEST 隔离、provenance、RF shape、BH-FDR、合成 Gaussian 中心/稳定性、中心平移和分类不使用 TEST。真实数据检查见 `tests/integration/test_phase5.py` 与 Phase 6.1 的五 fly 端到端重跑。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。合成测试不能替代真实数据的 Gate 结果。
