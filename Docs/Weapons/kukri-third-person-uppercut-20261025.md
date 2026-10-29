# 尼泊尔弯刀第三人称上挑

2026-10-25，按用户要求制作上挑。Jason、Kaitlin 各保存一套原生全身动画，并通过字段事务接入 `Kukri.FullBody.Uppercut`。

动作基于本地 CC0 Quaternius UAL2 的 `Sword Regular A` 与 `Sword Regular A Rec`。保留源动作的蓄势、身体转动与收势，适配低位起刀、向上刀路、屈膝与伸腿、前后换步和后脚蹬地。左手使用本地原生握拳姿态，拇指与四指错峰合拢，收势时放松。右手刀路以原生握点和刀刃坐标系制作。

完整动作长 38/30 秒，60 fps、77 个姿态采样，包含回到当前待机的收势。Contact 标记为 0.350 秒，Release 为 0.433 秒，沿用技能既有时钟。NativeSwordGrip 标记保留原生单手握姿；世界前冲仍由既有角色移动执行，动画根节点锁定。

两套新资产均位于已有 Cook 目录内：

- Jason：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/Jason/Animations/UppercutV4/A_Kukri_Uppercut_RisingStep`
- Kaitlin：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/Kaitlin/Animations/UppercutV4/A_Kukri_Uppercut_RisingStep`

制作文件：`SourceAssets/KukriUppercut20261025/author.py`、两套 `*-actions.json`、`save_assets.py`、`publish.py`。保存与接入回执分别为同目录 `assets-saved.json`、`published.json`、`delivery.json`。配置仅写入两套身体各自的上挑角色字段。

后台 commandlet 已保存资产，退出码 0。本轮没有 C++ 修改，无需新增原生构建；没有启动可视编辑器或游戏，没有渲染、自测或视觉验收。交由用户在 F6 第三人称／固定第三人称中体验上挑技能。
