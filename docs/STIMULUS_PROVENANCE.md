# 五次实验的刺激来源与核验

```text
simulate/07E_260530_01/05E.../stimulus_contract.py
  generate_family_updates(seed, p=0.5, 9000, 15, 15)
      → stimulus_updates_rc_float32 [9000,15,15], −1/+1
      → stimulus_updates_display_gray_uint8 [9000,15,15], 0/100
  generate_package(hold=8, marker overhead=1236, post baseline=1200)
      → display_frames_gray_uint8 [74436,15,15], 8-bit digital command
  05E.../host/build_stimulus_package.py
      → stimulus_package/stim_realized.npz + recipe/plan/manifest
  05H.../host/play_stage05h_package.py
      → PsychoPy frame flips + playback/stim_frames.csv
  Due capture → capture/dlp_ttl.csv
  05H marker lock → analysis_marker_lock/dlp_ttl_marker_locked.csv
  Zeiss frame-out → zeiss_ttl_<run>.csv
  microscope ROI table attached → Results.csv
  src/dm8_modeling/data.py → aligned update index and raw ROI intensity
```

所有箭头中，生成与文件读取为 `DIRECTLY_OBSERVED`；“数字命令等于果蝇收到的光”未获实测证据，为 `UNRESOLVED`。`stim_structure_priors.json` 是设计时边界（payload 起始帧 1236、终点帧 73236），锁定 DLP TTL 才提供共享采集钟上的逐帧时间。`playback/stim_frames.csv` 的 PsychoPy flip 时间属于播放端时钟；绝对对齐使用 marker-locked DLP TTL。

## 八个冻结数组

| 数组 | 五次实验共同 shape | 内容和单位 |
|---|---:|---|
| `display_frames_gray_uint8` | `[74436,15,15]` | 完整显示指令，数字灰度 |
| `payload_frames_gray_uint8` | `[72000,15,15]` | 600 秒主体数字帧 |
| `stimulus_updates_rc_float32` | `[9000,15,15]` | 行列刺激更新，−1/+1，无物理光单位 |
| `stimulus_updates_display_gray_uint8` | `[9000,15,15]` | 对应更新的 0/100 数字灰度 |
| `payload_update_index_by_payload_frame_int32` | `[72000]` | 主体显示帧 → 更新编号 |
| `payload_display_frame_idx_int32` | `[72000]` | 主体帧在完整显示序列的位置 |
| `update_start_display_frame_idx_int32` | `[9000]` | 各更新开始的完整显示帧编号 |
| `update_display_frame_count_int16` | `[9000]` | 每次更新保持帧数，当前全为 8 |

运行 `.venv/bin/python scripts/verify_stimulus_provenance.py --data-root Dm8_module --stimulus-code-root simulate --output-dir outputs/audit`，使用每次实验保存的**原配方**调用本地 05E `generate_package()`，对上述八数组逐一比对 dtype、shape、每个值，并在 `outputs/audit/stimulus_provenance_check.json` 记录数组 SHA-256。五次全部 `all_arrays_equal=true`。这是功能级来源证据；Windows 运行日志指向 `C:\RFmapping\07E_260529_02`，本地副本为 `07E_260530_01`，原始代码快照和对应 package_library 文件不在当前工作区，因此确切源码版本仍 `UNRESOLVED`。

五只 fly 使用同一 `seed=20260422` 和相同数字配方，故得到相同图案。`package_lineage.json` 表明 fly1、fly2、fly5 各自 `create_new`，fly3/4 共用同一个 package ID；不能说五只都读取同一物理包。相同 seed 使它们**不构成五段独立随机刺激**。

| Fly | 运行 ID | 保存的 package ID 后缀 | 关系 |
|---|---|---|---|
| fly1 | `20260619_105040` | `20260619_090023_...` | create_new |
| fly2 | `20260619_163025` | `20260619_125914_...` | create_new |
| fly3 | `20260622_221703` | `20260622_191941_...` | create_new |
| fly4 | `20260622_230745` | `20260622_191941_...` | 与 fly3 同包 |
| fly5 | `20260626_164950` | `20260626_133411_...` | create_new |

其他读取文件、时钟和 `X/y` 形成过程见 [数据处理逐步讲解](DATA_PIPELINE_WALKTHROUGH.md)。
