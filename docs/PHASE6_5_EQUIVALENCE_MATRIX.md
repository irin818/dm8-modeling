# Li 2021 与 CURRENT_PIPELINE_BASELINE 差异矩阵

`EXACT` 只表示该节点有足够证据且实现一致；`CLOSE_APPROXIMATION` 仍有未公开细节。P0 是足以改变科学解释的差异。实际 Phase 6.5 对照标签见冻结配置。

| Stage | Li 2021 | Current | Match level | Potential effect | Fixable with existing data? | Priority | Action |
|---|---|---|---|---|---|---|---|
| 1 raw movie registration | TurboReg time-average | 上游未知 | UNKNOWN | 位移混合 ROI | 否 | P0 | 问实验组 |
| 2 ROI identity | manual Dm8 neurites M4/M5 | MeanN 身份未知 | UNKNOWN | 细胞混合 | 否 | P0 | 要 mask/说明 |
| 3 background subtraction | 未明确 | 未知 | UNKNOWN | 公共荧光伪相关 | 否 | P0 | 要预处理记录 |
| 4 neuropil correction | 未明确 | 未知 | UNKNOWN | surround 污染 | 否 | P0 | 要预处理记录 |
| 5 fluorescence source | raw GCaMP | ROI mean intensity CSV | UNKNOWN | 信号含义不同 | 否 | P0 | 查 Results 导出来源 |
| 6 Gaussian baseline | σ10s subtract | σ10s subtract | CLOSE_APPROXIMATION | 边缘/核截断 | 是 | P1 | 保留 |
| 7 Gaussian edge | 未明确 | reflect, retained | UNKNOWN | 起止伪结构 | 是 | P1 | C4 trim |
| 8 response normalization | 先不标准化响应 | 响应先 zscore | MEANINGFUL_DIFFERENCE | ROI 权重 | 是 | P0 | C1 |
| 9 RF zscore | individual STRF after correlation | 仅用于 center，均值用原 K | MEANINGFUL_DIFFERENCE | group morphology | 是 | P0 | C1 |
| 10 temporal resolution | 未明确 | 4×10 updates | UNKNOWN | 瞬时环绕平均消失 | 是 | P0 | C2 native40 |
| 11 temporal history | 未明确 | 40 updates | UNKNOWN | 可能截断慢响应 | 仅可敏感性 | P1 | 明示限制 |
| 12 reverse correlation | described, exact formula absent | centered covariance | CLOSE_APPROXIMATION | scale/offset | 是 | P1 | 固定公式 |
| 13 stimulus encoding | white-noise UV LEDs | binary digital ±1 DLP | MEANINGFUL_DIFFERENCE | 非线性/空间光学 | 否 | P0 | 独立审计 |
| 14 timing | microscope triggers ~14Hz | posthoc TTL ~15Hz; Zeiss proxy | MEANINGFUL_DIFFERENCE | lag 错位 | 是（敏感性） | P0 | T−1/T0/T+1 |
| 15 STRF→spatial RF | 未明确 | 4 bins signed mean | UNKNOWN | polarity cancellation | 是（敏感性） | P0 | S0/S1/S2 |
| 16 center estimation | Gaussian axis cross-sections | dominant-bin abs peak, sign-orient, Gaussian axes | CLOSE_APPROXIMATION | 错中心 | 是 | P1 | extracted spatial cross-sections/centroid |
| 17 bar localizer | shifting bar before noise | 无对应证据 | MEANINGFUL_DIFFERENCE | 中心落阵列边缘 | 未知 | P0 | 查 localizer |
| 18 alignment interpolation | 未明确 | rounded integer | UNKNOWN | 弱环绕模糊 | 是 | P1 | C5 bilinear |
| 19 boundary padding | 未明确 | NaN crop | UNKNOWN | edge support 下降 | 是 | P1 | coverage |
| 20 group aggregation | neuron group mean | ROI→fly→5-fly equal | MEANINGFUL_DIFFERENCE | ROI/fly 权重 | 是 | P0 | C6/C7 |
| 21 2D→1D projection | 360° 1000 steps | 360° 1000 steps bilinear | CLOSE_APPROXIMATION | anisotropy 消失 | 是 | P1 | 共用投影 |
| 22 DoG form | normalized relative-amplitude DoG | bounded additive M1/M3 | MEANINGFUL_DIFFERENCE | 振幅不可比 | 是但角度未知 | P1 | 两套拟合 |
| 23 spatial units | degrees | grid pixels | MEANINGFUL_DIFFERENCE | width 不可直接比较 | 否 | P0 | 只报 px |
| 24 physical wavelength | 369nm UV peak | unknown | UNKNOWN | 光谱通道 | 否 | P0 | 请求测量 |
| 25 irradiance | ON ~0.1mW/cm² | unknown | UNKNOWN | 对比度/饱和度 | 否 | P0 | 请求测量 |
| 26 stimulus visual angle | ~4°/LED pixel | nominal recipe geometry only | UNKNOWN | RF 截断/宽度 | 否 | P0 | 请求 retinal calibration |
