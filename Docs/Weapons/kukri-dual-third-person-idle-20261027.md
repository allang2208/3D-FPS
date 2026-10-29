# 双刀第三人称待机：副手优化

原第三人称双刀待机使用 `Kukri.FullBody.Idle` 的单持全身动作，再由装备层闭合左手手指。副手缺少独立的持刀肩肘姿态。本次新增 Jason、Kaitlin 各一条 `Kukri.FullBody.Dual.Idle`，作为双刀普通持握状态的专用循环。

## 制作与调用

从当前已保存的原生单持待机提取完整 1.3333 秒循环，保留主手、躯干、双腿及呼吸。只改变左侧锁骨、手臂、手腕与手指：副手位于左前方低位，肘部自然下垂并位于躯干外侧，刀尖斜向前上方。刀柄挂接与手指包握复用当前双刀原生映射，不通过挪动手指骨或武器挂点来凑刀尖位置。

肩肘使用本角色骨长和原生弯曲平面解算；前臂承担持刀朝向所需的旋转，手腕额外摆角限制为 12 度，twist 辅助骨由最终姿态派生。循环继承原待机的细微动作，避免独立腕部摆动破坏握持。

运行时在 `FPSPlayerBodyAnimInstance.cpp` 通过已有实际副手弯刀装备标记选择新待机。新资产未加载时仍可使用单持待机。双刀待机按持握循环采样，不进入攻击进度分支；原左手独立动作占用规则继续生效。

双刀旋风也从新的待机边界重新制作 Start、Loop、End（V3），沿用 V2 的脚步、下蹲、肩高展开与原技能时钟；在同一连续时间线上返回新的副手准备姿态。单持旋风和第一人称动作不属于本轮修改。

## 资产与交付状态

作者目录：`SourceAssets/KukriDualIdleThirdPerson20261027`。`prepare.py` 只提取已保存待机作为制作输入；`author.py` 生成双刀待机及其旋风衔接；`save_all.py` 保存两套身体共八个资产；`publish.py` 通过字段事务接入八个动作角色键。

目标资产目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/DualCarry20261027`。

八个动画资产已通过后台 commandlet 保存（退出码 0），通过共享配置事务接入八个动作键。回执分别为作者目录内 `assets-saved.json`、`save_all-commandlet.json` 和 `published.json`。

等待资产批次期间，共享工程的正式 Editor 构建已经包含本次调用代码：源码修改于 06:51:59 UTC，对应对象文件生成于 06:58:05 UTC，基础 `UnrealEditor-FPSGAME.dll` 生成于 07:02:16 UTC，DLL 内含新增的 `Kukri.FullBody.Dual.Idle` 角色。随后 `Saved/BuildEditor/build-20261027-150557.log` 的 `FPSGAMEEditor Win64 Development` 构建报告 `Target is up to date`、`Result: Succeeded`，因此本轮未再重复发起构建或中断正在运行的后台进程。

本轮未新增预览渲染或运行游戏测试，最终自然度与衣服效果由用户测试。已完成本地资产保存、配置接入和基础 Editor 产物接入，未重新打包游戏，未提交或推送 Git。
