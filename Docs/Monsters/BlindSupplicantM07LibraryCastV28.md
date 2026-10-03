# M-07：匹配身高的近战距离与动作库施法 V28

日期：2026-10-03。用户要求提高攻击距离以匹配整体高度，并从参考动作中选用合适施法，当前 V24 施法被用户否定。已认可的 V27 近战主体与恢复修订保持现有资产。

## 近战距离

正式显示模型 `SK_M07_BodyMotionV18` 的当前包围盒高度为 310.0006 cm。原蓝图 `AttackRange=180 cm`，经现有 `MonsterCombatTuning::AttackDistanceScale=1.5` 后有效距离为 270 cm。

本次只将实际 AI/F6 蓝图基础攻击距离改为 220 cm，有效近战距离 330 cm；现有共同逻辑自动得到 315 cm 起手距离和 300 cm 追击停距。保留爪部扫掠半径 35 cm、玩家半径处理、遮挡、命中去重与原伤害窗口。当前近战接触区间爪尖前向位置约 186–201 cm，仍沿用既有沿前向补足距离的命中设计；330 cm 是调整后的玩法有效距离，不等于静止手臂骨长或全部由表面直接接触。

火球、冰锥与闪电射程保持原配置。近远程选择继续采用同一放大后的近战距离，未复制另一套硬编码停距，也未修改所有怪物共享倍率。

## 本地动作选择与制作

读取现有库中的 `HandsSpell_Vexa`（2 秒）、`SnappySpell_Vexa`（0.5 秒）、`SummonCreature_Vexa`（约 1.833 秒）及 Rampage `Cast`（约 0.967 秒）的原生全身骨姿态作为制作输入。双手施法包含明显举臂过顶和起伏，召唤主发力手为右手；选择左手向前释放、右臂配合回摆的 `SnappySpell_Vexa`，与当前左掌发射位置相容。

源动画：`/Game/Vefects/Easy_Impact_Frames/Demo/Stylized_Female_Character_Vexa/Animations/SnappySpell_Vexa`。
源网格：`/Game/Vefects/Easy_Impact_Frames/Demo/Stylized_Female_Character_Vexa/SK/SK_Vefects_Vexa`。

通过原生 IK Rig／IK Retargeter 重定向完整身体、肩臂和腿脚。Vexa 的上臂与前臂各有三个连续分段，目标为单个主上臂与前臂；分别以实际肩、肘、腕为端点映射，不能把七骨链直接 OneToOne 塞进三关节。脊柱插值，腿部对应关节匹配，禁用将地面根运动覆盖骨盆的操作。

将源动作作为一个连续整体放慢到 2.4 秒，1.1 秒处拆为蓄力与释放；两段共用边界帧。蓄力 1.1 秒，释放 1.3 秒，释放后 0.30 秒出手，因此总出手时刻仍为 1.40 秒。收势平滑回到当前待机，未单独拼接第二个动作。保留盲祷者原爪型，从肩部整体适配长臂与长爪通道；脚底支撑和组织避让离线烘焙，不增加运行时 IK 或 Tick。

火球／冰锥蓄积中心仍为左掌世界位置加角色前向 65 cm，发射和提前量仍使用该原点；本次不改玩家特效或魔法参数。

## 交付与重建

- 制作输入读取：`Tools/BlindSupplicantM07/intake_library_cast_v28.py`
- 原生重定向：`Tools/BlindSupplicantM07/retarget_library_cast_v28.py`
- 离线制作与导出：`Tools/BlindSupplicantM07/author_library_cast_v28.py`
- 动画与距离接入：`Tools/BlindSupplicantM07/import_library_cast_v28.py`
- 制作根：`SourceAssets/BlindSupplicantM07Meshy20261001/LibraryCastV28/`
- 可编辑源：`Motion/M07_LibraryCast_V28.blend`
- 正式动画：`/Game/Monsters/BlindSupplicantM07/AnimationsLibraryCastV28/A_M07_MagicGather`、`A_M07_MagicRelease`
- 实际保存回执：`ue_library_cast_delivery_v28.json`，`saved=true`；两段正式动画与原 AI/F6 蓝图均已保存。生产日志：`Saved/Logs/M07Import-20261003-173854.log`。

原生重定向资产、姿态制作输入、可编辑 Blender 源、两个 FBX 与正式 UE 资产均已落盘；正式片段时长分别为 1.10／1.30 秒，蓝图基础攻击距离为 220 cm。没有修改近战动作、C++ 或共享倍率，也没有打开交互编辑器。

只复用本机已导入的 Vefects 动作。源包、FBX、原生密集姿态缓存及由其制作的动画仅保存在本机工程，不作为可公开再分发素材。读取制作输入与导入保存不等于游戏验收；本次未启动 PIE、游戏、新渲染或性能测试，实际施法效果和距离由用户试玩。
