# Li 2021 RF 方法的来源审计

主来源：[Li et al., Current Biology 2021, main article and STAR Methods](https://www.sciencedirect.com/science/article/pii/S0960982221006151)，本地副本 `color_modify_research/papercore/2021_Li_NeuralMechanismSpatioChromaticOpponencyDrosophila.pdf`；RF 主图见该 PDF 第7–8页，刺激与钙成像 STAR Methods 见第21–23页。交叉来源：[Drews et al. 2020](https://www.sciencedirect.com/science/article/pii/S0960982219313752)，[Arenz et al. 2017](https://pubmed.ncbi.nlm.nih.gov/28343964/)。Figure S4 所在补充 PDF 未能可靠取得；其细节不能从正文推定。

标签：`LI_SOURCE_DEFINED` 正文/STAR 明示；`LI_REFERENCED_BUT_NOT_SPECIFIED` 仅给文献引用；`LI_RECONSTRUCTED_FROM_REFERENCE` 引文文献明确给出；`UNRESOLVED` 证据不足。

| 节点 | 状态 | 来源支持和限制 |
|---|---|---|
| raw image registration | LI_SOURCE_DEFINED | 全部时间帧用 Fiji TurboReg 对齐 time-average image。未公开具体变换和参数。 |
| ROI definition | LI_SOURCE_DEFINED | 手工 ROI；Dm8 individual neurites 根据 M4/M5 protrusions 界定。 |
| imaging trace for RF | LI_SOURCE_DEFINED | raw GCaMP signal 用于 RF mapping。具体背景/neuropil 操作未说明。 |
| baseline | LI_SOURCE_DEFINED | 10 s Gaussian low-pass 后从原始信号相减；这是 `F-G10s(F)`，不应替换成 ΔF/F。边界策略未说明。 |
| reverse correlation | LI_SOURCE_DEFINED | 用 white-noise stimulus 和相对信号得到 individual spatiotemporal RF。精确协方差归一化/去均值细节未说明。 |
| RF normalization | LI_SOURCE_DEFINED | individual spatiotemporal RF 在 reverse correlation 后 z-score；标准化轴未说明。 |
| STRF→spatial RF | LI_REFERENCED_BUT_NOT_SPECIFIED | 正文未规定 peak slice、积分或 separable 分量。Drews 文本提到 spatial RF，却未明确时间压缩公式；故 `METHOD DETAIL UNRESOLVED`。 |
| RF center | LI_SOURCE_DEFINED | 对 spatial RF 的 elevation/azimuth cross-sections 作 1D Gaussian fits。切线位置、符号处理、拟合损失/边界未说明。 |
| center alignment | LI_SOURCE_DEFINED | individual RF 中心对齐后平均。最近邻/双线性及有限阵列外策略未说明。 |
| group averaging | LI_SOURCE_DEFINED | group 内 neuron RF 平均；正文未指定先等 fly 还是全部 neuron 等权。 |
| 2D→1D | LI_SOURCE_DEFINED | mean 2D RF 在 360°内旋转 1000 steps；每步投影再平均。插值和边界规则未说明。 |
| DoG | LI_SOURCE_DEFINED | `exp(-φ²/(2σcen²)) − Arel exp(-φ²/(2σsur²))`；σsur 上界 60° 源于 Supplement Figure S4；幅度/符号是论文的归一化约定。未标定视角则无法等价使用 60°。 |
| white noise and timing | LI_SOURCE_DEFINED | 约 10 min，stimulus/imaging 约 14 Hz，显微镜触发刺激更新；细节依赖论文装置。 |
| pre-noise localizer | LI_SOURCE_DEFINED | shifting-bar 用于估计阵列上 RF center；实际用于后续截取/定位的精确算法未说明。 |
| physical stimulus | LI_SOURCE_DEFINED | UV LED peak 约369 nm、ON 约0.1 mW/cm²、单 LED pixel 约4°。这些是 Li 实验值。 |

## Figure 4 的实际比较组

本地论文 PDF 第 7–8 页的 Figure 4 caption 明确给出：D 是 wild-type R7；E 是 **wild-type Dm8**；F 是 `R7,R8-NorpA`；G 是 `R1–R6,R7-NorpA`；H 是 `R1–R6,R8-NorpA`。F–H 是 photoreceptor channel isolation 操作条件，不能把它们当作 pDm8/yDm8 分组。图及本地正文未给出当前五只 fly 对应的 genotype 或 subtype 身份；Table S1/补充文件无法核实该细节，故 `SUBTYPE / GENOTYPE UNRESOLVED` 对当前数据仍成立。

STAR Methods 还明确写的是“center-aligned RFs among **all neurons in one group**”生成 mean spatiotemporal RF，所以 C6 的全部 ROI 等权更接近论文形态展示；C7 则是本项目跨动物解释所需的等 fly 权重。Li 另说明每个 neuron 2D RF 可转为 1D RF 用于统计性质比较，不能将 group projection 与 per-neuron 参数统计混同。

## 引文方法追踪

- [Drews 2020](https://www.sciencedirect.com/science/article/pii/S0960982219313752) 能确认 mean-subtracted calcium 与刺激做 reverse correlation；其 spatial RF 用水平/垂直 Gaussian 截线定位，peak 对齐后旋转/投影 1D；文中承认投影忽略 anisotropy。没有找到可证明其 STRF→spatial RF 时间规约、zscore 轴或插值方法的文字。
- [Arenz 2017](https://pubmed.ncbi.nlm.nih.gov/28343964/) 的公开摘要可核对论文身份与 RF 背景，尚未找到可核实上述实现细节的开放全文或代码。不能称其为已复现的实现。
- 因此 Phase 6.5 的 peak-energy 和 fixed-integral 版本均为**预先声明的敏感性分析**；不称“exact Li pipeline”。
