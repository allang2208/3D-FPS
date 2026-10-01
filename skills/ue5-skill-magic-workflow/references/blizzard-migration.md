# 暴风雪迁移

案例：`Docs/Skills/blizzard-migration-20260930.md`。数值真源：`Content/ColdSteelData/skills.json:blizzard`；原来源 `game-dev/data/skills.json:skills.blizzard` 与 `src/entities/components/blizzard-system.js`、`src/effects/blizzard-zone.js`。

2026-10-01 当前版本转入 `/Game/Skills/Blizzard/ChargedV3`，制作记录 `Docs/Skills/blizzard-charged-storm-20261001.md`。首次按键凝聚，在火球默认施法位置保留浓密乌云；完成后再次长按同键显示地面椭圆预览，松键锁定最后显示的位置和法线，前挥接触时提交。菜单只收起预览，完成积蓄的乌云仍占用魔法；未完成凝聚被打断、死亡、离场、30 秒持有到期或读档弃置退还实际付款。Profile 预留期间冻结冷却，包括冷却缩减入口，实际释放后开始计时。组件独立持有未释放付款，不使用共享手势的临时付款槽。

当前视觉：四层 49 团稳定乌云核心，近手三层 29 团凝聚云；一个混合降水系统加入雨水和雪花；实际区域白色硬圆盘换为薄霜痕与贴地寒雾，细圈仅用于长按预览。坠落冰锥复用当前 IceSpike/FrostV2 的三种网格和心/壳结构，材质副本启用 InstancedStaticMesh 用途，原冰锥资产不改。仍为 3 个区域 Niagara，共 7 个 ISM、48 个装饰逻辑槽（24 坠冰、24 碎片），最多 4 个区域；所有装饰不额外造成伤害。作者 `Tools/Skills/build_blizzard_charged_v3.py`；只在后台制作、保存与构建，实机由用户测试。

2026-10-01 后续用户确认乌云恢复后，近手云改为 LocalSpace / NoInterpolation，渲染器配置Precise，专用 `M_BlizzardGatherCloud`、`MI_BlizzardGatherCloud` 使用 Responsive AA。仍为 29 粒子，各层独立翻卷、起伏、呼吸和密度变化；原世界区域乌云保持原样。长按地面细圈直接读取 `FPSMagicPreview::LineColor()` 的红色 `(0.95,0.12,0.08)`。定向作者 `Tools/Skills/refine_blizzard_gather_20261001.py`，制作记录 `Docs/Skills/blizzard-gather-natural-red-preview-20261001.md`。

用户随后报告凝聚云团棋盘格：实际SM6日志显示专用母材质DepthFade读取深度与Output Velocity写深度冲突，材质／实例编译失败后回退Default Material。仅关闭该凝聚母材质的透明速度输出，保留DepthFade软边、Responsive AA、纹理和局部翻卷；恢复作者同步False，不再同时开启两项。`Tools/Skills/refine_magic_readability_20261001.py` 已通过现有桥保存这两份材质；没有重建区域云或Niagara。制作记录 `Docs/Skills/magic-readability-and-blizzard-material-fix-20261001.md`，观感由用户测试。

历史 StormV2 乌云与砸落声音优化：诺曼底原生风暴云材质副本组成 18／14／9 团稳定三层核心，附周边飘散；核心结束淡出约 .6 秒。原版 `ice.mp3` 迁移音源派生空间化落地声，非碎片实际接触触发，每区域 .14 秒限流、全局 6 个并发，原伤害拍声音保留。作者 `build_blizzard_storm_cloud.py`，案例 `Docs/Skills/blizzard-cloud-impact-20261001.md`。当前版本继承落地声音限流，视觉由 ChargedV3 接替。

完整接入包含独立 Blizzard model/component/zone、冷钢详情与当前/下级公式、修炼、快捷栏图标/绑定/提示、Profile v18、释放前付款退还和读档恢复。L而不是L−1用于伤害与半轴，(L−1)/19用于冷却和持续台阶。每0.5秒一拍，立即首拍、终点不再伤害；冰锥坠落是装饰，不能重复造成伤害。训练自然结束后汇总，角色经验即时；死亡/离场丢弃未结束训练。

用户限定只覆盖陨星与冰墙，暴风雪 `requiresStaff=false`。仍应用已装备法杖的冰系/法术、链式、耗蓝/冷却/距离与施法速度词条。起手前排队不消费；凝聚起手快照数值，松键锁定地面。落点失效保留完成积蓄的乌云；实际取消/到期与读档弃置返还付款并清除冷却，释放成功清空付款。

性能：局部对象碰撞查询 + 椭圆/高度/遮挡筛选，不扫描全世界；当前 ChargedV3 为 3 个 Niagara、7 个 ISM，共 48 个坠冰/碎冰槽，最多 4 个区域，共享风/装饰几何/细节预算，异步预载。资产 `/Game/Skills/Blizzard`。原迁移作者为 `Tools/Skills/build_blizzard_assets.py` 与后台 Blender几何制作脚本，新视觉作者见上文。后台资产保存及构建不等于测试；实机由用户自测。

冰墙／暴风雪新版图标与暴风雪拖拽入口补齐见 Docs/UI/ice-skill-icons-and-blizzard-drag-20260930.md。新技能必须同时接入技能卡片按下的 DetectDrag 名单和拖影刷子，并沿 StartQuickDrag/DropQuickDrag 的共享绑定与存档链路。新版图源 SourceAssets/IceSkillIcons20260930，恢复脚本同步；不回退旧金边或程序卡通图。未进行实机测试。
