# 刺激等价性：数字序列与物理光刺激

Li [2021](https://www.sciencedirect.com/science/article/pii/S0960982221006151)：UV LED array，peak 约369 nm，ON 约0.1 mW/cm²，单 pixel 约4°，显微镜触发的约14 Hz 刷新和成像，white noise 约10 min，之前有 shifting-bar center localizer。

当前五个记录可由 `data/stimulus.py` 的 seed reconstruction 与保存包核验：15×15、9000 个 binary update、数字分析值±1、命令灰阶0/100、标称15 Hz、约10 min；`data/alignment.py` 核验 DLP marker-locked TTL 与 Zeiss frame-out TTL 的行数和 payload，frame-out 近13.53 Hz。几何 recipe 的 degrees 值只是指令和几何推导，不是蝇眼实测视角。

**DIGITAL_EQUIVALENCE ≠ PHYSICAL_EQUIVALENCE**。当前没有实测 wavelength、irradiance、gamma、单 pixel 视角、视野落点或 optical leakage。目录名不能作物理波长证明。不同装置和不同 14/15 Hz clock 足以影响解释，不能以算法相似代替实验等价。
