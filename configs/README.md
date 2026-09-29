# 参数入口

`workflow.json` 只定义 12 阶段的来源根、派生数据根、输出根，以及 Phase 5 配置文件路径。`phase5_first_round.json` 是五 fly 建模的唯一响应、特征、全局 split、RF 筛查阈值、模型超参数与随机种子来源。修改工作流路径后，应从 Stage 01 重跑；修改 Phase 5 配置后，应从读取该配置的 Stage 05 重跑，且前序 manifest 校验必须通过。

不要把 `stim_recipe.json` 的实验事实当成建模参数：15×15、9000 updates、120/15 Hz、数字灰度和 seed 来自各 fly 原始包。原始目录只读，配置不能改写它。旧 CLI 的 `--lag-count`、`--model` 等历史参数仍可用；它们与 Phase 5 配置的 4-bin 特征不是同一个实验，结果需分开比较。没有引入 YAML 依赖。
