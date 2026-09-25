# 独立服装与手套换装：实现记录

## 使用入口

在 F6 开发面板的「服装与手套」分类领取以下物品，再通过现有背包装备操作穿戴：

| 装备 | Definition | 现有装备槽 |
| --- | --- | --- |
| 野行长袖上衣 | ue_field_sweater | armor，上衣槽 7 |
| 炭灰长袖上衣 | ue_field_sweater_charcoal | armor，上衣槽 7 |
| 棕革短手套 | ue_field_gloves | gloves，手套槽 3 |
| 墨黑短手套 | ue_field_gloves_black | gloves，手套槽 3 |

衣服与手套独立穿脱。手套槽未穿戴本套手套时使用裸手表面；没有新上衣时保留原有布袖外形和材质。四个物品使用现有背包、仓库、掉落和存档机制，不添加另一个拥有权系统，不向玩家存档自动塞物品。

## 运行结构

`UFPSModularOutfitComponent` 消费本地现有装备栏变化，以及世界身体的 `FFPSBodyOutfitSlot`。原枪械、近战、工具和施法组件继续负责动作；新衣袖、手套与身体基底通过 Leader Pose 跟随实际宿主。

源网格按完整资源路径匹配 `RigProfile`，各自使用其真实参考骨架生成的派生资源。PKM、SVD 不共用猜测的重绑；双持左右显示按网格真正使用的骨骼侧制作。源武器的动画、骨骼 reference pose 和机械部分不改。

外观资源先异步加载。新网格与材料齐备后才切换部件并隐藏原手臂 section；期间保留上一套完整外观。快速换装与切枪重新读当前装备/宿主，过期请求取消。第一人称组件不依赖第三人称身体开关。

装备材料使用组件独立覆盖，不在穿戴时修改共用材质。原腕指骨保持驱动；不通过缩骨或隐藏骨来遮挡身体。

## 配方与扩展

实际实现采用 `Content/ColdSteelData/modular_outfits.json` 作为独立的**表现配置**，现有 `items.json` 仍是物品目录，现有 `player_body.json.outfits` 的老入口保留。这样可登记整套现有姿态源的绑定派生表，不把数据重复写入每件物品或改动其它世界身体配置。

- `profiles.<source asset path>`：基底网格、默认长袖/手套网格、原手臂材质区和基底遮挡区。
- `items.<Definition>`：装备槽、部件类别、材料、逐 profile 的 `rig_meshes`。
- 同款不同颜色复用网格；新形状指定自己的 `rig_meshes`。缺少派生资源时保留当前完整表现。
- 新短袖、长手套、肩甲或护臂要制作自己的覆盖边界，必要时扩展基底分区；本版的整臂覆盖不能直接用于短袖。

覆盖的姿态源包括世界身体、M4、AKM、QBZ191、ASH12、M16、M1911、DW715、A762、SVD、PKM、两种剑/独立剑手臂、斧、镐、四个双持来源、Traversal/施法手臂，共 21 个 profile。

## 制作与交付范围

衣服由 CC0 完整上衣适配体型后派生第一人称袖子；裸手使用 CC0 解剖表面适配既有腕指关节，手套是独立带权重薄壳。来源、可编辑 Blend、导出 FBX 和工具顺序见 `SourceAssets/ModularOutfit20260924/README.md`。

第一版无 Chaos Cloth 或额外布料求解。部件复用源姿态，不运行独立 AnimBP；远距离 LOD 使用 50% / 20% 减面目标，并保留接缝边界。实际帧率和动作穿插没有进行测试。

世界服装接入现有权威装备外观入口；这不新增客户端背包网络协议。完整联机装备交易、权限与多人联调仍属于后续联机系统工作。

本轮按用户规则不启动游戏、不运行回归、不制作验收截图。最终保存与构建状态单独记录在本目录交付状态段；脚本、FBX 生成不等同于 UE 资产已保存。

## 交付状态

2026-09-24 19:58，完成以下交付：

- 21 组绑定 profile，共 63 个骨骼网格，均已导入 UE 并保存；每个网格包含 LOD0、LOD1、LOD2。资产目录为 `/Game/Characters/ModularOutfit20260924`。
- 4 个装备材质、针织法线、2 个静态掉落模型已保存；4 张透明库存图标已写入 `Content/ColdSteelData/Icons/ModularOutfit20260924/`。
- 4 件物品已登记到现有 `items.json`；`modular_outfits.json` 已发布全部 21 组配方。沿用现有装备、仓库、掉落和存档路径。
- 常规 Editor 模块构建完成，日志 `Saved/BuildEditor/build-20260924-195253.log`。
- 后台资产导入完成，日志 `SourceAssets/ModularOutfit20260924/import-headless-05.log`；保存回执为同目录 `imported.json`。
- 本轮未启动编辑器 GUI 或游戏，未运行测试、截图或联机验收。实际动作贴合与穿插仍由用户试穿确认。

## 未装备时的原手模恢复

以下为上一轮修复记录，后续默认裸手按下一节的新原生绑定资产实现。

用户反馈未穿戴新装备时也出现手模破碎和缺失。原实现只要识别到姿态源就创建替换基底并隐藏原手臂，因此空装备状态也受到新基底影响。

`DiscoverSources` 现先判断上衣槽或手套槽是否有本套外观配方；两者都没有时，取消未完成的资源加载，释放所有替换部件，按记录恢复原手臂材质区，然后直接结束处理。隐藏/非活动姿态源也会一起释放，避免再次切回时残留替换。原武器资产、动画及新装备资源均保留。

本次仅修改现有 C++ 函数逻辑，已在当前运行的编辑器中通过 Live Coding 应用；结果为 `SourceAssets/ModularOutfit20260924/default-hands-livecoding-result.json`。源码已保存，基础 Editor DLL 仍以此前常规构建为准，后续常规构建会纳入该修复。本次未运行游戏测试或视觉验收。

## 默认裸手：原生绑定制作

用户确认原手模恢复后，要求空手套槽不再显示原生皮革手套。本次新增 `NativeSkin/SK_<Profile>_NativeBareSkin`，覆盖现有 21 组源网格；原枪械网格和动画资源保留。

- 从 UE 原资源提取参考姿态、前臂位置和权重；在原 UE 网格的独立副本上写入表面数据。骨骼顺序、参考骨架、逆绑定矩阵和 Skeleton 引用沿用源资源，不再通过 FBX 重新生成绑定。
- 替换腕部以外的原手套几何，使用已有 CC0 MakeHuman 手掌和五指表面，适配本枪腕指关节。保留原前臂及默认布袖，手腕处以闭合环桥接为连续网格，前臂一侧继承原扭转骨权重。
- 手掌、五指及裸露前臂使用项目皮肤材质，去除皮革、缝线和卷边表现；装备手套仍使用独立手套部件与覆盖区。
- 配方 `base` 与 `native_bare_skin` 指向新资源；`native_bare_hands_default` 显式启用空装备默认裸手。尚无原生裸手资源的未来 profile 保留原模型，不自动启用旧重绑基底。
- 保留异步加载与 Leader Pose，不新增独立 AnimBP 或布料求解。LOD0 为作者网格，LOD1/2 继续采用 50% / 20% 的制作目标。

作者源与资产保存回执见 `SourceAssets/ModularOutfit20260924/NativeSkin/`。本轮不运行游戏、截图或验收；动作中的裸手贴合由用户体验确认。当前编辑器使用 Live Coding 接入，基础 Editor DLL 仍待正常关闭编辑器后的常规构建。

本次制作已完成：21 个原生绑定裸手网格及其 LOD 已保存，配方已发布。最终制作日志 `native-skin-author-04.log`，资产接入回执 `native-skin-import-04.txt` 至 `native-skin-import-09.txt`，当前编辑器编译结果 `native-skin-livecoding-result.json` 为 Success。保存过程中曾因当前游玩状态被拒绝，已结束该次游玩后续接完成；没有重新启动游戏。

## 裸手发黑修正：三角面绕序

用户随后反馈双手剑的裸手与前臂全黑。读取源网格和新网格后发现，源网格顶点法线与面法线的平均点积约为 +0.968，新网格约为 -0.986；原袖子相同顶点位置的法线与源模型仍约为 +0.997，而面方向相反。材质路径正确，原资源构建日志成功。

原因在 `author_native_skin.py`：坐标反射转换到 UE 后又反转三角顶点顺序，导致实际面朝向与保留的外向法线相反。修正为 UE DynamicMesh 的绕序，`surface_export_version=2`；`repair_native_skin_winding.py` 将已制作的 v1 表面数据迁移到 v2，位置、权重、UV 和法线不改。`import_native_skin.py` 据作者散列重新构建 LOD0/1/2 并保存，按正式 profile 清单读取表面文件，避免把配方备份当作网格。

本次仅涉及模型表面与作者脚本，无 C++ 变更。诊断记录为 `black-skin-cause-02.txt`，重建回执为 `native-skin-winding-import-01.txt` 至 `native-skin-winding-import-06.txt`。未启动游戏、截图或运行验收。
# 当前生效状态：M4 裸臂候选默认启用，其他武器保留原手模

用户反馈 NativeSkin 全局替换后多套原动画扭曲、穿模，已暂停批量替换。配置 `native_bare_hands_default=false`，其他武器空装备状态恢复原手模。M4 单独使用 `Config/DefaultEngine.ini` 的 `fps.Outfit.BareArmsCandidate=1` 作为项目默认；已应用到用户当前运行的编辑器，不再要求手动启用。本套模块化装备仍沿用已有配方，不清除物品或修改存档。

写实制作转入 `SourceAssets/ModularOutfit20260924/RealisticM4Candidate`：连续 MakeHuman 裸臂网格、官方 CC0 肤色贴图、独立皮肤材质，M4 原参考骨架和动画不变。控制台 `fps.Outfit.BareArmsCandidate 1` 仅对未穿戴模块化上衣/手套的本地 M4 视模生效，`0` 恢复原模型。候选键纳入异步加载和部件身份，切回时释放候选并恢复原材质区。

本轮 C++ 常规构建为 `Saved/BuildEditor/build-20260924-210632.log`。没有启动编辑器 GUI、游戏或运行测试。资产保存状态见候选目录 `saved.json`，操作说明见同目录 `README.md`。M4 尚待用户试用，其他枪械和第三人称没有切换到这个新候选。

注册脚本保留当前默认开关和 M4 候选字段，重新登记装备不再自动重新启用全局裸手。下方是此前迭代历史，不能作为当前动画兼容性结论。
