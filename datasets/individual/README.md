# IndividualDataset 清单

Stage 06 从每只 fly 的 `AlignedSession`、共享历史特征表和统一 split 构造一个数据集。模型使用 `X [约8084,900]`（4 时间 bin × 225 像素数字刺激）和 `y_raw [约8084,ROI]`（原始 ROI 图像强度），保留微秒时钟、ROI 名和 Results.csv 原始行。每只 fly 的实际帧数以生成的 `manifest.json` 为准。由 `src/dm8_modeling/datasets/individual.py` 构造；Stage 06 [`README`](../../modeling_pipeline/stage_06_individual_dataset/README.md) 给出复现和检查命令。生成文件可删除重建；原始文件不可改。
