# 方法参考与等价性边界

- [Li et al. 2021, Neural mechanism of spatio-chromatic opponency in the Drosophila amacrine neurons](https://www.sciencedirect.com/science/article/pii/S0960982221006151)：Figure 4与STAR Methods。报告raw image TurboReg、manual neurite ROI、10s Gaussian baseline subtraction、reverse correlation后individual STRF zscore、Gaussian轴截线中心、对齐后neuron组平均、360°/1000-step投影与DoG；UV LED peak约369nm、ON约0.1mW/cm²、pixel约4°、stimulus/imaging约14Hz。[PubMed书目信息](https://pubmed.ncbi.nlm.nih.gov/34033749/)。
- [Drews et al. 2020, Dynamic signal compression for robust motion vision in flies](https://www.sciencedirect.com/science/article/pii/S0960982219313752)：Li引用的RF/projection方法来源之一。
- [Arenz et al. 2017](https://pubmed.ncbi.nlm.nih.gov/28343964/)：Li引用的reverse-correlation/DoG方法来源之一。

已取得材料未完全说明exact STRF→spatial RF时间规约、zscore轴、插值及边界策略。补充Figure S4与部分引文实现细节未可靠取得。当前全局能量lag、整STRF zscore与有效支持插值均为公开声明的实现选择。

当前five-fly数据缺实测光谱/辐照度/视角，不能使用Li的60°surround bound作为等价px约束。数字刺激校验不证明物理等价。Li Figure4的WT Dm8及photoreceptor isolation组不等同于未经确认的当前实验条件，也不能用RF形状推断p/y subtype。参考论文PDF未复制进仓库。
