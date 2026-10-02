# 最终结果：白噪声反向相关与 Dm8 群体感受野

本文件是最终科学结论及历史探索的权威汇总。当前主流程为 reverse correlation / STRF；唯一入口是 `analysis/run_final_analysis.py`。当前机器可读结果不包含已经退出主流程的空间参数化模型。

## 1. Dataset

5只fly，236个原始ROI；技术QC后228个（40、48、46、48、46），不以RF符号或显著性筛选。五fly共用保存的15×15 binary刺激、9000 updates、约15Hz、约10min，数字灰阶0/100对应分析编码±1。每fly有8084帧完整40-update历史，主空间分析3σ裁剪后7307帧。Zeiss frame-out约13.53Hz，是曝光时刻代理；生物学n=5。

## 2. Main RF model

主模型是刺激历史与 `R=F−Gaussian10s(F)` 的中心化协方差，形成 `[40,15,15,ROI]` 的individual STRF；之后每ROI整个STRF做z-score。负系数表示ON刺激与随后荧光下降相关。该系统辨识估计用于RF特征分析，不能直接当作已验证的预测器或电生理抑制机制。

## 3. Primary population spatial RF

完整记录的等flyRF能量选择共同lag1；裁剪后同lag空间图用Gaussian截线定位，双线性亚像素无环绕对齐，先ROI→fly，再五fly等权平均。**5/5 fly中心为负**。这里的Gaussian用于中心定位，属于正式RF主线。

| fly | 中心≤1.5px | 环绕3–6px |
|---|---:|---:|
| fly1 | −0.751888 | +0.005155 |
| fly2 | −1.434101 | +0.000692 |
| fly3 | −0.811939 | +0.016727 |
| fly4 | −1.122387 | −0.028006 |
| fly5 | −1.497428 | +0.002404 |
| 五fly等权 | **−1.1235485** | **−0.0006056** |

单位为individual STRF标准化后的协方差系数。空间图是共同peak-lag截面，不是时间积分。四fly有微弱正环绕，但群体均值接近零、略负；不支持稳定population positive surround。对应主图1、2。

## 4. Temporal RF

冻结完整记录时间诊断中，各fly最强负中心均在lag1，population center = **−1.1019568527**。lag4的population surround = **+0.0277113137**，**4/5 fly为正**。

这是 **post-hoc temporally dependent peripheral candidate**，不能按它的外围正值改选正式空间lag，也不是确认性显著结果。各fly外周峰并非出现在一致lag。该诊断沿用4×10 raw-covariance参考核中心及整数无环绕对齐，与主空间估计器的裁剪/亚像素定义不同。对应主图3。

## 5. Full-pipeline null

固定seed `65020261001`，500次fly独立raw circular shift；同fly各ROI共同移动，两个环向与零偏移至少相距60s。每次完整重做Gaussian baseline、全记录选lag、裁剪后STRF、z-score、中心、对齐及层级平均。

| 统计量 | observed | 单侧empirical p |
|---|---:|---:|
| 负中心 | −1.1235485013 | **0.001996008** |
| 正环绕 | −0.0006055535 | **0.548902196** |

使用plus-one校正。负中心处于500次null样本之外；环绕不支持正向偏离。这是当前五份数据内的错位检验，不是新动物/新刺激上的外部确认。对应主图4。

## 6. Method robustness

**Negative center：METHOD_ROBUST。** 既往标准化顺序、native时间核、边界裁剪、对齐和ROI/fly权重审计均保留五fly负中心。结合完整流程null，正式表述为 **method-robust stimulus-linked negative central RF component**；稳健性范围限于已审计的方法与当前数据。

**Surround：METHOD_SENSITIVE。** 标准化顺序、时间定义和subpixel对齐明显影响微弱外周；fly-equal/ROI-equal没有改变中心结论，也未建立统一宽正环绕。覆盖补图S1说明外围有效ROI支持较低：中心区每像素最少196、中位215；环绕区最少102、中位180.5；全部像素仍有5fly贡献。各fly约23–52%的ROI中心距原阵列边缘<3px，外周可能被截断。

## 7. Comparison with Li 2021

支持相似的negative center与center dominance；当前不支持跨fly保守的broad positive surround。已取得材料没有完整规定STRF→spatial RF的exact temporal rule，当前能量peak-lag、归一化轴、插值及边界是声明的项目选择。物理刺激和上游ROI处理未完成等价核验，不能将差异直接归因于某种生物机制。来源见 [references/README.md](references/README.md)。

## 8. Exploratory model analysis

项目曾探索single Gaussian与antagonistic DoG对群体RF的参数化描述。历史M1的R²≈0.988720、AICc≈−235.102；DoG的R²≈0.988958、AICc≈−226.937。DoG虽略提高R²，但AICc未显示额外正向宽环绕成分的必要性，因此该分析不进入毕业设计主流程，也不改变主要RF结论。数值来自简化前commit `5401a34799c974df40081bc5adbb826a09042173` 的冻结输出，仅在此透明保留；当前runner不重算，执行代码与原表/图可由Git历史恢复。

## 9. Limitations

`MeanN` exact origin、raw movie registration、Dm8 neurite ROI/mask、background/neuropil、实际wavelength/irradiance、visual angle/retinal position、moving-bar localizer、raw movies、曝光窗口与TTL物理意义均未完整核实。`UV-15Hz`目录名与数字灰阶不能证明真实波长、辐照度或论文实验等价。当前按提供标签视为Dm8，不以genotype/subtype为模型参数。

既往预测分析未取得稳定held-out表现；严格预定义individual RF reliability gate为 **0/236 ROI通过**。它们说明现有数据对个体确认性推断与预测外推的限制，不代表population RF不存在；旧可靠性gate不用于当前群体ROI纳入。这些历史发现不属于当前执行流程。

## 10. Final conclusion

The five-fly dataset robustly supports a stimulus-linked negative central Dm8 RF component. A conserved opposite-sign broad surround is not supported by the primary population spatial RF, although weak and temporally dependent positive peripheral structure remains a post-hoc hypothesis for future validation.

五只fly的数据稳健支持与刺激关联的Dm8负中心RF分量。正式群体空间图尚不支持跨fly保守的反号宽环绕；弱、随时间变化的正外周结构仍是事后候选，等待独立验证。信号身份与光学标定的限制不允许据此断言某种生物机制不存在。
