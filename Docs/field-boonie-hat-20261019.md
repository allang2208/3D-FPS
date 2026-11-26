# 野行奔尼帽（土黄迷彩）

物品 ID：`ue_field_hat`，显示名「野行奔尼帽」，头部装备槽 `helmet`（界面显示「头部」）。按用户明确要求，放弃早先的油布田野帽方案，改为奔尼帽；外观与野行套装的橄榄针织长袖、灰色工装裤、棕色系带皮靴和厚棕皮手套配套。

设计说明见 [spec.md](../SourceAssets/FieldHat20261019/Design/spec.md)，首版设计提示词见 [prompt-v01.txt](../SourceAssets/FieldHat20261019/Design/prompt-v01.txt)。本版没有另做概念图；第一张正式外观图就是 320×320 库存图标 [ue_field_hat.png](../SourceAssets/FieldHat20261019/ue_field_hat.png)。

## 造型与配套

- 土黄迷彩油蜡帆布软冠、宽檐、棕色皮革帽带和帽绳，黄铜日字扣、keeper、四个气眼和滑扣；帽带承接手套/靴子的暖棕，帆布的土黄/橄榄迷彩承接上衣的橄榄色，不引入新的高饱和色。
- 帽冠参数高 9.6 cm，顶部中心实高约 **9.27 cm**（顶部浅凹约 0.35 cm）；帽檐宽 7.4 cm，外径约 33.9 × 35.6 cm；帽檐前缘约低于帽口 1.8 cm，后缘约低 1.35 cm，后缘相对前缘抬约 0.45 cm。
- 开口按 Jason 头部原始网格在头顶下 7.2 cm 采样，头部椭圆半轴约 8.99 × 9.86 cm；冠壁厚 0.32 cm，帽口外沿比头部大约 0.55 cm，内沿净余量约 0.23 cm。当前仅配置 `jason` 头型。
- 帽口有 2.5 cm 皮革汗带和皮革包边；帽带高 2.9 cm，上下各一道皮革圆边；后侧收一圈下颌绳，前右装扣。帽檐、帽带、汗带、包边和帽绳都有可见缝线。

## 模型与材质

- 源模型 **41,712** 三角形；帽冠/檐分段从首版加密到 `SEG=128`、冠 38 行、檐 20 行；顶部改为 3 圈同心环 + 中心扇面的软冠盖，使用平面投影 UV，避免旧单点扇面的径向拉伸；六个材质槽固定为 `Canvas / CanvasUnder / Leather / Brass / Lining / Thread`。可编辑文件 [FieldHat.blend](../SourceAssets/FieldHat20261019/Exports/FieldHat.blend)，交换文件 [FieldHat.fbx](../SourceAssets/FieldHat20261019/Exports/FieldHat.fbx)。
- 帆布 **4K BaseColor / Normal / ORM**，25 cm 平铺周期、256 根经纬纱；迷彩为浅土黄、橄榄、深棕和少量深褐四档不规则软边斑块，可平铺、低对比；整体以土黄/暖黄为主，深色斑块占比已按反馈降低。皮革 **2K** 三张，12 cm 周期；两者都有可平铺的织纹/粒面、折痕和蜡感/磨耗。帆布法线重新生成，强度从 7.5 降到 6.0，并减小高频微纤维振幅；顶部平面 UV 让织纹不再沿旧扇面拉成长条。檐底使用压暗的帆布变体，内衬是深棕近黑布料，缝线是浅土黄/亚麻色。
- 黄铜材质为暖色金属度 0.85、粗糙度 0.30；没有使用高光贴图或自定义节点。
- 骨架导入 UE 后保存为 `/Game/Characters/ModularOutfit20260924/FieldHat20261019/SK_FieldHat`，三级 LOD 目标 100% / 55% / 25%，锁边缘和骨骼边界；掉落和图标展示静态网格为 100% / 55% / 30%。

## 头部装备与物理

- 复用现有 `player_body.json/head_equipment` 和装备复制接口，挂到身体 `head` 骨骼；所有武器共用这一个头部挂点，不依赖各武器第一人称手模。第一人称仍走现有头部隐藏/身体投影策略，第三人称和其他玩家可见。
- `UFPSHeadEquipmentMeshComponent` 的局部角弹簧：三节后檐骨骼 `BrimBackBase / BrimBackMid / BrimBackEnd`，最大偏转 **10°**、频率 **2.5 Hz**、阻尼 **0.6**，与蓝法师帽同档；都在组件允许的 0–15°、1–5 Hz、0.4–1.0 范围内。超过本地相机约 22 m 回到静止；不逐帧联网同步弹簧速度。后檐现在有较明显的滞后回弹，不再只是几乎看不见的微动。
- 帽子是蒙皮刚体外观，**没有使用 Chaos 布料或碰撞刚体**。帽冠、帽带、汗带和前檐绑定帽根，只有后檐约 ±60° 的三节骨骼链参与摆动；帽冠、帽檐和帽带都是闭合实体，结构交界靠实体重叠和帽带遮盖，不用双面材质补洞。
- 本版不接入 NPC 那种帽子击落/刚体回收；玩家帽子没有碰撞、掉落链或服务器击落事件。

## 图标与展示

- 图标为 320×320 透明 PNG，3/4 前视，alpha 实体外接框约 290×166，软边外接框约 294×170，含软边的框内 alpha 覆盖约 0.9125；主体不接触边缘。
- 展示几何参数在 [ue_field_hat-display.json](../SourceAssets/FieldHat20261019/ue_field_hat-display.json)；UE 侧以 `ue_icon_yaw=-90` 反算成静态展示网格。目录图标和标准备用图标分别写到 `Content/ColdSteelData/Icons/FieldHat20261019/ue_field_hat.png` 与 `Content/ColdSteelData/Icons/ue_field_hat.png`。
- 另有一张离线贴合检查 [worn-preview.png](../SourceAssets/FieldHat20261019/Design/worn-preview.png)：由 `Tools/FieldHat/render_worn.py` 把帽子直接放在已采集的 Jason 头部网格上，用中性人台材质渲染；它只用于检查开口、帽檐高度和遮挡，不是最终游戏画面。

## 制作与接入结果

1. `capture_head.py`（已有工具）采集 Jason 头部；`make_textures.py` 生成六张 PBR 贴图（帆布 4K、皮革 2K）；`author_boonie.py` 生成模型、骨骼、材质源、UV、库存图标和展示 JSON。
2. `run_asset.ps1 -Script save_assets.py` 通过共享批次互斥导入 FBX，保存六个材质、六张纹理、三级 LOD、骨架、掉落/图标静态网格和图标纹理；使用 `save_icon.py` 保存图标展示网格和 UI 纹理。命令返回 0，日志为 [asset-boonie-05.log](../SourceAssets/FieldHat20261019/asset-boonie-05.log)，回执 [saved_assets.json](../SourceAssets/FieldHat20261019/saved_assets.json) 为 `completed=true`、`lod_count=3`、`source_triangles=41712`。
3. `publish.py` 只在资产保存成功后写入 `ue_field_hat` 物品和 `head_equipment` 配置，复制图标；没有修改 `modular_outfits.json` 或其他外观。回执 [published.json](../SourceAssets/FieldHat20261019/published.json)。

首次发布值：`price=28`、`grid=2×2`、`defense.base=6`、`ue_icon_pitch=0`、`ue_icon_yaw=-90`；头部配置使用 `jason` 的 `fits`，当时 `covers_scalp_hair=true`，后檐弹簧 `tip=10°/2.5 Hz/0.6`，与蓝法师帽同档。拟合值在回执中为 `location [12.0213, -0.2247, 0.1073]`、`rotation [-86.6846, 117.0672, -122.6236]`、`scale ≈ 1.0`；与 Blender 原始拟合一致，说明导入后的骨骼坐标没有产生额外偏移。2026-10-24 模型升级沿[工装套装](Characters/workwear-set-20261024.md)；男女角色整束毛发隐藏已关闭，现为 `covers_scalp_hair=false`，见[头饰与发型可见性](Characters/headwear-hair-workflow.md)。

UE 命令日志末尾有 9 条 warning、0 条 error；其中 “未找到Object” 是命令结束阶段对新保存包的清理提示，BlueMageHat 的同批日志也有同样模式，磁盘上的 uasset 全部存在。没有因此改写资产。

## 未完成与验收边界

- **未启动可见编辑器、PIE 或游戏**；未做穿戴贴合、帽檐弹簧手感、帽带/气眼在游戏光照下的颜色、第一/第三人称投影、摘戴发型恢复和联机显示的实机验证。按项目规则，这些由用户试玩确认。
- 物品和 `head_equipment` 配置已写入数据；正在运行的游戏/编辑器需要重新加载数据或重启后才会读到新的弹簧参数。和蓝法师帽一样没有额外掉落配方，通过目录物品、开发面板或管理员发放后装到头部槽即可测试。
- 帽檐软硬、后檐摆幅、帽带宽度和皮革明度是首版参数；如果游戏里显得太硬/太软或帽带偏暗，优先调 `tip_limit_degrees`、`tip_frequency_hz`、`tip_damping` 和材质色，不改骨架拓扑。
- 当前只支持 Jason 头型；新增头型需要补对应 `fits`，不能直接套用本版尺寸。
