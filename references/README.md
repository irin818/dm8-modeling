# RF方法参考与比较边界

- [Li et al. 2021, Neural mechanism of spatio-chromatic opponency in the Drosophila amacrine neurons](https://www.sciencedirect.com/science/article/pii/S0960982221006151)：Figure 4与STAR Methods为Dm8 RF比较基准。已取得材料报告TurboReg、manual neurite ROI、10s Gaussian baseline subtraction、reverse correlation后individual STRF z-score、Gaussian轴截线中心及对齐后群体均值。[PubMed书目信息](https://pubmed.ncbi.nlm.nih.gov/34033749/)。
- [Drews et al. 2020, Dynamic signal compression for robust motion vision in flies](https://www.sciencedirect.com/science/article/pii/S0960982219313752)：Li引用的RF方法来源之一。
- [Arenz et al. 2017](https://pubmed.ncbi.nlm.nih.gov/28343964/)：Li引用的reverse-correlation方法来源之一。

Li实验报告UV LED peak约369nm、ON约0.1mW/cm²、pixel约4°及stimulus/imaging约14Hz。当前five-fly数据缺实测光谱、辐照度和视角，保存的数字刺激不能证明物理等价；本项目只用grid pixel，不据此换算角度。

已取得材料未完全说明exact STRF→spatial RF时间规约、z-score轴、插值及边界策略；补充Figure S4和部分引文实现细节未可靠取得。当前全局能量lag、整STRF标准化与有效支持插值为公开声明的项目选择。Li实验条件不能未经证据映射到当前五fly，不能以RF形状推断p/y subtype。论文PDF未复制进仓库。

RF空间参数化描述的历史探索仅在[FINAL_RESULTS.md](../FINAL_RESULTS.md)中说明，不属于当前反向相关/STRF主流程。
