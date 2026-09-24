# 仓库箱子五档材质升级 · 2026-09-24

用户要求：使用 Blender 管线，参考现在的仓库箱子，做五款由低到高等级的不同材质的箱子：
木质 → 石头装饰+木质 → 铁质主体 → 铁质主体+金子花纹 → 银材质主体+宝石+金花纹。
后续追加：接入建筑面板「其他」栏；**首轮程序化箱体被用户判定"模型不达标"，
第二轮改为直接基于现行仓库宝箱几何派生五档**（本文档现状＝第二轮）。

## 第二轮（现行交付）：基于真宝箱几何派生

- 源：`SourceAssets/ChestRitual20260909/warehouse_chest_ritual_v8.glb`（现行仓库宝箱制作源）。
  `inspect_chest_source.py` → `chest_source_report.json` 先做槽位角色测绘（11 槽：
  大理石面板、黄铜导轨/拱箍/铰链锁件、金饰件、蓝宝石、深蓝绒/魔法蓝内衬、
  正面香槟金浮雕／深枪灰浮雕／雕花纹线），并确认 rest 姿态＝闭盖。
- `derive_from_chest.py`（Blender 5.1 无头）：导入 GLB（该文件 `skins:0`，导入器不建骨架，
  代码里的"应用 Armature 修改器"是**条件分支、从未触发**——静态网格本就无蒙皮，详见第五轮）→
   **连层级先 join 主体/盖/锁扣（世界拼装天然正确）→ `parent_clear(CLEAR_KEEP_TRANSFORM)`
  烘进数据 → 用"目标 151.2 cm ÷ 实测"归一系数定标成厘米**（glTF 单位链陷阱见自检清单）→
  地面枢轴、清自定义分裂法线、按 40° 面夹角重建平滑组（`edge_keys` 邻接，5.1 无
  `MeshEdge.link_polygons`）、平面 UV（米制 1:1）→ 每档复制一份，按槽位映射表把 11 个源槽
  重排到 `Crate_*` 材质族（先捕获面索引再 clear，槽序固定），三角化导出
  `Authored/SM_WarehouseCrate_T*_*.fbx`（各 46 674 三角，源模型原样），可编辑源
  `Authored/WarehouseChestDerived.blend`，回执 `derive_receipt.json`。
  拼装实测 **151.2 × 119.6 × 123.3 cm**，与参考宝箱逐厘米一致（同一几何）。
- 槽位 → 五档映射（同一轮廓，只换材质分区）：
  | 源槽（角色） | T1 木箱 | T2 石饰木箱 | T3 铁箱 | T4 金纹铁箱 | T5 宝石银箱 |
  | --- | --- | --- | --- | --- | --- |
  | 面板（大理石） | Wood | Wood | Iron | Iron | Silver |
  | 导轨/拱箍（黄铜框/箍） | WoodDark | Stone | Iron | Gold | Gold |
  | 铰链/锁扣（黄铜五金） | IronDark | Iron | IronDark | Gold | Gold |
  | 金饰件（Gold_PBR） | WoodDark | Stone | IronDark | Gold | Gold |
  | 宝石（Sapphire） | WoodDark | IronDark | IronDark | IronDark | **Gem（保留）** |
  | 内衬（绒/魔法蓝） | WoodDark | WoodDark | IronDark | IronDark | IronDark |
  | 正面浮雕·香槟 | WoodDark | Stone | Iron | Gold | Gold |
  | 正面浮雕·枪灰 | Wood | Stone | IronDark | IronDark | Silver |
  | 雕花纹线 | IronDark | IronDark | IronDark | **Gold（金花纹）** | **Gold（金花纹）** |
- 贴图与 8 个 `M_Crate_*` 材质沿用第一轮产物（程序化 Surface/Normal 图＋槽名绑定），未重建。
- 引擎重导（编辑器在跑 → 远程执行 `reimport_derived.py`）：五个网格以 **`SM_*_v2`** 新名导入
  （绑定既有 `M_Crate_*`，Complex-as-Simple、切线重算、Nanite），回执 `reimport_receipt.json`
  （43 369 三角＝UE 口径，尺寸逐档 151.2×119.6×123.3）。
- **幽灵包事故与处置（如实记录）**：首轮重导按"delete→同路径导入"执行，`delete_asset` 只注销
  注册表，内存包与磁盘 `.uasset` 仍被运行中的编辑器锁住，同路径再导入撞上内存孤儿，
  `get_objects()` 为空；`delete_loaded_asset` 因图标池引用返回 False。改走 `_v2` 新名 +
  调色板改指新名（幂等复用分支防半途崩重跑）。**旧 `SM_*` v1 五个 .uasset 文件仍在
  `Content/Props/WarehouseCrateTiers20260924/`，注册表已不认、无任何引用，编辑器重启后可删**
  （拟删清单：`SM_WarehouseCrate_T1_Wood.uasset` … `SM_WarehouseCrate_T5_SilverGem.uasset`，
  删除前用 `trash/warehousecrate-procedural-v1-20260924/` 收纳）。

## 建筑面板「其他」栏（现行状态）

- 调色板 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette` `Components` 五条
  `warehouse_crate_wood/stonewood/iron/irongold/silvergem`（木箱／石饰木箱／铁箱／金纹铁箱／
  宝石银箱），`Material` 留空＝只出现在「其他」栏（高炉先例），`Surface` 留空＝不压多材质。
- 占格按 v2 包围盒重取整：**8 × 6 × 7**（160 × 120 × 140 cm 占位，四边余量 4.4/0.2/8.4 cm），
  `PivotOffsetCm.Z = −8.35` 落地贴地，`Mount=Free`，构件免料；条目 23 → 28。
- 全程编辑器内远程执行（`ue_python_exec.py --script`），整数组写回＋`save_packages`＋
  重读断言＋磁盘核对；注册脚本 `register_crate_prefabs.py`（回执 `register_receipt.json`）。
- 当前运行中的 PIE／已开面板不会热感知；重启 PIE 后面板出现五张新卡片，图标由
  `VoxelBuildIcons` 逐槽取材质渲染（重启后自动用 v2 网格）。

## 第一轮（已取代）：程序化箱体

`author_crates.py`＋`make_crate_maps.py`＋`install_crates.py`：从零 `from_pydata` 堆出
164×132.5×111–117 cm 的同族箱体（9 384–32 629 三角），自造木/石/铁/金/银无缝 PBR 贴图
与 8 个材质，UE commandlet 导入（日志 `install-1..6.log`，含槽位塌陷与 API 笔误的如实记录）。
**用户判定模型不达标**，箱体网格与源（`Authored/superseded_procedural/`）已被第二轮取代；
贴图与材质族全部保留复用。第一轮的技术教训（材质槽 clear、曲线封口、commandlet API 兜底等）
已沉淀到 `skills/asset-model-workflow/references/blender-hardsurface-checklist.md`。

## 第三轮（质感修复）：拱盖缺失修复 + 贴图材质 v2（2026-09-24）

用户游戏内截图反馈：**所有档位的上半圆弧盖面缺失**（透过箍带能看见内衬），且表面材质粗糙。

- **根因（实测确认，非猜测）**：宝箱的拱盖外壳是**单层薄面片且绕向与箱壁相反**，
  原始资产一直靠双面渲染盖住这一点——探针读到原 `M_Ritual_Metal.two_sided = True`。
  我们的 `M_Crate_*` 是单面 → 外壳被背面剔除 → 拱面"消失"。
  **修复：7 个结构材质 `two_sided=True`**（与源设计口径一致；`M_Crate_Gem` 为封闭实体保持单面）。
  零网格改动、无需重导 FBX。
- **质感 v2**：`make_crate_maps_v2.py` 重画 10 张 2048² 贴图——木纹改为**沿板长方向的
  定向纹理＋4 条板带各自色调/相位＋板缝凹槽**；石头改大块晕染＋软裂纹；铁/金/银改
  **拉丝长条纹理**（银双向拉丝、粗糙度 0.08–0.22 接近镜面）；法线生成先 5×5 周期盒式低通
  再取导数（v1"静电感"的直接来源就是逐像素高频抖动法线），回执断言 z_mean≥0.90
  （实测 0.911–0.984）。材质图重建：反照率真正用上宽域 R＋细节 G 双通道（v1 的 G 通道
  在图里根本没接线）、逐族粗糙度区间收紧、加 Specular 常量（金属 0.55–0.6、木 0.35、石 0.25）。
- **执行**：贴图**同名 replace_existing 原地重导**（更新同一 UTexture 对象，材质连线自动保留，
  无幽灵包风险——幽灵只发生在"删除再导入"）；`fix_crate_materials.py` 先经远程执行（编辑器
  在跑时完成 7 图重建），编辑器关闭后以 commandlet 补完宝石图并保存全部；
  断言逐项读回（`two_sided`、压缩设置、sRGB、recompile 空返回），回执 `fix_receipt.json`，
  日志 `fix-1.log`。
- **v1 幽灵文件已清**：编辑器关闭后五个旧 `SM_WarehouseCrate_T*`（程序化箱体）`.uasset`
  移入 `trash/warehousecrate-procedural-v1-20260924/`，散列见该目录 `manifest.txt`。
  引擎目录现仅存 `_v2` 五网格＋8 材质＋10 贴图。

## 第四轮：木档改用游戏体素木材质（2026-09-24）

用户指定：宝箱木制材质换成**游戏内木头体素块的材质**，并做优化。

- **源确认（远程探针实测）**：建造调色板 `wood` 条目 → `/Game/Building/Voxels/Rounded/M_Voxel_Wood`
  （纯 Material），采样 Normandy 实拍扫描库三件套
  `T_WoodSurface_00A_{BaseColor(sRGB/TC_DEFAULT), RHAOM(TC_MASKS), Normal(TC_NORMALMAP)}`，
  Custom 节点只加微调色相/边缘磨损/湿度——与箱体无关，不搬运。
- **做法**：`replace_wood_with_voxel.py` 原地重建 `M_Crate_Wood` / `M_Crate_WoodDark`，
  **直接引用这三个库贴图对象**（不复制、不新造贴图）→ 木箱与体素木块同一份纹理数据，
  显存/包体零增量（优化点①）。通道语义按项目 RHAOM 口径：BaseColor×AO(B)×色调、
  粗糙=R、金属=0、法线=Normal 贴图；采样器类型逐张贴图与压缩设置对齐
  （COLOR/MASKS/NORMAL），读回断言通过（`WOOD_REBUILT` 日志＋verify 探针）。
- **优化点②**：箱体平面 UV 是米制 1:1，tiling 定 1.0＝每米一次扫描，木纹跨板连续、
  与体素块同尺度；拱盖双面保持。`Crate_WoodDark`（框/箍/内衬）同贴图×0.42 暖暗色调
  ＋粗糙 +0.12，保留箱体层次。石/铁/金/银不受影响。
- **回执**：`replace_wood_receipt.json`。`T_Crate_Wood_{Surface,Normal}` 自此无引用，
  暂留盘（编辑器运行中不删，遵循幽灵包教训；下次重启可随 v1 清理流程入库 `trash/`）。
- **未做**：游戏内视觉验收（按规则由用户实测）。

## 第五轮：开盖动画真复用——SK_* 五档骨骼变体（2026-09-24）

用户问打开动画是否同步复用，选定路线＝"骨骼版五档，供开箱 Actor 用"（体素面板维持静态版）。

**结构考古（`parse_glb_skin.py`，直解 GLB 二进制块）**：源 GLB **`skins:0`——根本没有蒙皮**；
开合是**节点动画**（`Open`＝LidHinge 节点四元数旋转＋Latch 节点平移；`Close` 反向），
UE 的 5 骨骨架正是 5 个节点（WarehouseChest/BodyAssembly/LidHinge/LidAssembly/LidLatch）。
另确认：**Blender 5.1 的 glTF 导入器对该文件不建臂骨、不写顶点组**（OBJ 探针实测
ARMDS=[]、vgroups=[]）——之前"派生丢动画"的判断不成立，静态管线从头就是无骨导入。
Blender 侧重建骨架路线因此废弃。

**复用做法（`make_skeletal_variants.py`，commandlet）**：源 `SkeletalMesh`
`/Game/ColdSteelUI/Warehouse20260909/RitualV8/warehouse_chest_rigid/SkeletalMeshes/warehouse_chest_rigid`
（11 槽，槽名＝derive 映射键，实测逐一吻合）→ **`duplicate_asset` 五份**
`/Game/Props/WarehouseCrateTiers20260924/Skeletal/SK_WarehouseCrate_T{1..5}_*`，
每份按 TIERS 换 11 个槽的 `material_interface` 为既有 `M_Crate_*`——**几何、骨架、LOD、
物理资产、Open(0.9s)/Close(0.7s) 片段全部原样共用，零新增动画数据、零网格再造**。
新包名＋只读源资产，编辑器在开也安全。

**踩坑（已修）**：`USkeletalMesh.materials` 是 struct 数组——**for 循环里的元素是值拷贝**，
改了不回写数组等于没改（首跑静默保存了源材质，独立进程读回才暴露）；改为逐索引
`slots[i]=slot`＋整组写回＋**同进程读回闸门**（断言每槽 == 目标材质才保存）。
`material_slot_name` 返回 `unreal.Name`，与 dict 的 str 键比对须先 `str()`。

**接法（无需任何代码改动）**：`AColdSteelWarehouseChest` 的 `ChestAsset` 直接填
`SK_WarehouseCrate_T*`，`OpenClip/CloseClip` 用现有两条片段即可——同骨架同名骨骼，
`SetOpen()` 照常播放（盖绕 LidHinge 骨旋转、锁扣随骨平移）。要新档箱子换外观，换
`ChestAsset` 就行。

**验证**：`verify_sk_final.py` 全新进程磁盘读回——5 份 `skeleton_shared:true`、
11×5 槽材质 0 错配、两条片段 `skel_match:true`，`ALL_OK:true`（`probes/sk_final.json`）。
**未做**：游戏内开盖实测（按规则由用户验收）。

## 第六轮：五档储物箱接入仓库式储存面板（2026-09-24，C++）

需求：五档箱子参照仓库宝箱的**同一套样式**做可交互储物——各档独立容量、E 键开面板、
开盖/关盖播放动画。通读既有交互链路后按最小侵入实现：

**架构（容器分域，全局语义零漂移）**：所有仓库操作都以纯函数作用于 Items 平铺数组，
故不新增第二套存储——给 `FColdSteelItem` 加 `Container` 字段（""=背包/装备/主仓库，
既有存档天然为空，逐字节兼容），储物箱内容沿用 `Place==4` 格坐标但以 `Container`
划出**各自独立的 18×12/页格空间**；容量记 `Profile.StoragePages`（键→页数，只增不减）。
`ColdSteelWarehouse::Fits/Insert/Transfer` 与 `Owner/PlaceDisplaced` 增加 Container 参数
（默认空＝原全局行为），`Validate` 按各容器自身页数复核越界与重叠，`MigrateLayout`
只重排主仓库行。

**会话**：`UColdSteelStatusModel` 新增 `BeginStorageSession(key,pages,caption)/EndStorageSession`
与 `OpenStorageCapacity()/InOpenStorage()`。面板一切实读/写路径统一走这两个入口：
`ProposeMove/ProposeWarehouse/TransferWarehouse/AddWarehouseItem/Split/SortWarehouse/
WarehouseBatch/RetrieveAll/…`（UI 无需知道"仓库"与"储物箱"是两回事，切会话即切格空间）。
**生产/制作/采集/material 计数一律限定 `Container.IsEmpty()`**（储物箱内物品不参与锻造、
采集台账、强化补给），避免玩家把材料藏箱子里绕过或误耗。

**表现层容器感知**：board/presentation 的绘制、占用查询、拖放预览、tooltip"存储位置"、
右键"存入/取出"文案全部由 `Model->ActiveContainer/ActiveStorageCaption` 驱动；面板大标题、
格区小标题、按钮文案随容器显示（主仓库显示"仓储空间"，箱子显示档位名）。

**Actor**：基类 `AColdSteelWarehouseChest` 加虚接口 `GetStorageKey/Pages/Caption/PromptLabel`
（默认空＝主仓库，旧宝箱行为不变），提示板文本改为可在 BeginPlay 覆写。新增
`AColdSteelCrateChest : AColdSteelWarehouseChest`——按 `Tier` 载入第五轮的
`SK_WarehouseCrate_T*` 与共享 Open/Close 片段，容量 `TierPages`（1..5 页），
复用同一套面板、交互、动画逻辑（E 键走基类，Cast<AColdSteelWarehouseChest> 天然命中子类）。
`SpawnBeside` 在宝箱右侧成排固定生成；PlayerController 仓库初始化定时器内，非审计时自动补一排
五档箱（已存在则跳过）。

**验证**：仅编译（`build_crate_storage.log`），**未做游戏内实测**（按规则由用户验收）。

## 第六轮修复：箱子变灰、拱顶"上表面缺失"（2026-09-24，用户截图反馈）

用户进游戏看到五档箱**通体灰白、拱形盖顶透明**。PIE 日志给出决定性证据：
`Material with missing usage flag was applied to skeletal mesh .../SK_WarehouseCrate_T*`。

**根因（一个原因解释两个症状）**：`M_Crate_*` 八张材质当初为**静态箱**制作，只勾了
静态网格用法标志，**缺 `bUsedWithSkeletalMesh`**。骨骼网格拒用无标志的材质 → 回退到
引擎默认材质：默认材质是**单面**的，而拱顶壳面（`Brass_Strap` 槽，法线朝内）从外侧看
被背面剔除 → "上表面缺失"；其余面变默认灰 → "通体灰白"。源宝箱不受影响是因为它的
`MI_Ritual_*` 本就带骨骼标志。第五轮把 M_Crate 设为双面是为静态箱拱壳修的，
但骨骼标志这一层当时没补上。

**修复**：经 MCP 桥在**运行中的编辑器内**给 8 张 `M_Crate_*` 置 `used_with_skeletal_mesh=True`
并 `save_loaded_asset` 落盘（`fix_usage_flags3.py`）。踩坑：`save_asset(path, only_if_is_dirty=False)`
与"值已是 true 就跳过 modify()"两版都没真正写盘（mtime 不变、`save_ret:false`）；
**无条件 `modify()` 再 `save_loaded_asset`** 才落盘（mtime 变、`save_ret:true`）。

**验证**：全新进程读回 `probes/usage_readback.json`——8/8 `skeletal:true`（`M_Crate_Gem`
`two_sided:false` 是其 authored 原状，宝石切面朝外、与拱壳无关，未动）。
**用户侧**：材质已在编辑器内存更新并重编着色器；**已开着的 PIE 里那批箱子需重开 PIE**
才会以新标志渲染（旧会话生成时已被拒用，不会自动回血）。仍未做游戏内实测。

**后续**：表面材质系统性提升已立项为计划稿 `material_upgrade_plan_20260924.md`
（现状盘点 + P1 母材质/实例收敛 + P2 三通道贴图升级 + P3 档位识别 + P4 验证交付），待批准后分阶段执行。

## 第八轮：统一 E 交互小浮窗，拆除模型上方名牌（2026-09-24，C++，全项目口径）

用户指令：任何交互统一为高炉/工作台式**准星下小浮窗**；不再显示模型上方名称与 E 提示；
浮窗背景毛玻璃灰黑、字体白色。要点：

- 唯一文案源 `ColdSteelWorldInteraction::ResolveInteractionHint()`（祭坛→宝箱→仓库箱/储物箱→
  拾取→高炉→工作台→门，分派顺序与 E 键一致；门为新增提示，此前无提示）。
- `UColdSteelHUDWidget::BuildInteractHint/UpdateInteractHint`：`UBackgroundBlur`＋`GlassTint`
  灰黑毛玻璃、白字、E 徽标（只读状态自动隐藏 E）、自动宽度，准星下 56px；
  出现条件沿用旧即时提示（面板开/光标/弹药轮/命中反馈时不显示）。
- 拆世界名牌：`UColdSteelChestPrompt` 类与宝箱 `Prompt` 组件删除（`GetPromptLabel()` 改作
  浮窗正文，如 `武器仓库 · 打开仓库面板`、`木质储物箱 · 打开储物面板`）；`AColdSteelPickup`
  的 `Prompt` 组件删除（`PromptCaption`＋`GetPromptText()`）；`ColdSteelCrosshair.cpp`
  旧即时绘制块移除。生产工具底部按键说明（视口浮窗、非模型上方）按原样保留。
- 高炉/工作台按 E 后打开的功能面板不变（本就已是毛玻璃+浅字）。
- 文档：`Docs/UI/unified-interaction-hint-20260924.md`。编译记录：`build_unified_hint.log`。

## 边界与未做

- **废案归档（2026-09-24 仓库整理）**：v1 顶面探针与 FBX 导出尝试（路线被运行日志证据
  否决）连同其空产出已移入 `trash/warehouse-crate-tiers-probes-20260924/`，
  SHA-256 清单见 `trash/warehouse-crate-tiers-probes-20260924.sha256.txt`；不要再重跑。
- 与仓库等级/升级的绑定、`warehouse_assets.json`、现行宝箱骨骼网格与开合动画均未触碰；
  五档互动箱走**复制源宝箱 SK + 复用骨架开合片段**路线（第六轮），静态 SM 构件仍留在
  体素建造面板目录，两者并存互不影响。
- 未提交 Git；未启动 PIE、未渲染预览、未做游戏内验收，交由用户测试。
- 若对"花纹"还想更强区分度：T4/T5 的雕花纹线现在靠 `M_Crate_Gold` 微表面凸起呈现，
  如需真正独立浮雕可把 `Ritual_Engraving` 槽挪壳再加高。
