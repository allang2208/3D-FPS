# 箭步上挑 V3

用户随后否定此版并指定新的出剑路径，当前已转为 [右下出镜上劈 V4](sword-uppercut-lower-right-v4-20261003.md)。以下为 V3 历史记录，当前技能不再自动箭步或改变镜头。

2026-10-03。用户否定 V2，改用[《老头环 箭步，上砍，起飞！》](https://www.bilibili.com/video/BV1fB4y1v72r/) 0–8 秒的两次示范。旧 V2 不作为已认可基线。

## 参考与动作设计

通过正常网页播放器观看并定位参考帧。两次示范都采用「箭步压低／落脚蓄势 → 起身猛挑 → 惯性带过 → 恢复」的两拍节奏。本次用两个示范共同设计一次技能动作，不将两次重复示范串成自动连击。

重做了 V2 的头侧停剑：剑先收至右下，蓄住后沿前方大弧迅速向上挑，越过高点继续向侧后带出，最后从侧方卸力回到原待机。武器朝向用连续旋转曲线跨过竖直方向，避免逐帧取最短方向旋转而切换扭转分支。进深、速度与手部摆位为第一人称三维改编；参考镜头的遮挡细节不宣称逐帧复刻。

| 动作时间 | 阶段 |
|---|---|
| 0–0.36 秒 | 右下收剑、压低；0.10–0.36 秒执行箭步 |
| 0.36–0.70 秒 | 落脚后低位蓄住 |
| 0.70–1.05 秒 | 起身带剑快速上挑 |
| 1.05–1.20 秒 | 越过高点，剑与双手继续带出 |
| 1.20–2.10 秒 | 侧方卸力、回到原待机 |

保留 V7 原生手型、指握、两种握距、骨长与蒙皮。双手跟随同一剑柄变换，肩肘重新求解，前臂辅助骨承担新增扭转。只制作原创关键帧，没有下载或提取参考游戏动画，也没有使用付费内容。

## 游戏接入

仍使用技能页中的「上挑」与既有快捷槽绑定。

- 实际箭步复用 `AdvanceThrustLunge` 和 `ApplyMeleeLungeStep` 的贴地胶囊扫掠，制作距离 85 cm；碰撞、失去地面、闪避／滑铲等沿用已有中断限制。方向在箭步开始时确定，不逐帧追随转向。
- 箭步与动画使用同一 Elapsed 时钟。视角只添加压低、起身与侧向重心变化，不用镜头偏移伪造角色前移。
- 站稳持剑才能开始；保留菜单、死亡、换装及高优先级动作的原取消逻辑。结束和取消释放步进状态。
- 不设置伤害、击飞、消耗、额外冷却、等级或修炼。视频里的敌人起飞仅作出剑节奏参考，未接入战斗结算。

运行源码：`Source/FPSGAME/Weapons/RuneSwordUppercutRhythm.h`、`RuneSwordUppercut.cpp`、`RuneSwordComponent.cpp`。没有新增反射字段或改变组件实例布局。动画／步进／镜头的作者秒数共同维护，动作不受攻速缩放。

## 已保存资产与制作源

标准柄和长握柄继续沿用原接入路径，路径中的 V1 为固定名称，内容更新为 `ArrowStepUppercutV3`：

- `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard`：2.10 秒。
- `/Game/Weapons/SwordUppercut20261003/LongGrip/A_Sword_UppercutV1_LongGrip`：2.10 秒。
- `/Game/Weapons/SwordUppercut20261003/Standard/A_Sword_UppercutV1_Standard_PreviewLoop`：末尾另加 0.65 秒待机，共 2.75 秒；独立静态场景不承载游戏内角色箭步。

制作目录：`SourceAssets/SwordUppercut20261003/ArrowStepV3/`，含作者脚本、两套可编辑 Blend／原生关键帧／FBX，以及 `authoring.json`、`install_receipt.json`。改写前保存的 V2 包保留于 `PreviousAssets/`，V1、V2 的作者源保持可追溯。

Blender 后台制作完成；三支动画通过已运行编辑器的 MCP 互斥批次保存，结果见 `install_bridge_result_02.txt`。第一次写入因来源路径的重复分隔符匹配失败而停止，未改写资产；规范化路径后完成本批保存。

本次不主动运行游戏、测试、验收截图或渲染。网页截图仅用于用户指定的视频参考。由用户在游戏内自行试玩；构建与当前编辑器生效范围另记本目录构建回执。

现有编辑器 Live Coding 已成功（`ArrowStepV3/livecoding_result.txt`）；本次未打开或重启编辑器。热编译补丁与基础 Editor DLL 的常规构建分别记录，不能把热编译成功当成基础 DLL 已更新。

同一工作区已进行的 `FPSGAME Win64 Development` 常规构建包含本轮源码，日志中 `RuneSwordComponent.cpp` 编译与最终 `Result: Succeeded` 已记录；复用该轮产物，没有叠加构建。日志为 `Saved/BuildEditor/m07-FPSGAME-20261003-124722.log`，本任务记录为 `ArrowStepV3/build_provenance.json`。基础 Editor DLL 仍待编辑器关闭后的常规构建；当前编辑器使用已成功应用的热编译补丁。
