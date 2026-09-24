# 原 gamedev 传送门迁移 · 2026-09-22

用户授权：迁移模型，并接入现有 UE 场景传送入口。当前目标为 `D:/FPS3D/FPSGAME`。

## 来源

- 原可编辑模型：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev/tools/ai-gen/_settlement_building_pack_20260821/portal/portal_model.blend`。
- 正式视觉参考：原项目 `assets/terrain/portal_structure_occluder.png`；原游戏另有 `portal.png` 接地层。这里采用完整三维台座和拱门，不把 2D 分层图当成贴片模型。
- 原模型是正式图片细化前的几何源；保留原网格和比例，材质在 UE 重新制作，不声称搬运了图片细化中的全部像素细节。
- 原始文件只读；完整副本为 `Authored/GamedevPortal_Original.blend`。只在当前自有项目中复用，没有发布原素材。
- 白石纹理复用此前祭坛接入的同项目材质：`/Game/Props/SquareAltar20260922/Textures/T_SquareAltar_Marble`。传送门使用独立材质副本，不修改祭坛材质。

## 制作与资产

- `export_portal.py` 去除原 44.8° 展示朝向，统一门面为 UE 的 +X 朝向。Blender 工作源使用厘米坐标、0.01 米单位尺度，FBX 也明确使用厘米，避免重导入时米／厘米转换丢失；UV 仍按米制物理尺度展开。
- 维持原有双层台座、两侧方柱、圆拱、金边、顶端拱心石及门槛；已有倒角提高至至少 3 段，赋予按物理尺度展开的 UV0。
- 门框含台座约 4.4 × 3.6 × 3.87 m，4616 三角面；独立光幕约 1.70 × 0.07 × 2.88 m，168 三角面。导出统计属于制作信息，不是运行验收。
- UE 文件夹：`/Game/Props/GamedevPortal20260922`。
- 网格：`SM_GamedevPortal_Frame`、`SM_GamedevPortal_Energy`；可编辑工作源：`Authored/GamedevPortal_UE.blend`。
- 材质：`M_Portal_WhiteMarble`、`M_Portal_PolishedMolding`、`M_Portal_SatinGold`、`M_Portal_Energy`。光幕使用蓝绿色渐变、缓慢流动和轻微呼吸，双面无光照材质；不需要逐帧 C++ 更新。
- 固体门框使用 Nanite、三角面碰撞；光幕独立关闭碰撞与投影，保留通道开口。

## 游戏接入

`ASceneTestPortal::Configure` 复用已有 Frame0 / Frame1 组件承载门框与光幕，隐藏第三条占位横梁，不改变反射类布局。完整资产可用后才切换模型；缺失时保留原简易外观。

保留现有目的地配置、2 m 内按 E 传送、Esc 取消加载、丘陵异步加载与 TransitLoading 页面。未移植 gamedev 世界网络、科技、位面解锁和建设数据。

台座底部贴地，行列间隔调整为 520 cm，目的地标牌移至拱顶上方；默认关卡与其他目的地不改。源网格目录加入打包 Cook 列表，材质纹理由资产依赖携带。

## 接入方式与状态

通过项目桥依次执行 `import_portal_materials.py`、`import_portal_meshes.py`，每次使用新的输出回执路径。源目录与 UE 新资产目录独立，不保存或覆盖既有主场景地图。

实际保存结果见 `materials_receipt.json`、`mesh_receipt.json`；仅有导出文件不代表已经导入。原生构建结果另行记录。用户未要求测试、预览或渲染，本任务不运行 PIE、游戏测试、截图与渲染，交由用户测试。

本次四个材质和两个网格均已导入保存。最终网格回执为 `meshes-import-cm-3.txt`：门框 X 深度 360 cm、Y 宽度 440 cm、Z 高度 387 cm，Build Scale 为 (1,1,1)；光幕与门框共用地面原点。导入使用桥内临时切换的传统 FBX 工厂，结束后恢复原有 Interchange 开关，没有持久修改全局导入设置。

导入期间共享编辑器进入过运行模式，导致部分编辑 API 拒绝写入；最终保存已在编辑器模式完成。只请求过结束阻碍资产编辑的既有运行会话，本任务没有启动 PIE 或游戏测试。

### 本次原生构建

常规 `FPSGAMEEditor Win64 Development -WaitMutex -NoHotReloadFromIDE` 构建已成功，包含本次传送门接入代码，产出基础 `UnrealEditor-FPSGAME.dll`。首次构建遇到的外部怪物 UHT 阻塞已在工作区后续变化中消失；本任务没有修改该怪物类，也没有强制关闭共享编辑器。

这是必要编译结果，不代表运行或视觉验收。资产导入保存与游戏运行效果分开记录，仍由用户测试。
