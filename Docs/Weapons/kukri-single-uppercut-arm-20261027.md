# 单持上挑：主手肩肘、前臂与手腕重做

后续更新：已在保留本页主手姿态的基础上完成[单持腿部衔接修订](kukri-single-uppercut-legs-20261027.md)，当前单持入口使用该后续版本。

本轮只更新 Jason、Kaitlin 的第三人称单持 `Kukri.FullBody.Uppercut`。此前版本沿用了 Meshy 第三人称手臂局部动作，仅更换下半身并端正躯干，并不是根据第一人称完整重建。本轮读取项目当前实际使用的第一人称 `A_Kukri_Uppercut`，以其低位蓄力、向上挑起、高位随挥和回收节奏为参考，重新制作原生身体的主手链。

## 修改

此前主手的作者逻辑先求解肩肘，再独立旋转手腕控制刀尖，最后混回待机角度。手腕朝向与前臂支撑脱节；原有主手轨迹也包含较深的向后折叠和较早的向下回落。这些是制作数据中的问题定位，并非本轮游戏复现结论。

- 用各身体原生肩、肘、腕骨长重新求解右臂。参考第一人称的动作节奏，将手部轨迹适配到完整身体前侧，不直接照搬镜头空间位置。
- 保留肘部弯曲余量，手腕最远目标限制在原生臂长的 94%；不拉长骨骼。
- 连续选择肘部弯曲平面与前臂转角，由前臂承担主要转刀。相对原生待机腕部的小幅修正使用约 12 度摆动、15 度轴向转动软限制。
- 锁骨随抬手和回收轻度参与，重建右臂 twist 辅助骨，保留原生待机偏移及握刀指形。
- 首尾接回原单持待机。双手剑下半身、此前端正的躯干、空手左臂、双持动画及第一人称资产不改。

仍为 120 Hz、153 帧、约 1.267 秒，保留已有 Contact、Release 和 NativeSwordGrip 标记。技能时长、命中、伤害及前冲不变；本轮没有 C++ 修改，无需新增编译。

## 已落盘与接入

两个新资产均由无界面 commandlet 保存，退出码为 0，`assets-saved.json` 记录 `complete: true`。两个配置入口通过 `Tools/PlayerBody/config_transaction.py` 的字段所有权事务切换，其他字段不变。

资产路径：

`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/UppercutSingleArmV1/A_Kukri_Uppercut_NativeArm`

制作目录：`SourceAssets/KukriSingleUppercutArm20261027/`。

- `prepare.py`、`inputs.json`：当前安装的第一人称参考、原生身体与原单持上挑。
- `author.py`、`*-actions.json`、`authoring.json`：主手动作制作及来源记录。
- `save_assets.py`、`save_all.py`、`run_commandlet.ps1`、`assets-saved.json`：资产保存及结果。
- `publish.py`、`published.json`、`delivery.json`：仅两个单持入口的接入及交付状态。

原动画保留。没有主动启动图形编辑器、运行游戏、截图、渲染或追加测试；肘腕观感、握刀表现和穿模情况仍由用户测试。本轮未打包、提交或推送。
