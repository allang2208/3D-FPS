# 虎首侧面重塑 V6

用户反馈 V5 与原图仍有较大差距，主要在侧面。本轮以原参考图侧视为主重做头部纵向结构，不沿用 V5 把整个下部向前挪的形变。

当前已完成可编辑模型、FBX/GLB、三档 LOD、两组 PBR 及新版灰阶框图标。用户结束原有 PIE 后，已通过现有编辑器桥及批次互斥保存 V6 网格、六张贴图、四个普通/旋风材质及 Texture2D 图标，现有选项和活动源指针已切换到 V6。没有新开编辑器或运行游戏。本轮用户圈选图保存在 `Reference/LowerBeard_UserMarked.png`。

## 造型方案

1. 后脑与下方后鬃保留圆厚体积。按用户圈选的位置，把下颌鬃尖上收约 6 mm、根部横向拓宽最多 9%，颌后局部拱起降至 3.5 mm，使鬃尖沿宽阔根部汇入侧颊。
2. 使用逐高度的侧面深度站点塑造额头、鼻吻、上唇、口角、下颌和须尖。口角退到獠牙根部之后，使侧面能读出上下颌和口腔的间隙。
3. 红石、眼圈与眼睑沿眼窝的切向坐标系制作，从正面到侧面保持同一对眼睛，不增加假眼。
4. 侧颊雕刻六组、每组三缕的向后下方长鬃。主要凹凸由实体承担。后部仍保留云纹，正面中央沿用原浮雕，外侧脸颊逐渐切换到侧鬃的曲面投影，避免正面图案拉长到侧面。
5. 虎脸与侧壳共用实际轮廓顶点，用带前后切向的 Hermite 曲面重建连接带，移除覆盖脸部的球壳截断做法。下缘也属于同一连续曲面，不另挂一个鬃尖零件。
6. 连接带使用对应边界的面部颜色和 ORM，向侧鬃贴图平滑过渡，颜色在线性空间混合。侧面微法线逐渐引入。冠饰单独保留原侧壳材质，避免重排侧壳 UV 影响冠纹。
7. 保留冠饰、实际安装端、单一尾环及接座，保留 ID、数值和长握柄偏移。新网格与侧鬃材质单独保存，V4/V5 保留。

## 源与制作

- `surface_recipe.py`：新侧鬃高度域与三张 2K PBR；`TexturesRaw` 保留烘焙前的原始侧面图集。
- `profile_surface.py`：侧面深度站点、前脸及侧鬃混合高度场，供几何作者与 PBR 烘焙共用。
- `author_pommel.py`：可编辑 Blend、FBX、GLB、三档 LOD 与 manifest，并输出共享边界对应关系。侧面站点写入 manifest；它们是作者形状参数，不是原图的真实物理尺寸。
- `bake_transition.py`：由作者脚本调用，将正面边界与侧鬃原始图集烘入连接带的实际 UV。输出正面三张 4K、侧壳三张 2K 贴图及 `transition_bake.json` 制作记录。
- `render_menu_icon.py`：真实模型纯侧视灰阶图标素材，便于表达这次侧面变化；图标制作用途，不是验收渲染。
- `Icons/framed_icon_prompt.json`：内置 imagegen 金属框合成提示词；主体以本轮真实模型为准。
- `import_background.ps1` / `import_assets.py`：后台保存网格、侧鬃贴图与材质、旋风材质对应项、图标，再切换现有选项和活动源指针。

当前源模型以 `SM_TangDao_Pommel_tiger_mountain_SideProfileV6` 命名，六个原槽名保留，增加 `ChasedCrown` 槽复用原冠纹材质。`BronzeFace` 与 `ChasedBody` 使用独立 `ProfileV6` 材质，普通与旋风映射一起更新，目录重建继续读取 `active_revision.json`。

## 眼位修订（2026-10-03）

按用户截图，将偏在眼睛两侧的两颗红石移回虎脸原浮雕的瞳孔位置。原图 UV 定位为左眼 `(0.3485, 0.2990)`、右眼 `(0.6510, 0.2982)`，V 由上向下；红石、瞳孔、眼圈、眼睑和雕刻凹槽共用 `profile_surface.py` 中的定位。删除为侧视可见性添加的外移偏置，眼部朝向仍跟随脸颊曲面。纯侧视的遮挡保留真实模型关系。三档模型、两组贴图和菜单图标同步重制。

眼位修订前的可编辑模型和作者源已于 2026-10-04 移入本机 `trash/attachment-effects-20261004/SourceAssets/TangDaoMeshy20261002/TigerPommel20261002/SideProfileV6/BeforeEyeAlignment20261003`；原路径、大小与散列见 [归档清单](../../../../Docs/Publication/AttachmentEffects20261004/archive-manifest.json)。本轮图标提示为 `Icons/eye_alignment_icon_prompt.json`。对应版本标识为 `TangDaoTigerPommelSideProfileV6EyeAlign_20261003`，已由无界面 commandlet 保存并更新现有选项，未运行游戏或测试。

## 交付边界说明

沿用原用户参考与素材来源，原始图片和三维二进制保留本机。原图正侧视存在设计与透视差异，背面也未完整给出；侧面形体为优先约束，不声称逐像素或逐纹饰复刻。

制作与保存状态记录于 `delivery.json` 和 `import_receipt.json`。未启动交互 UE、游戏或 PIE，未执行自动检查、测试或验收，效果由用户测试。
