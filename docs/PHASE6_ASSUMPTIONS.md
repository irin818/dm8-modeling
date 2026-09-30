# Phase 6.1 数据事实与生物学工作假设

本页是可更新的证据登记表，不把论文同体系的方法自动套到当前五次实验。标签在代码、响应 provenance 和报告中统一使用：`CONFIRMED_FROM_FILES`、`WORKING_BIOLOGICAL_ASSUMPTION`、`INFERRED_FROM_LI2021`、`UNRESOLVED`。

| 项目 | 标签 | 当前判断与证据 |
|---|---|---|
| 五份 `Results.csv` | `CONFIRMED_FROM_FILES` | 每份有 8,570 个连续帧序号及 42/50/50/48/46 列 `MeanN`；`data.response.load_response_data` 逐列读取有限的图像强度。`offsite_analysis/analysis_manifest.json` 还标记来源为 `results_csv_raw`。 |
| 刺激与时钟 | `CONFIRMED_FROM_FILES` | 五只 fly 存有同一条 9,000 更新的 15×15 数字二值刺激、DLP/Zeiss TTL 与分析元数据；`AlignedSession` 保留原始 Results 行号和哈希。数字命令不是实测视网膜光强。 |
| ROI 解释 | `WORKING_BIOLOGICAL_ASSUMPTION` | 暂把每个 `MeanN` 当作一个 **individual Dm8-related neurite ROI recording**。236 是 ROI 记录数，不是 236 个完整独立神经元；生物独立层级是 5 只 fly。当前包里没有可核实的 ROI mask 或逐个身份标注。 |
| `MeanN` 数值含义 | `CONFIRMED_FROM_FILES` + `WORKING_BIOLOGICAL_ASSUMPTION` | 文件直接给出逐帧 ROI mean intensity；把荧光来源称作 GCaMP 属于实验背景工作假设。建模数值 target 统一写 `raw/near-raw ROI mean GCaMP fluorescence intensity F(t)`，不称放电率、电位、正式 ΔF/F 或校准钙响应。 |
| motion registration、人工 ROI | `INFERRED_FROM_LI2021` | Li et al. 2021 的方法页描述 raw movie 配准及手工 ROI；正文图注说其 ROI 根据 M4/M5 neurite protrusions 划定。这支持同体系最可能的分析链，但不能直接证实本包五次记录采用了相同处理。 |
| 本包成像预处理 | `UNRESOLVED` | 是否经过 motion、neuropil/background correction，原始 movie、ROI mask、ROI 坐标、独立的 ROI set 都未可靠取得。`Results.csv` 很可能在 RF 特定慢基线相减之前，但不能标为已证实。 |
| 光学/刺激物理量 | `UNRESOLVED` | `UV-15Hz` 是文件夹标签；绝对波长、辐照度、眼位与精确曝光起点无可靠实测。 |
| genotype、driver、reporter、pDm8/yDm8 | `UNRESOLVED` | Phase 6.1 不把它们引入模型变量，也不从文件名推断。 |

**论文依据**：Li et al., *Neural mechanism of spatio-chromatic opponency in the Drosophila amacrine neurons*, Current Biology 31 (2021), doi:10.1016/j.cub.2021.04.068。本地 `color_modify_research/papercore/2021_Li_NeuralMechanismSpatioChromaticOpponencyDrosophila.pdf` 第 3 页图注与第 22 页方法段。论文所述细胞/ROI、成像参数和 RF 处理是 **论文自身实验的证据**，不是当前数据包的直接 provenance。

**更新方式**：以后若获得实验记录、movie、ROI mask 或处理日志，先更新证据标签与来源，再评估是否重跑 Phase 6.1。原始 `Dm8_module/` 与 `simulate/` 始终只读。
