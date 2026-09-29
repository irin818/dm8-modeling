# tests/data/

**验证对象：**刺激、响应、时钟与因果对齐。

**科学不变量：**相同时间采用已呈现更新；payload 尾边界为排他；Results 行与 Zeiss 帧一致。

**测试文件：**test_alignment.py；更大真实数据检查见 tests/integration/test_workspace_audit.py。运行全部测试：从仓库根目录执行 `.venv/bin/python -m unittest discover -s tests -q`。运行结果须与 Stage README 的输入、单位和输出一起解释；合成测试不能替代五只 fly 的端到端回归。
