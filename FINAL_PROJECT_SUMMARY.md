# Dm8视觉感受野：毕业设计项目说明

## 研究背景与问题

果蝇视觉系统的Dm8神经元参与颜色信息处理。Li et al. 2021使用UV LED白噪声刺激报告Dm8的中心与环绕空间拮抗。本项目用五次已保存实验回答：能否从刺激和ROI荧光轨迹恢复一个可解释、跨动物一致的RF；负中心及正环绕分别得到多少数据支持？

## 数据与RF的含义

数据为5只fly、236个原始ROI的`Results.csv`、保存的15×15 binary刺激及设备TTL。五fly使用同一条9000-update白噪声，约15Hz、约10min；技术QC后保留228个ROI。`MeanN`是ROI平均图像强度，尚未证明为正式校正后的钙响应。RF系数描述过去某位置刺激ON与随后荧光变化的关联；负系数表示荧光下降关联，不能直接等同于电生理抑制机制。

## 最终计算流程及理由

1. 从保存刺激/recipe核验seed与数字灰阶，用marker-locked DLP TTL把每个Zeiss frame-out映射到此前已显示update。真实曝光窗口仍未知。
2. 只排除非有限、过多零值或无波动的技术无效ROI，避免按最终RF形状筛选。
3. 使用`R=F−Gaussian10s(F)`去慢基线；这是离线、非因果描述性处理。空间主分析丢弃两端各约30s，降低边界影响。
4. 建立40个独立过去update lag的设计，计算stimulus-response covariance；不提前标准化响应，再对每ROI整个STRF做zscore，使RF形态可平均。
5. 完整记录的五fly等权RF能量选择一个全局lag（当前lag1），没有按正环绕选择时间；裁剪后同lag空间图用Gaussian轴截线定位中心。
6. 双线性亚像素平移到中心，不wrap；阵列外为NaN，平均只计算有效支持。先fly内ROI均值，再五fly等权，使独立层级仍为5只动物。
7. 输出固定区域中心/环绕、覆盖以及native时间诊断。时间诊断沿用完整记录的固定参考中心/整数对齐，以复现已冻结lag1/lag4读数；配置明确区分其用途。
8. 对1000步旋转投影比较single Gaussian与antagonistic DoG；同一表征下用AICc衡量第二空间分量是否必要。
9. 对原始轨迹做500次每fly共同circular shift，完整重做选lag、预处理、RF、中心、对齐和聚合，检验中心是否只是重新定位产生的假象。

Li公开材料没有完全定义STRF→spatial RF的exact temporal rule；当前peak-lag规则是本项目声明的实现假设。RF归一化轴、插值和有限视野支持也不能自动认定为论文精确实现。全部空间量采用grid px。

## 最终代码结构

| 模块 | 用途 |
|---|---|
| `data.py` / `timing.py` | 只读来源、刺激/ROI校验、TTL关联和文件哈希 |
| `preprocessing.py` / `rf.py` | Gaussian响应、native设计、协方差、STRF标准化和区域量 |
| `alignment.py` / `population.py` | Gaussian中心、无环绕对齐、有效支持和等fly聚合 |
| `models.py` / `statistics.py` | 最终两个空间模型、信息准则、完整流程错位null |
| `plotting.py` | 七张毕业设计主图 |
| `analysis/run_final_analysis.py` | 唯一正式runner：读取原始来源到所有最终输出 |

## 结果、解释和局限

5/5 fly有负中心，正式群体中心约−1.12355；完整流程null的单侧p≈0.001996。环绕均值约−0.000606，正环绕p≈0.549，single Gaussian足以描述群体空间图（R²≈0.989、AICc优于DoG）。中心对已审计方法稳健，弱环绕对时间、标准化和插值敏感。

lag4完整记录诊断中4/5 fly出现正外周，群体约+0.0277；这是事后时间候选，不能用作已复现的宽环绕。结论及各fly数值详见[FINAL_RESULTS.md](FINAL_RESULTS.md)。

主要边界为上游image/ROI provenance、背景与neuropil处理、物理wavelength/irradiance、视角、独立moving-bar localizer、RF边缘截断和真实曝光时刻。取得这些信息或新动物/新seed数据后，可沿同一流程重新分析；基因与subtype不作为当前拟合参数。

## 复现与维护

运行方法见[README.md](README.md)。唯一配置为`configs/final_analysis.json`；输出五张核心表、七张主图及汇总JSON。runner在运行前后核验全部受保护来源哈希，并检查冻结数值；`simulate/`、`Dm8_module/`不移动、不编辑。测试覆盖时序、RF、中心/对齐、聚合、模型与null的科学不变量。科学结论和结果保留于当前仓库，研究过程可从Git历史恢复。

主图依次展示：[五fly/群体RF](results/figures/figure_1_rf_maps.png)、[时间曲线](results/figures/figure_2_temporal_rf.png)、[fly中心/环绕](results/figures/figure_3_fly_zones.png)、[群体空间拟合](results/figures/figure_4_population_fit.png)、[模型比较](results/figures/figure_5_model_comparison.png)、[完整流程null](results/figures/figure_6_full_pipeline_null.png)、[有效覆盖](results/figures/figure_7_coverage.png)。数值表为`dataset_summary.csv`、`fly_rf_summary.csv`、`temporal_rf_summary.csv`、`model_comparison.csv`、`null_summary.csv`，均在`results/tables/`。

最终验证完成两次从源数据的完整计算（迁移前与删除旧实现后）：11个关键数值检查通过；全部RF/覆盖数组、240行时间诊断、12个M1/M3拟合的R²/AICc和500次null的中心/环绕样本均与冻结基准精确一致。19项集中测试全部通过，4,949个源文件的内容哈希及大小与清理前记录一致。[final_results.json](results/final_results.json)保留计算与回归证据，[source_hashes.json](results/source_hashes.json)保留逐文件指纹。

当前正式工作树为34个Git文件、12个活动Python文件（九个科学模块、必要的包标记、唯一runner、集中测试）。256个历史受Git管理路径已移除，旧输出与缓存一并清理；原始目录及其内部文件全部保持原位和原内容。历史结论已迁入`FINAL_RESULTS.md`；旧runner、variant框架、可靠性/预测实现和重复说明不再属于活动项目。清理前基准commit记录在唯一配置中，可从Git历史恢复。

最终流程是在多轮预测、RF reliability、population validation和preprocessing audit后确定。
