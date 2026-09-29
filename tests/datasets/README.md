# tests/datasets/

**验证对象：**个体/整合数据 provenance 与共享 split。

**科学不变量：**每条观测能回到 fly/ROI/Results 行；共同冻结刺激共用全局 split；历史 purge 不重叠。

**测试文件：**test_integrated.py；tests/integration/test_phase5.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
