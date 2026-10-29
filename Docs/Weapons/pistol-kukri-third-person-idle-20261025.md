# 主手手枪、副手尼泊尔弯刀：第三人称待机

日期：2026-10-25。

## 目标与动作来源

匹配已经制作的第一人称手枪与反握弯刀组合：右手持枪，左手握刀，左前臂从持枪手下方交叉支撑。腰射保留持枪侧倾；瞄准时转为直枪和腕下支撑。

手掌方向、双手相对位置和刀柄抓握来自 `SourceAssets/DualPistolKukri20261025` 的已制作姿势，以及 `OffhandKukriAuthoredPose.h`。肩、肘、前臂按 Jason 与 Kaitlin 各自的原生骨架重新制作；基础身体来源为 `Pistol.Idle`，左臂参考现有 `Staff.BookCarry`。未引入外部动画资源。

## 资产与运行时接入

每个人物新增两份原生姿势：`A_Pistol_KukriCarry_Hip` 和 `A_Pistol_KukriCarry_Aim`，位于各自 `Kukri20261024/ComboV3/<Body>/Animations/OffhandCarryV1` 目录。配置角色为 `Pistol.KukriCarry.Hip`、`Pistol.KukriCarry.Aim`。

姿势资产提供完整肩肘腕和辅助骨链；运行时只覆盖双臂，保留原有身体待机、呼吸、下肢与行走层。进入姿势时使用 0.24 秒全臂过渡，瞄准使用现有瞄准权重。跑步时降低持枪组，射击时双手共同响应。换弹沿用副手降低、隐藏、返回阶段；翻越、交互和施法等动作获得对应手部控制。

第三人称副手刀模由装备组合生成，挂在原生左手。刀柄变换和手指通过现有 `FFPSBodyGripRig` 解剖掌心映射转入各人物骨架。最终手指握持由装备层提供，单独打开姿势资产不会包含这一运行时握持层。枪械保留各自的原生掌心与枪身对齐关系。

第一人称镜头和第一人称姿势不在本次修改范围。

## 制作与落盘记录

制作目录：`SourceAssets/PistolKukriBody20261025/`。

- `prepare.py`：读取原生人物骨架与现有姿势，输出 `inputs.json`。
- `author.py`：按原生骨长制作两套人物的腰射、瞄准姿势，输出原生骨轨及 `authoring.json`。
- `save_assets.py`：通过无界面 commandlet 保存四个新动画包，记录 `assets-saved.json`。
- `publish.py`：通过 `Tools/PlayerBody/config_transaction.py` 仅发布四个新增角色，记录 `published.json`。
- `build.ps1`：必要的 Editor、Game 后台构建，记录 `build.json`。

首轮落盘状态：四个动画包保存完成，四个配置角色已通过字段事务接入。Game 在 2026-10-25 20:39 构建成功。Editor 于 20:44 构建失败，错误位于并行新增的 `Source/FPSGAME/Production/WarhammerSprintNetworkAudit.cpp:76`：访问 `AFPSGAMECharacter` 的私有成员 `bSprintHeld`（C2248）。

用户要求继续后的编译收尾：在 `FPSGAMECharacter.h` 中按既有审计类约定补充 `UWarhammerNetworkAuditCommandlet` 友元声明，保留原断言与玩法实现。`BuildCompletionR1` 保存这一轮构建结果；其中暴露的身体组件未声明变量和战锤调试控制器错误随后已有并行修复，继续使用当前工作文件，没有覆盖这些修复。`BuildCompletionR2` 又遇到新增副手上挑代码访问角色私有函数 `IsWeaponBusy()` 的编译错误，因此按既有武器组件约定补充 `UOffhandKukriComponent` 友元声明，保留其动作占用判断。未关闭或中断其他任务。

最终状态：`BuildCompletionR3` 的 `FPSGAMEEditor Win64 Development` 构建成功，已完成 `UnrealEditor-FPSGAME.dll` 链接与目标元数据生成，结果为 `Succeeded`，334 项构建动作完成。输出与回执位于 `SourceAssets/PistolKukriBody20261025/BuildCompletionR3/`。第三人称待机、瞄准、反握刀及抓握接入已编入新的 Editor 模块；本次没有再运行 Game 构建，首轮 Game 成功记录保留在原目录。没有执行任何审计 commandlet 或游戏测试。

制作中的骨段间距与目标拟合数据仅是作者计算，不代表实际网格没有穿插。未启动编辑器界面、PIE 或游戏，未进行截图、渲染或运行验收；最终自然度、服装接触和 F6 第三人称显示由用户自行测试。
