# 赛博朋克公寓 → UE5 接入报告

> 历史导入记录。当前场景与制作入口见 [2026-10-21 的 1.25 倍可体验版本](CyberpunkApartment-Playable20261021.md)。下文旧出生点、门位、碰撞与根因推断不代表当前配置。

生成时间：2026-10-20

## 资产位置

```
/Game/Props/CyberpunkApartment20261020/CyberpunkApartment/
    StaticMeshes/   80 个 SM
    Materials/      79 个 材质实例
    Textures/       96 张贴图
```

关卡：`/Game/GameMaps/L_CyberpunkApartment`

## 导入结果

| 项目 | 结果 |
| --- | --- |
| 导入资产 | 255 |
| 导入错误 | 0 |
| 关卡内 Mesh Actor | 80 |
| 关卡灯光 | 8 |
| 已设碰撞的 Actor | 25 |
| BodySetup 复杂碰撞 | 25 |
| 带贴图的材质 | 33 |

## 比例核对

全部 80 个 mesh 的联合包围盒（UE 单位 cm）：

```
min  [-149300.0, -80000.0, -15600.0]
max  [150700.0, 220000.0, 42000.0]
size [300000.0, 300000.0, 57600.0]
```

楼板 `S_plate` 实测 1660 × 1160 × 328 cm，与 Blender 中 16.6 × 11.6 × 3.28 m 一致，
glTF 导入已正确完成米→厘米换算（×100）。联合包围盒达 3 km 是因为城市远景 mesh 本身
跨越数公里，属于设计意图。

## 材质结构

所有材质都是 `M_GLTF`（glTF 母材质）的 **MaterialInstanceConstant**，贴图通过三个标准
参数挂接：

| 参数 | 指向 |
| --- | --- |
| `BaseColorTexture` | `*_alb` |
| `NormalTexture` | `*_nrm` |
| `MetallicRoughnessTexture` | `*_rgh` |

自发光材质另有 `EmissiveStrength`（例如车灯 30、尾灯 26）。


## 出生点

第一次进关卡时玩家落在城市地面（原点 0,0,0 在西外墙里，胶囊直接下坠 152 m）。
已加入 `PlayerStart_Apartment`：

| 项目 | 值 |
| --- | --- |
| 位置 | (700, 420, 6) cm |
| 朝向 | Yaw 270（面向电视墙 / 沙发区） |
| 所在房间 | 客厅（x 396–1128，y 12–540） |

选点过程不是拍脑袋：脚本枚举了 8 个候选位置，按胶囊半径 40 cm 与全部非建筑
网格的包围盒做重叠检测，前 5 个候选（y=180–300 一带）因落在阳台/家具体块上被
排除，最终取 (700,420) 一带的空地。落点 z 用 6 cm（`PlayerStart` 的原点是胶囊底，
不是中心，所以不能放在 100 cm）。

复核结果：位于客厅范围内、四向留边、头顶净高充足、该竖直柱体上无任何家具或墙体。


## 下坠问题修复（2026-10-20）

首次进入时玩家从公寓直接坠落到城市地面。原因链条：

1. **glTF 导入的网格没有可用碰撞**。导入器只给每个 mesh 生成 1 个凸包，
   而 `S_floors` 是零厚度平面（24 三角面全在 z=0.002），凸包退化成零体积，
   物理上挡不住任何东西。
2. `S_plate` 的凸包跨越 z=−34…328，玩家出生在凸包**内部**，会被直接挤出去。
3. 之前的 `body_setup` 修改在 commandlet 里**没有持久化**（读回仍是原值,
   box_elems 为 0），所以改了等于没改。

修复方式：不依赖导入网格的碰撞，改用引擎自带 `/Engine/BasicShapes/Cube`
铺一层碰撞地板：

| 项目 | 值 |
| --- | --- |
| Actor | `CollisionFloor` |
| mesh | `/Engine/BasicShapes/Cube` |
| 位置 | (800, −295, −30) |
| 缩放 | (16.6, 16.7, 0.6) |
| 世界范围 | x −30…1630，y −1130…540，**z −60…0** |
| 碰撞 | `BlockAll` + `QUERY_AND_PHYSICS`，可见 |

顶面精确落在 z=0（建模地面高度），因此玩家会站在公寓地板上而不是悬空或穿透。
立方体在建模楼板下方，正常视角看不到。

### 关于验证

在 `UnrealEditor-Cmd`（无头）里做射线检测一律返回 miss，因为无头模式不初始化
物理场景。因此**碰撞效果未经过运行期验证**，需要进编辑器 PIE 实际确认。
`CollisionFloor` 的属性（位置/缩放/碰撞配置/可见性）已逐项读回核对无误。


## 第二轮修复（2026-10-20 上午）

### 进不去室内
根因：`S_walls` 等 9 个网格的碰撞标记仍是 `SIMPLE_AND_COMPLEX`，每个 mesh 只有
**1 个凸包**。凸包会把门洞整块填实，所以门看着是通的、人却过不去。

已全部改为 `CTF_USE_COMPLEX_AS_SIMPLE`（按三角面碰撞），读回确认 9/9 生效：

```
S_walls S_floors S_plate S_ceiling S_finish S_trim S_facade S_balcony S_balcony_glass
```

门洞在包围盒层面本来就是通的（8 个门洞逐一验证，0 阻挡），现在三角面也通了。

### 门交互（复用现有系统）
项目已有成熟的 `AColdSteelSlidingDoor`（E 键交互、服务器权威、6 秒自动关、
滑动路径被挡时拒绝开门），直接复用，没有新写一套。已放置 6 樘：

| 门 | 位置 |
| --- | --- |
| Door_Master | (197, 546) |
| Door_Bed2 | (1134, 455) |
| Door_Bed3 | (1134, 803) |
| Door_Bath1 | (370, 814) |
| Door_Bath2 | (162, 814) |
| Door_Balcony | (930, 0) |

### 翻不过围栏
**这是引擎的正确行为，不是 bug。** 翻越规则要求 `bTopStandingSpace` 与
`bLandingStandingSpace`，而阳台栏板顶面外侧是 152 m 高空，没有落脚面。参数：
`VaultMaxHeight=120`、`MantleMaxHeight=200`，栏板高 106 cm，高度本来就够。

要让人能"翻出去"，等于允许跳楼。若确实需要，得给栏板外侧加一个**可站立平台**
（比如设备平台），否则不该放行。


## 第三轮：下坠根因（2026-10-20 上午）

### 真正的原因：Nanite
glTF 导入器给**所有网格默认开了 Nanite**。Nanite 用的是虚拟化几何，
`CTF_USE_COMPLEX_AS_SIMPLE` 在 Nanite 网格上拿不到可靠的三角面碰撞数据，
所以玩家没有落脚面，一路掉到城市地面。

这解释了之前的反复：碰撞标记写得再对，Nanite 开着就白搭。

修复：

1. **关闭 25 个建筑网格的 Nanite**（读回 25/25 生效）。这些网格本来就很轻
   （`S_floors` 只有 24 个三角面），Nanite 毫无收益，关掉反而让碰撞可用。
2. **清除退化凸包**：导入器给每个 mesh 塞了 1 个凸包。`S_floors` 是零厚度平面，
   凸包塌成零体积；`S_walls` 的凸包是实心板，把门洞全填死。已全部清空，
   读回 `convex: 0 / box: 0`，只剩三角面碰撞。
3. **出生点修正**：之前放在 `y=+420`，那是**阳台外**（UE 里阳台在 +Y，
   室内在 −Y，和 Blender 相反）。现在放在客厅中央空地 `(790, −180, 6)`。

### 当前碰撞配置

| 层 | 方式 |
| --- | --- |
| 站立面 | `CollisionFloor`（引擎 Cube，可靠盒碰撞，顶面 z=0，覆盖 x −30..1630 / y −1130..540） |
| 墙体 / 楼板 | Nanite 关闭 + 三角面碰撞，门洞通行 |
| 空 | `convex=0, box=0`，纯 complex |

## 关卡内容

- 80 个 StaticMeshActor，按原名命名（`S_walls`、`LIV_furniture`、`CITY_blocks` …）
- 7 盏 RectLight + 1 盏 DirectionalLight（冷色天光）
- 建筑 25 个网格已设 BlockAll + QueryAndPhysics，BodySetup 为 SimpleAndComplex

## 复现步骤

```
# 1. Blender 侧导出（glTF + 贴图）
python _setup/run.py build/export_gltf.py

# 2. UE 侧导入
UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript \
  -script=FPSGAME/Saved/_import_apartment.py -unattended -nop4 -nosplash

# 3. 建关卡 / 碰撞 / 材质校验
  _build_level.py  _collision.py  _bodysetup.py
```

## 未做 / 需注意

1. **灯光是 UE 侧重打的**，不是 Blender 的物理灯。Blender 里 52 盏灯没有随 glTF 过来
   （glTF 无 UE 灯光语义），关卡里是 7 盏 RectLight 近似还原，需要按口味再调。
2. **后期（Bloom/Streaks/调色）没有迁移**。UE 侧需要自己加 PostProcessVolume。
3. **碰撞是每个网格一个凸包/包围盒级**，不是逐面精确碰撞；房间里走动够用，
   但家具边缘可能偏胖。要精确碰撞得在 Blender 里生成 UCX 或改用 Complex 碰撞。
4. **未做 LOD / Nanite 设置**，685k 三角面在近景没问题，远景城市需要再优化。
5. 按项目规则，**未做运行测试与视觉验收**，交给用户自行进游戏确认。
