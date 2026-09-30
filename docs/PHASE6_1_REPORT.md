# Phase 6.1 完整报告：响应重建、RF 可靠性与中心对齐准入

**运行日期**：2026-09-30。**输入**：五只 fly、236 列 `MeanN`、同一条已保存的 9,000 更新数字刺激。**结论**：Phase 6.1 的计算链已完成并验证，但按事先固定的多重检验和中心稳定规则，**0/236 ROI 达到 `RF_RELIABLE`**；Gate A/B 不通过，暂不进入 Phase 6.2，也不增加深度模型。完整机器可读结果在 Git 忽略的 `outputs/phase_06/`。

## 1. 项目阶段与历史保留

Phase 1–5 和原 Stage 01–12 现为 `HISTORICAL / LEGACY BASELINE`：STA 预测基线、旧 Ridge/Pixel、compact CNN、绝对坐标 Shared/Hierarchical STRF、shared basis、population-average 路径都不再是新研究默认入口。Phase 6.1 从独立的 `modeling_pipeline/phase_06/run.py` 运行；新代码不调用旧预测模型。旧报告、模型比较表、保存权重、命令兼容层、回放和回归检查仍保留，以便毕业设计解释科学过程，也避免把历史负结果抹掉。Stage 08 旧训练段响应性表只用于方法对照，不向新分类提供 ROI 白名单。

## 2. 证据边界与目标含义

文件直接证实：`Results.csv` 的 `MeanN` 是逐帧 ROI mean intensity；五次分别有 42、50、50、48、46 个 ROI；offsite manifest 将来源称为 `results_csv_raw`；刺激数组、DLP/Zeiss TTL 和原始哈希可核对。工作假设：每列暂指一个 individual Dm8-related neurite ROI 的 raw/near-raw GCaMP fluorescence `F(t)`，不是一个已验证的完整独立神经元。五只 fly 才是生物重复。Li 2021 同体系论文描述其自身的 movie registration、人工 neurite ROI、10 秒 Gaussian RF 基线、反相关、z-score 和中心拟合；这些步骤是本项目**方法依据或推断**，不是当前五份文件的已证实采集史。原 movie、mask、ROI 坐标及当前记录是否经过 motion/neuropil correction 仍未解。详见 [证据登记](PHASE6_ASSUMPTIONS.md)。

## 3. TRAIN-only 方案与响应表示

采用 Phase 5 `fold_a` 的 TRAIN 更新，分两半，中点两侧各空出 40 个刺激更新；Li-style Gaussian 在每个半段独立计算，丢弃 3σ 边缘。五只 fly 每半约剩 1,163–1,165 帧。A/B 的刺激历史不重叠。四种表示共用这些成像行：raw、Li-style `F - Gaussian_10s(F)`、60 秒 causal EMA residual、60 秒 causal block-median residual。Li-style 是 **NON-CAUSAL / OFFLINE RF CHARACTERIZATION ONLY**，不能直接送入未来 held-out 预测。每个派生数组都有原始 `Results.csv` SHA-256、参数与 causality provenance；没有更改 raw。

表示选择使用运行前固定的 TRAIN fly-balanced 分数：每 fly 对有效 ROI 分别求 split-half RF r 与 A→B 投影 r 中位数，平均两项后再跨 fly 平均。非 raw 表示须比 raw 提高至少 0.02 才替换。四种表示的结果为：

| 表示 | 有效 ROI | median split-half RF r | median A→B projection r | median 中心位移（像素） | TRAIN fly-balanced 分数 | FDR q<0.05 |
|---|---:|---:|---:|---:|---:|---:|
| raw | 229 | −0.0010 | −0.0030 | 6.27 | 0.0016 | 0 |
| Li-style offline relative | 229 | 0.0141 | 0.0174 | 6.02 | 0.0165 | 0 |
| causal EMA residual | 229 | 0.0088 | 0.0125 | 6.25 | 0.0130 | 0 |
| causal block-median residual | 229 | 0.0017 | 0.0027 | 6.27 | 0.0089 | 0 |

另外 7 个 ROI 在 TRAIN 中零值比例过高，未进入有效检验。Li-style 的**观察分数最高**，相对 raw 高约 0.0149；最佳 causal EMA 高约 0.0114，二者均未达到事先固定的 0.02 清晰增益线。按预设规则，本轮记录的 **RF characterization 选择为 raw**，未来 **predictive representation 暂选 raw**；这不是宣称 raw 在生物学上更好。Li-style 保留为必做方法对照和将来独立数据的敏感性分析，不以事后降低门槛来改变本轮结论。没有根据测试 R² 选表示。

## 4. 可靠性、中心与五只 fly 的结果

对 TRAIN A/B 核相关、A→B RF 投影、10 秒排除区的双侧循环时间错位零模型、四表示×236 ROI 的 BH-FDR、原始零值比例及 Gaussian 中心位移作联合判断。无效 trace 以 p=1 留在全部 944 项检验家族中。最低有效 q≈**0.0961**，故没有 ROI 满足 q≤0.05。虽然各表示分别有 18–27 个 *未校正* p<0.05，它们不能替代全家族 FDR。分类 `RF_RELIABLE / RF_WEAK / RF_UNRESOLVED` 只表示刺激响应证据，不表示 Dm8 身份。

| fly | RF_RELIABLE / total | 可靠 ROI 的 split-half RF r 分布 | 可靠 ROI 的中心半段位移分布 |
|---|---:|---|---|
| fly1 | 0 / 42 | 不可估计 | 不可估计 |
| fly2 | 0 / 50 | 不可估计 | 不可估计 |
| fly3 | 0 / 50 | 不可估计 | 不可估计 |
| fly4 | 0 / 48 | 不可估计 | 不可估计 |
| fly5 | 0 / 46 | 不可估计 | 不可估计 |
| **总计** | **0 / 236** | **空集** | **空集** |

在未通过可靠性筛选的 229 个有效 ROI 中，raw 的中心半段位移中位数约 6.27 网格像素，Li-style 约 6.02；这些数字只作失败原因诊断，**不是可靠 RF 中心精度**。个例 fly1/Mean29 的 Li-style TRAIN split-half r≈0.110、投影 r≈0.202、中心位移≈0.35，但全家族 q≈0.096，故仍不得纳入可靠集合。中心拟合只用 TRAIN，行/列 Gaussian 网格拟合及绝对能量 centroid 可作为未来预定义的敏感性比较；本轮没有看 TEST 后改中心算法。

Stage 08 历史规则曾选出 fly1/2/3/4/5 分别 9/2/1/2/7 个，共 21 个；旧规则无本轮跨表示 FDR，也未把中心稳定作为门槛。新旧数量不在同一检验定义下，不能称作“RF 生物信号变差”或“改善”。本轮方法更保守，**未证明可靠性改善**。

## 5. Center alignment 与 Gate

只允许 `RF_RELIABLE` ROI 进入规范中心 `(7,7)` 的无环绕平移及群体平均。当前集合为空，因此每 fly 和跨 fly 的均值 RF 保存为 NaN 并标记 `has_reliable_rf=false`；对齐前后 fly 内、跨 fly RF 相似度均是 `null`。**本轮不能声称 center alignment 提高或降低了相似度。** DoG/center-surround 群体拟合也缺少可靠中心对齐样本，暂不作生物结论。

| Gate | 预设要求 | 实际结果 |
|---|---|---|
| A：跨 fly 的可靠 RF | ≥3 只 fly 各 ≥5 ROI | 0 只；**不通过** |
| B：稳定中心 | ≥10 可靠 ROI，位移中位数≤1.5、75 分位≤2 像素 | 无可靠 ROI；**不通过** |
| C：表示相对 raw 的清晰收益 | Li-style/最佳 causal 分数分别至少 +0.02 | +0.0149 / +0.0114；**未达到** |

**决策**：不进入 Phase 6.2 的 RF-centered canonical stimulus dataset。下一步优先复核 Results 的实验处理史、ROI/mask 与时钟/空间坐标证据，并在完全独立的数据或预先冻结的新分析方案上检验更长训练时段、中心估计或 RF 正则化；不能用本轮 TEST 反向筛选和调门槛。本轮不训练新 CNN、TCN、Transformer 或共享预测模型。

## 6. 复现与限制

```bash
OPENBLAS_NUM_THREADS=2 .venv/bin/python -m unittest discover -s tests -q
OPENBLAS_NUM_THREADS=2 .venv/bin/python modeling_pipeline/phase_06/run.py --workspace-root .
```

输出分为 `response/`、`reliability/`、`alignment/`，三个有源/输出 SHA-256 的 `stage_manifest.json` 串联，原始 `Results.csv` 保持只读。训练段检验已基于**同一条冻结随机刺激**的五个生物重复，shift null 依赖时间平稳性；Li-style 仅复现论文公开的处理逻辑而非其完整私有代码。当前 TEST 在历史阶段已查看过，本阶段完全不以它作选择或新的确认性显著结论。剩余 provenance 问题和证据标签见 [假设登记](PHASE6_ASSUMPTIONS.md)。

**实际验证**：40 项测试通过；历史 Stage 01–12 完整重跑通过；Phase 6.1A/B/C 三份 manifest 的全部声明哈希通过；fly1/Mean29 保存的 Pixel 与 CNN 模型各自独立重播 2,413 个历史测试帧，均得 r≈0.493、R²≈0.235。原始目录 536 个文件相对路径与 SHA-256 相比先前审计清单完全一致。测试覆盖离线变换可重复、causal 后缀不泄露、TEST 改动不影响 TRAIN 变换/shift null、来源记录、RF 形状、BH-FDR、合成中心恢复与对齐；合成测试不替代新动物验证。
