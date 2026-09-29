# 从实验文件到 X/y/RF：可讲解的处理流程

## 1. 目录发现和文件解析

`workspace.WorkspacePaths` 从 `--workspace-root` 定位 `Dm8_module`、`simulate` 与输出目录，允许分别覆盖。`workspace.scan_data_inventory` 全量扫描原数据，记录每个文件 hash 与格式元数据，所有输出写入 `outputs/audit/`。`data.discover_sessions` 只把含 `Results.csv` 的 `fly*/<run>` 识别为建模会话。每个实验原文件保持只读。

## 2. S(x,y,t)：冻结刺激与三个时间概念

`stim_realized.npz` 的 `stimulus_updates_rc_float32` 是 `[update=9000,row=15,column=15]`，−1/+1 是相对于数字 0/100 灰度的编码。`data.align_session` 仅为矩阵建模将其按 row-major 展平为 `[9000,pixel=225]`。`display_frames_gray_uint8` 有 `[74436,15,15]`，它包括 marker 和后基线，属于完整播放指令；更新数组不是每一帧播放一次。

`stim_structure_priors.json` 提供**计划**的 payload 帧号；`playback/stim_frames.csv` 是播放端 PsychoPy flip 时间；`analysis_marker_lock/dlp_ttl_marker_locked.csv` 是经 marker lock 后同采集钟上的显示帧微秒时间。分析用计划帧号索引实测锁定 TTL，得到 `[9000]` 个更新起始时间。具体 code → file 关系见 [刺激来源](STIMULUS_PROVENANCE.md)。

## 3. F(t)：ROI 表与成像时钟

`Results.csv` 首列是从 1 开始的帧序号，后续每列 `MeanN` 是该 ROI 的平均图像强度；五次分别为 `[8570,42/50/50/48/46]`。当前不能证明这些数值已经过背景、neuropil、运动或 ΔF/F 处理。`zeiss_ttl_<run>.csv` 每行是同一采集设备上的 frame-out 微秒 timestamp `[8570]`。`data._read_results`、`_read_clock` 检查列、有限值、逐帧编号、递增和行数对应，错误即停止。

## 4. 对齐和筛选

对第 i 个 Zeiss 代理时间 `t_i`，用 `searchsorted(update_times, t_i, side='right')−1` 取此前最近一次刺激更新 `u_i`。再要求 `u_i≥0` 且 `t_i < payload_end_us`，排除刺激主体前后帧；得到每只约 `[8119, ROI]` 响应和对应的 update index。**8570 → 约 8119** 主要来自 payload 外筛选；滞后模型还要丢掉开头缺乏完整历史的几十个成像帧。Zeiss TTL 表示 frame-out，并不直接给出曝光起点，时间偏移的影响在审计中仅作探索。

## 5. 预处理候选与模型矩阵

默认 `y=raw ROI mean intensity`，单位为表中强度单位。`preprocessing.candidate_response` 还提供过去 60 秒因果 EMA 扣基线，以及明确标为**候选**的 `(F−F0)/max(F0,1)`。后一分母下限是零值保护，不是正式荧光算法。`model.lagged_design` 对每个合格成像帧抓取当前及过去 `L−1` 次更新，按 `[sample,lag,pixel]` 展为 `X=[sample,L×225]`；不读取未来刺激。`pipeline.build_model_dataset` 将 X、y、时钟、ROI 标签和分块边界装为 `ModelDataset`。

## 6. RF、估计器与留出验证

`model.fit_sta_baseline` 用训练段 `Xᵀy/n` 做 white-noise reverse correlation，核 reshape 为 `[lag,15,15,ROI]`；每个 ROI 的 SVD rank-one 分数描述估计核的时空可分程度。`ridge.fit_binned_ridge` 将 40 个过去更新分成 4 个时间箱并正则拟合；`pixel.fit_pixel_model` 用训练 STA 选一个位置、较早验证段选惩罚，再在晚段评分。它们是同一刺激到响应问题的不同估计/简化方法，不能把 STA 当成与 CNN 同层级的生物学模型。

`splits.blocked_split` 统一现有 70/30 或 50/20/30 时间边界，保留已报告的留出帧数；新增的 `_separate` 检查两段实际使用的更新历史区间**无交叠**。如果成像快于刺激而固定帧数 gap 不够，直接报错。五只 fly 分别训练/评估；由于使用同一冻结刺激，跨 fly 不等于独立随机刺激样本。所有候选变换和 offset 都是探索性；既有测试段已被多次查看，不应称为全新盲测。

## CLI 和模块对照

| 旧入口或数据 | 当前责任模块 |
|---|---|
| 路径散落在调用命令 | `workspace.py`；CLI `--workspace-root`/`--data-root`/`--stimulus-code-root`/`--output-dir` |
| 会话读取及 TTL/响应对齐 | `data.py`，原行为保留 |
| 可讲解的 X/y 对象 | `pipeline.py`；`model.py:lagged_design` |
| 候选 F0 / ΔF/F | `preprocessing.py`，单独标记，未替换主 y |
| STA/Ridge/像素模型各自分块 | `splits.py` 统一边界及刺激历史防泄漏检查；模型算法保持原模块 |
| 逐 ROI、时间、RF 审计 | `audit.py` 和 `scripts/audit_*`；输出到 `outputs/audit/` |

运行命令及每步产生文件见仓库 [README](../README.md)。
