# Stage 03 · ROI 原始强度与时钟

## 1. 这一阶段为什么存在？

区分观测响应、播放侧时间和采集设备 TTL。

## 2. 上一阶段提供了什么？

Stage 02 刺激摘要。

## 3. 实际读取哪些文件？

Results.csv、zeiss_ttl_<run>.csv、analysis_marker_lock/dlp_ttl_marker_locked.csv、playback/stim_frames.csv。

## 4. 输入数据对象是什么？

ResponseData 与 ClockData。

## 5. 输入 shape / axis / units 是什么？

ResponseData.values [8570,ROI] 原始平均图像强度；ClockData DLP/Zeiss [帧] 微秒，playback [帧] 秒。

## 6. 这一阶段进行什么处理？

检查 ROI 列唯一、帧号从 1 连续、值有限、TTL 单调、Results/Zeiss 行数一致。

## 7. 为什么这样处理？

需要独立核对响应与两个时钟才能进行因果对齐。

## 8. 数学逻辑是什么？

t_DLP,t_Zeiss 以采集设备微秒表示；playback 秒是另一时钟，不能直接相减当作响应延迟。

## 9. 实际调用哪些 src 模块？

data/response.py: load_response_data；data/clocks.py: load_clock_data。

## 10. 数据 shape 如何变化？

每次 Results [8570,42/50/50/48/46] → ResponseData；TTL CSV → ClockData。

## 11. 输出是什么？

response_clock_summary.json、stage_manifest.json。

## 12. 输出提供给哪个 Stage？

Stage 04 对齐。

## 13. 哪些参数可以修改？

输入根在 `configs/workflow.json`；响应是 `Results.csv` 的原始 ROI 平均强度，ROI 列由文件头定义。

## 14. 哪些东西不能随便修改？

原始 TTL、Results.csv 和 ROI 列名不可改。

## 15. 当前科学限制是什么？

MeanN 尚未证实为正式 ΔF/F、放电率或校准钙浓度；Zeiss frame-out 是曝光时刻代理。

## 16. 如何运行？

先确保 Stage 02 manifest 为 complete；随后执行：

```bash
cd /Users/irin/Documents/dm8_modeling
.venv/bin/dm8-model pipeline stage 3 --workspace-root .
```

## 17. 如何检查结果是否正确？

五次均 8570 原始帧；42/50/50/48/46 ROI；时钟严格递增。

## 18. 如何调试？

先核对首列帧号、TTL 单位和缺行，再看源文件哈希。

## 19. 对应哪些 tests？

tests/integration/test_workspace_audit.py；tests/data/test_alignment.py
