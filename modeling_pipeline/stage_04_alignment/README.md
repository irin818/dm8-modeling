# Stage 04 · 刺激与成像帧对齐

## 1. 这一阶段为什么存在？

把每个成像帧配到此前已显示的刺激更新。

## 2. 上一阶段提供了什么？

Stage 03 的 ResponseData、ClockData 和 Stage 02 的 StimulusData。

## 3. 实际读取哪些文件？

同一 run 的 stimulus package、marker-locked TTL、Zeiss TTL、Results.csv、payload metadata。

## 4. 输入数据对象是什么？

StimulusData + ResponseData + ClockData → AlignedSession。

## 5. 输入 shape / axis / units 是什么？

StimulusData [9000,225] 数字 ±1；ResponseData [8570,ROI] 原始强度；TTL 微秒。

## 6. 这一阶段进行什么处理？

用 marker-lock 的 DLP TTL 索引更新起点；searchsorted(side=right)-1 取最近过去更新；仅保留 payload 内帧。

## 7. 为什么这样处理？

side=right 使刚好同一时间的更新可用；payload end exclusive 排除后基线；从不使用未来刺激。

## 8. 数学逻辑是什么？

u_i=max{k:t_stim,k≤t_img,i}；include=(u_i≥0)∧(t_img,i<t_payload_end)。

## 9. 实际调用哪些 src 模块？

data/alignment.py: align_session；data/clocks.py: associate_imaging_with_updates。

## 10. 数据 shape 如何变化？

8570 原始帧 → 每 fly 约 8119 payload 帧；X 尚未加历史。

## 11. 输出是什么？

aligned_sessions.json、stage_manifest.json；内存 AlignedSession 进入 Stage 05/06。

## 12. 输出提供给哪个 Stage？

Stage 05 响应处理。

## 13. 哪些参数可以修改？

源路径与时钟文件在 configs/workflow.json；对齐公式固定，不暴露任意 offset 默认值。

## 14. 哪些东西不能随便修改？

不能改原始 TTL、payload end、source hash 或把未来刺激并入窗口。

## 15. 当前科学限制是什么？

Zeiss frame-out ≠ 真正曝光起点；marker-lock 只保证指定设备时钟上的对应。

## 16. 如何运行？

先确保 Stage 03 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 4 --workspace-root .
```

## 17. 如何检查结果是否正确？

检查各 fly 对齐帧数、更新范围、原始 Results 行索引和 QC。

## 18. 如何调试？

先看 marker-lock 状态、payload 边界、Results/Zeiss 行数、时钟单调性。

## 19. 对应哪些 tests？

tests/data/test_alignment.py；tests/integration/test_workspace_audit.py
