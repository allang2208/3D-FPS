# 无面安保 V01

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

日期：2026-10-08。使用用户提供的男性 Meshy GLB，延续无面接待员的独立衣物、原生人形动作复用路线。

当前已更新为 [V08 腋窝与袖根修订](../V08/README.md)。本目录保留 V01 模型／服装及最初女僵尸同源动作的制作历史；当前正式蓝图使用 V08 组合网格和 V06 三段配套动作。

## 本次制作

- 深藏蓝长袖安保衬衫、长裤、肩章、胸袋及袋盖、领带与领带夹、姓名牌、背部 SECURITY 字样、腰带与两个小腰包、黑色系带执勤鞋。
- 肩部与衣袖采用一张连续衣物表面；裤装沿两腿分别变形，腰带与腰包由骨盆支撑。衣领、袖口、袋盖、裤脚和鞋口有实际厚度。
- 89 个衣物及细节对象在 Blender 源文件中独立保留。完整身体、单独衣物、穿衣组合分别导出；UE 穿衣版合为一个骨骼网格、7 个材质槽。
- 织物采用 20 cm 尺度的斜纹颜色、切线法线、ORM，UE Substrate 加入受限绒面反光；皮革和金属单独制作。服装微表面为程序化同源表面场，不称作扫描或高模烘焙。
- 新建蒙皮以男性肩、肘、腕、髋、膝、踝为适配点，保留成熟女僵尸骨架的名称、父链和原生绑定坐标，直接复用待机、行走、攻击的独立副本。没有改源女僵尸或女接待员资产。

## 身体与面数

原输入：`C:/Users/allan/Downloads/Meshy_AI_Faceless_Athletic_Man_1008070333_texture.glb`，包含材质、没有骨架。原始文件复制到 `Source/`，SHA-256 见 `Authoring/input_structure.json`。

完整身体保留 111909 个导入顶点、199401 三角面及原 UV／贴图，不对源身体减面。衣物为新建独立表面，作者体型采用约 1.90 m 的建模尺度，再适配成熟骨架绑定姿态；这个尺度不等于最终游戏站姿实测身高。

穿衣导出为 154988 三角面，其中衣物 130476 三角面，露出身体 24512 三角面。穿衣显示身体只保留头颈和双手，衣内躯干、手臂、腿脚不重复显示。完整身体另存在隐藏作者对象与独立导出中。

这些是制作导出的几何计数，不是帧率或视觉验收结果。当前没有制作独立 LOD，不强制改变用户源模型的精度。

## 文件

- `Authoring/FacelessSecurity_V01.blend`：可编辑身体、独立衣物、161 骨 UE 对应层级；待机／行走／攻击源动作保存在静音 NLA 轨中，默认绑定姿态。
- `Delivery/FacelessSecurity_V01.glb`：穿衣模型，包含皮肤、衣物、材质与骨架，不含动作时间轨。
- `Delivery/FacelessSecurity_Clothing_V01.glb`：独立衣物及骨架。
- `Delivery/FacelessSecurity_Body_V01.glb`：完整身体及骨架。
- `Delivery/SK_FacelessSecurity_V01.fbx`：UE 穿衣组合骨骼网格。
- `Delivery/SK_FacelessSecurity_Clothing_V01.fbx`：UE 独立衣物骨骼网格。
- `Delivery/SK_FacelessSecurity_Body_V01.fbx`：UE 完整身体骨骼网格。
- `Textures/`：3 张原身体贴图、6 组新衣料／皮革／金属 PBR 共 18 张贴图。
- `authoring_receipt.json`、`export_receipt.json`、`animation_sources.json`：制作与导出回执。
- `ue_delivery.json`：后台实际保存的 37 个 UE 资产清单。
- `build_receipt.json`：F6 入口所需 Editor／Game 构建结果；构建成功不代表游戏测试通过。

## UE 接入

- 蓝图：`/Game/Monsters/FacelessSecurity/BP_FacelessSecurity`。
- 穿衣模型：`/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_V01`。
- 独立衣物：`/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Clothing_V01`。
- 完整身体：`/Game/Monsters/FacelessSecurity/SK_FacelessSecurity_Body_V01`。
- 骨架／物理：同目录 `SKEL_FacelessSecurity`、`PA_FacelessSecurity`，从成熟人形来源独立复制。
- 动作：同目录 `Animations/A_Security_idle`、`A_Security_walk`、`A_Security_attack`。
- 材质／贴图：同目录 `Materials/M_FS1_*`、`Textures/T_FS1_*`。
- 生成入口：F6 → 无面安保，位于无面接待员之后。

复用女僵尸既有 AI、导航胶囊、战斗时序、物理资产来源和三段动作；本轮没有新增安保专属战斗能力，没有修改关卡或刷怪表。服装采用蒙皮变形，没有 Chaos 动态布料，没有新增运行时 Tick 或额外碰撞求解。

## 执行状态

制作、GLB／FBX 导出、材质编译、37 个 UE 资产导入与保存已完成，后台 commandlet 正常退出。F6 入口的 FPSGAMEEditor 与 FPSGAME 两个目标均已成功构建并落盘，回执见 `build_receipt.json`。

按用户规则，未打开 UE 图形编辑器，未运行游戏／PIE、渲染、动作检查或自动测试；造型、穿插和动作效果由用户体验。不能把女接待员 V04 的认可或历史检查结论当作本角色的验收结果。

## 重建入口与来源

`Tools/FacelessSecurity/prepare_inputs.py` → `build_recipe.py` → 生成的独立 `author_character.py` → `export_delivery.py` → `attach_source_actions.py` → `import_assets.py` → `build_entry.ps1`。

`build_recipe.py` 只读取女接待员 V02 已有骨架适配函数，再追加本目录 `garment_recipe.py`；生成的 `author_character.py` 已完整保存。动作作者源来自项目现有 Nurse FBX，UE 动作来自 `A_Nurse_*` 副本，不混入女接待员裙摆修正曲线。导入器已存在同名资产时默认续接使用；进一步修订应使用新版本名或明确的重导策略。

身体来源为用户提供的 Meshy 产物；新服装与贴图本地程序化制作；成熟动作与骨架来自本项目既有授权资源。本次没有调用付费生成 API，没有上传或公开分发源资源。
