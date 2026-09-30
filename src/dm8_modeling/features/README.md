# features/

`lagged.py` 和 `temporal_basis.py` 只从**当前及过去**的保存数字刺激更新构造特征。Phase 6.2 固定 40 更新历史，分成 4 个各 10 更新的均值箱，形成 `[frame,900]` 设计矩阵（4×15×15）。这一数组是数字命令表示，不是测得的光谱/照度。旧 Stage 06–07 仍可使用同一特征模块；测试见 `tests/features/`。
