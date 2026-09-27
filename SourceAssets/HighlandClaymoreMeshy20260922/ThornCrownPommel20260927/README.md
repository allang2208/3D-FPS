# 棘冠配重球：模型制作与游戏接入

2026-09-27，用户要求继续已选棘冠方案并完成建模。以此前 [棘冠配重球概念](../SpikedPommelConcept20260927/README.md) 为外形依据，在 Blender 中精确制作。模型制作阶段完成外部模型、PBR、导出与图标，并后台保存六个 UE 独立资产；随后按用户指定的数值完成改造目录、快速近战逻辑与正式图标接入，详见下方「游戏接入」。

## 模型

- 银灰球体直径 5.2 cm，六枚向外的短棱刺与一枚尾刺；短刺净突出约 13.8 mm、尾刺约 20.8 mm。斜向短刺略向柄尾倾斜，靠握持的一侧保留平顺连接肩。
- 前后两颗切面蓝宝石、银色镶口；四道纵向编结纹饰和一圈柄尾编结带均为实际几何，暗槽、边线和交织起伏独立制作。
- 复制当前原装配重的上端 4 mm 安装带，保留原端面、UV 和面角法线；新连接颈从实测下截面连续过渡。原装配重主体没有缩放后冒充新设计。
- 作者轴：米制，+Z 朝剑尖，X 为剑宽，Y 为厚度；导出原点位于实际配重安装面。高地剑原装挂点为 `(0,0,-22.7)` cm，长柄继续使用宿主的柄尾偏移。
- 游戏导出含 29,254 顶点、58,251 三角形；安装带与新主体为两个材质槽。保留可编辑分件，最终刚体合并导出。

## 材质与文件

新主体使用独立 2048 PBR 图集：BaseColor、OpenGL 法线，以及 ORM（R=实际烘焙 AO、G=粗糙度、B=金属度）。银钢、深色凹槽和非金属宝石在图集中分区。宝石采用不透明切面材质；未模拟透射。安装带沿用高地剑原材质，未将新 UV 套入原装花纹图。

- [可编辑分件模型](Highland_ThornCrown_Editable.blend)：真实接口、主体、短刺、尾刺、蓝宝石、镶口与编结分件；含原装宿主参考。
- [PBR 烘焙源](Highland_ThornCrown_BakeSource.blend)：UV 展开和程序材质节点。
- [整剑装配源](Highland_ThornCrown_Assembly.blend)：新配重与当前收窄 V2 棱脊刃、原装护手和握柄的制作装配。
- [FBX](Export/SM_Highland_Pommel_ThornCrown_V1.fbx) / [GLB](Export/SM_Highland_Pommel_ThornCrown_V1.glb)：局部安装原点导出。
- `Textures/`：打包图与独立 AO/粗糙度/金属度源图。
- [菜单图标](Icons/ue_highland_claymore_pommel_highland_thorn_crown.png)：从实际模型制作的 1024×1024 透明单件图，按武器水平朝左的方向，安装端朝左、尾刺朝右。它是制作资产，未追加验收渲染。
- `Highland_ThornCrown_MenuIcon.blend`：图标源。
- `author_thorn_crown.py` / `authoring.json`：制作入口与参数/产物记录。
- `import_thorn_crown.py`：仅导入独立新网格、材质、贴图与图标，不改任何运行目录或已装配件。

## UE 保存与接入边界

已保存目录 `/Game/Weapons/HighlandClaymore20260922/ThornCrown20260927`，网格为 `Meshes/SM_Highland_Pommel_ThornCrown_V1`，材质为 `Materials/M_ThornCrown_PBR`，另外保存三张 PBR 纹理和一张菜单纹理。导入时继承原装配重的 Nanite / LOD 制作设置；法线绿通道由 UE 导入翻转一次。

首次在已有编辑器中调用时因 PIE 阻止保存而停止，没有写入资产。随后的结束游玩调用未取得可用节点；读取执行环境时编辑器已关闭，改用 `UnrealEditor-Cmd -run=pythonscript -NullRHI` 后台保存。该次 commandlet 返回 0，记录 `THORN_CROWN_MODEL_ASSETS_SAVED`；六项 `saved: true` 及 `complete: true` 见 `import_receipt.json`。导入日志 `import-commandlet.log` 中存在插件 Python API 重名与 commandlet 环境警告，导入返回 0 错误。没有打开交互编辑器或启动游戏，本次不需要 C++ 构建。

以上为前一轮模型制作记录。后续按用户要求接入游戏，详见下节。未启动游戏、执行测试或验收渲染。

## 游戏接入（2026-09-27）

- 配件 ID：`highland_thorn_crown`，仅 `ue_highland_claymore` 可装，位于 `pommel` 槽。`melee-gunsmith.json` 定义可选项与属性；`highland-claymore-modules.json` 直接引用已保存的新网格，使用原装挂点和 `highland_hilt_v1` 接口。长握柄继续沿用已有柄尾偏移。
- 用户明确所有新增效果仅快速近战生效：伤害倍率加值 `+0.5`、韧性伤害倍率 `×1.5`、击退距离 `×1.5`；每个有效命中的存活目标独立以 `25%` 概率施加 `1` 层流血。普通挥砍、第三段突刺、重击、旋风和冲刺不获得这些快速近战专属加成。
- 流血复用 `UCombatStatusFormula::AddBleeding`，没有另建状态。现有逻辑为每秒扣除 `max(1, floor(当前生命 × 0.01 × 层数))`，每 10 秒消退一层；重新施加刷新消退计时。沿用状态免疫、清除与图标逻辑。
- 配件、工作台总览、配件详情与物品提示使用同一份快速近战数值。沿用现有 `gunsmith_parts` 安装、预览和存档路径；不改用户存档，不自动给现有武器安装配件。
- 菜单使用 `Icons/ue_highland_claymore_pommel_highland_thorn_crown.png` 的正式副本：`Content/ColdSteelData/AttachmentIcons20260913/`；UE 纹理由 `integrate_menu_icon.py` 保存到同名 `/Game/ColdSteelData/AttachmentIcons20260913/` 路径，执行记录见 `menu_icon_receipt.json`。
- 同次修改陨星锤首 `ballast_hardened`：保留快速近战伤害倍率 `+0.25` 与击退 `+50%`，增加 `quick_combat_aoe`。接触帧使用原配重端起点、瞄准方向、技能距离与球扫半径，对范围内多个目标分别结算一次；场景仍阻挡，不增加爆炸半径。小手仍沿用原短距离低位扇区的未命中补判。
- 构建产物与交付状态见 `integration_delivery.md`。没有运行游戏或追加自测；游戏内表现由用户测试。

## 来源

造型来自本对话内置 imagegen 生成、用户已选定的概念图；新主体、尖刺、编结与镶口是本地参数化建模，未调用图生 3D 服务。安装带和宿主参考复用项目高地剑来源，沿用 [原始接入与许可记录](../Integration/README.md)，不将概念生成授权扩大为原 Meshy 素材公开再分发授权。本次没有发布二进制资产。
