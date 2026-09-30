# rf/

`characterization.py` 提供反向相关核、Gaussian 中心与 Phase 6.1 严格诊断；`null_tests.py` 保存其时间错位/FDR 工具；`population.py` 提供 Phase 6.2 的能量质心、NaN 无环绕中心平移、有效像素平均、相关/径向曲线、条件性 DoG 门槛。`phase62.py` 负责用固定 4×10 更新估计器将其应用于五次完整记录。

输入核 `[4,15,15,ROI]`，空间图 `[15,15,ROI]`；中心和径向距离单位仅为网格像素。先 ROI 再 fly 层级平均，不能把 ROI 当独立动物。主结果见[Phase 6.2](../../../docs/PHASE6_2_POPULATION_RF.md)，测试见 `tests/rf/`。

`validation.py` 提供 Phase 6.3 的四箱共中心对齐、fly 均值、带符号 zone/径向汇总、精确符号共识、反号抵消与 plus-one null 经验尾部。阈值和区域沿用 6.2，外周峰为描述性检查，不能重新定义主 surround。[Phase 6.3](../../../docs/PHASE6_3_FLY_POPULATION_VALIDATION.md)记录保守的科学解释。
