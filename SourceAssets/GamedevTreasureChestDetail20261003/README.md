# 地牢探险宝箱 · 2026-10-03 细节版

制作方案见 [PLAN.md](PLAN.md)。延续现有黑铁／旧金色拱盖宝箱，不改白石仓库箱。

本版本补足实体镶板、框边倒角、曲面卷叶、分节铰链与贯穿销、锁牌真实开孔、提手轴座，以及七块内底板、四面暗木内衬、内口包边、角码和拱盖加强筋。顶盖徽章的圆环和装饰全部归属 Lid；Root／Lid 的参考姿态与原开启动画复用上游源。盖壳使用连续弧面 UV，细节坐标随网格／盖子运动。

金属 PBR 为本机原创 2K BaseColor／DirectX Normal／ORM 两套；微划痕、锤痕、氧化层、包浆与少量铜绿分别影响反照率、法线、粗糙度和金属度。部件边缘磨损由第二套 UV、真实部件尺寸和倒角标记控制，避免整面变成均匀亮斑。内衬直接引用工程内的 Normandy 木材贴图，不复制或改动第三方源纹理。

## 制作入口

- `Scripts/run_background.ps1 -Stage Author`：Blender 制作 FBX、分件可编辑源和原动作源；Python 制作 PBR。
- `Scripts/run_background.ps1 -Stage Install`：编辑器未运行时使用受现有批次互斥保护的 UE commandlet 导入和保存。编辑器已运行时通过工程 MCP 桥执行 `Scripts/install_detail.py`；试玩期间脚本停止写入。
- `Authored/TreasureChest_Detail_Components.blend`：保留命名分件、内外构造、骨骼、UV 和磨损数据。
- `Authored/TreasureChest_Detail.blend`：闭合正式导出源。
- `Authored/TreasureChest_Detail_Opening.blend`：新版网格与原版 1 秒开启动作的编辑源。
- `Authored/SK_GamedevTreasureChest.fbx`、`SM_TreasureChest_Closed/Open.fbx`：三种引擎网格导出。
- `Receipts/authoring.json`、`surfaces.json`：本轮制作数据；`install.json` 的 `stage=assets_saved` 才表示导入与正式包保存完成。

## 正式接入

新材质、纹理及本轮导入网格留在 `/Game/Props/GamedevTreasureChestDetail20261003`。
先新名导入，随后通过 GeometryScript 将本轮几何及三种材质写入原正式网格对象，保持所有关卡／蓝图硬引用：

`/Game/Props/GamedevTreasureChest20260922/SK_GamedevTreasureChest`

同时更新同目录的 `SM_TreasureChest_Closed` 和 `SM_TreasureChest_Open`。原骨架与三段动画资产不重导；碰撞尺寸、领取标签、掉落和持久化沿用已有实现。原网格包保存在 `BeforeRepair/`，不覆盖原模型制作源。

原路径写回使随机地牢、保留的线路测试地图、主神空间测试箱共用本轮外观，不需要重生成或另存地图。此更新限于共用探险宝箱，不修改其他医院／车站／焚化炉储物柜。

本次只制作、必要材质编译、导入及保存；没有启动编辑器或游戏，没有测试、截图或验收渲染，交由用户测试。

## 本轮保存结果

用户关闭编辑器后，`run_background.ps1 -Stage Install` 使用后台 commandlet 完成保存，退出码 0。`Receipts/install.json` 和 `Receipts/published.json` 已记录 `stage=assets_saved`：六张纹理、三种材质、本轮三种导入网格，以及原正式路径下的骨骼／闭合静态／开启静态网格均已保存。

本轮通过 GeometryScript 在原对象上写回几何，未删除正式网格、未重生成关卡，原骨架、三段动画和碰撞配置沿用。黑铁正式材质为 `M_TreasureDetail_Iron_R2`；首次未完成的材质图未被正式网格采用，确认无引用后已可恢复地归档到 trash。制作源约 19.3 万三角面，近景几何保留本轮细节；未主动进行减面或性能测试。

这份回执证明制作、接入与保存完成，不代表外观或开盖玩法验收通过。未打开交互编辑器、未运行游戏或测试。
