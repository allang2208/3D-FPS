# 法袍第一人称袖型、织物和袖口惯性

用户反馈第一人称袖子像紧身衣、材质质感不足，并要求按照技能里的衣物标准升级袖口物理。

采用 `ue5-fps-arms-animation` 的 `glove-clothing-surface-production.md`、`garment-quality-pipeline.md` 和 `chainmail-surface-and-secondary-motion.md` 中关于真实厚度、物理纹理尺度、原生绑定及内外层同步运动的做法。遵守本次用户规则：完成制作、必要构建、保存与接入，游戏测试和视觉验收交由用户。

## 修改范围

当前法袍共有 23 个第一人称 rig 路由：M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、RuneSword、FrostSword、FrostArms、Axe、Pickaxe、DW715_l/r、M1911_l/r、Traversal、Bow、LMG201、Super90。装备管理器继续通过这些 profile 为现有武器别名选择对应原生网格。

在活动法袍的成对袖子源上局部修形，保留每个 profile 的参考骨架、权重、手部动作和原拓扑。外层与内衬一起增加松量，袖口额外约 6.5 mm、袖身最高约 11 mm；肩部平滑减弱，肘部留有较小增量。加入幅度受限的纵向、斜向压褶，袖口压褶更轻。厚度由原 1.4 mm 调为袖身约 1.8 mm、袖口约 2.2 mm。

布面使用同一物理高度场生成的斜纹、法线和粗糙度：8 cm 周期、约 0.625 mm 纱线间距、2048² 贴图。刺绣保留原浅银星纹及藤线图案，增加线体起伏与纤维方向；内衬为更暗、更粗糙的蓝色织物。UE Cloth 着色提供有限绒面反光，金属刺绣区域抑制绒量，纹理保留 mip 和流送。

袖身及内衬重新按厘米校准 UV，避免同一织纹随手臂原图集比例变化。端面保留独立厚度 UV，原刺绣带比例保留。

## 袖口运动

复用 `FPSOutfitSecondaryMotion` 和服装管理器的现有更新流程。左右手各一组阻尼弹簧，读取手部位移及旋转带来的惯性：

- 法袍频率 4.5 Hz，阻尼比 0.9，最大偏移 0.28 cm。
- 相同轴向位置的外层、内衬和端面共享顶点色遮罩及位移；从袖口向肘部衰减。
- 当前/上一帧位移同时传给材质，沿用显隐、跳变和过大时间步重置。
- 独立强度开关 `fps.Outfit.RobeCuffSway`，范围 0–1；锁子甲继续使用原频率、阻尼、幅度和开关。
- 无新增动画或独立袖子 Tick；仍由各武器原生手臂驱动蒙皮。

这部分为有界弹簧惯性形变；并未制作逐点 Chaos 袖口或新增袖口碰撞求解。

## 资产与接入

本轮源和回执位于 `SourceAssets/BlueMageRobe20261018/FPSoftSleeves20261020/`。`Authored/` 保留 23 套完整原生源，`Exports/` 保存 23 个 FBX 和 M4 可编辑 `.blend`，`Textures/` 保留 PBR 与物理高度场。

新 UE 资产位于 `/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/FPSoftSleeves20261020/`。保存沿用原生服装写入器及三档第一人称 LOD。只切换当前法袍的 23 个 FP 路由和 `secondary_motion=robe_shared_sway_v1`；第三人称身体、裙摆布料、内层腿部遮罩和裤靴映射均保留。原始总发布入口保留已经发布的新版第一人称路由，避免后续重制裙身时退回旧袖子。

作者入口：`author_soft_sleeves.py`、`bake_soft_sleeves.py`、`export_soft_sleeves.py`。材质与接入入口：`soft_sleeve_materials.py`、`save_soft_sleeves.py`、`publish_soft_sleeves.py`。

## 完成状态

`soft-sleeves-build-02` 的 Editor 和 Game 目标均构建成功。首轮 DLL 链接曾因占用失败，后续窗口已完成。材质保存首轮遇到 Clamp 引脚命名差异，改为读取实际引脚名后已保存三种材质。

`soft-sleeves-save-02` 至 `04` 保存了前 12 套原生衣袖；`05` 通过现有编辑器桥接入时检测到 PIE，作者脚本在任何写入之前停止。用户关闭后，`06` 至 `08` 继续完成剩余 11 套。23 套网格与三种材质现已全部保存，`saved_assets.json` 和 `published.json` 均记录完成，配置已切换到新袖子与独立袖口惯性样式。

没有启动编辑器、游戏、截图或执行动作/物理回归；重新开始试玩后生效，实机布面、袖型和袖口运动尚待用户确认。
