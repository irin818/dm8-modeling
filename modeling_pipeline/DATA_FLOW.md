# 数据对象的生产、消费与单位

| 对象 | Produced by | 主要字段 / shape / units | 科学含义 | Consumed by |
|---|---|---|---|---|
| `StimulusData` | Stage 02 `data.stimulus.load_stimulus_data` | `updates [9000,225]` 数字 ±1；`update_start_display_frame_idx [9000]` 显示帧序号；recipe | 已保存、seed 校验过的数字视觉命令；不是视网膜光强 | Stage 04、06 |
| `ResponseData` | Stage 03 `data.response.load_response_data` | `values [8570,ROI]` 图像强度；`roi_labels`；原始 Results 行序号 | ROI 平均强度，未证实为正式 ΔF/F | Stage 04 |
| `ClockData` | Stage 03 `data.clocks.load_clock_data` | DLP/Zeiss TTL `[frame]` 微秒；PsychoPy flip `[frame]` 秒 | 两个时钟来源与 Zeiss frame-out 代理 | Stage 04 |
| `AlignedSession` | Stage 04 `data.alignment.align_session` | 刺激 `[9000,225]`；响应 `[约8119,ROI]`；update index、time `[frame]` 微秒；source hashes | payload 内每个成像帧对应最近过去更新 | Stage 05、06 |
| `ProcessedResponse` | Stage 05 `preprocessing.normalization.process_individual_response` | `values [8084,ROI]`，原始强度或训练 z-score；`ResponseScaler` | 明确标记的候选响应目标及仅训练拟合尺度 | Stage 08–10 |
| `IndividualDataset` | Stage 06 `datasets.individual.load_individual_datasets` | `X [8084,900]`、`y_raw [8084,ROI]`，时间微秒、split、ROI 名、原始行 | 一只 fly 的模型样本，保留个体来源 | Stage 07–10 |
| `IntegratedDataset` | Stage 07 `datasets.integrated.build_integrated_dataset` | 逻辑 `X [1907824,900]`，物理公共表 `[8961,900]` + 索引；`y [1907824]` 原始强度；fly/ROI/time/provenance | 五 fly 的响应长表，只有一条独立冻结刺激 | Stage 10 的建模概念与来源审计 |
| `PopulationDataset` | Stage 10 `datasets.population.build_population_dataset` | 每 fly `response [8084]`，训练 z-score ROI 均值；ROI membership | 一只 fly 的选定 ROI 群体目标，不是第六只 fly | Stage 10 population-average Ridge |
| RF 结果 | Stage 08 `evaluation.reliability.ReliabilityResult`；历史 `rf.sta.BaselineResult` | Stage 08 每 fly NPZ 三个核 `[900,ROI]`（训练前半/后半、验证诊断）；历史 RF `[lag,15,15,ROI]`；投影 r、shift p | 反向相关估计和训练段响应性，不等同最终预测精度 | Stage 09/10 的分层比较 |
| ModelResult | Stage 09/10 各模型 dataclass | 参数（系数或共享 K）、每 ROI/每 fly prediction `[frame,ROI]`；测试指标 CSV | 明确目标表示与配置的预测结果 | Stage 11 |
| EvaluationResult | Stage 11 `evaluation.comparison` JSON | Pearson r、R²、MSE、normalized MSE、成对 ΔR²、每 fly 汇总 | 对同一目标、同一 fold 的模型比较；飞虫是生物重复单位 | Stage 12 |

处理前后单位必须跟随对象：原始 `Results.csv` 是图像强度；数字 `stimulus_updates` 是 −1/+1 命令；DLP 与 Zeiss TTL 是采集设备微秒；训练 z-score 无单位。15 Hz、120 Hz 是实验配方中的名义更新/显示速率。Zeiss frame-out 不是精确曝光起点。
