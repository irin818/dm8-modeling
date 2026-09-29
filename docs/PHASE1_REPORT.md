# 第一阶段：真实实验数据入口与时空基线（2026-09-29）

## 目标与范围

本阶段用 `Dm8_module/UV-15Hz` 的五次记录，验证冻结刺激、播放时间、显微镜时间信号与 `Results.csv` 是否可形成一致的数据入口；随后建立可复现的初步时空预测基线。本报告不将 ROI 平均强度认定为已验证的 Dm8 ΔF/F。

原始实验目录仅被读取。全部生成结果存放在仓库忽略的 `outputs/` 下。
本机实验目录中的 532 个有效文件与上传的 `Dm8_module.zip` 逐个按大小及 CRC 核对，全部一致；数据 QC 输出还记录了建模输入文件的 SHA-256。

## 数据入口结论

| 项目 | 五次记录的核验结果 |
|---|---|
| 刺激更新 | 每次 9,000 个 `15×15` 二值图案，约 15 Hz |
| 显示帧与锁定 DLP TTL | 每次均为 74,436 条，一一对应；中位间隔 8.333 ms |
| ROI 行与 Zeiss TTL | 每次均为 8,570 条，一一对应；中位间隔 73.899 ms |
| 落在刺激主体内的成像帧 | 每次约 8,119 帧 |
| ROI 列数 | fly1–5 分别为 42、50、50、48、46 |
| 播放记录与 DLP TTL | 扣除会话固定偏移后，时间差绝对值的 99% 分位约 9–10 ms |
| 采集及标记锁定 | 五次记录的已有 QC 标志均为通过 |

模型使用 `stim_realized.npz` 的实际保存刺激数组。对于刺激时间，使用 `analysis_marker_lock/dlp_ttl_marker_locked.csv`；对于 ROI 行时间，使用 `zeiss_ttl_<run>.csv`。两者均为同一采集设备的微秒计时。每个成像帧只取它之前已经呈现的刺激更新。Zeiss frame-out TTL 只是帧曝光时间的代理，真实帧内采集时刻仍需确认。

## 留出时段预测结果

先运行 45 个刺激更新（约 3 秒）历史的 reverse-correlation STA，并比较其秩一空间×时间近似。训练使用前 70% 的可用记录，隔开 45 帧，再测后段。又运行 4 个时间区间、每区间 10 个刺激更新的 Ridge STRF；正则化由较早的验证段选择，后段评估仍与训练段隔开。两类方法分别对原始 ROI 平均强度和仅使用过去数据的 60 秒指数去漂移信号运行。

下表是各果蝇全部 ROI 的**测试集相关系数中位数**；括号中为 R² 中位数。负 R² 说明其平方误差甚至高于以测试集均值为基准的常数预测，不能宣称模型具有实用预测能力。

| 输入/模型 | fly1 | fly2 | fly3 | fly4 | fly5 |
|---|---:|---:|---:|---:|---:|
| 原始强度，STA | 0.005 (−0.419) | 0.017 (−2.714) | −0.014 (−0.552) | 0.013 (−0.347) | 0.045 (−0.257) |
| 去漂移，STA | 0.005 (−0.280) | −0.009 (−0.478) | −0.017 (−0.396) | −0.014 (−0.264) | 0.028 (−0.244) |
| 原始强度，Ridge | 0.010 (−0.199) | 0.015 (−2.222) | −0.011 (−0.294) | 0.015 (−0.117) | 0.084 (−0.036) |
| 去漂移，Ridge | 0.006 (−0.028) | −0.015 (−0.080) | −0.016 (−0.114) | −0.020 (−0.039) | 0.048 (−0.026) |

这是探索性筛查：原始强度与去漂移等方案已查看同一后段结果，不能把其中较好的一个重新称为完全独立的最终测试成绩。需要重新设计正式的模型选择与验证，再报告确定性结论。

## 如何解释这一阶段

计数、单调时间信号和播放时间的检查支持**文件之间存在可用的时间关联**。它们没有证明图像 ROI 是 Dm8、强度代表可靠钙响应、光刺激达到标称物理亮度，或光学标记与显微镜曝光绝对时间没有系统偏差。

低预测性可能来自 ROI 身份与质量、背景/运动伪影、荧光预处理、真实曝光时间与 frame-out 的差异、记录条件，或模型仍过于简单。现有结果无法在这些解释之间作因果判定。既有 `offsite_analysis/ref` 中的 RF 图和核是计算输出，没有留出预测成绩；不能用图形看似有结构来替代验证。

`alife_study_exp` 当前检出的 Python 源码服务于 Allen Visual Coding/DANDI 学习项目，未发现这套 Dm8 实验的刺激生成或设备播放源码。冻结的刺激矩阵已经足够继续进行单条件时空分析，但要核对亮度、空间方向和实际 UV 条件，还需要实验端代码及物理校准资料。

## 科学与工程上的下一关

1. 取得 ROI mask、标注、基因型和成像/钙指示剂信息；确认哪些 ROI 对应 Dm8，以及 `Results.csv` 是怎样提取的。
2. 核查原始成像、运动校正、背景与 neuropil 校正、基线和 ΔF/F 算法；至少取得可追溯的预处理说明及质量指标。
3. 核对 Zeiss frame-out 与真实曝光时刻，并用实验端刺激/播放代码确认图案方向和亮度映射；取得波长和辐照度测量。
4. 完成上述响应核验后，在独立验证设计下重新估计 (K(x,y,\tau)) 和空间—时间可分离性，并比较可解释模型与紧凑神经网络。
5. 光谱模型及完整整合模型需有多波长、强度和条件标签的数据。当前单条件记录无法识别光谱效应。

## 可复现命令

在仓库根目录执行 README 中的环境安装步骤后：

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --qc-only
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --output-dir outputs/first_pass
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --response-transform causal_ema_60s --output-dir outputs/ema_exploratory
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --model ridge --output-dir outputs/ridge_raw
.venv/bin/dm8-model --data-root /Users/irin/Documents/Dm8_module --model ridge --response-transform causal_ema_60s --output-dir outputs/ridge_ema_exploratory
```

各方案的完整逐 ROI 数值、核和数据 QC 分别位于所选 `outputs/<方案>/` 目录；这些输出未提交到 Git，也没有修改实验数据。
