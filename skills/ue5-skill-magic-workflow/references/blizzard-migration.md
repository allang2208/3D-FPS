# 暴风雪迁移

## 法杖限定高级魔法（2026-10-14 当前规则）

用户指定暴风雪是必须当前装备法杖才能释放的高级魔法。配置 `blizzard.requiresStaff=true`，原生默认值同为 true；卡片分类、简介、详情和快捷槽“需要法杖”提示同步。排队、凝聚、持有和接触释放沿用当前装备校验，释放请求发出前切走法杖取消并退还实际付款；已发出的联机释放由权威回执完成提交或退款，已释放区域继续运行。伤害、消耗、冷却、成长、修炼和特效不改。记录见 `Docs/Skills/blizzard-staff-required-20261014.md`。下文 `requiresStaff=false`／不限定法杖仅描述此前历史，本条优先；未进行游戏或联机测试。

## 立体范围与分层表现（2026-10-13 当前口径）

用户明确完整楼板仍阻挡，只在开放楼梯、中庭中跨高度。当前伤害改为以落点为中心的椭圆柱体：水平半轴沿用施法快照，垂直上、下各 `RadiusY * 2.3 + 150` cm；目标身体多点同时满足体积与无遮挡视线即可命中，不再依赖贴地或视觉网格。传播起点受本层天花板限制，实墙、门和楼板保留；不是绕墙扩散。

环境按 2 Hz 采样 25 列、每列最多 3 个可见地面层，复制 75 单元。各有效层独立云雪雾霜，最多 9 个激活 Niagara；48 个落冰／碎片槽仍全区域共享。3 层只限制特效，不限制伤害的楼层数。雷暴云副本新增同层台阶插值及时间平滑，并立即限制在真实天花板下；云的基础高度沿各层地面调整，区域仍固定于释放点。定向作者 `Tools/Skills/build_blizzard_volume_cloud.py`，完整云作者同步。交付状态及明确边界见 `Docs/Skills/blizzard-volume-20261013.md`。下文单层 25 单元及最多 3 个 Niagara 均为历史实现；未做游戏或性能测试。

## 暴风雪直接复用雷暴云层（2026-10-12 后续修订）

用户截图否定初版 RollingV1 的 50 个细小网格云团，现用暴风雪资产保持同一路径，改为直接复制雷暴的五层云发射器：48 个核心粒子加有界边缘，尺寸／分布／密度／材质沿用雷暴，不带放电和电火花。25 个房间单元只约束实际云团的净空与墙边宽度，不再决定云团的 XY 排列。定向作者 `Tools/Skills/reuse_storm_domain_blizzard_cloud.py`，完整作者的 `blizzard()` 同步；已在现有编辑器中编译保存，无 C++ 变更，未游戏测试。说明 `Docs/Skills/blizzard-storm-cloud-reuse-20261012.md`。下文 50 云团配置是被替代的历史。

## 翻卷乌云 RollingV1（2026-10-12）

雷暴、暴风雪区域云与近手凝聚云的运行引用改为 `/Game/Skills/StormClouds/RollingV1` 三个独立 Niagara，当前作者 `Tools/Skills/build_rolling_storm_clouds.py`；制作和实际保存状态见 `Docs/Skills/rolling-storm-clouds-20261012.md`。参考百目 SmokeVisibilityFixV21／沉匣毒雾共用的 Mantaflow 密度图集，独立时间循环密集帧，采用深灰／冷灰配色，保留怪物源资产。

雷暴仍按头顶锚点同步 XYZ、压缩净空内厚度并保留原电光；暴风雪云仍依 IndoorV5 的 25 单元地面／净空／宽度定位，雪、寒雾、落冰、伤害与预览继续沿用 IndoorV5；近手云保留 ChargedV3 的局部跟随。48／50／29 个主体粒子不增加，新材质每像素两次密度采样。旧版本作者仍是恢复输入，完整恢复最后执行 RollingV1 作者；下文旧云资产路径只描述历史，不能覆盖当前加载引用。未游戏测试或观感验收。


## 室内适配 IndoorV5（2026-10-12）

用户已授权实施室内方案，交付状态见 `Docs/Skills/blizzard-indoor-implementation-20261012.md`。运行引用转入 `/Game/Skills/Blizzard/IndoorV5` 的三套区域 Niagara 及地霜／预览材质，近手凝聚云仍为 V3；作者 `Tools/Skills/build_blizzard_indoor_v5.py`，完整 V3 作者末尾衔接 V5。以下 V4 描述为修复历史。

`BlizzardEnvironment` 共用落点、地面、空间和通路判定，墙／顶命中从障碍前方向下找同室地面。25 单元保存局部地面、净空和宽度，2 Hz 复制；预览 5 Hz 共用足迹。低顶逐步转薄云、短落冰、贴地寒雾和横向飞雪，基础雪雾保留最低发射量。伤害独立于装饰，35／90／150 cm 通路限制在各自净空内，保留真实墙／门／楼板；不再按中心固定 100 cm 高差排除楼梯。装饰云／冰／声音缺失可降级，有效基础反馈全缺失则失败退款。仍最多三区域 Niagara、48 冰槽、四区域；没有实机验收。

## 暴风雪修复口径（2026-10-12）

本节替代下文区域云仍为 ChargedV3 的历史描述。区域云使用 `/Game/Skills/Blizzard/ClearanceV4/NS_BlizzardStormCloud`，近手云、雨雪、寒雾与冰锥继续使用当前 V3／FrostV2。25 个邻接盒体扫掠以 2 Hz 更新净空，服务端复制高度与厚度；四层 49 团云按表面法线对齐、零旋转，低顶压薄且不缩小伤害范围。定向作者 `Tools/Skills/build_blizzard_clearance_v4.py`，完整 V3 恢复作者末尾会接着恢复 V4。

联机凝聚等成功回执后才可释放；释放回执前保留付款，成功提交、失败两端退款。取消和释放不得被节流静默丢弃；服务端重新核对地面、距离、视线与四区上限，并对死亡／丢失 pawn／持有超时回收预留。区域异步加载资源，显示年龄来自服务端起始时间，客户端结束不发修炼奖励。技能已补升级通知、F6 调级与两阶段施法说明；原等级成长和 `requiresStaff=false` 保留。修改与交付状态见 `Docs/Skills/blizzard-fixes-20261012.md`，未做游戏或联机测试。


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
