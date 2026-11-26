# 公寓街角样板交付

**2026-11-10 后续接入：** 街角现已保存到用户实际使用的 `/Game/GameMaps/L_CyberpunkApartment`。本页保留上一轮独立样板的历史记录；当前入口与悬空原因见 `Docs/Publication/ApartmentStreetCorner20261110Formal/README.md`。旧样板发布器已停止重放。

2026-11-10，后台制作并保存独立样板。正式地图 `/Game/GameMaps/L_CyberpunkApartment` 未保存覆盖，默认地图、主菜单、打包地图列表未修改。

## 打开样板

在项目内容浏览器打开 `/Game/GameMaps/Design/L_ApartmentStreetCorner_Subject`。

地图文件：`D:/FPS3D/FPSGAME/Content/GameMaps/Design/L_ApartmentStreetCorner_Subject.umap`。样板的 PlayerStart 位于街角东侧人行道，世界厘米坐标 `(-4900, -7400, -10750)`。

## 本轮布局

范围约 204 × 202 米，位于公寓西南侧。8 米宽双向沿街道路与 6 米宽滨江支路形成街角，支路末端设置回车空间，并通过步道接入原滨江铺装。西北为底商住宅，西南为零售与小办公，东南为住宅沿街立面；公寓前场保持开放。两个路边停车位位于路口以东，街道家具放在设施带，路口设置四方向过街线和配套坡道。

布局制作图：`D:/FPS3D/FPSGAME/SourceAssets/ApartmentStreetCorner20261109/StreetCorner_Layout.svg`。

三栋新增建筑使用现有 City Sample PCG 模块按指定地块、风格和高度生成，再保存为静态实例。没有生成或扩建其余城市。新增建筑是外立面样板，室内未制作。

## 悬空与错位的制作处理

| 部分 | 处理 |
| --- | --- |
| 道路 | 路面统一世界 Z=-108.75 米，实体厚度 45 厘米，底部进入原地基；路口先合并平面轮廓，再生成顶面、底面和侧壁。 |
| 人行道、路缘石 | 顶面 Z=-108.60 米，比道路高 15 厘米；与道路共用基底标高。 |
| 坡道 | 从对应支承面的标高连续过渡；切除原高人行道，避免坡道与平面叠加。 |
| 长椅、护柱 | 新制网格使用明确的落脚零点；长椅不再包含旧模型附带的下沉铺装块。 |
| 灯杆、消防栓、邮筒、车辆 | 显式记录安装坐标、朝向和接触高度；车辆只放入两个指定停车位。 |
| 树木 | 与独立树池位置对应，树根进入土面，格栅与人行道齐平；树冠不参与物件平面占地推导。 |
| 旧散布 | 在样板副本中移除 26 个旧 native PCG 街区 Actor；复制两份旧近岸摆件蓝图，只从副本删除样板范围内 86 个旧实例。 |

## 已保存内容

- 61 个新静态网格，包括道路、人行道、路缘石、基础、坡道、标线、格栅、长椅和护柱。
- 3 个指定地块的建筑输出，共 1,211 个静态实例，保留生成时的世界变换和实例材质数据。
- 4 个样板蓝图：建筑组合、局部设施支承，以及两份裁剪后的近岸背景组合。
- 样板地图新增 117 个 Actor。14 盏局部路灯设有限距离、无动态阴影，不更改原有全局光照和天气。
- 公寓、江对岸远景、原近岸地基和滨江护栏沿用原场景。

制作源位于 `D:/FPS3D/FPSGAME/SourceAssets/ApartmentStreetCorner20261109`；新网格和蓝图位于 `/Game/Props/ApartmentStreetCorner20261109`，三个 PCG 屋顶位于 `/Game/ApartmentStreetCorner20261109/Authoring/Meshes`。

## 继续制作

布局参数在 `design.py`，实体几何作者脚本为 `author_geometry.py`，Blender 源文件为 `StreetCorner_Source.blend`。改布局后必须重新生成相关几何和建筑，不能只移动关卡里的道路。

生产次序：修改布局 → Blender 后台生成实体几何 → 需要时在独立 CityAuthoring host 生成三块建筑用地 → 迁入生成资产 → `import_geometry.py` 导入并保存 → `publish_sample.py` 从原地图重新生成样板。

UE 后台脚本通过 `run_background.ps1` 执行，并使用现有 UE 批次互斥；不要与正在运行的图形编辑器或其他构建同时写资产。`publish_sample.py` 会重新保存此样板地图，用户手调样板后应先另存再重制。

实际保存回执：`geometry_saved.json`、`sample_saved.json`。最终生产批次为 `import-02` 和 `publish-02`。这些记录代表导入、构建和落盘结果，不代表画面或运行验收。

按照用户规则，本轮没有开启图形编辑器，没有运行游戏、截图、渲染、自动检查或验收测试。实际接地观感、走行碰撞、路口尺度、夜间效果和性能交由用户在样板地图中体验。
