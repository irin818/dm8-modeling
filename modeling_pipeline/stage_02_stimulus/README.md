# Stage 02 · 冻结刺激与数字播放

## 1. 这一阶段为什么存在？

确认实际保存的刺激矩阵及其生成配方一致。

## 2. 上一阶段提供了什么？

Stage 01 来源清单和 5 个 session 路径。

## 3. 实际读取哪些文件？

stimulus_package/stim_recipe.json、stim_realized.npz。

## 4. 输入数据对象是什么？

StimulusData 与 seed/digital-gray QC。

## 5. 输入 shape / axis / units 是什么？

StimulusData.updates [9000,225]，数字 ±1；update_start_display_frame_idx [9000]，显示帧索引。

## 6. 这一阶段进行什么处理？

用 seed 重建更新矩阵，核对 ±1↔0/100 数字灰度、display[start]、9,000 updates 与 74,436 display frames。

## 7. 为什么这样处理？

模型必须使用实验包中已存在的实际数字刺激；不能从源码猜测播放内容。

## 8. 数学逻辑是什么？

u(t)=max{k:t_k≤t} 留待 Stage 04；本阶段核验 P(seed)=stored updates。

## 9. 实际调用哪些 src 模块？

data/stimulus.py: load_stimulus_data, verify_binary_stimulus_package。

## 10. 数据 shape 如何变化？

每 fly 的 NPZ 多数组 → StimulusData [9000,225] 与核验 QC；5 fly 的公共矩阵在 Stage 06 再相等校验。

## 11. 输出是什么？

stimulus_summary.json 与 stage_manifest.json；Stage 04、06 使用。

## 12. 输出提供给哪个 Stage？

Stage 03 的响应与记录时钟。

## 13. 哪些参数可以修改？

配方中的 update_hz、display_refresh_hz、stimulus_hold_frames；修改 configs/workflow.json 的来源根会选别的实验包。

## 14. 哪些东西不能随便修改？

不能改 frozen NPZ、seed、灰度对应、显示起始索引。

## 15. 当前科学限制是什么？

0/100 是数字命令，不是视网膜照度；此步不证明物理波长。

## 16. 如何运行？

先确保 Stage 01 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 2 --workspace-root .
```

## 17. 如何检查结果是否正确？

每 fly 9000×225，72000 payload 帧，74436 完整显示帧，8 display frames/update，seed 检查通过。

## 18. 如何调试？

先查 recipe schema、NPZ 数组名、seed、灰度编码、文件损坏。

## 19. 对应哪些 tests？

tests/models/test_legacy_models.py；tests/data/test_alignment.py
