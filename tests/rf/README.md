# RF 测试

`test_phase6.py` 覆盖严格 RF 核与响应不变量；`test_rf_method_audit.py` 覆盖历史方法审计；`test_population.py` 覆盖无环绕对齐、有效像素平均、fly 层级和 DoG 门槛等 Phase 6.2 规则；`test_validation.py` 验证 Phase 6.3 的共同 raw 平移、重新预处理/中心估计、四箱共中心、偏移排除、经验尾部与符号抵消。运行：`.venv/bin/python -m unittest discover -s tests -q`。合成单元测试不能替代五只 fly 的真实数据报告。
