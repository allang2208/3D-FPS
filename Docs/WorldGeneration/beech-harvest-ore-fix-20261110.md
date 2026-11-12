# 山毛榉伐木接入与矿脉默认材质修复

用户要求将温带丘陵的新山毛榉接入既有伐木和生长系统，并排查游戏中的白模矿脉。本次后台制作，不启动图形编辑器、游戏、渲染或验收。

## 问题与直接证据

温带丘陵已将山毛榉作为主树种，但 `ProductionHarvestAssets::TreeVariant()` 只识别四个 `SK_BlackPoplarPCG_*`。新 `SK_Beech_*` 返回 `INDEX_NONE`，使 `PrepareFall()` 跳过预加载、`ReadyFall()` 永远为 false，最后一击无法进入采尽与生长记录提交。树桩分组和倒树加载数组也固定为四项。第一处不匹配在采集资产映射，而不是树木生成概率。

期望行为为斧头扣除生命，最后一击提交木材、采尽和再生记录，留下对应树桩并倒下原树的上半段；生长完成后可再次砍伐。本轮沿该调用链阅读源码和制作实际资产，没有在游戏内重演。

矿脉的直接证据保存在 `SourceAssets/BeechHarvestOreFix20261110/Receipts/ore-fallback-before.log`：2026-11-10 20:02:56 的游戏日志对 Iron、Gold、Copper、Silver 四个实例逐一报告 `missing usage flag InstancedStaticMeshes! Default Material will be used in game.`。后台读取母材质也得到 `used_with_instanced_static_meshes=false`，与症状一致。模型和矿种无需替换。

## 山毛榉接入

- 采集变体表保留黑杨 0–3，追加山毛榉 A–D 为 4–7。倒树预加载数组和树桩实例分组使用同一个八项常量，网络倒树沿既有源网格路径解析。
- 四种山毛榉分别从正在使用的原树源主干制作切割几何。上下段使用同一局部 42 cm 切面和真实封盖，树桩保留原根部、树皮 UV 与局部原点；切口轮廓生成对应的支点配置。
- 上半段复制原骨骼树，再写入切割后的主干，保留源骨架、Nanite Assembly 设置及叶片材质映射。保留山毛榉自己的树皮、叶片遮罩、贴图和材质静态开关，不套用黑杨表皮。
- 新材质在原 PVE 属性链外增加切口／渐隐控制；默认使用真实几何上半段，旧 source-mesh 对照开关使用山毛榉自己的遮罩材质与封盖。黑杨专属板根与内壁裁剪参数不会作用于山毛榉。
- 山毛榉 A/B/C/D 基础生命为 84/96/60/48，继续使用既有尺寸、工具伤害和生命比例存档。木材产出、树桩半血与劈桩掉落规则保持原系统口径。
- 生长记录提交、休眠／成熟时间、偏移幼树、成熟门禁及再砍流程复用既有实现；生长显示本来就按 `Assets->Trees` 动态创建各树种实例。稳定候选 ID 和存档结构未改动，不新增逐树 Actor、Tick 或运行时切割。
- 林下独立装饰幼树不在本次采集树表扩展范围；本轮接入的是主树层的四种山毛榉。

资源目录：`/Game/Items/HarvestTimber/Beech/`。制作源位于 `SourceAssets/BeechHarvestOreFix20261110`：先执行 `export_sources.py`，再以后台 Blender 执行 `cut_tree_sections.py`，最后用序列化的 UE commandlet 执行 `install_assets.py`。源 Fab 资产和站立树资产不保存、不覆盖。

## 矿脉修复

母材质 `M_HillsOreRock` 启用 `used_with_instanced_static_meshes`，更新并保存铁、铜、银、金四个材质实例，保留现有纹理、矿脉颜色和矿种参数。`Tools/Production/build_ore_vein_rocks.py` 同步增加该标志，后续重建也具备 ISM/HISM 所需的材质用途。没有重建岩块网格或改变矿种掉落判定。

矿脉五个资产已于 20:08:33 保存，回执为 `Receipts/ore-saved.json`。原材质二进制备份与修改前源码保存在同一任务目录的 `Backups`。

## 构建与交付边界

`FPSGAMEEditor Win64 Development` 于 20:11:24 后台构建成功，回执为 `Receipts/FPSGAMEEditor-build.json`。源码编译和链接完成，不代表已完成游戏内挥砍、联机、生长或画面验收。

山毛榉 28 个资源已于 20:14:14 保存，包含四种树形各自的静态上下段、骨骼上半段、切口封盖和支点配置，以及八个专用材质／实例。回执 `Receipts/beech-saved.json`，后台保存日志 `Receipts/import-20261110-201305.log`，commandlet 退出码 0。首次材质连接脚本因 If 引脚的显示名与字段名不同而中断，修正为使用引擎返回的引脚名后完成制作；中断前未保存山毛榉目标资产。

未使用 computer use，也未进行游戏、画面或性能测试。用户重新进场查看山毛榉伐木、树桩和矿脉表现；生长及再砍仍按现有游戏时间推进。
