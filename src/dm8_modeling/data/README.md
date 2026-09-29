# data/ 模块说明

## 模块目的

读取刺激、ROI 强度和设备时钟，完成因果对齐。

## 对应科学问题

哪个数字刺激已展示给某个成像帧？

## 输入

stim_recipe.json、stim_realized.npz、Results.csv、DLP/Zeiss TTL、flip log。

## 输出

StimulusData、ResponseData、ClockData、AlignedSession；原始数据保持只读。

## 数据 shape

刺激 [9000,225]；Results [8570,ROI]；payload aligned [约8119,ROI]。

## 单位

刺激数字 ±1；ROI 平均图像强度；DLP/Zeiss 微秒；PsychoPy flip 秒。

## 核心数据对象

Session/SessionPaths、StimulusData、ResponseData、ClockData、AlignedSession。

## 处理逻辑

stimulus.py 校验 seed/灰度；response.py 检查 ROI 行；clocks.py 检查单调；alignment.py 取最近过去更新并排除 payload 外帧。

## 数学逻辑

u_i=searchsorted(t_update,t_img,i,side="right")−1；t_img<payload_end。

## 核心函数

load_stimulus_data；load_response_data；load_clock_data；align_session。

## 可调参数

路径由 configs/workflow.json 定义；配方提供 15/120 Hz、9000 更新、15×15 网格。

## 上游依赖

workspace 路径与只读实验包。

## 下游依赖

preprocessing、datasets、RF、模型。

## 常见错误

帧号非连续、TTL 非单调、刺激 seed/灰度不一致、Results/Zeiss 行数不等。

## 当前假设

Zeiss frame-out 作为成像时间代理，同一采集设备微秒时钟用于 DLP/Zeiss。

## 科研限制

未提供精确曝光开始、ROI mask、正式 ΔF/F、物理照度。

## 对应 tests

tests/data/test_alignment.py；tests/integration/test_workspace_audit.py；tests/models/test_legacy_models.py。

## 对应 modeling_pipeline stage

02–04
