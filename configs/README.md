# 参数入口

`workflow.json` 定义 12 阶段的只读数据根、派生数据与输出根、响应/特征默认值，并指向 `phase5_first_round.json`。后者是第一轮五 fly 模型比较的实际参数来源，包括共同 split、feature bins、响应表示、模型超参数与随机种子。Stage README 会指向相关字段；修改参数会导致前一 Stage manifest 的 config 校验失效，应从 Stage 01 重跑。

不要把 `stim_recipe.json` 的实验事实当成建模参数：15×15、9000 updates、120/15 Hz、数字灰度和 seed 来自各 fly 原始包。原始目录只读，配置不能改写它。旧 CLI 的 `--lag-count`、`--model` 等历史参数仍可用；它们与 Phase 5 配置的 4-bin 特征不是同一个实验，结果需分开比较。没有引入 YAML 依赖。
