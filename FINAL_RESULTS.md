# 最终结果与科学结论

本文件是毕业设计的权威结果汇总。数值来自已冻结的五 fly 数据；正式复算入口为 `analysis/run_final_analysis.py`，机器可读结果在 `results/final_results.json`。开发过程由 Git 历史保存，最终运行不依赖旧阶段输出。

## 1. 数据事实

5 只 fly、236 个原始 ROI；最终技术筛选保留 228 ROI（40、48、46、48、46），不以响应显著性筛选。五次实验共用同一条保存的 binary stimulus：15×15、9000 updates、约15 Hz、约10 min、数字灰阶0/100（分析编码±1）。每 fly 有8084帧完整40-update历史；空间主分析裁剪10s Gaussian首尾各3σ后为7307帧。Zeiss frame-out 约13.53 Hz，是曝光时间代理。ROI 列 `MeanN` 为图像平均强度，上游钙信号处理尚未核实；生物学重复为5只 fly。

## 2. 历史预测结果

基于当前 frozen white-noise 数据，预测模型未获得稳定的 held-out performance，因此毕业设计主分析转向 receptive-field characterization。旧预测实现不参与最终流程。

## 3. 个体 RF 可靠性

严格预定义的 individual RF reliability gate 中 **0/236 ROI 通过**。这说明个体 ROI 的信噪比与现有样本不足以支持确认性个体 RF 推断，不代表群体 RF 不存在。该历史结论保留，严格筛选不用于当前群体 ROI 纳入。

## 4. 群体空间 RF

正式空间图使用：`F−Gaussian10s(F)` → native40 stimulus-response covariance → 每个完整 STRF 后 zscore → 一个全局能量峰 lag（当前为lag1）→空间图 Gaussian 截线定位→双线性亚像素无环绕对齐→fly内ROI均值→五fly等权。**5/5 fly中心为负**。

| fly | 中心区均值 | 3–6px环绕区均值 |
|---|---:|---:|
| fly1 | −0.751888 | +0.005155 |
| fly2 | −1.434101 | +0.000692 |
| fly3 | −0.811939 | +0.016727 |
| fly4 | −1.122387 | −0.028006 |
| fly5 | −1.497428 | +0.002404 |
| 五fly等权 | **−1.123549** | **−0.000606** |

单位是individual STRF zscore单位；空间单位仅grid px。主空间图是预定义全局peak-lag截面，不是对40个lag简单积分。四fly的环绕值微弱正，但五fly平均接近零且略负，不能将其写成稳定宽正环绕。

## 5. 完整流程 null

固定seed `65020261001`、500次独立fly circular shift、与零偏移至少相距60s。每次从共同平移的原始ROI轨迹重做Gaussian baseline、完整记录能量选lag、裁剪后RF、RF zscore、中心、对齐和fly/population平均。

| 统计量 | 实际值 | 单侧 empirical p |
|---|---:|---:|
| 群体负中心 | −1.1235485013 | **0.001996008** |
| 群体正环绕 | −0.0006055535 | **0.548902196** |

这是当前数据内的错位检验，不是新动物或新刺激上的独立确认。它支持stimulus-linked负中心；不支持保守空间图中的正环绕。

## 6. Native temporal RF

完整记录的40-lag时间诊断中，各fly中心最强负响应均在 **lag1**，五fly中心约−1.101957。**lag4有4/5 fly环绕为正，群体约+0.027711**。这是已观察后提出的 temporal candidate，不能按其正环绕幅度选它替代正式lag1空间图。不同fly的正外周峰出现在不同lag，尚未建立跨动物一致的延迟环绕。

为忠实复现该时间诊断，它沿用完整记录、4×10参考核的dominant-energy中心和整数无环绕对齐；它是同一runner中的固定诊断输出，不是正式裁剪/亚像素空间估计器的时间曲线。两种定义及单位在配置、代码和图注中明确保留。

## 7. Gaussian / DoG

最终空间图的1000步360°旋转投影，按固定绝对峰0.01重标后拟合（只换振幅单位，不改空间形状）。M1为single Gaussian；M3为中心负/环绕正的antagonistic DoG，与`a*(Gcenter−Arel*Gsurround)`同形。比较使用同一投影和AIC/AICc/BIC。

| 群体模型 | R² | AICc |
|---|---:|---:|
| Single Gaussian M1 | **0.988720** | **−235.102311** |
| Antagonistic DoG M3 | 0.988958 | −226.937077 |

M1的AICc更低约8.17，因此正式population spatial RF不需要一个保守的正环绕DoG。无约束双Gaussian曾提示外围多尺度结构，但结果依赖表征且跨fly泛化不稳，未进入最终模型。拟合宽度只报px；Li论文60°环绕上界缺少本实验视角标定，不能称角度等价拟合。

## 8. 与 Li 2021 的比较

支持相似的negative center与center dominance；没有稳定复现broad positive surround和population antagonistic DoG。论文公开材料尚未完全规定STRF→spatial RF的时间压缩规则，因此当前全局能量peak-lag是一项明确的实现假设。论文WT Dm8与photoreceptor channel-isolation组也不能未经证据映射到当前五fly。来源见[references/README.md](references/README.md)。

## 9. 方法审计结论

- **Negative center：METHOD_ROBUST。** 标准化顺序、native时间核、edge trim、对齐和ROI/fly权重改变后，五fly负中心始终保留。
- **Surround：METHOD_SENSITIVE。** 响应先zscore与RF后zscore改变弱环绕；native时间分析揭示时间依赖；subpixel对齐明显改变微弱外周符号；ROI-equal/fly-equal没有改变中心结论，均未建立统一宽正环绕。
- 对齐后的外围有效ROI贡献少于中心。主环绕区每像素最少102 ROI、中位180.5，而中心最少196、中位215；仍全部有5fly贡献。约23–52%的ROI中心（按fly）距原阵列边缘<3px，外周可能被截断。

## 10. 实验限制与下一步

优先核实：`MeanN` exact origin、raw movie registration、individual Dm8 neurite ROI/mask、background/neuropil处理、实际wavelength和irradiance、visual angle及retinal field position、moving-bar localizer、raw movies、Zeiss曝光窗口与TTL的物理意义。genotype/subtype仅是可比性解释信息，不进入当前模型参数。目录名`UV-15Hz`与数字命令不能证明物理光刺激等价。

当前主要可计算方法差异已完成检验。高价值下一步是获得上述实验记录或新数据，而不是继续提高模型复杂度。

## 11. 最终项目结论

The five-fly dataset robustly supports a stimulus-linked negative central Dm8 RF component. A conserved opposite-sign broad surround is not supported by the primary population spatial RF, although weak and temporally dependent positive peripheral structure remains a hypothesis for future validation.

这五只fly的数据稳健支持一个与刺激相关的Dm8负中心RF分量。正式群体空间RF尚不支持跨fly保守的反号宽环绕；弱、随时间变化的正外周结构仍是等待独立验证的假设。由于信号身份与光学标定未核实，不能据此断言某种生物机制不存在。
