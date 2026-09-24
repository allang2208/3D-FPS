# 宝箱支路门框收口与 Fab 金属材质（2026-09-23）

## 门框闪动原因与修改

随机路线通过 `AddTreasureRooms` 将普通房间侧口、2 米连接段、宝箱房入口按端口对齐。布局的 `JoinedWallSeam` 允许相连模块共享墙厚；这项空间规则本身不能排除渲染表面共面。

旧连接段宽 3.24 米，墙厚 0.24 米，内表面位于 X=±1.50 米，顶棚底面 Z=2.80 米，恰好与两端门框内表面一致。门框厚 0.29 米，向连接段伸入 14.5 厘米，因此两端均产生深度冲突。连接段没有再生成独立门框；冲突来自相邻构件表面。

采用房间负责门框收口、连接段负责通道结构的接口约定：

- `portal_recess_m=0.04`：连接段两侧墙和顶棚退后 4 厘米。
- `portal_collar_m=0.15`：两端各 15 厘米内不铺贴砖，保留后方结构，避免砖面伸入钢框。
- 地面仍是连续实体，端口位置、两米长度和 3 × 2.8 米通行口不变。
- 目录的包围盒/占地格随新外廓更新到 X=±180 厘米、最高 302 厘米；不会因外廓改变而放宽房间重叠规则。
- 更新共享连接段作者算法、宝箱支路生成配方、已导入网格、随机地图目录及后续目录重建入口。

用户要求的模型几何检查：旧连接段有 10 个跨入门框区域的共面三角形，修正后为 0。报告在 `SourceAssets/DungeonSeamMetal20260923/Receipts/seam-geometry.json`。此结果不是运行时画面验收。

## Fab 素材选择及实际来源

本次查询到 Fab 页面显示免费的候选：

- [Rusty Metal Sheet](https://www.fab.com/listings/54c7decd-5aac-491c-ad3f-cdfde8d4b1c8)：Quixel，2 × 2 米扫描，含底色、粗糙度、法线等完整贴图。
- [Scratched Painted Metal Sheet](https://www.fab.com/listings/73831f43-ac27-4705-b14c-3adb2fec4ba0)：Quixel，2 × 1 米扫描，含金属度、法线、底色等贴图。
- [Metal Material Pack PBR](https://www.fab.com/listings/ec4b0dc8-37f4-41b9-913b-8cc84b4664bf)：UE 材质包，页面显示免费。

上述新候选未下载。Fab 直接访问返回 HTTP 403，未尝试绕过网站限制。

实际接入复用项目已经取得并导入的 Fab 素材，无新增购买：

- [Industrial Infrastructure / Sierra Division](https://www.fab.com/listings/60cf60a7-3646-40ed-bdc9-0159eefb9db0)：`/Game/SD_Art/Industrial_Infrastructure/Materials/Rust/Textures/T_Tiling_Rust_*` 的 4K 底色、法线、ORM。Fab 搜索索引有免费促销记录，具体当前领取价以账户页面为准；本项目已有资产，无需再次领取。
- [Dirty Metal / Quixel](https://www.fab.com/listings/17d58a5d-f1a8-4417-9e6f-f21ed6fc7031)：已取得的污渍与粗糙度扫描，来源/授权记录见 `SourceAssets/ChestZiarat20260909/README.md` 与 Launcher 的 `Dirty_Metal-17d58a5d` 缓存。它不是完整钢材贴图。

原厂包和纹理保持原样，仅创建地牢专用主材质与 21 个实例。实例区分管道漆、切口裸钢、机械外壳、结构钢、格栅及机械门。按实例局部空间三向投射，统一厘米尺度，避免旧 UV 拉伸；锈层降至非金属反射，粗糙度和法线采用实际贴图，顶点色保留接缝老化和边缘磨损。警示字、灯光、自发光、橡胶、电缆护套与瓷砖不在金属替换范围。

## 接入与恢复

实际交付已落盘：5 组 TreasureLink 网格重新导入，21 组材质实例保存，175 个既有地牢网格的材质绑定更新并保存；`/Game/GameMaps/L_Dungeon_Randomized` 地图已保存。`Receipts/install.json` 状态为 `map_saved`，保留逐槽修改记录。原宝箱房作者清单中的 TreasureLink 记录也已更新，原记录单独备份，后续重新导入继续使用本次连接段。

执行记录：`Saved/Logs/DungeonSeamMetal20260923-materials-07.txt` 与 `Saved/Logs/DungeonSeamMetal20260923-install-01.txt`。本次没有修改 C++，没有启动游戏进行验收，`runtime_tested` 为 `false`。

- 新材质目录：`/Game/Dungeons/SeamMetal20260923/Materials`。
- 几何作者脚本：`SourceAssets/DungeonSeamMetal20260923/Scripts/author_seam.py`。
- 材质制作和绑定脚本：同目录 `create_materials.py`、`install.py`。
- 材质映射：`Config/material-remap.json`。
- 实际保存状态：`Receipts/materials.json`、`Receipts/install.json`。
- `Sources/Before_SM_RS_TreasureLink_*.uasset`、地图与目录备份及 `Receipts/install.json` 的逐槽 before/after 记录支持定点恢复；不回退其他任务的修改。

只执行本次要求的生成/几何排查以及必要材质编译、导入、保存。未主动运行 PIE、游玩回归、截图或场景渲染。

读取原始贴图期间，强制使用 TGA 导出 ORM 触发 UE `SupportsTexture` 断言，原编辑器退出；未保存地图或材质修改。后续取消该导出方法，直接引用已导入贴图。按此前授权结束已有 PIE 后完成接入，不启动新游戏。
