# tests/preprocessing/

**验证对象：**响应尺度与因果候选处理。

**科学不变量：**训练段尺度不会因验证/测试响应变化而重新拟合；在线 EMA 只看当前与过去。

**测试文件：**test_normalization.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
