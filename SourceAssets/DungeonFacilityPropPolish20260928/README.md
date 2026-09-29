# 地牢货箱与配电柜精修 · 2026-09-28

替换已有 `SM_Facility_CargoStack` 和 `SM_Facility_PowerCabinet` 的近景几何与材质，保留原正式资产路径、落地轴心、摆放关系和简单碰撞体积。本批没有新增房间。

- `Scripts/author_textures.py`：生成原创 4096×2048 共用 PBR 图集；木纹、漆面、拉丝、局部氧化、仪表刻度、设备铭牌、货运标签。
- `Scripts/author_props.py`：Blender 后台精密建模，导出两件 FBX、UCX 碰撞、清单及 `Authored/FacilityProps_Polished.blend`。无需下载模型或纹理。
- `Scripts/import_props.py`：通过现有 UE 互斥桥导入贴图、构建材质、重导入两个既有网格、构建 Nanite 并保存。保留活动 PIE 与未保存目标，不保存地图。
- `Scripts/publish_source.py`：仅更新原 FacilityScenes 作者目录内的两件 FBX 和对应清单项，备份旧输入。
- `Scripts/sync_combined_source.py`：仅替换原合集 Blender 内的两件组合件及其 UCX，保留其余作者对象。
- `Receipts/install.json`：实际 UE 保存记录，`stage=assets_saved` 才代表接入完成。

原 `DungeonFacilityScenes20260927/Scripts/author_assemblies.py` 已改为调用本批精修作者函数，避免后续重建恢复旧模型。独立作者文件及原合集文件均为可编辑源。先生成图集，再运行 Blender 作者脚本；安装顺序为本批材质/网格安装，再按需要运行既有其他设施安装器。完整房间安装器不属于本批任务。

配电柜 21,504 三角形、货箱 32,452 三角形；各为一个网格、一个材质槽，共用 BaseColor / Normal / ORM 三张图集。Nanite、显式切线、完整回退网格和原 UCX 碰撞保留。没有逐螺丝 Actor、Tick 或新增灯光。

Normal 源为 OpenGL，UE 导入翻转绿通道。ORM 为 R=AO、G=Roughness、B=Metallic，线性色彩。纹理与几何均由本批脚本原创制作，标签使用虚构设施信息。

实际接入已完成：`Receipts/install.json` 为 `assets_saved`，六个目标资源已保存，待处理项为空。用户关闭编辑器后通过无界面 commandlet 完成，日志 `Receipts/import-commandlet-02.log`，退出码 0；没有自动打开编辑器或保存地图。

本批未运行游戏、截图渲染或性能测试。实际观感与游玩由用户测试，面数与保存记录不代表视觉验收。
