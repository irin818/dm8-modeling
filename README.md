# 白噪声反向相关的 Dm8 时空感受野建模

用五只果蝇的保存刺激、设备TTL与ROI荧光轨迹，恢复时空感受野并分析跨动物稳定出现的空间结构。

正式流程：TTL对齐 → 技术QC → Gaussian10s基线相减 → 40-lag反向相关/STRF → z-score → 全局能量lag → Gaussian中心定位/亚像素对齐 → 等fly群体RF → 空间/时间诊断 → 500次完整流程null。

## 运行

Python ≥3.11，在项目根目录执行：

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python analysis/run_final_analysis.py --config configs/final_analysis.json
python -m unittest discover -s tests -v
```

需要本地只读目录 `Dm8_module/` 与 `simulate/`；源数据不随Git分发，克隆后需取得原输入。配置记录唯一方法、来源路径与冻结数值；新数据须显式更新相关参数和回归基准。

## 文件与输出

- [FINAL_PROJECT_SUMMARY.md](FINAL_PROJECT_SUMMARY.md)：项目方法、解释及完整图注。
- [FINAL_RESULTS.md](FINAL_RESULTS.md)：最终科学结论与透明保留的历史探索。
- `src/dm8_modeling/`：八个科学模块；`analysis/run_final_analysis.py` 为唯一入口。
- `configs/final_analysis.json`：唯一配置；`tests/test_final_pipeline.py`：集中测试。
- `results/tables/`：4张CSV；`results/figures/`：4张主图、覆盖补图S1、方法图，各含300 dpi PNG和SVG。
- `results/final_results.json`：当前RF主线数值、RF/支持矩阵、null样本与8项回归。
- `results/source_hashes.json`：逐源文件指纹；[references/README.md](references/README.md)：方法参考。

最终复算只读取保存来源；历史执行过程由Git保存。
