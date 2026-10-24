# 赛博朋克公寓 · 位置记录与待办

> 历史定位记录：下文各处“当前”指当时的修订，不再作为最新恢复入口。当前 V19–V21 场景、阳台栏杆、联机修补及后续独立动作精修的边界，以 [2026-10-24 发布说明](Publication/CyberpunkApartment20261024/README.md) 为准；不要用这里的早期整库脚本覆盖现有公寓。

> 最新外观为 [V4 柜体与 PBR 升级](CyberpunkApartment-RefinementV4-20261022.md)：保留 V3 空间与交互，重做柜门嵌入结构，23 类表面接入法线与粗糙度；275 组件逐项清单在 V4 源目录。实际落盘以 `RefinementV4/installed.json` 为准。

> 当前公寓为 [V3 空间与细节修订](CyberpunkApartment-RefinementV3-20261022.md)：整体再放大 20%、约 47 m² 健身房、卫生间墙柜／悬空洗手台、靠墙床位、电脑细节与主城 HDR 夜空；45 个储物格带单人可重复开合。权威回执：`SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV3/installed.json`。下方 V2 和原始尺寸为历史记录。

> 窗外继续采用 [分层海湾夜景](CyberpunkApartment-LayeredBay20261022.md)：近岸与对岸实体、复用 Clearwater 水面、4K 每面远景烘焙。实际地图安装状态以 `SourceAssets/CyberpunkBayLayered20261022/installed.json` 为准，旧背景源保留供恢复。

> 当前制作源为 2026-10-22 截图反馈 V2，见 [V2 修订说明](CyberpunkApartment-RefinementV2-20261022.md) 和 `SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV2/installed.json`。当前房间用途为两卧、办公室、单卫和健身室；下文是历史记录。资产落盘不代表游戏或视觉验收。

> 更新时间：2026-10-20

## 一、源文件位置

### Blender 工程（权威源）

| 项目 | 路径 |
| --- | --- |
| 主文件 | `D:\CyberpunkApartment\CyberpunkApartment.blend` |
| 大小 | 64.5 MB（贴图已内嵌） |
| 场景规模 | 685,110 三角面 / 80 网格 / 79 材质 / 52 灯光 / 21 相机 |

### 构建脚本（程序化生成，可完整重建）

```
D:\CyberpunkApartment\build\
    cy_lib.py          MB 网格累加器、UV 盒式投影、材质登记、集合工具
    furn.py            家具与道具库（超椭球、回转体、叶片扫掠）
    furn2.py           植物与微物件库
    gen_textures.py    程序化 PBR 贴图生成器
    s0_materials.py    材质注册 + 法线强度 + 贴图材质变体
    s1_arch.py         建筑外壳（楼板/墙/幕墙/天花/门洞/地面）
    s2_living.py       客厅
    s3_kitchen.py      厨房
    s4_bedrooms.py     三间卧室
    s5_bath_foyer.py   卫生间 / 玄关 / 走廊
    s6_details.py      天花服务 / 外墙 / 阳台
    s7_city.py         城市（166 栋楼）
    s8_lights.py       世界 + 52 盏灯
    s9_cameras.py      21 台相机
    s10_post.py        合成器 + Cycles 设置
    s11_micro.py       12 组微物件
    s12_joinery.py     踢脚线 / 门窗五金 / 收口
    s13_finish.py      瓷砖墙裙 / 地面分格 / 灯带
    s14_practicals.py  实用灯具 + 卧室落地灯
    save_blend.py      打包贴图 + 保存
    export_gltf.py     glTF 导出
```

### 重建顺序

```powershell
# 1. 启动无头 Blender
Start-Process "E:\Program Files\Blender Foundation\Blender 5.1\blender.exe" `
  -ArgumentList '--background','--factory-startup','--python','D:\CyberpunkApartment\_setup\serve.py'

# 2. 载入带贴图的 .blend（贴图材质由 MCP 侧创建，必须先载入）
python _setup\run.py _setup\load_blend.py

# 3. 依次重建
python _setup\run.py build\s0_materials.py
python _setup\run.py build\s1_arch.py
python _setup\run.py build\s2_living.py
python _setup\run.py build\s3_kitchen.py
python _setup\run.py build\s4_bedrooms.py
python _setup\run.py build\s5_bath_foyer.py
python _setup\run.py build\s6_details.py
python _setup\run.py build\s7_city.py
python _setup\run.py build\s8_lights.py
python _setup\run.py build\s9_cameras.py
python _setup\run.py build\s10_post.py
python _setup\run.py build\s11_micro.py
python _setup\run.py build\s12_joinery.py
python _setup\run.py build\s13_finish.py
python _setup\run.py build\s14_practicals.py
python _setup\run.py _setup\clean3.py
```

### 程序化贴图

```
D:\CyberpunkApartment\textures\     94 张 PNG（29 套 PBR：alb / nrm / rgh）
D:\CyberpunkApartment\build\gen_textures.py   生成器（numpy，可重跑）
```

### glTF 导出物（UE 导入源）

```
D:\CyberpunkApartment\export\
    CyberpunkApartment.gltf    0.6 MB
    CyberpunkApartment.bin    45.9 MB
    *.png                     88 张贴图
```

### 成品渲染

```
D:\CyberpunkApartment\renders\final\     16 张，1920×1080 / 300 spp
D:\CyberpunkApartment\renders\contact_sheet.png   总览图
```

### UE 侧资产

```
D:\FPS3D\FPSGAME\Content\Props\CyberpunkApartment20261020\CyberpunkApartment\
    StaticMeshes\   80 个 SM
    Materials\      79 个材质实例（M_GLTF 派生）
    Textures\       96 张

关卡：D:\FPS3D\FPSGAME\Content\GameMaps\L_CyberpunkApartment.umap
```

### 接入脚本

```
D:\FPS3D\FPSGAME\Tools\AssetPipeline\cyberpunk_apartment\
    00_gltf_geometry.py          ★ 从 glTF 提取权威几何（UE 厘米）
    01_import_gltf.py            glTF 导入
    02_build_level.py            建关卡 + 摆 mesh + 灯光
    03_collision.py              actor 碰撞
    04_bodysetup.py              BodySetup 标记
    05_verify_materials.py       材质校验
    05b_material_params.py       材质参数读取
    06_verify_scale.py           比例核对
    07_player_start.py           出生点
    08_spawn_height.py           出生高度
    09_audit_spawn.py            出生点复核
    10_collision_floor.py        碰撞地板（已废弃，见 20）
    11_wall_complex_collision.py 墙体三角面碰撞
    12_place_doors.py            推拉门（坐标错误，见 20）
    13_balcony_door.py           阳台门
    14_disable_nanite.py         关闭 Nanite
    15_remove_hulls.py           清除退化凸包
    16_spawn_living_room.py      客厅出生点（已废弃）
    17_diagnose.py               诊断
    18_structure_audit.py        ★ 离线结构审计（门洞净宽/地面/栏杆）
    20_rebuild_level.py          ★ 关卡重建（清补丁 + 碰撞 + 门 + 出生点 + 灯光）
    21_verify_rebuild.py         ★ 读回校验
```

Blender 源改动：

```
D:\CyberpunkApartment\build\widen_bath_doors.py   卫浴门洞 80→96cm 并重导出
D:\CyberpunkApartment\build\s1_arch.py            门洞 openings / frame / door_leaf
D:\CyberpunkApartment\build\s12_joinery.py        踢脚缺口 / 门槛 / 五金
D:\CyberpunkApartment\build\s13_finish.py         瓷砖墙裙缺口
```

---

## 二、空间坐标（权威，来自源码）

### Blender 坐标（米，Z 向上）

| 房间 | X | Y |
| --- | --- | --- |
| 客厅 | 3.96 – 11.28 | 0.12 – 5.40 |
| 主卧 | 0.12 – 3.84 | 0.12 – 5.40 |
| 次卧 | 11.40 – 15.88 | 0.12 – 5.40 |
| 小卧 | 11.40 – 15.88 | 5.52 – 10.88 |
| 厨房 | 4.80 – 8.64 | 6.84 – 10.88 |
| 玄关 | 8.76 – 11.28 | 6.84 – 10.88 |
| 走廊 | 0.12 – 11.28 | 5.52 – 6.72 |
| 主卫 | 2.84 – 4.68 | 8.20 – 10.88 |
| 次卫 | 0.12 – 2.72 | 8.20 – 10.88 |
| 家政 | 0.12 – 4.68 | 6.72 – 8.08 |

- 层高 2.95 m，楼板 16.0 × 11.0 m
- 立面朝 −Y，阳台在 −Y 侧（y −2.80 … −0.02）
- 城市地面在 z = −152 m

### UE 坐标（厘米）

**注意：UE 里 Y 轴与 Blender 相反。**

`UE_x = Blender_x × 100`，`UE_y = −Blender_y × 100`

| 物件 | UE X | UE Y |
| --- | --- | --- |
| 客厅 | 396 – 1128 | −540 … −12 |
| 阳台 | 390 – 1138 | −1 … 285 |
| 阳台栏板 | 406 – 1122 (y=279) | 高 z 4 – 106 |
| 玻璃幕墙 | 66 – 1596 | −956 … 14 |
| 楼板 | 12 – 1588 | −1088 … 280 |

### 全部房间换算表（源码核对通过）

`UE_x = Blender_x × 100`，`UE_y = −Blender_y × 100`

| 房间 | Blender (m) x / y | UE (cm) x / y |
| --- | --- | --- |
| 客厅 | 3.96–11.28 / 0.12–5.40 | 396–1128 / **−540 … −12** |
| 主卧 | 0.12–3.84 / 0.12–5.40 | 12–384 / −540 … −12 |
| 次卧 | 11.40–15.88 / 0.12–5.40 | 1140–1588 / −540 … −12 |
| 小卧 | 11.40–15.88 / 5.52–10.88 | 1140–1588 / −1088 … −552 |
| 走廊 | 0.12–11.28 / 5.52–6.72 | 12–1128 / −672 … −552 |
| 家政 | 0.12–2.72 / 6.72–8.08 | 12–272 / −808 … −672 |
| 次卫 | 0.12–2.72 / 8.20–10.88 | 12–272 / −1088 … −820 |
| 主卫 | 2.84–4.68 / 8.20–10.88 | 284–468 / −1088 … −820 |
| 家政(砖) | 2.84–4.68 / 6.84–8.08 | 284–468 / −808 … −684 |
| 厨房 | 4.80–8.64 / 6.84–10.88 | 480–864 / −1088 … −684 |
| 玄关 | 8.76–11.28 / 6.84–10.88 | 876–1128 / −1088 … −684 |

### 客厅家具（UE 坐标）

| 家具 | X | Y |
| --- | --- | --- |
| 沙发 | 892 – 1212 | −356 … −254 |
| 茶几 | 738 – 912 | −354 … −256 |
| 单椅 A | 558 – 652 | −202 … −108 |
| 单椅 B | 558 – 652 | −492 … −398 |
| 电视柜 | 411 – 457 | −440 … −150 |
| 地毯（中心） | 545 – 1105 | −479 … −131 |

---

## 三、当前 UE 关卡状态（2026-10-20 23:13 重建后）

| 项目 | 状态 |
| --- | --- |
| Mesh Actor | 94（80 个导入网格 + 12 块地板 + 栏杆碰撞 + 门槛） |
| 灯光 | 7 盏 RectLight（已移进室内）+ 1 盏 DirectionalLight |
| 推拉门 | 9 樘 `ColdSteelSlidingDoor`（坐标已修正） |
| 碰撞地板 | 12 块 `Floor_*`（引擎 Cube，顶面 z=+0.2；阳台 −3.0） |
| 阳台门槛 | `Threshold_Balcony`，真实 3.2 cm 平台 |
| 阳台栏杆 | `Rail_BalconyCollision` + `S_balcony` + `S_balcony_glass`，均带 `Traversal.GuardrailDrop` |
| 出生点 | `PlayerStart_Apartment` = (790, −180, **0.2**)，yaw 90 |
| `S_doors` | 烘焙门扇取消碰撞（保留外观） |
| `CITY_*` | 全部取消碰撞 |
| 卫浴门洞 | 80 cm → **96 cm**（改 Blender 源后重导出/重导入） |

> 完整排查过程与根因见 [从头排查报告](CyberpunkApartment-DIAGNOSIS-20261020.md)。
> 本表为数据读回结果，**未经 PIE 运行验收**。

---

## 四、待办

### P0 · 阻断性问题

- [x] **出生后掉落到楼底** — 根因：4 层重叠碰撞板把刚出生的角色包住（`InitialPenetrating`），
  `S_floors` 又是 24 个单面三角形接不住。已重建为每房间一块碰撞板，顶面 z=+0.2，出生点 z=0.2。
  **待 PIE 实测确认**
- [ ] **阳台唯一通道被竖框截断**（新发现）
  - 幕墙开口 x 705…805（100 cm），但 `S_facade` 竖框在 x 757.8…766.2，两侧各剩约 49 cm
  - 需决定：删掉该竖框（改立面观感），或接受从两侧挤过去
  - 源位置：`D:\CyberpunkApartment\build\s1_arch.py` 的 `mull = [...]` 列表

### P1 · 可访问性

- [x] **无法进入室内 / 门洞空气墙** — 根因：`S_doors` 烘焙了 5 扇旋开的静态门扇，
  实测封死入户门洞 104/105 cm。已取消该网格碰撞，门洞交给 `ColdSteelSlidingDoor`
- [x] **卫浴门洞过窄** — 净宽 80 cm < 胶囊 84 cm。已改源加宽到 96 cm 并重导出/重导入
- [x] **无法翻越阳台栏杆** — 根因：栏杆从未打 `Traversal.GuardrailDrop` 标签，
  `IsAuthoredGuardrail()` 恒 false 直接 reject。已加标签 + 实体碰撞
- [x] **门摆在楼外** — 根因：`12_place_doors.py` 按镜像 Y 摆位。已按修正坐标重摆 9 樘
- [ ] **出生点朝向**需按实际进入后的视野再调

### P2 · 视觉质量

- [ ] **贴图穿模**：需明确属于哪一类：
  - A. 贴图拉伸/错位（需调 UV）
  - B. 物体互相穿插（需移模型位置）
  - C. 材质缺失显示灰白（需查材质实例）
- [ ] **家具穿过卫浴门洞**：`LIV_furniture` 柜体 x 304…386 / y −807…−779 卡在门洞，
  需在 Blender 源里挪开
- [ ] **室内细节偏粗糙**

### P3 · 功能扩展

- [ ] 灯光明暗与颜色按实景再调（现 7 盏 RectLight 已移进室内）
- [ ] 后期效果（Bloom / Streaks / AgX 调色）迁移为 PostProcessVolume
- [ ] LOD / Nanite 设置（685k 三角面近景可用，城市远景需优化）

---

## 五、重要经验

1. **坐标换算只有一套**：`ue_x = bx*100`，`ue_y = -by*100`，`ue_z = bz*100`。
   从 glTF 读（`ue = (gx, gz, gy)*100`）可以直接反推。之前 `10/12/16` 脚本按
   `ue_y = +by*100` 摆东西，门和出生点整体镜像到了楼的另一侧。
   **任何手写坐标前先跑 `00_gltf_geometry.py` 并对照 UE 读回的包围盒。**
2. **单面薄片不是地板**：`S_floors` 是 24 个零体积三角形（厚 3.2 cm）。它能被射线打到，
   但站不住快速下落的人。碰撞地面要用引擎 Cube 或明确厚度的盒体。
3. **叠加碰撞会反噬**：每加一层 `BlockAll` 地板，出生时就多一层穿插。
   现在只保留每房间一块，顶面严格等于真实地面高度。
4. **`S_doors` 的门扇是烘焙好的静态几何**，按开启角度旋开并参与碰撞。
   要接交互门必须先让这个网格退出碰撞。
5. **栏杆没有标签就永远翻不过**：`Traversal.GuardrailDrop` 是遍历系统的准入门槛，
   不是可选装饰。标签在组件或 Actor 上都要一致。
6. **`UnrealEditor-Cmd` 无头模式不初始化物理**：所有 `LineTrace` 返回空，
   不能作为碰撞验证依据。离线几何审计（`18_structure_audit.py`）只能验证尺寸关系，
   实际站不站得住仍需 PIE。
