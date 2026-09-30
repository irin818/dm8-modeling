# 向实验组索取的信息（Phase 6.5）

这些项目是现有文件无法核实的实验 provenance，不是开始描述性重算的前置许可。任何缺失项都不得用目录名或 RF 形状推断。

| 优先级 | 需要确认 | 用途 |
|---|---|---|
| P0 | Results.csv 每列 MeanN 的提取软件、原始图像、处理与单位 | 确定响应定义 |
| P0 | 是否做 motion correction/TurboReg；参数和日志 | 对比 Li 注册 |
| P0 | ROI 是否 individual Dm8 neurite，ROI mask/坐标/层位 | 排除混合及检查 coverage |
| P0 | background subtraction 是否做过 | 排除共同背景 |
| P0 | neuropil/common signal correction 是否做过 | 排除空间伪结构 |
| P0 | raw movie 是否仍在、能否只读复核 | 恢复上游 provenance |
| P0 | 对应 moving/shifting-bar localizer 及中心标注 | 核对 RF 阵列位置 |
| P0 | 实际 stimulus wavelength/spectrum | 光谱等价 |
| P0 | ON irradiance 与光强调制/gamma 曲线 | 强度等价 |
| P0 | 实测 visual angle per pixel、array 在 retinal field 位置 | RF 大小/边界 |
| P1 | fly1–5 genotype 是否相同 | 跨动物可比性，不进入模型参数 |
| P1 | p/y Dm8 subtype 标签/比例 | 仅解释群体组成 |
| P1 | imaging gain、laser power、depth、field position | 信号权重 |
| P1 | 其他 stimulus seed/repeat | 重复性 |
| P1 | control/background ROI | 排除共同信号 |
| P1 | Zeiss frame-out TTL 的准确物理时刻与曝光窗口 | timing offset |
