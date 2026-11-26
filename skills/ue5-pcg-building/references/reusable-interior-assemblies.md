# 可复用室内组合件

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 以组合件维护，而不是在关卡里逐个挪小物件

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 自然摆放要保留支撑关系

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 近景几何和表面分别解决

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 制作链与 UE 接入

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 本机案例与恢复边界

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 顶棚、灯具与管线标高（2026-09-22）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 保留空间整体的生成扩展（2026-09-22 返工）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 差异房间先完成建筑背景（2026-09-22 用户进一步明确）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 认可的剥落表面必须随扩展继承（2026-09-22）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 地牢通风家族共享配方（2026-09-26，已退役）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 设施近景道具精修（2026-09-28）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 随机医疗布景与墙面图集（2026-09-29）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

### 告示与标牌的字形比例（2026-10-02）

详见[维护源](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md)中的同名章节。

## 丘陵酒馆的残破与修复

- 房壳在子关卡以 `VillageTavern.Site` 标记，状态构件分别标记 `VillageTavern.Ruined` 和 `VillageTavern.Repaired`。修复前由权威端在壳体局部坐标合并两态实体构件范围，连屋顶、檐边一起查 Pawn 占用，避免屋顶站人时换掉脚下的屋面。世界修复位成功落盘后，`UHillsTavernSite::Refresh` 同步切换可见性、碰撞，并更新受影响的导航组件。
- `FHillsTavernInterior` 给每个模型独立声明 `bBlocks`。两态的阻挡网格随丘陵入口提前载入，桌凳、柜台和隔断与房壳同次安装。无碰撞器皿、餐具与灯具按当前状态异步补齐；弱回调绑定本次室内 Actor 与根组件。卸载或二次修复使旧宿主失效时，回调自行结束。
- 以装修后的地板采样值放桌脚，用桌面、柜面及搁板的局部高度摆放碗筷、木勺与食物。酒馆厅堂、过菜口和后厨各有承托面，残破状态有独立的破碗、冷灶、损坏隔断和台面。换桌时连同附属摆件使用同一变换；只有阻挡家具参与寻路。

## 村庄店铺的工作台近景

- 木工台的驱动水晶用不透明矿体表现厚度。`SourceAssets/WoodworkingCrystalBench/Surfaces/author.py` 的 `crystal()` 按局部法线区分切面亮暗，再沿局部视线在浅、深两处取样生长带与裂理，让晶体内部纹路随视角错动。保留 `DriveStrength` 驱动发光，用 `max(EyeAdaptation, 1)` 作发光值的除数，使暗处仍能看清切面。
- 草药架的透明瓶、琥珀瓶和清液共用单面薄层彩色透射材质。红、绿、蓝药液先以不透明材质写入深度，再用朝上法线提亮模型已有的弯月面，隔着玻璃也能辨出液位。配方见 `Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py`。在 `PotionWorkbenchVisualComponent.cpp` 中，仅对草药铺宿主异步加载这六种外观，按槽名同时覆盖原始台体和交互时使用的 `Body`。
- 用户要求前后对照时，每家店配一张能交代光源与工作台关系的全景，再配一张能看清目标表面的近景。各视图分别沿用原图的种子、修复状态、游戏时刻、相机位置、目标点和视场角。将每对原图和相机参数一起归档。早晨的全景和下午的近景各自与同时刻的原图配对。

## 村庄店内陈设与离场开销

实例化材质、店内陈设的视距和招牌摆动的休眠，见[店内陈设与离场开销](../../_shared/ue5-pcg-building/references/reusable-interior-assemblies.md#村庄店内陈设与离场开销)。
