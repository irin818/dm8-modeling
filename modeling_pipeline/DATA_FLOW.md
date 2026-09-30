# 当前数据流与单位

| 对象 | 形状或单位 | 来源 → 用途 |
|---|---|---|
| `StimulusData` | `[9000,225]`，保存的 15×15 数字更新 | `stim_realized.npz`/recipe → 帧对应、40 更新历史。数字命令不是测得光强。 |
| `ResponseData` | 原始 `Results.csv` 的 `[frame,ROI]` 图像平均强度 | ROI 表 → 时钟对齐。不是已核实的正式 ΔF/F。 |
| `ClockData` | DLP/Zeiss TTL 微秒，PsychoPy flip 秒 | 保存日志 → 最近已显示刺激更新映射。 |
| `AlignedSession` | payload 约 `[8119,ROI]`；映射到更新索引和原始行 | `data.alignment` → Phase 6.2 全记录输入；前 35 帧不足 40 更新历史。 |
| Li-style 响应 | 完整 payload raw 减 10s Gaussian 慢基线 | `preprocessing.rf_response` → 离线主 RF；raw 同时诊断。 |
| 粗时间 RF | `[4,15,15,ROI]`，数字刺激 × 标准化响应协方差尺度 | 8,084 个可用样本/每 fly → 带符号空间图。 |
| 中心与对齐图 | `[ROI,2]` 网格像素；`[15,15,ROI]`、NaN 掩码 | 同白噪声估中心 → 无环绕整数平移。无独立 localizer。 |
| fly / population RF | 五张 `[15,15]` fly 图 → 一张 `[15,15]` 群体图 | fly 内 ROI 等权、fly 间等权；生物学 n=5。 |
| 径向与留一 fly | 1D 网格像素曲线、五张四 fly 图 | 描述空间形状与对个别 fly 的敏感性，不能当独立验证。 |

Stage 01–07 的历史数据对象与时间分割仍可在原 Stage 文档和 Git 历史中查找；预测型 Stage 08–12 已退役。完整结果见[Phase 6.2](../docs/PHASE6_2_POPULATION_RF.md)。
