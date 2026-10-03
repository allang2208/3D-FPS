# 唐刀 · UE5 近战武器接入

2026-10-02。用户指定原始模型 `C:/Users/allan/Downloads/Meshy_AI_Dragonforged_Saber_1002040045_texture.glb`。
物品 ID 为 `ue_tang_dao`，显示名称「唐刀」，采用现有双手近战合同。

## 获取、装备与战斗

唐刀加入 `ColdSteelStatusModel::GrantStartingArmory`，按已有 `ArmoryReceived` 标记向仓库幂等发放一把。
占 2×4 格，双手持握并占用副手；沿用已有快捷栏、强化、仓库转移、丢弃拾取与保存流程。
仓库容量不足时不消耗领取标记。未改写用户现有存档。

现有动作时钟、音效和业务保持原合同：右向左横斩、左向右横斩、突刺的三段循环，蓄力重击、
格挡、检视、装备、快速近战、冲刺攻击与旋风。共用基础公式：基础 40，每强化 +5，
智力 4.5／每强化 +0.9，力量 3.5／每强化 +0.6；基础近战距离为 180 cm。
唐刀没有继承符文长剑专属命中减冷却、飞剑或寒晶专属精神迸发。

## 模型与实际接口

原模型为 291,676 个三角面；不主动减面。源模型长轴 X 转到武器 +Z，旋转不镜像。
原始 GLB 保留在 `Original/`，原始可编辑副本为 `TangDao_Original_Editable.blend`。
原 GLB 的 2048 基色、ORM 和 OpenGL 法线保留；UE 的 ORM 使用 R=AO、G=粗糙度、B=金属度，
法线翻转绿通道。材质为静态部件用途，不添加骨骼用途。

护手侧与柄尾侧的真实源切口分别为 X≈0.382 与 X≈0.806，映射到当前双手握持区 Z=-5..-22.7 cm；
原装刀尖沿 Z=88 cm，保留原模型的侧向弧度。整刀长约 116.7 cm。
手臂与手指动画沿用现有资源，当前 `SK_FrostSword_Arms` 的原生默认是认可的 V7 裸手／裸臂。
驱动骨 `WPN_root` 的骨骼缩放由已有 `bone_mount` 抵消一次。
真实刀尖侧向坐标写入本刀目录，基础伤害范围仍由玩法数据决定。

四个原装模块为刀刃、护手、握柄、环形柄尾。新切口保留插值 UV、表面法线和实际安装截面，并封闭切面。
三款刀刃、三款护手、三款握柄沿用现有改造 ID 和属性；改造形变保留安装端。
长柄向后增加 2.8 cm，联动柄尾和现有长柄手臂动作家族。
六款共用柄尾通过两类实测截面转接件装配，主体与属性继续取 `shared-sword-pommels.json`。
专属于其他剑的改造未开放给唐刀。

本刀的原装与变体静态网格使用 Nanite，保留显式切线和完整误差回退；保留当前项目光照路线。
手持、改造台、库存预览与掉落均取同一 `tang-dao-modules.json` 配方。

## 图标

库存图为彩色 384×768 PNG，刀尖朝上，长轴占纵向约 91%，按现有库存图构图提供目录回退。
改造栏图标保持无彩色灰阶、厚倒角金属框、四角铆钉、银色内环与深灰底板。
13 张独立母图由内置 imagegen 按实际新部件素材与认可边框生成；分类入口复用原装母图。
通用符文与六款共用配重保留已有同形实物／语义图，并复制为唐刀专用键。
最终共部署 28 张改造图和 1 张库存图，保存同名 UE Texture2D，使用 UI 组、Editor Icon 压缩与 Never Stream。

生成工具记录和提示词在 `imagegen_prompts.json`，母图映射在 `generated_icons.json`，项目母图在 `FramedIcons/`。
实际部件出图源为 `TangDao_MenuIcons_Editable.blend`，独立灰阶仅应用于图标作者场景。

## 制作、导入与保存入口

当前表面版本为 [SurfaceV2](SurfaceV2/README.md)：独立精修 PBR、Substrate 材质、原装/改造件覆盖、
六款专用柄尾金属外观与正式彩色库存图。当前可编辑表面源为 `SurfaceV2/TangDao_SurfaceV2_Editable.blend`；
早期原始 Blend、贴图和导入回执保留为制作输入与历史记录。

- `read_source.py`：读取原始几何、提取 GLB 内嵌贴图和原始 Blend。
- `author_tang_dao.py`：姿态尺寸适配、模块切分、改造件、共享柄尾转接件与 FBX 导出。
- `render_production_icons.py`：正式库存素材与实际部件图标输入制作。
- `import_tang_dao.py`：实际导入并保存三张 PBR、两种基础材质、16 个静态网格与两种旋风材质。
- `install_catalog.py`：合并本刀物品、公式、五栏改造与独立模块目录，保留其他武器。
- `flip_holding_direction.py`：保存用户要求的局部 +Z 轴 180° 持握前后调转；`holding_orientation.json` 由目录安装器复用。
- `deploy_icons.py`、`import_icons.py`：部署正式 PNG 并实际保存 UE UI Texture2D。
- `build_and_import.ps1`：等待已有构建，后台完成必要 Editor 构建和无界面资产保存；不启动交互编辑器或游玩。

UE 新资产目录 `/Game/Weapons/TangDao20261002`；运行目录 `Content/ColdSteelData/tang-dao-modules.json`。
主可编辑源 `TangDao_Modular_Editable.blend`；游戏模型导出在 `Export/`，材质原贴图在 `Textures/`。
原装动作 `/Game/Weapons/AzureRunesword20260913`，长柄动作
`/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations`。

本轮状态：模型、配置和 PNG 已制作落盘；必要 Editor 构建成功。
三张 PBR、四种材质（含旋风变体）与 16 个静态网格已实际导入并保存，共 23 项；
29 张 UI Texture2D 已实际导入并保存。两次无界面 commandlet 均返回 0。
资产保存记录为 `import_receipt.json` 和 `icon_import_receipt.json`；构建记录为 `build-editor.log`。
本轮成功导入日志为 `import-commandlet-final.log` 和 `icons-commandlet.log`。
保留此前失败日志用于制作记录；其失败状态不代表最终保存状态。
本次没有游戏测试、验收截图、运行回归或用户视觉验收；交由用户测试。

2026-10-02 后续持握修正：按用户反馈将持握根绕刀身 +Z 长轴旋转 180°，调换刃口／刀背的前后朝向。
此修改保存于本刀运行目录的 `bone_mount`；所有原装、改造模块以及局部采样与符文随同一个根变换。
持握位置、比例、模型和动画保持当前资源；目录安装器复用修正作者参数，不会在再次接入时恢复旧朝向。
原方向备份位于 `Before/HoldingDirection20261002/`；本轮未启动 UE 或执行游戏测试，重新进入游玩后读取新配置。

## 来源与许可边界

2026-10-02 破锋燕翎刀身开发：独立制作源与后台导入入口见
[YanlingBlade20261002](YanlingBlade20261002/README.md)。新增 `blade_1/yanling_edge`
唐刀专属外观选项，保留现有龙纹刀根，制作燕翎折面刀尖、双导槽与独立 4K 钢刃 PBR。
新钢刃沿用已修复的刀身原生符文绘制；父级安装器及表面刷新保留已保存扩展。
实际资源保存状态见扩展目录的 `import_receipt.json`；没有游戏或视觉验收。

模型和内嵌纹理由用户提供的 Meshy 导出文件取得，本次仅在用户本机工程使用。
没有收到独立可再分发许可证明，不对外发布原模型、贴图或导出二进制。
手臂、既有动画、声音、符文材质与共享柄尾分别沿用工程现有来源／许可，Meshy 来源不覆盖这些资产。
imagegen 仅制作正式改造图标，未改写用户提供的模型或实战纹理。

## 2026-10-03 源码发布与退役归档

本次唐刀废案和历史备份归档到工程根 `trash/tang-dao-retired-20261003`，其中 `manifest.json` 保存旧路径、新路径、大小、SHA-256 和替代入口。历史回执或文字中的旧日志、Before、ReferenceV2 路径按此清单查找，不再作为当前制作入口。

保留原始 Meshy 输入、当前可编辑 Blend、有效导出、PBR、浮雕高度源和参考图在本机。燕翎配重使用 ConeV3，游龙刀身使用 PlanarRepair/SolidV4，虎首配重使用 ConnectorV4；游龙仍使用 JointRepair 资产目录里的符文材质，不能删除该材质依赖。虎首卡片框样式输入已迁到 `TigerPommel20261002/Icons/frame_style_reference.png`，当前提示词同步记录新路径与原路径。

公开 Git 仅包含源码、小型参数与恢复说明；不包含上述模型、贴图、参考图或 UE 二进制。完整依赖和恢复顺序见工程 `Docs/Weapons/tang-dao-publication-20261003.md`。未为本次发布启动游戏或进行视觉验收。
