# 当前模块依赖

```text
只读 simulate/、Dm8_module/
    ↓
workspace / data → preprocessing / features
                           ↓
                       datasets（Stage 06–07）
                           ↓
                 rf.characterization / rf.population
                           ↓
                 experiments.phase6 / phase62 → io
```

`data` 只读取保存事实和时钟，不写原始来源；`features` 不读取未来刺激更新；`preprocessing.rf_response` 的 Gaussian 表示属于离线 RF；`rf.population` 不训练预测器，保留裁剪像素掩码；`experiments.phase62` 先 fly 内 ROI 等权，再 fly 间等权。旧预测模型与评价器已退役，清理见[记录](../../docs/PHASE6_2_CLEANUP_LOG.md)。工作流入口见 [`modeling_pipeline/README.md`](../../modeling_pipeline/README.md)。
