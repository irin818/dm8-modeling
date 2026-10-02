# 基于白噪声反向相关的果蝇 Dm8 神经元时空感受野建模与群体特征分析

## 科学问题与主模型

能否利用二维 binary white-noise stimulation 和 ROI fluorescence，通过 reverse correlation 恢复 Dm8 的时空感受野，并判断哪些空间结构能够跨动物稳定出现？

主模型是白噪声系统辨识得到的 **STRF（spatiotemporal receptive field）**：每个空间位置、每个过去刺激 lag 都有一个与后续荧光变化关联的系数。它描述响应的时空结构；当前项目不声称得到可泛化的 held-out 预测器或完整生物机制。

Li et al. 2021 的 Dm8 RF 工作提供中心与外围空间结构的比较基准。本实验的光学标定和部分上游处理尚未核实，因此比较重点是负中心、中心主导及跨 fly 一致性。文献及实现边界见 [references/README.md](references/README.md)。

## 数据与刺激

来源为五只 fly 的 `Results.csv`、保存刺激、recipe 与设备 TTL。共有236个原始ROI，技术QC后保留228个，分别为40、48、46、48、46。五fly使用同一条15×15 binary white noise，9000次update、约15 Hz、约10 min；保存的数字灰阶0/100映射为分析编码−1/+1，数字校验不等于物理亮度或波长校准。

`MeanN` 是ROI平均图像强度，上游钙信号提取、背景/neuropil处理与ROI身份尚未核实。当前按提供者的Dm8数据标签开展分析，不以基因或subtype作为拟合参数。生物学重复数为5；228个ROI和500次null迭代都不能替代动物重复数。

## 最终方法链及每一步的作用

1. **来源指纹。** 只读 `Dm8_module/` 和 `simulate/`；记录文件大小及SHA-256，运行前后核验。
2. **TTL对齐。** 核验保存刺激的seed/数字灰阶，以marker-locked DLP TTL将Zeiss frame-out对应到此前最后显示的update。frame-out是曝光时间代理，真实曝光窗口未知。
3. **技术ROI QC。** 排除非有限、零值占比≥0.2或无波动的ROI。纳入不依赖RF显著性、中心符号或环绕形状。
4. **Gaussian基线相减。** 使用 `R(t)=F(t)−Gaussian10s(F(t))` 去慢漂移；不在反向相关前进行response z-score。这是离线对称滤波，不用于因果预测。
5. **Gaussian边界处理。** 滤波采用reflect边界；主空间分析丢弃首尾各3σ、约30s，之后重新计算STRF。完整记录仍用于全局lag选择和冻结时间诊断。
6. **40-lag刺激历史。** lag0是当前已显示update，lag1是前一个update，依次到lag39；每帧包含40×15×15个系数位置，绝不使用未来update。
7. **白噪声反向相关。** 对刺激历史与相对荧光计算中心化协方差：

   `K = mean[(stimulus_history − its_mean) × (R − its_mean)]`

   重排为 `[40,15,15,ROI]` 的individual STRF。负系数表示ON刺激与随后较低荧光相关，不直接等同于膜电位抑制。
8. **STRF z-score。** 每个ROI在整个STRF上标准化，保留符号，便于跨ROI比较形态；论文的exact normalization axis并未完全确认。
9. **全局RF能量lag。** 完整记录先计算各ROI的空间RF能量，再fly内平均、fly间等权，选择共同能量峰。当前为lag1；不按正环绕大小选lag。它是空间截面，不是40个lag的积分。
10. **Gaussian中心定位。** 从裁剪后选定lag的空间图，用最大绝对值像素的带符号行/列Gaussian截线估计中心，保留原质量阈值。这里的Gaussian是几何定位步骤。
11. **亚像素对齐。** 双线性平移至共同中心，不wrap；阵列外为NaN，插值和平均只使用有限支持。
12. **层级聚合。** 同fly内ROI等权均值，再五fly等权均值。贡献数量随像素变化，但不将缺失ROI视为零。
13. **空间区域量化。** 中心半径≤1.5 pixel；环绕为3–6 pixel环带。使用有效像素的带符号均值，分别展示五fly和population。
14. **40-lag时间诊断。** 保留冻结的完整记录定义：4×10 raw-covariance参考核定位中心，整数无环绕对齐，再分析lag0–39。它与主空间分析的裁剪/亚像素估计器不同。lag4是事后外周候选。
15. **完整流程null。** 固定seed，500次每fly独立、同fly各ROI共同的原始轨迹circular shift，与零偏移在两个环向均至少相距60s。每次重新计算基线、完整记录能量选lag、裁剪后STRF、中心、对齐、fly及population均值。单侧经验p使用plus-one修正。

Li已取得材料未完整规定STRF到spatial RF的exact temporal rule、插值与边界策略；上述选择是公开声明的项目定义，不能称论文逐步精确复刻。全部空间单位仅为grid pixel。

## 核心结果与解释

五只fly均有负中心，population center = **−1.1235485**；完整流程null的负中心单侧p = **0.001996**。结合先前方法审计，这支持方法稳健、与刺激关联的负中心分量。

population surround = **−0.0006056**，正环绕p = **0.548902**；当前主空间图不支持跨fly保守的宽正环绕。时间诊断在lag4有4/5 fly为正，population surround = **+0.0277113**，属于事后、随时间变化的外周候选，尚非确认性结果。完整结果与历史发现见 [FINAL_RESULTS.md](FINAL_RESULTS.md)。

## 论文图与图注

所有图宽170 mm、白背景、统一字体；PNG为300 dpi，另有可编辑SVG。四张主图的角色依次是空间结构、动物重复、时间结构和统计验证。

- **[Figure 1 — Five-fly and population receptive fields](results/figures/figure_1_receptive_fields.png)**：A–E为五fly，F为等fly群体。六个15×15 panel使用完全相同的对称、零居中色标；十字表示共同对齐中心。值为individual STRF标准化后的协方差系数。
- **[Figure 2 — Fly-level center and surround quantification](results/figures/figure_2_spatial_zones.png)**：A中心、B环绕采用独立y轴；每个fly一个点，空心大菱形为population。保留fly4负环绕与全部点，不绘制SEM、不连接成重复测量。
- **[Figure 3 — Native temporal RF](results/figures/figure_3_temporal_rf.png)**：五fly为细线并用不同线型区分，population为粗线，保留全部40个lag，无平滑。lag1标注early center，lag4只标事后候选。Temporal diagnostic uses the frozen full-record reference-center definition and is not identical to the primary trimmed/subpixel spatial estimator. 一个lag的名义时间约1/15s，精确对应仍以保存TTL为准。
- **[Figure 4 — Full-pipeline circular-shift null](results/figures/figure_4_full_pipeline_null.png)**：A中心、B环绕展示500次完整流程null、实际值及null的2.5/50/97.5%分位数；这不是观测值置信区间。中心panel的明确标记inset仅放大完整null样本范围，主轴仍保留远离null的实际中心。p分别检验负中心和正环绕。
- **[Supplementary Figure S1 — Coverage/support](results/figures/supplementary_s1_support.png)**：有效ROI与fly贡献数。missing support ≠ zero；外围ROI支持低于中心。仅作为覆盖说明，不作独立主结论。
- **[Methods schematic](results/figures/methods_pipeline.png)**：概览共同STRF估计、主空间链与独立冻结时间诊断，明确两种reference定义及null所在层级。

## 代码、结果与复现

唯一入口为 `analysis/run_final_analysis.py`，唯一配置为 `configs/final_analysis.json`。八个科学模块分别负责来源、时序、预处理、RF、中心/对齐、层级聚合、统计及绘图；`__init__.py` 仅标记Python包。集中测试为 `tests/test_final_pipeline.py`。

`results/tables/` 仅含 `dataset_summary.csv`、`fly_rf_summary.csv`、`temporal_rf_summary.csv`、`null_summary.csv`。`results/final_results.json` 只装载当前RF主线的数值、RF/支持矩阵、500次null样本与8项回归证据。`results/source_hashes.json` 保留4,949个受保护文件的逐项指纹。安装和执行见 [README.md](README.md)。

重新计算已核对全部核心数值、RF/覆盖矩阵、240行时间结果、500次null样本及四张表，与简化前精确一致。清理前commit在配置的 `pre_simplification_head` 中记录；历史探索的结论保留于最终结果，执行代码与原输出可从Git历史恢复。

## 限制与适用范围

尚缺上游image/ROI provenance、背景与neuropil处理、实际wavelength/irradiance、视角和视网膜位置、moving-bar localizer、原始movies及真实曝光窗口。外围覆盖截断、同一frozen刺激和5只动物也限制外推。当前结果描述刺激与荧光的关联，不能证明某种膜电位机制，不能将弱环绕候选升级为已复现的空间拮抗。

取得新记录后可按同一RF方法检验外推性；源数据参数或冻结基准需显式更新。本次提交不启动新分析。
