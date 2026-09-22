# 遗迹侧穴：复用 Fab 土石资产 / 2026-09-21

已按用户“按你计划调整”的授权完成遗迹土坡、坡脚砂砾与碎石的改造，并保存到 `/Game/GameMaps/L_Dungeon_Prototype`。本轮没有重新抽取 AI 土堆，没有运行游戏、碰撞/导航/性能测试或截图渲染。视觉效果与通行情况由用户实机查看。

## 本轮改变

- 从 RuralAustralia 的两个土质坡脊扫描件裁取局部，适配左侧主堆积区与右侧较小堆积区。控制前端收坡，使裁切边进入墙体或地面；保留原生扫描 UV。
- 以 MilitaryTrench 的砂砾面片制作 7 处坡脚及门槛过渡，根据现有石板、门槛和新土坡的实际几何高度贴合。
- 以该包的两种石屑扫描件布置 26 组局部碎石，主要集中在坡脚，保留中央通行留白。
- 以 UnrealNormandy 的破碎砌体堆制作 3 处坍塌残骸，连接较大块体和细碎砂砾。
- 增加顺着旧门槛破损边缘下降的土质缓坡；石板缝下补细土底层，减少原先深黑缝隙的视觉断开。
- 为本轮建立 6 个独立材质实例，使用原有扫描颜色、法线与粗糙度信息。土坡降低红色偏向，碎石收敛黄调，统一到灰褐色；坡脚使用第二 UV 和顶点遮罩混入同一细土颜色。
- 新网格按表面连续性重建平滑法线，保留较大的硬折边；没有修改源素材包。

当前是 40 个局部网格/Actor 的一轮装配，不是 40 个新生成母版。碰撞只启用于两处主体土坡和门槛缓坡，其余砂砾、细土与碎屑作为装饰。中央留白属于制作布置，尚未作通行验收。

## 被替换的旧摆放

以下旧 Actor 隐藏并关闭碰撞，原网格、材质和生成源均保留：

- `DGN_Room_RU_EarthBank`
- `DGN_Room_RU_ThresholdEarth`
- `DGN_Room_RU_BankFragments`
- `DGN_Room_RU_MasonryBank_A`
- `DGN_Room_RU_MasonryBank_B`

本轮只处理土石堆积与地面衔接。维修间、遗迹墙石/石拱/雕像、照明以及运行时随机生成器均沿用当前版本；[细节提升方案](dungeon-room-detail-improvement-plan-20260921.md) 中这些部分仍为后续工作。

## 复用来源

| 来源 | 本轮使用 | 适配方式 |
| --- | --- | --- |
| RuralAustralia | `SM_Ridge_Dirt_01_A_NoOverlay`、`SM_Ridge_Dirt_01_B_NoOverlay` | 局部裁切、房间尺度适配、端部收坡；复用 `T_Ridge_Dirt_01_CA/NA`，原父材质读取结果表明 CA 的 alpha 承担粗糙度 |
| [Military Trench Megascans Sample](https://www.fab.com/listings/f18c343f-b771-47b0-a02a-129771fd9804) | `SM_Ind_Con_Pile_Rubble_Gravel_Patch_01`、`SM_Mil_Trench_Debris_Pile_Rock_S`、`SM_Mil_Trench_Debris_Patch_Rock_S_01` | 贴合坡脚/地面，复用 BaseColor、Normal、ORM；保留原虚拟纹理属性并采用匹配采样器 |
| [Sharur's Normandy Village + PCG Plants](https://www.fab.com/listings/bf734560-f98b-4e4d-9a6c-e473b910a780) | `SM_H_RubblePile_00A`、GroundSoilExcavated 表面 | 布置破碎砌体，复用土层纹理；石块沿用原石墙材质的独立子实例 |

素材使用的是项目既有导入内容，沿用各源包的来源与许可；导出的 Fab 网格、贴图和可编辑衍生源保留本机。本次没有采购或下载，也没有将 Fab 模型/纹理输入生成式模型。

## 交付路径

- 新 UE 内容：`/Game/Dungeons/AtmosphereV2/RoomInteriors/Earthwork/`
- 场景 Actor 文件夹：`DungeonAtmosphereV2/RoomInteriors/Ruin/Earthwork`
- 源目录：`SourceAssets/DungeonRuinEarthwork20260921/`
- 局部编辑源：`Authored/DungeonRuinEarthwork.blend`
- 完整房间装配源：`Authored/DungeonRooms_WithFabEarthwork.blend`
- 几何/材质配方：`Authored/manifest.json`
- 原始导出、源材质参数与贴图路径：`Sources/source-manifest.json`、`Sources/surface-maps.json`
- 导入回执：`Receipts/asset-import.json`，阶段 `assets_saved`，40 个网格和 6 个材质实例。
- 地图回执：`Receipts/scene-install.json`，阶段 `map_saved`，输出 `RUIN_EARTHWORK_MAP_SAVED 40 actors`。
- 替换前状态：`Receipts/previous-actors.json`。

V2 的全量安装脚本已追加本轮导入/摆放阶段，以便日后主动重建时保留该版本；本轮没有运行整个 V2 重建入口。所有 UE 导出、导入与地图保存均通过项目批次互斥桥完成。

先前交付的四张截图显示的是本轮改造之前的版本，不能作为这一轮的实景效果证明。

## 18:28 整机死机后的恢复

恢复编辑现场时发现 40 个新摆放仍在，但 5 个旧土堆的隐藏/禁用碰撞状态未持久保存。已对旧 Actor 和组件显式调用 `modify()` 后重新设置并保存，同步修正安装脚本的保存标记；没有重新导入资产。编辑器停在遗迹入口，详见 [恢复记录](dungeon-earthwork-recovery-20260921.md)。本次未运行游戏或截图，整机死机原因尚不明确。
