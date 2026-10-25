# 尼泊尔弯刀 V11/V12 三段连击、上挑、蓄力重击与挥砍剑气

本批公开弯刀三段连击的第二段（V11 斜劈）与第三段（V12/V12b/c/d 单手低位戳刺）定稿、
三段之间的双手剑式连段间隔、挥砍命中的冲击时刻（镜头重音＋迟延命中提示＋接触特效）、
上挑技能 `swordUppercut`、蓄力重击技能 `heavyStrike`（左键按住蓄力、松开出手，快捷栏蓄满自动出手）、
以及每次挥砍的剑气飘带（复用符文剑 M_RuneRift 月牙）。配套体力服务器计费、上挑权威回执与
命中上报校验一并公开。原作者脚本、拟合产物与技能沉淀随批更新。

## 直接进入运行树的内容

- `Source/FPSGAME/Weapons/Kukri/`：`KukriStrike.cpp`（冲击时刻）、`KukriRift.cpp` +
  `KukriRiftRibbons.h`（剑气）、`KukriUppercut.cpp`、`KukriHeavy.cpp` + `KukriHeavyRhythm.h`；
  `KukriRhythm.h`、`KukriWeaponComponent.h/.cpp` 按本批差量提交。
- `Source/FPSGAME/Multiplayer/ColdSteelUppercutAuthority.cpp` +
  `UppercutStaminaReceipt.h`：上挑/重击的服务器权威与体力回执；
  `Source/FPSGAME/Skills/LightningHasteSpeed.h`：本批 cpp 引用的攻速系数入口。
- `FPSImpactFXSubsystem.h/.cpp` 差量：`SpawnImpact` 增加 `bPlaySound/bDecal` 形参，
  近战接触自带音效、不留弹孔贴花。
- `items.json` 弯刀条目、`kukri-20261020.md` 武器文档、`Backlog.md` 四条记录、
  `melee.md` 九条沉淀、`SourceAssets/Kukri20261020/` 的 V11/V12 拟合键、上挑/重击/剑气
  作者脚本与参考配准脚本、`clips.json` 的 Attack2/Attack3/Uppercut/HeavyCharge/HeavyRelease 条目。

## 共享宿主差量（Integration/，17 份补丁）

**此提交不是完整本机工程的可构建检出。** `ColdSteelPlayerState.h/.cpp`、`FPSGAMECharacter.cpp`、
`FPSMeleeMovementNetwork.cpp`、`FPSStaminaModel.cpp`、`ColdSteelStatusModel.h`、
`ColdSteelQuickBarModel.cpp`、`ColdSteelQuickSlot.cpp`、`ColdSteelSkillPage.cpp`、
`ColdSteelStaminaHUD.cpp`、`ColdSteelInventoryTypes.h`、`ColdSteelSkillRules.cpp`、
`ColdSteelSkillTypes.h`、`ColdSteelAdditionalMasteries.cpp`、`ColdSteelHeavyStrikeModel.cpp`、
`MeleeWeaponStats.h/.cpp` 为多方并行编辑的宿主，本批只发布 `Integration/` 下按 HEAD 对齐的
差量补丁；`integration-prerequisites.json` 给出每份的规范化前置/结果 SHA-256 与语义依赖
（哈希不符时合并语义，不覆盖现有文件）。要点：

- `ColdSteelPlayerState` 补丁新增上挑权威成员与重击释放回执校验；实现位于本批新文件
  `ColdSteelUppercutAuthority.cpp`，`IsSwordWhirlwindExecuting` 的实现在已公开的
  `ColdSteelWhirlwindAuthority.cpp`。
- `ColdSteelInventoryTypes.h` 补丁新增 `IsOneHandedMelee` 与上挑/重击冷却镜像字段，是
  其余宿主补丁与本批已提交文件的共同前置。
- `author_kukri_clips.py` 保留 `pose(left_arm=…)` 调用，依赖并行会话尚未发布的
  `kukri_rig.py left_hand_explicit`；clip 导入走并行会话的 `import_kukri_attacks.py`／
  本批 `import_kukri_uppercut.py`、`import_kukri_heavy.py`。

## 废案归档

141 项废案（V8–V11 双手戳刺中间稿、旧拟合轮、废版 key 备份、Python 缓存与对照中间图）已移至
`trash/kukri-20261025-closeout/`（本地目录，不入库）；逐文件原路径、归档路径、字节数、
SHA-256、原因和替代物见 `archive-manifest.json`。

## 测试声明

历史完整本机 Editor/Game 构建成功；本批公开裁剪树未重新构建、未做真实主客机联机验收，
动画观感以用户本地体验为准。`clips.json` 保留 `runtime_tested:false`。
