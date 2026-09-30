# Phase 6.1b：RF 时间表示、统计功效与方法审计

**性质：EXPLORATORY REANALYSIS。** 本页只用原 `fold_a` TRAIN 两半和已保存的 Phase 6.1 响应；没有读取 VALIDATION/TEST 响应、训练预测模型、重定阈值或改写 Phase 6.1 的 **0/236 `RF_RELIABLE`**。机器结果位于 `outputs/phase_06/rf_method_audit/`。原始 `Dm8_module/`、`simulate/` 和历史 Phase 6.1 输出均保持原样。

## 1. 方法冻结与可比性

Phase 6.1 确实使用 Phase 5 的预测特征：40 次过去刺激更新平均成 **4 个各含 10 次更新的箱，共 900 特征**。本次主要敏感性比较用已存在的 `features.lagged.lagged_design` 建立 **40 个逐 update 时滞 × 225 像素，共 9,000 特征**，顺序为当前更新、逐次往前。两法固定同一 40 更新历史窗，在当前 15 Hz 数字刺激下约 2.67 秒。保持历史窗相同是为了单独检验时间平均的影响；历史 offsite 分析曾用约 3 秒过去窗口。Li et al. 2021 的方法依据是白噪声反相关和时间精细的 RF，而不是本数据可用的逐次滞后数由论文唯一确定。**40 并非根据本次结果或 TEST 选择。** 当前数字刺激命令未换算成实测照度。

两个方法复用相同的中心化 reverse correlation、A 核到 B 响应的投影、双侧循环错位零模型、dominant 时间截面的行/列 Gaussian 中心法和相同 ROI 有效性规则。因 9,000 特征远多于每半约 1,163–1,165 个成像帧，逐时滞核比 900 特征的粗箱核更容易受估计方差影响；这里检验的是**无正则化 RF 表示**的敏感性，不能排除预先固定的平滑或正则化方法有不同结果。A/B 为 TRAIN 内不重叠刺激历史；Li-style 高斯响应在各半独立处理并截去 3σ 边缘。

Li-style `F − Gaussian_10s(F)` 是本页的 **LI_STYLE_PRIMARY_RF_REANALYSIS**，原因是 Li 2021 的 RF 流程对其自身实验从 raw GCaMP 去除慢 Gaussian 基线，再作反相关与 RF 中心估计；这个方法理由独立于 Phase 6.1 的分数。它是离线、非因果的描述性 RF 响应，不作为后续预测目标。Phase 6.1 按当时预设的 +0.02 表示门槛仍选 raw；本页没有撤销该历史决定。raw 和 60 秒 causal EMA 作敏感性对照。论文对其自身采集史的陈述不证实本包的 ROI 或预处理史。

## 2. A：粗箱与逐时滞比较

以下均为 229 个有效 ROI 的中位数；中心位移是 A/B 估计中心的距离，**不是定位误差或可靠中心精度**。细核的两个相关中位数和中心稳定性均未超过粗核。

| 响应与时间表示 | split-half RF r | A→B 投影 r | 中心位移 px | A/B 中心≤2 px |
|---|---:|---:|---:|---:|
| Li-style，粗 4×10 | 0.0141 | 0.0174 | 6.02 | 52/229 |
| Li-style，细 40×1 | 0.0039 | 0.0105 | 6.93 | 24/229 |
| raw，细 40×1 | 0.0008 | 0.0025 | 7.29 | 23/229 |
| causal EMA，细 40×1 | 0.0042 | 0.0091 | 7.39 | 22/229 |

| fly | 有效 ROI | 粗核 split r / 投影 r / 中心 px | 细核 split r / 投影 r / 中心 px |
|---|---:|---:|---:|
| fly1 | 40 | 0.0222 / 0.0308 / 5.61 | 0.0047 / 0.0129 / 7.53 |
| fly2 | 48 | 0.0342 / 0.0456 / 5.46 | 0.0081 / 0.0234 / 5.28 |
| fly3 | 47 | 0.0108 / 0.0099 / 7.07 | 0.0045 / 0.0139 / 5.67 |
| fly4 | 48 | −0.0236 / −0.0215 / 5.71 | −0.0064 / −0.0170 / 8.01 |
| fly5 | 46 | 0.0244 / 0.0323 / 6.52 | 0.0041 / 0.0107 / 7.67 |

因此当前证据**不支持“4×10 平均是 0/236 的主要原因”**。五只 fly 的细核 split r 均很小，个别中心距离下降但未形成群体稳定性。细核相对粗核增大参数 10 倍，可能把每个时滞的信噪比进一步降低。历史粗核 Li-style 的有效 ROI 指标复算差异（float32 数值精度下）低于 `1e-5`；原历史文件未被覆盖。

## 3. B：TRAIN 内功效曲线

固定 B 半全部帧作为参照；A 半按索引模 4 作预先定义的嵌套、全时段均匀抽样。25/50/75/100% 分别在每 fly 的 A 半使用约 291/582/873/1,163–1,164 帧。各档共用 Li-style、40 时滞、同一中心拟合和固定 B；不以 B 或 TEST 选参数。B 是 TRAIN 内内部参照，不是独立确认数据。

| A 半比例 | 有效 ROI | split r 中位数 | A→固定 B 投影 r 中位数 | 中心位移中位数 px | 中心≤2 px |
|---:|---:|---:|---:|---:|---:|
| 25% | 229 | 0.0002 | 0.0006 | 7.27 | 10 |
| 50% | 229 | 0.0026 | 0.0073 | 6.82 | 11 |
| 75% | 227 | 0.0037 | 0.0096 | 7.35 | 25 |
| 100% | 229 | 0.0039 | 0.0105 | 6.93 | 24 |

相关随样本量有**很小的**上升，中心位移不单调且最终仍约 7 px；fly4 为负，fly1/fly3/fly5 的 100% 指标未持续优于 75%。所以结论为 **NO CLEAR EVIDENCE OF SAMPLE-SIZE-LIMITED RF RECOVERY**。有限样本和细核高维估计仍可能是因素，但现有 TRAIN 曲线不足以证明“只要加数据就能恢复稳定 RF”，更不能外推所需新增 fly 数。不同抽样比例的有效 ROI 数略变，曲线只作群体诊断，不筛 ROI。

## 4. C：独立 localizer / shifting bar 检索

只读遍历 `Dm8_module/`、`simulate/`、`outputs/`、`datasets/` 及项目脚本、文档和配置目录的文件名与可读文本/CSV 前 2 MB，检索 `bar`、`moving_bar`、`shifting_bar`、`localizer`、`rf_center`、`receptive_field`、`mapping`、`position`、`azimuth`、`elevation` 及同义写法；完整候选表及扫描数在 `localizer_search.json`。在本次扫描中，五只 fly 的 `stimulus_package/stim_recipe.json` 均为 `binary_discrete_time`、`formal_rf_mapping`，保存的 offsite `rf_plots/` 是**同一白噪声数据的派生分析**，不能作独立中心。`simulate/07E_260530_01/profiles/stimulus_profiles/operator_moving_bar_screening_balanced_profile.py` 及同目录 fast/wide/120 Hz 配置是**刺激生成模板**：未含这五只 fly 的同步采集响应、ROI 对应表或 RF center。`simulate/` 的文档、准备清单和代码中另有 moving-bar 字样，也未检出当前五次记录可匹配的独立 localizer 输出。

**NOT FOUND：NO LOCALIZER DATA FOUND IN CURRENT WORKSPACE。** 这里的意思是未找到可与当前 `MeanN` ROI 配对的、独立采集的 localizer 数据或中心；并非没有 bar 刺激设计代码。若将来获得 bar run，需核对 fly/run 标识、时钟、ROI ID 和数据采集先后，再决定是否用它独立定中心。Li 2021 的 shifting-bar 先验属于论文自己的实验，不是这五次记录的 provenance。

## 5. D：统计检验家族与未达门槛的证据

历史 944 家族的科学问题是：在四种响应候选与全部 236 ROI 的搜索中，控制这整组 RF 假设的假发现。新 236 家族只回答事先选定单一 Li-style 表示时的 ROI 问题；本数据已看过旧结果，所以它是**探索性重分析**，不能作为独立确认。两家族所有无效 trace 均以 p=1 留在分母中。下表的“粗 Li 236”与历史 Li 行使用**完全相同的 p 值**，仅 BH 家族改变；细 Li 236 另外改变 RF 时间表示。

| 家族 | 假设数 | Li-style 原始 p<0.05 | Li-style BH q<0.05 | Li-style 最低 q |
|---|---:|---:|---:|---:|
| 历史：四响应×236 | 944 | 26 | 0 | 0.0961 |
| 探索：粗 Li-style×236 | 236 | 26 | 0 | 0.2640 |
| 探索：细 Li-style×236 | 236 | 22 | 0 | 0.1762 |

**缩小家族没有使 Li-style 通过 FDR，最低 q 反而上升。** BH 调整取决于整组 p 值的排序，不是单项 p 简单乘假设数；历史四表示中的其他小 p 值改变了排序。粗 Li 的 split r 四分位数约 −0.019/0.014/0.042，投影 r 为 −0.022/0.017/0.053；细 Li 分别为 −0.006/0.004/0.014 和 −0.017/0.011/0.038。粗 Li 有 2 个有效 ROI 同时达到 split r≥0.1、投影 r≥0.1、中心≤2 px，但都未通过旧 q 门槛；细 Li 没有此类 ROI。这些是提示性局部证据，不能形成可靠 RF 集合。

事先已知的 sanity check `fly1/Mean29`：粗 Li 的 split≈0.110、投影≈0.202、中心位移≈0.35 px；细 Li 分别≈0.044、≈0.131、≈0.25 px。细核仍能看到投影关系，但核相关下降；其探索性细 Li q≈0.176，粗 Li q≈0.264，旧 944 家族 q≈0.096。所有参数对 236 ROI 完全相同，没有为 Mean29 调参。

**未来独立实验的建议预注册规则**：在采集及查看新响应前，固定一个 primary RF 响应（若沿用 Li 2021 处理逻辑，可固定 Li-style 离线减基线）、刺激历史窗和时间表示、ROI 排除标准、A/B 或独立 localizer 的中心规则、shift-null 排除窗以及单一 236 ROI BH 家族和 q≤0.05 门槛；raw/causal EMA 各自报告为敏感性分析，不替代 primary 的显著性。若多种时间核也作为可择主结果，应预先并入检验家族或先用独立数据选择。当前没有新实验，故本页不得重命名为 confirmatory。

## 6. 决策与最可能原因

**本轮最接近 OUTCOME 4：暂停 RF-centered dataset 路线。** 逐时滞没有提高整体核恢复；增加当前 TRAIN A 样本仅带来很弱的相关上升，中心仍不稳；没有可匹配的独立 localizer；Li-style 的 236 家族也无 q<0.05。Phase 6.1 的 Gate A/B 继续不通过，**不进入 RF-centered canonical dataset**。

最可能的共同解释是：每半仅约 1,164 个成像帧，而细核有 9,000 个未经正则化的刺激特征；响应为来源/处理史尚不完整的 ROI mean 强度；无独立 bar 中心可锚定、中心需从噪声较大的白噪声核自身估计。刺激物理强度与眼位、ROI mask、motion/neuropil 处理和精确成像相位仍未证实，可能进一步限制 RF 可辨识性。这些是**机制候选，不是由本轮数据分别识别出的因果原因**；不能据此断言 Dm8 没有 RF，也不能说数据没有刺激驱动信号。下一步先做响应质量及实验 provenance 核验；若未来拿到独立 localizer 或新增数据，再事先冻结中心/正则化方法并验证，避免在当前数据上反复挑选阈值。

## 7. 复现与完整性

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run_method_audit.py --workspace-root .
OPENBLAS_NUM_THREADS=2 .venv/bin/python -m unittest discover -s tests -q
```

`summary.json` 保存全体和逐 fly 表、学习曲线、两种 BH 家族及历史文件 SHA-256；`temporal_comparison_roi.csv`、`learning_curve_roi.csv` 保留逐 ROI 诊断。运行前后逐个核对历史 `response/`、`reliability/`、`alignment/` 51 个文件 SHA-256 一致。合成测试覆盖因果时滞、细核信号恢复、粗箱求平均、TRAIN 抽样与只读检索；这些不等于新实验验证。
