# 派生数据层

这里保存**可重建的元数据和清单**，不复制 `Dm8_module/` 的原始 Results、TTL、刺激 NPZ，也不把几 GB 的逐 ROI 特征矩阵写入 Git。生成的 `manifest.json`、summaries 与 cache 被 Git 忽略；各目录 README 可追踪。

| 层级 | 一行的意义 | 主要对象 | 读取/生成阶段 |
|---|---|---|---|
| 实验原数据 | 保存的图像强度、时钟、数字刺激 | `Dm8_module/` | Stage 01–04，只读 |
| Individual | 一只 fly/run 的一个成像帧，`y [frame,ROI]` | `IndividualDataset` | Stage 06 |
| Integrated | 一个 fly/run/ROI/成像帧观测，逻辑 `y [1,907,824]` | `IntegratedDataset` | Stage 07 |
| Population | 一只 fly 内训练段选定 ROI 的平均响应，`y [frame]` | `PopulationDataset` | Stage 10 |

五只 fly 共享一条 frozen stimulus：生物观测增加，独立刺激序列仍为 1。Stage 07 的特征表 `[8961,900]` 只存一次，观测通过索引引用它。必须保留 fly、run、ROI、Results 原始行、微秒时间、刺激更新、响应处理类型、split 和源 SHA。详见 [`DATA_FLOW`](../modeling_pipeline/DATA_FLOW.md) 与源模块 [`datasets/README`](../src/dm8_modeling/datasets/README.md)。
