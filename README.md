# Dm8 modeling：毕业设计最终分析

用五只果蝇的保存刺激和ROI强度轨迹，描述Dm8的空间/时间感受野并检验跨fly一致性。数据为236 ROI（技术QC后228）、同一条15×15 binary刺激、9000 updates、约15 Hz及设备TTL。`MeanN`上游钙处理与实际光学标定尚未核实。

唯一流程：Gaussian10s基线相减 → native40协方差STRF → RF后zscore → 中心定位/亚像素对齐 → fly等权RF → Gaussian/DoG比较 → 500次完整流程null。稳健结果为负中心；宽正环绕尚不受支持。

## 运行

Python ≥3.11。在项目根目录执行：

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python analysis/run_final_analysis.py --config configs/final_analysis.json
python -m unittest discover -s tests -v
```

需要本地只读目录`Dm8_module/`与`simulate/`；二者不上传Git，克隆仓库后须从原持有人取得。唯一配置记录来源路径、全部方法和冻结数值；新数据应显式更新预期fly/刺激参数及回归基准。当前实现固定15×15、40 lag和两种明确用途的空间/时间定义，拒绝未知方法名称。

## 文件与输出

- [FINAL_PROJECT_SUMMARY.md](FINAL_PROJECT_SUMMARY.md)：完整项目说明。
- [FINAL_RESULTS.md](FINAL_RESULTS.md)：最终科学结论与历史发现。
- `src/dm8_modeling/`：九个科学模块；`analysis/run_final_analysis.py`为唯一入口。
- `configs/final_analysis.json`：唯一配置；`tests/test_final_pipeline.py`为集中测试。
- `results/tables/`：5张核心CSV；`results/figures/`：7张毕业设计主图。
- `results/final_results.json`：关键数值、RF/支持矩阵、500次null样本与回归检查。
- `results/source_hashes.json`：4,949个受保护源文件的内容哈希；每次重跑均核验。
- [references/README.md](references/README.md)：方法来源与Li benchmark等价性边界。

开发过程由Git历史保存。最终复算独立读取来源，不依赖任何旧阶段输出。
