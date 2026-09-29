# tests/features/

**验证对象：**刺激历史特征。

**科学不变量：**每个样本的 lag 不可引用未来更新，首个完整历史索引正确。

**测试文件：**test_lagged.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
