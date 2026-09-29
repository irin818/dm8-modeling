# 刺激工程代码审计（2026-09-30）

证据状态采用 `DIRECTLY_OBSERVED`、`DERIVED`、`ESTIMATED`、`INFERRED`、`UNRESOLVED`。这里的源码路径均相对工作区根目录 `simulate/07E_260530_01/`。本地副本是 **07E_260530_01**，六月五次运行的日志指向 Windows **07E_260529_02**；本页的功能比对不能证明两个源码树逐字相同。

## 当前五次运行的调用链

| 步骤 | 代码和作用 | 实验记录证据 | 状态 |
|---|---|---|---|
| 操作入口 | `05L_operator_training_handoff/run_stage05i_prepare_package.py` 提供 create/reuse/clone 包流程；`03_microscope_play_run_dell.py` 是运行日志明确调用的实验启动脚本，本地副本的对应流程由 `run_stage05i_microscope_play_run.py` 实现 | 每只 fly 的 `logs/run_gui.log`、`package_lineage.json` | DIRECTLY_OBSERVED；精确源码版本 UNRESOLVED |
| 生成配方 | `05E_stimulus_timing_geometry_contract/stimulus_contract.py:build_recipe` 结合 rig geometry 和 stimulus design；应以实验保存的 `stim_recipe.json` 为准，本地 05L 默认常量已经变化 | 五次 `stim_recipe.json` | DIRECTLY_OBSERVED |
| 随机图案 | 同文件 `generate_family_updates`，`RandomState(seed).random_sample((updates, rows, cols)) < p` 生成 Bernoulli binary；每格 +1 或 −1 | `seed=20260422`，`p=0.5`，`15×15`，`9000` | DIRECTLY_OBSERVED |
| 灰度映射 | 同函数先映射到 8-bit 灰度，再从灰度反算 `rc_updates`；本配方暗/亮为 0/100，故返回恰好 −1/+1 | `stimulus_updates_rc_float32` 与 `stimulus_updates_display_gray_uint8` | DIRECTLY_OBSERVED |
| 显示帧与 marker | `generate_package` 将每张更新图重复 8 帧，调用 03 阶段 marker protocol 形成最终 `display_frames_gray_uint8` | `72000` payload + `1236` 前缀 marker/间隔 + `1200` 后基线 = `74436` 帧 | DIRECTLY_OBSERVED |
| 冻结打包 | `05E_stimulus_timing_geometry_contract/host/build_stimulus_package.py` 写 `stim_recipe.json`、`stim_realized.npz`、`stimulus_plan.csv`、`package_manifest.json` 和重建检查 | 实验 `stimulus_package/` | DIRECTLY_OBSERVED |
| 设计先验 | `05H_pm100_parametric_imaging_bridge/stimulus_priors.py:build_stimulus_priors` 写 `stim_structure_priors.json` | `planned_frame_structure`；**仅设计帧界，不是实测时间** | DIRECTLY_OBSERVED |
| 播放 | `05H_pm100_parametric_imaging_bridge/host/play_stage05h_package.py` 加载最终显示帧，用 PsychoPy `ImageStim`/`win.flip()`，逐帧写 `playback/stim_frames.csv` 的 `flip_time_s` | 播放日志及帧表 | DIRECTLY_OBSERVED |
| DLP 时间 | 采集端 `capture/dlp_ttl.csv`，`05H.../analysis/lock_ttl_with_front_marker.py` 利用前段 marker 写锁定帧表及 summary | `analysis_marker_lock/dlp_ttl_marker_locked.csv`、`marker_lock_summary.json` | DIRECTLY_OBSERVED |

**关键区别：** `stimulus_updates_rc_float32` 是建模用的 15 Hz 更新矩阵 `[9000,15,15]`，`display_frames_gray_uint8` 是实际送往渲染器的完整 120 Hz 数字帧 `[74436,15,15]`；`payload_frames_gray_uint8` 是中间 72,000 帧，不含前后标记和后基线。显示命令不等同于已测得的果蝇处光谱或辐照度。

## 数字参数及空间方向

- 五次保存配方均指定 120 Hz 显示刷新、8 帧保持、15 Hz 有效更新、600 秒 payload，因此 `600×15=9000` 更新，`9000×8=72000` payload 显示帧（DIRECTLY_OBSERVED / 算术 DERIVED）。
- 格点 `grid_rows=15, grid_cols=15`，行/列按 NumPy `[row,col]` 存储；配方的设计几何为每格约 4°。播放 image 渲染器在 `build_display_texture` 中 `flipud` 以匹配屏幕纹理坐标，`make_grid_layout` 把 row 0 放在屏幕上方。实验 offsite summary 引用了 fly-side `local_row_col_flip_row_col` 校准；其**独立原始校准文件没有出现在五次运行内**，所以模型仍以本地网格坐标为主，不能无条件把坐标说成果蝇眼中的上下左右。
- 保存的渲染配方设置数字 green channel、gray 0/100；前段 marker 0/25。`preflight_checklist.json` 写设备 `light_source=blue`。这些描述数字命令和设备选择，不是实测中心波长、光谱、irradiance 或 gamma 曲线。05H/05E 的 PM100 脚本出现 450 nm 等可配置标称设置，但不能代替当前五次实验的物理测量。

## 当前代码与历史内容的界限

**与本实验直接相关：** 05E stimulus contract / package builder，05L operator handoff，05H playback、priors 和 marker lock，03 marker protocol。根目录 `package_library/` 的 2026 年 7–9 月包、`fly_runs/` 的 9 月运行是后续/历史生成产物；05G、05C、03 等还含旧阶段和 bench 检查。5 Hz、Gaussian、moving-bar 包属于其它范式。它们不应自动被说成六月五只 fly 的刺激源。五次六月 `package_lineage.json` 指向的 package ID 目前未在本地 `package_library/` 找到（UNRESOLVED）。

源码中还存在本地 05L 的旧默认 `4×4`、60 Hz、另一 seed；证明只看当下默认值会得出错误的六月参数。实际参数来自每次保存的 `stim_recipe.json`，由重生成验证。全量代码树保留原处，未做清理、编辑或导入分析包。
