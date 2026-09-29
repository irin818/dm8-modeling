# 五次实验数据全量审计与可用性（2026-09-30）

`Dm8_module/UV-15Hz/fly1..fly5` 有 536 个文件，总计 440,142,600 bytes；4 个 `.DS_Store`，532 个实验相关文件。`outputs/audit/data_inventory.json` 为**逐文件**只读清单，含相对路径、fly/run、大小、SHA-256、角色、使用状态、解析状态，以及 CSV 列/行/数值范围、JSON key、NPZ shape/dtype/range、PNG 尺寸。502 个可结构化解析、30 个文本可读、4 个 Finder 文件为不支持格式，**没有解析失败或 Unknown 类别**。`outputs/audit/data_inventory.md` 可直接浏览全部 536 项。

## 文件类别

| 类别 | 文件数 | 模型意义 |
|---|---:|---|
| Existing analysis | 337 | offsite RF 图、normalized trace、summary；只作参考，非原始成像 |
| Stimulus package | 50 | 五次配方、冻结数组、计划、manifest、几何、lineage |
| Playback | 35 | 实际 flip 帧表、启动/状态日志 |
| QC | 30 | 运行日志和实时采集质量 |
| Experimental metadata | 30 | preflight、session/run bundle、实验路径 |
| Calibration | 20 | optical trace、alignment 支持与分析 |
| DLP timing | 15 | 捕获 DLP TTL 及副本 |
| ROI measurements | 5 | `Results.csv` 原 ROI 均值强度 |
| Marker lock | 5 | 锁定后 DLP 帧表及摘要（另 5 个文件归 QC/metadata） |
| Zeiss imaging | 5 | Zeiss frame-out TTL，不是图像 |
| Temporary/generated | 4 | `.DS_Store` |

按 SHA-256 有 27 组重复内容，共 69 个文件参与；包括每次 `capture/dlp_ttl.csv` 与顶层 DLP TTL 副本、部分 offsite 与播放帧表，以及五次完全相同字节的 `stim_realized.npz`。重复文件仍保留原处，不自动删除。五次配方虽然有各自来源路径，冻结 NPZ **字节级相同**（DIRECTLY_OBSERVED）。

## 直接可用与真实缺口

| 项目 | 现状与证据状态 | 用途或限制 |
|---|---|---|
| 15×15、15 Hz 二值刺激，9,000 updates | 文件和代码双重核对，DIRECTLY_OBSERVED | 单条件时空 RF / STRF 的 X |
| 完整数字播放指令，74,436 帧 | NPZ + playback，DIRECTLY_OBSERVED | 前段 marker、主体、后基线区分 |
| DLP、Zeiss TTL | 五次记录均有，DIRECTLY_OBSERVED | 同一采集设备微秒钟上的对齐 |
| ROI 平均强度 | 五个 `Results.csv`，每个 8,570 行，42/50/50/48/46 列，DIRECTLY_OBSERVED | 当前 y；不是已证明的钙浓度或 ΔF/F |
| offsite RF / `normalized_results_trace.csv` | 有，DIRECTLY_OBSERVED | 先前分析输出；其 `analysis_manifest.json` 明确来源为 `results_csv_raw`；不能当成官方预处理 |
| ROI masks、坐标、背景/neuropil 区域 | 五次运行内未找到，UNRESOLVED | 无法重算 ROI 或独立核验 ROI 身份 |
| 原始 CZI/TIF/movie、运动校正/registration | 未找到；bundle 的 `raw_video_origin_path` 为空，UNRESOLVED | 无法从原视频重做成像处理 |
| 正式 F0/ΔF/F、指示剂/GCaMP | 未找到可追溯产物，UNRESOLVED | 只能做明确标注的候选变换 |
| genotype / subtype / 条件标签 | 未找到，UNRESOLVED | 用户毕设按 Dm8 数据约定，不纳入基因参数 |
| 波长、辐照度、gamma 曲线 | 未找到五次实验的物理标定，UNRESOLVED | `UV-15Hz`、`blue`、green 数字通道均不能推出物理光谱 |
| 完整六月刺激代码快照 | Windows 路径指向另一日期，UNRESOLVED | 本地代码对八数组功能等价，但版本身份未证 |

`Results.csv` 是已经存在的 ROI 测量表。`simulate/07E_260530_01/03_attach_results_07e.py` 的职责是**附加/验证现有表**，05L `results_trace_adapter.py` 依据帧号和 Zeiss TTL 派生时间；`analysis_manifest.json` 标注 `results_csv_raw`。**是谁用什么 ROI 提取软件从图像生成这个表仍未查明**，不能把附加脚本误说成原始提取器。

## 时间轴与响应质量

每次 74,436 条锁定 DLP TTL 与数字显示帧一致；8,570 条 Zeiss TTL 与 ROI 行一致。中位间隔分别为 8,333 μs（约 120 Hz）和 73,899 μs（约 13.53 Hz，DERIVED）。五次这两条时钟均单调，无重复/倒退，也无大于各自中位间隔 1.5 倍的间隔。Zeiss frame-out 是曝光时刻的代理，不是曝光起点的直接记录。位于 payload 内的成像行约 8,119，完整 18-update 刺激历史后约 8,103–8,104；具体按模型滞后数另有差异。

`outputs/audit/roi_quality.csv` 覆盖 236 个 ROI 的 count、均值/中位数/标准差/CV、分位数、0 值、极大值重复、首尾十分位漂移、跳变、异常值、lag-1 自相关及谱峰。含 0 值的 ROI 在 fly1–5 分别为 8、20、16、13、9；首尾十分位强度变化中位数约为 −1.8%、−56.3%、−11.8%、−43.0%、−18.0%（DERIVED），提示明显的跨时间非平稳性；它不单独证明漂白，可能混有运动、亮度、ROI 定义或其他因素。

## RF 与候选预处理

`outputs/audit/rf_quality.csv` 对 236 个 ROI 计算早段两半 STA 核的相关、后段固定核投影相关、rank-one SVD 能量及局部峰位置。RF 投影的 circular-shift null 在第二个早段块上打散刺激—响应对应，同时保留 ROI 时间相关；显著性证据还来自此前像素模型的晚段 circular-shift null、全 236 ROI 的 FDR q。高可信另要求训练/验证像素位置一致、正向 split-half 核一致和早段 shift-null p<0.05。分类结果：**HIGH 31，MODERATE 38，LOW 45，NO_DETECTABLE 122**。这是保守的 *stimulus-response signal-quality* 分类；早段 p 不是跨 ROI 校正的 RF-kernel p，且分组包含先前测试集结果，不能再把这 31 个 ROI 的测试成绩当盲测确认。

`outputs/audit/candidate_preprocessing.csv` 比较原始 F、过去 60 秒 EMA 基线扣除、候选 `(F−F0)/max(F0,1)`。分母下限 1 个强度单位是为本数据的零强度所作**人为保护**，故第三者尤其不能称为正式 ΔF/F。EMA 后，fly1/2/4/5 的 split-half 核中位相关略升，fly3 不升；但后段投影相关的改善不一致，五只 fly 均在接近零的小量级。**当前没有经验依据把某一种候选确定为全局最可靠的正式输入**；主模型继续采用 raw ROI mean intensity，EMA 仅为敏感性比较。此处还未验证 running percentile 或特定文献方法，不能声称比较了所有可能预处理。

`outputs/audit/timing_offset_sensitivity.csv` 固定原像素模型权重，将有效 Zeiss/DLP 偏移在 −500 至 +500 ms、50 ms 步长下重放，同时计算固定像素位置的早段时域滤波器强度、半程一致性。各 fly 的中位测试相关峰值位于 +50、0、+450、−50、−150 ms；三种指标的峰也不在五只 fly 间共同出现。位置在原时钟下选定，重放没有为每个偏移重训练，因此只说明敏感性（ESTIMATED），不提供时钟修正。`outputs/audit/cross_fly_rf.json` 对 31 个高可信 ROI 的空间能量图作描述：各 fly 局部峰 row 5–11、col 7，成对相关 0.03–0.62。相同冻结刺激、每 fly 仅 3–10 个被选 ROI 和未知 ROI 对齐限制了生物学解释。

## 对当前弱预测的解释边界

STA、Ridge 与紧凑像素模型的多数 ROI 后段 R² 为负；结合非平稳强度、零值、未知 ROI 来源及缺乏正式荧光预处理，可提出**数据与时间代理可能限制预测**的假设。偏移检查没有统一校正证据。也不能排除真实神经响应较弱、测量噪声或模型假设不足；这些不是已证明的因果排序。现有数据适合毕业设计的**单条件 RF 描述、可解释局部时空模型和验证流程展示**；单次记录对单 ROI 的精确预测较弱，且不支持光谱建模。
