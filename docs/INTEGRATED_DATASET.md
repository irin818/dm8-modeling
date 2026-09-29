# 五只 fly 的整合数据集

## 为什么整合

五次记录播放同一份冻结的二值视觉刺激。整合让模型检验跨 fly 共享的刺激到 ROI 强度映射，并保留每只 fly 的读出参数。它**没有**把独立刺激序列数从 1 增至 5；236 个 ROI 也不是 236 只动物。生物学重复单位是 fly，ROI 嵌套于 fly，成像帧嵌套于 ROI。个别 ROI 是否真正属于 Dm8、已做何种荧光校正，原文件尚不能独立验证。

## 数据对象和维度

`IndividualDataset` 每只 fly 一份：原始 `y_raw=[eligible imaging frame, ROI]`、15 Hz 更新索引、Results.csv 原始行索引、Zeiss frame-out 代理时间、全局分块标签、公共因果特征表引用。每只 fly 约 8,084 个具备 40 更新历史的成像帧；ROI 数依次为 42、50、50、48、46。

`IntegratedDataset` 是逻辑长表，每行 `(fly, run, ROI, imaging frame)` 对应一个目标 `y`，以及一个指向共同特征表的 `X` 索引。实测为 **1,907,824 条 ROI×成像帧观测、236 个 ROI、5 只 fly、8,961 个有完整历史的独特刺激更新**。逻辑 `X=[1,907,824,900]`，实际只存 `feature_table=[8,961,900]` 和每条观测的行索引，避免约数 GB 的刺激特征重复。`IndexedFeatureMatrix.materialize()` 默认拒绝超过 512 MB 的整表分配。

刺激源 `stim_realized.npz` 内的 `stimulus_updates_rc_float32=[9000,15,15]` 是已保存的数字刺激矩阵，不需要从生成脚本推测实现图案。特征是 40 个**当前及过去**的更新，按每 10 个更新平均为 4 个时间箱，再展平 15×15 空间。因此 `X=[sample,4×225]`；一个更新可被多个成像帧及 ROI 使用。灰度编码为数字 −1/+1；缺少实际视网膜照度与光谱校准，不能解释为绝对物理光强。

`y` 默认是 `Results.csv` 各 `MeanN` ROI 的原始平均图像强度；不称为已验证的钙活动或正式 ΔF/F。`response_kind`、`preprocessing_kind` 随对象和实验结果保存。

## 逐行来源

`IntegratedDataset.explain_row(i)` 返回 fly、run、原 ROI 列名、ROI 内序号、Results.csv 数据行序号、Zeiss 时间、刺激更新索引、原始响应数值、分块标签、源文件 SHA-256。`outputs/experiments/phase5_first_round/<fold>/dataset/` 有 manifest、236 行 ROI 贡献表、来源示例和八项诊断图。长表本身不写回原始数据目录。五次刺激数字矩阵加载后逐元素相等才建立公共特征表，否则失败。

## 归一化与 ROI 筛选

主分析对每个 ROI 用该 fold 的 **TRAIN** 成像帧计算均值和标准差，冻结后用于验证和测试；零方差 ROI 标记并以 1 作尺度。单独保留原始强度单位的对照。候选响应包括因果 EMA 残差、带安全分母的候选 EMA ΔF/F、前 60 秒窗口的块中位数残差，均只使用当前或过去的响应。它们不是正式实验预处理，也不是对相同目标的等价尺度换算。

`TRAIN_DEFINED_RESPONSIVE` 只由训练数据的前后半 RF 一致性、后半投影与循环位移零模型、零值比例确定；验证稳定性另列诊断，测试响应不参加筛选。阈值中的未校正 p<0.05 是探索性筛查，不能直接用作单 ROI 显著性结论。Fold A、B 分别选到 21、30 个 ROI。

## 全局时间切分和防泄漏

所有 fly 在相同刺激更新编号上分成 TRAIN、VALIDATION、TEST、PURGE。Fold A：训练更新 `[39,4500)`、验证 `[4539,5400)`、测试 `[5439,6750)`；Fold B：训练 `[39,5400)`、验证 `[5439,6750)`、测试 `[6789,9000)`。相邻区间之间隔 39 个更新，确保长 40 的过去刺激窗口不跨区间重叠。未使用的更新标为 UNUSED。程序在全局更新轴上检查窗口和分块，而不是各 fly 随机分样本；同一刺激更新及其历史在所有 fly 中取相同标签。

Fold A 的测试窗口被 Fold B 用作验证窗口，且本项目历史模型已查看过较晚数据。因此这两折是**探索性、相关的时间验证**，不是两个独立盲测。模型超参数只用本折验证集选，测试集不参与本折拟合或 ROI 选择；结论不能声称外部泛化已被独立确认。

## 复算

从仓库根目录：

```bash
.venv/bin/dm8-model dataset build-individual --workspace-root .
.venv/bin/dm8-model dataset build-integrated --workspace-root .
.venv/bin/dm8-model dataset describe-integrated --workspace-root .
.venv/bin/dm8-model fit all --workspace-root .
```

配置在 `configs/phase5_first_round.json`；结果在 Git 忽略的 `outputs/experiments/phase5_first_round/`。原始 `Dm8_module/` 和刺激源码 `simulate/` 只读。入口实现见 `src/dm8_modeling/datasets/`、`features/`、`preprocessing/` 和 `experiments/`。
