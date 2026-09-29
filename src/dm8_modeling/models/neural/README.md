# 神经网络对照

`compact_cnn.py` 实现已保存的单 ROI 小型 CNN 对照，输入过去 18 次更新的 15×15 数字刺激窗口 `[sample, lag, row, col]`，输出一个 ROI 的预测 `[sample]`，单位随原始响应目标为 ROI 图像强度。模型保存/重播由根级 `cnn.py`、`cnn_cli.py`、`cnn_predict_cli.py` 兼容入口服务，结果位于 `outputs/cnn_comparison/`。测试：`tests/models/test_cnn.py`。

它不是 Stage 10 的共享神经模型。共享 CNN、TCN 仍为计划项，未建空实现；当前 CNN 没有整体改善测试表现。阅读 Stage 09 [`README`](../../../../modeling_pipeline/stage_09_individual_models/README.md) 和 `modeling_pipeline/MODELING_MAP.md`。训练、验证、测试边界要和线性模型对应，不能用测试段选择网络规模。
