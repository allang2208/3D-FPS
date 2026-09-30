# 炭灰短袖：第三人称破口与攀爬衣袖修复（2026-09-30）

本轮根据用户提供的第三人称截图与攀爬反馈，修复 `ue_field_sweater_charcoal` 的 Body、Traversal 两个绑定。资产、配置、掉落模型与图标已落盘；未启动游戏或进行实机验收。其他枪械的衣袖、橄榄长袖、锁子甲、动画和玩法属性不在本轮变更中。

同日后续的第一人称色块/尖刺反馈另见 [第一人称衣袖修复](charcoal-camera-repair-20260930.md)：处理剩余 21 个第一人称绑定，保留这里的 BodyV4 与 TraversalV2。

## 已定位的原因

1. 旧 `author_charcoal_short_sleeves.py` 按骨名 `_l/_r` 后缀选择裁切顶点。Body 下摆也有腿部权重，袖口切平面误切了下摆；源网格留下两处各 89 条边的破口。仅限制到上肢骨名又会漏掉带其他权重的旧袖口残片。本轮 Body 改为明确选择躯干外侧的袖身，重新裁短，完整保留下摆。
2. 衣身来自较早的衣物拟合，肩部在原生身体内约 1.6 cm；领口附近也未充分适配。源身体与衣服在肩/腋下的权重过渡不一致，抬臂会放大问题。
3. Body 原 `world_covers=[3]` 隐藏整个躯干材质区，而该区包含一部分脖子，最高到约 161.5 cm。领口并不能覆盖它，因而会显示身体断口。另一方面，上臂区没有隐藏，会从衣服肩部穿出。
4. Traversal 虽在前一次修正过权重，仍保留旧自动填孔产生的 240 个肩部封面及 32 条非流形边；最长边约 18.17 cm。权重修正不能消除错误拓扑。

## 实际修复

- 从完整 Body 长袖源重新裁切短袖，恢复完整下摆；按当前身体拟合肩、领、胸背，内外层共用位移与权重，平滑肩部权重过渡。
- 采用这件衣服专属的身体覆盖：`world_covers=[1,3,4]` 隐藏原粗分的上肢、躯干、其余身体区，衣服组件按实际衣缘带回可见的原生手臂、颈部、头部和下半身。旧“其余身体”区也混有衣内几何，不能把它当作纯头腿。皮肤位置、权重、UV、材质保持原生；袖口皮肤搭接 0.5 cm，颈部按实际领口曲线切边。手掌/手指仍由原基底与手套接管，现有手套覆盖规则保持。
- 不靠继续膨胀腋下布料消除所有遮挡；未采用中途的额外全姿态推离尝试。
- Traversal 完全重建袖身：按原生 V7 上臂的 24 个截面、每圈 80 个采样拟合内外层，共享同一权重场，明确连接肩端与袖口的厚度环。肩端保持真正开口，不再继承旧封面；保留原攀爬动作与接触点。
- 两个资产均实际生成并保存三档 LOD。沿用衣物保边策略，保护边界/骨骼分区、禁止内外层焊接，比例为 1.0/0.9/0.8，设置写入 UE 的 `source_models`。
- 使用同一修复后的纯衣服源生成掉落 FBX/静态网格与透明装备 PNG；图标不包含随衣服接回的皮肤片。

## 当前路径

- Body：`/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/BodyV4/SK_Body_Charcoal`
- Traversal：`/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/TraversalV2/SK_Traversal_Charcoal`
- 掉落：`/Game/Characters/ModularOutfit20260924/CharcoalGarmentRepair20260930/PickupsV3/SM_Charcoal_Garment`
- 图标沿用 `Content/ColdSteelData/Icons/FieldSweaterKnit20260929/ue_field_sweater_charcoal.png`，旧存档别名同步。

`SourceAssets/CharcoalGarmentRepair20260930/` 保存实际资产快照、作者 JSON、带原生骨架和材质的 Body/Traversal Blend、掉落 FBX、导入/发布回执。`Authored/Body.json` 是纯衣服；`BodyEquipped.json` 是带专属可见皮肤片的装备组合。不要用旧的 `ShortSleeve/Body.json` 覆盖当前版本。

可重建顺序：后台 Blender `produce.py` → UE `install.py` → Python `publish.py` → 图标入口 `inventory(only_items=['ue_field_sweater_charcoal'])`。首次导入/保存使用适用 commandlet；已有编辑器时沿用 MCP 互斥桥。`install.py` 的保存回执用于续接同次制作，改源后应使用新候选路径。

## 排查边界

检查了实际保存源/三档 LOD 的衣服拓扑，以及 Body 待机/持枪、Traversal 翻越/翻上/攀爬的压缩姿态。离线资料与 `diagnosis.json` 仅解释本次结构和蒙皮问题，不代表游戏相机、运行时 IK、光照或最终画面验收。裁掉被衣服遮住的皮肤后，开放皮肤表面的最近法线距离不再能当作闭合人体的穿透深度。

最终落盘结构记录为 `saved-structure.json`：Body 三档衣服部分为 23976/21634/19752 三角形，Traversal 为 15360/13822/12286；六档的非预期开放边和非流形边均为 0。Traversal 最长边为约 1.54/2.61/2.90 cm，已消除旧的约 18.17 cm 肩部跨面。完整的薄壁模型可以有袖口/领口孔洞，同时其布料厚度表面没有开放边。

制作阶段 `contact-authored.json` 中的定向诊断（并非最终资产的游戏验收）：参考姿态下衣服与可见皮肤没有三角面相交；Traversal 的 33 个动作采样外表面没有检出相交，个别采样内壁仍有接触。Body 持枪姿态仍检出领口/腋下局部接触，**不能据此交付为全动作零穿模**，尚未在实际游戏中确定其可见性。先前增加全局姿态推离量的尝试没有采用；最终保留可辨认的衣服轮廓与原生动作。

剩余实机确认：第三人称持枪领口/腋下，以及玩家攀爬时的肩端相机近裁面。该项保持未验收，不把构建成功、网格闭合或离线采样代替实际画面。

配置在角色初始化时读取；本次不启动或重启游戏。用户下一次进入游戏测试第三人称领口/肩/下摆与第一人称攀爬袖口。保留旧资源作为恢复依据，未清理其他工作。
