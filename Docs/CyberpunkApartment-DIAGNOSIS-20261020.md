# 赛博朋克公寓关卡 · 从头排查报告（2026-10-20）

> 结论先行：三个主症状（出生下坠、空气墙、阳台翻不过）各有确定的几何根因，全部可以用源几何量出来。之前反复修不好，是因为**没有可核对的几何数据源**，11 个补丁脚本互相叠了 4 层碰撞地板、一块悬空隐形平台，并把幕墙碰撞整体关掉。

---

## 一、权威几何来源

```
工具：Tools/AssetPipeline/cyberpunk_apartment/00_gltf_geometry.py
输出：Saved/_gltf_geometry.json      （80 个网格的顶点 + 索引，UE 厘米）
审计：Tools/AssetPipeline/cyberpunk_apartment/18_structure_audit.py
```

### 坐标换算（按 UE 实际读回的包围盒校正）

```
Blender(Z向上) --导出--> glTF(Y向上) : gx=bx, gy=bz, gz=-by
glTF --导入 UE(Z向上,厘米)-->        : ue = (gx, gz, gy) * 100
                                    => ue_x = bx*100, ue_y = -by*100, ue_z = bz*100
```

旧文档说"UE 的 Y 与 Blender 相反"是对的，但 `10/12/16` 三个脚本按 `ue_y = +by*100` 摆东西，**门和出生点整体镜像到了楼的另一侧**。核对依据：

| 网格 | glTF | UE 实际读回 | 结论 |
| --- | --- | --- | --- |
| `S_balcony_glass` | y +279 | y **+279** | 阳台在 +Y |
| `S_glazing` | y −956…14 | y −956…14 | 幕墙在 y≈0 |
| `S_floors` | — | y **−1088…280** | 室内 −Y，阳台 +Y |

---

## 二、根因

### P0-1 出生后坠落到城市地面

**不是碰撞没生效，是出生点被 4 层重叠碰撞体同时包住。**

| 事实 | 数据 |
| --- | --- |
| `S_floors` | **24 个单面三角形**，厚度 3.2 cm（z −3.0 … +0.2），无体积 |
| 室内地面真实高度 | **z = +0.2** |
| `S_plate` 结构板顶面 | **z = 0.0**（−34 是板底） |
| 角色胶囊 | `InitCapsuleSize(42, 96)`，直径 **84 cm** |

历史上叠了四块 `BlockAll` 地板：

```
CollisionFloor      z −60  … 0      (10_collision_floor.py)
FloorTile_00..11    z −99  … 1      (_calibrated.py)
SlabFloor           z −400 … 0      (_thick_slab.py)
BlockFloor_Apartment volume          (_volumes.py，brush 未建成)
```

角色在 z=6 出生时同时穿插在多层盒体内 → `InitialPenetrating` 成立 → 引擎把角色挤出，`S_floors` 又是单面薄片接不住 → 一路掉到 `CITY_ground`（z ≈ −15200）。

### P0-2 空气墙：门是"画上去的"，门扇真的挡路

`S_doors` 里烘焙了 5 扇**按 58/22/−34/12/−46 度旋开的静态门扇**，跟着 actor 一起 `BlockAll`。实测覆盖：

| 门洞 | 洞口净宽 | 被 `S_doors` 封住 |
| --- | --- | --- |
| 入户 | 104 cm | **104 / 105 cm —— 100% 封死** |
| 主卧 | 90 cm | 门扇横跨 |
| 厨房 / 客厅 / 卫浴 / 次卧 | — | 门扇横跨 |

同时 `12_place_doors.py` 按镜像 Y 把 6 樘滑动门摆在 **楼外**（如 (197, **+546**)），门洞里反而空着。

### P0-3 阳台翻不过去：三层原因

| 层 | 事实 |
| --- | --- |
| ① **栏杆没有翻越标签** | `Traversal.GuardrailDrop` 全工程只有读取（`FPSTraversalComponent.cpp:87`）和地牢生成时写入（`AuthoredDungeonGenerator.cpp:1178`）。公寓栏杆从没打过标签 → `IsAuthoredGuardrail()` 恒 false → 直接 `Reject("NoWallInReach")` |
| ② 栏杆几何是 2 个三角形 | `S_balcony_glass` 只有 **2 tris**（x 406…1122, y=279, z 4…106），单面薄片过不了 9 点承托测试 |
| ③ 扶手/玻璃顶差 6.5 cm | 玻璃顶 106，扶手顶 112.5 |

旧方案加的 `BalconyLedge`（y 290…410, z=106 隐藏立方体）是错的：那是个**悬空 152 m 的隐形方块**，玩家翻过去站在空气上。

正确做法按项目 [场景开发标准](../../skills/ue5-pcg-building/references/scene-development-standard.md)：
> 需要双向跨栏、台阶高差和高处翻下的栏杆，在 Actor 或组件上设置 `Traversal.GuardrailDrop`；此标记不是所有家具、墙体的默认标签。符号本身不生成碰撞。

### P1 整体结构问题

| 问题 | 实测 |
| --- | --- |
| **卫浴门洞比角色窄** | 净宽 **80 cm** vs 胶囊 **84 cm** —— 两个卫生间**物理上进不去**，任何碰撞设置都无解 |
| 阳台比室内低 3.2 cm | 室内 z=+0.2，阳台 z=−3.0 |
| 阳台唯一通道被竖框截断 | 幕墙开口 x 705…805（100 cm），但 `S_facade` 的竖框在 **x 757.8…766.2**，把通道切成两半 |
| 幕墙碰撞被整体关掉 | `_open_glazing.py` 把 `S_glazing`/`S_balcony_glass` 设成 `NO_COLLISION`，**整面玻璃都能穿过去**（含卧室窗户） |
| 家具穿过门洞 | `LIV_furniture` 一件柜体（x 304…386, y −807…−779, z 0…90）正卡在卫浴门洞 |
| 灯光在楼外 | 7 盏 RectLight 摆在 y=110…950（阳台外/楼外），室内没光 |
| 城市几何全带碰撞 | `CITY_fog` 跨 115 km、`CITY_blocks` 24k tris 全部 `BlockAll` |

---

## 三、已做修复

| # | 动作 | 脚本 |
| --- | --- | --- |
| 1 | 删除全部历史补丁物（14 个 actor） | `20_rebuild_level.py` |
| 2 | 每个房间一块碰撞板，顶面 = 真实地面 z=+0.2；阳台 −3.0 | 同上 |
| 3 | 阳台门槛做成真实 3.2 cm 平台（非隐形方块） | 同上 |
| 4 | 栏杆加实体碰撞（8 cm 厚）+ `Traversal.GuardrailDrop` 标签 | 同上 |
| 5 | `S_doors` 烘焙门扇取消碰撞（保留外观） | 同上 |
| 6 | 9 樘 `AColdSteelSlidingDoor` 按修正坐标重摆 | 同上 |
| 7 | 出生点 (790,−180,**0.2**)，朝沙发区 | 同上 |
| 8 | 7 盏灯移进室内 | 同上 |
| 9 | 全部 `CITY_*` 取消碰撞 | 同上 |
| 10 | **卫浴门洞 80 → 96 cm**（改 Blender 源 + 重导出 + 重导入） | `D:\CyberpunkApartment\build\widen_bath_doors.py` |
| 11 | 装饰件（招牌/线缆/窗帘/涂鸦/电线）取消碰撞，家具保留 | `20_rebuild_level.py` |

### 当前关卡状态（`Saved/_rebuild_verify.json` 读回）

```
StaticMeshActor        94
RectLight               7
DirectionalLight        1
PlayerStart             1
ColdSteelSlidingDoor    9
PlayerStart_Apartment   (790, -180, 0.2) yaw 90
```

| 网格 | 碰撞标记 | 凸包 |
| --- | --- | --- |
| S_walls / S_floors / S_plate / S_facade / S_joinery | `CTF_USE_COMPLEX_AS_SIMPLE` | 1 |
| S_balcony / S_balcony_glass | 同上 + `Traversal.GuardrailDrop` | 1 |
| S_doors | `CTF_USE_DEFAULT`（不参与碰撞） | 0 |
| CITY_blocks | `CTF_USE_DEFAULT`（无碰撞） | 0 |

### 门洞净宽（改后）

| 门洞 | 净宽 | 84 cm 胶囊 |
| --- | --- | --- |
| 入户 | 102 cm | 通过 |
| 厨房 | 258 cm | 通过 |
| 客厅 | 298 cm | 通过 |
| 主卧 | 88 cm | 通过 |
| 次卧 / 小卧 | 88 cm | 通过 |
| **卫浴 ×2** | **96 cm**（原 80） | 通过 |
| 阳台 | 100 cm | 通过 |

---

## 四、未验证边界（按项目规则）

- 本次**不做运行期验收**。碰撞效果需进 PIE 实测：`UnrealEditor-Cmd` 无头模式不初始化物理场景，射线一律 miss。
- 进入：
  ```
  open /Game/GameMaps/L_CyberpunkApartment
  ```
- 返回：
  ```
  open /Game/GameMaps/DayNight_Lighting
  ```
- 建议人工确认：出生站立不下坠、穿过每个门洞、走到阳台、翻越栏板掉下去、卧室窗户不可穿。
- **已知遗留**：阳台唯一通道 x 705…805 中间仍有 `S_facade` 竖框（x 757.8…766.2），两侧各剩约 49 cm。要么在 Blender 源里删掉该竖框，要么接受"从两侧挤过去"。本次未动，因为删竖框会改变立面观感，需要你确认。

---

## 五、备份

```
D:\FPS3D\FPSGAME_Backups\CyberpunkRebuild-20261020-2315\
    GameMaps\L_CyberpunkApartment.umap        （重建前）
    MeshHashes\staticmeshes-before.sha256     （重导入前 80 个网格哈希）
```
