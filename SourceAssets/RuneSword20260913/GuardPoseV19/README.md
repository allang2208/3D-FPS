# 双手剑格挡动作修正 · V19

**2026-09-14 后续反馈：用户仍不满意格挡姿态，决定暂停。以下为尝试记录，导入完成不代表动作被接受；V19 保留作下次继续入口。** 当前状态见 [符文剑作者入口](../README.md)。

2026-09-14 用户反馈 V18 防御姿态不符预期、手臂错误旋转，并明确本轮仅调整动作。

## GitHub 参考

- [rico345100 的第一人称近战原型](https://github.com/rico345100/unity-basic-melee-combat-system-for-fps-rpg)：实际读取 `Assets/Models/firstperson.fbx.meta`，含 `metarig|GuardStart`（0–14 帧）、`metarig|Guarding`（0–1 帧、循环）和 `metarig|GuardEnd`（0–20 帧）。借鉴独立抬起、稳定持守、放下的动作组织。作者 README 提醒其格挡姿态高度存在问题；不把该项目视为成熟动作母版。
- [BigAndCrispy 第一人称近战示例](https://github.com/BigAndCrispy/Unity-First-Person-Melee)：CC0，已查看本项目此前保存的 `Reference/Gameplay1.png`；实际 `Arms.fbx.meta` 只列出 Sword_Idle、Sword_Slash1、Sword_Slash2、Sword_Walk，未将它当作现成格挡动作。
- 本轮没有复制上述仓库的模型、骨架、曲线或代码到游戏。以既有 Manny 双手剑动作重做；读取的 GitHub FBX 元数据提供动作参考，不宣称直接重定向了其格挡。

## 动作调整

V18 将格挡握姿交给挥砍使用的绕柄旋转路径搜索；搜索允许多圈角度，代价偏向腕折角与肩肘位置，缺少独立的格挡握柄转动约束。这是本轮移除的动作生成方式，不代表已对用户游戏画面完成实机诊断。

V19 直接取已接受 `A_RuneSword_Slash1` 第 0 帧的完整双手待机关系，保持手掌、手指和剑柄的相对矩阵。剑身改为朝右上斜横在身前，剑柄在胸前偏左，避免左手在柄尾时随朝左上的剑轴挤到右臂一侧。

手掌不再独立绕剑柄寻优。剑只沿最短旋转抬起，双肘使用各自外下方的目标平面；肩部轻微前送，前臂跟随握柄方向并保持原握姿的 twist 辅助骨关系。接住冲击时手臂重新按同一握点与肘位求解，不再把整条肩臂一起刚体转动。

输出仅覆盖三个现有动画：

- `A_RuneSword_Guard`：0.20 秒举剑，末帧保持；既有运行逻辑按约 0.18 秒反向收剑。
- `A_RuneSword_GuardHit`：106/480 秒受击回弹，两端接到同一持守姿态。
- `A_RuneSword_GuardBreak`：0.40 秒压开并回到原待机。

输入、弹反窗口、减伤、体力、位移、镜头、声音及全部攻击动作均不修改。沿用已有 UE 资产路径，只导入三个动画，无 C++ 修改或原生构建。

## 文件与交付

`author_guard.py` 为可编辑动作生成源，直接读取 V18 Blend；`AzureRunesword_Manny_Editable.blend` 保留原动作，并将旧三项格挡以 `REF_V18_` 保存。FBX 位于 `Export/`；导入前原有三项 UE 资产保存在 `Before/`。无调用的 `read_author_source.py` / `accepted_idle_source.json` 已按 [归档清单](../../../Docs/Weapons/runesword-archive-20260914.json) 移至 trash。

按用户规则未制作新预览、未运行游戏测试或验收。日志仅记录制作和导入结果，姿态效果交由用户自行体验。

制作脚本与三项 UE 动画导入均已正常结束（退出码 0），分别记录 `RUNESWORD_V19_AUTHORED` 与 `RUNESWORD_V19_IMPORT_COMPLETE`。已打开的编辑器需要重新加载资产，或重启编辑器后体验本轮动作。
