# CURRENT_PIPELINE_BASELINE：按源码追踪的数据流

精确参数在 `configs/phase6_2_population_rf.json`，本页记录 Phase 6.3 实际执行的主路径。`F` 指 ROI 平均图像强度，不等于已验证的 calcium concentration。`f` 为 frame，`u` 为 stimulus update，`r` 为 ROI，`b` 为 10-update bin。

| 步骤 | 输入 → 输出、单位/shape | 公式、参数、源码和科学假设 |
|---|---|---|
| 数据读取 | `Results.csv` → `F[f,r]`，原始 ROI 图像强度 | `data/response.py:load_response_data`；首列连续 1-based frame，余列 float32 `MeanN`；未验证上游 motion/ROI/background。 |
| 刺激读取 | saved NPZ/recipe → `S[u,225]`，无量纲 ±1；9000×15×15 | `data/stimulus.py:load_stimulus_data`；与 seed、0/100 digital gray、display frame 验证；不是光功率测量。 |
| 时钟 | marker-locked DLP TTL、Zeiss frame-out TTL → `update_index[f]`, `time_us[f]` | `data/alignment.py:align_session`, `data/clocks.py:associate_imaging_with_updates`；取 frame-out 前最近 stimulus update；frame-out 代 exposure。 |
| payload | 全部帧 → payload 帧，约8084帧/fly | `data/alignment.py:align_session`；按 saved payload end 裁剪，剔除起止非刺激帧。 |
| technical ROI QC | `F[f,r]` → ROI subset | `experiments/phase63.py:prepare_fly`；全部有限、零值比例<0.2、原始 std>1e−8；技术筛选不等于细胞身份。 |
| baseline | `F[f,r]` → `R=F-Gσ(F)`，原强度 | `preprocessing/rf_response.py:li_style_relative_response`；σ=10s、truncate=3σ、reflect edges；中位 frame interval 换算，FFT、保留全部 payload。 |
| response normalization | `R[f,r]` → `Rz[f,r]`，无量纲 | `experiments/phase63.py:estimate_fly`；每 ROI 对 eligible frames 减均值/除 std。与 Li 的 RF 后 zscore 顺序不同。 |
| temporal design | `S[u,225]`, `update_index[f]` → `X[f,900]` | `features/temporal_basis.py:binned_design`；4 bins × 10 updates，bin0 为当前及过去9 updates，完整40-update history，均值不含未来。 |
| reverse correlation | `X[f,900]`, `Rz[f,r]` → `K[900,r]` | `rf/characterization.py:reverse_correlation`；`(X−X̄)^T(Rz−R̄z)/n`，无 ridge。 |
| RF normalization | `K[900,r]` → `Kz[900,r]` | `rf/characterization.py:rf_maps`；整个 STRF per ROI zscore，**但仅供 center/temporal diagnostic；后续平均仍用 K 原幅度**。 |
| center | `Kz[b,15,15,r]` → `[row,col]` px | `rf_maps`：最高能量 bin，最大绝对像素取符号，row/col 截线，带 offset 正 Gaussian 固定网格拟合；fit quality<0.05 为 NaN。 |
| align | `K[b,15,15,r]` → aligned K，NaN 边界 | `experiments/phase63.py:estimate_fly`、`rf/validation.py:align_temporal_bins`、`rf/population.py:shift_to_center`；round center 到整数，移至(7,7)，不 wrap；各像素有效支持变化。 |
| ROI/fly average | aligned K → mean bins → fly spatial → population | `rf/validation.py:fly_mean_bins`：每 fly ROI 等权有效像素均值；4 bins 带符号均值；`experiments/phase63.py:run_phase63`：五 fly 等权。 |
| 1D/model | population 15×15 → 15-point projection → M1/M3 | `rf/dog.py:projection_matrix`, `GaussianGrid.fit`；1000 次双线性旋转，有效点投影；Phase6.4 bounded Gaussian/DoG 是模型选择而非论文精确归一化 DoG。 |

Phase 6.5 输出命名中，`C0` 永远读取冻结的 Phase 6.3 数组；其余版本的 zscore 值单位不同，不可直接按幅度跨 C0 比较，只能比较符号、归一化形态或各自的 within-variant 指标。
