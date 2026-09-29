# 砍树自然截断升级：年轮封口 + 板根裁剪 + 截断倒伏恢复（2026-09-28）

用户第四轮砍树反馈（对 09-26"整树倒伏"取舍的推翻）：

1. **树木底部没有用年轮木纹封死**——整树倒伏时根部抬起，原树网格 Z≈0 的空心筒口暴露（09-26
   文档 §12.3 预判过的问题，本轮实测出现）；
2. **树皮过于延展**——切口附近向外张开的板根树皮（09-26 第三次反馈"支棱树皮"的同一来源）；
3. **不是从砍口截断而是整个模型倒伏**——希望像真实伐木：树桩留下、上半段从砍口倒下。

## 1. 根因（全部实测确证）

| 问题 | 根因 | 证据 |
| --- | --- | --- |
| 底部中空 | 09-26 把 `fps.Harvest.TreeFallCutAtStump` 默认设 0：整树倒伏不截断、不挂封盖，原树网格底部是开口筒 | `ProductionFallingTree.cpp` CVar 默认值；`TreeFallTriangleFixPlan-20260926.md` §12 |
| 树皮延展/支棱 | 原树切口高度（42 cm）以上仍有板根，实测半径超出封盖 **A 5.9 / B 5.4 / C 3.8 / D 1.1 cm**；封盖按干身横截面取，盖不住 | 本轮剖面实测（下表），`Tools/Production/probe_tree_flare_profile.py` |
| 整树倒伏 | 同第一条：不截断路径是 09-26 第三次反馈后定的默认 | 同上 |

年轮贴图**本来就已接线**（无需新增资产）：倒树断面材质 `M_FallingCutEnd` 与树桩切面
`M_TreeCutSurface` 都采样 `T_PoplarEndReference` 年轮参考图（本轮 `probe_falling_materials_detail.py`
实测；树桩切面 09-26 已获用户认可）。恢复截断+封盖即得年轮封口。

## 2. 板根径向剖面实测（SM_CutUpper_* SOURCE_MODEL 全顶点，2026-09-28）

| 变体 | 封盖最大半宽 (cm) | 切口带最大半径 (z=42..50) | 干身回落半径 | 回落高度 | 形态备注 |
| --- | --- | --- | --- | --- | --- |
| A | 39.74 | 45.6 | ~37.5 | ~85 cm | 单干 |
| B | 39.60 | 45.0 | ~38 | ~85 cm | 单干 |
| C | 26.05 | 29.8 | 丛生 | **62 cm 截止** | z≥70 起半径增大是**真实分干**，不能裁 |
| D | 13.74 | 14.8 | ~13.5 | ~85 cm | 细干 |

日志：`Saved/ProductionTreeHealth/treeprobe11-20260928.log`（`TREEPROBE BAND/CAP/RIM` 行）。
DA_TreeCut_* 轮廓 rim 最大半径 A 45.61 / B 45.05 / C 29.81 / D 14.60，与剖面带一致。

## 3. 方案与落地

### 3.1 材质：遮罩加径向裁剪（`Tools/Production/patch_falling_poplar_flare_clamp.py` 已落盘）

`M_FallingPoplar` 的不透明遮罩自定义节点从

```hlsl
return O*step(H,P.z)*step(frac(sin(dot(P,float3(12.9898,78.233,37.719)))*43758.5453),F);
```

扩为

```hlsl
return O*step(H,P.z)*saturate(step(T,P.z)+step(length(P.xy),R))*step(frac(sin(...)),F);
```

- 新标量参数 `HarvestCutRadius`（默认 100000＝不裁）、`HarvestFlareTop`（默认 0＝不裁），
  已连接到新输入脚 R/T；两实例 `MI_FallingPoplar_Bark/Foliage` 自动继承；
- 语义：`P.z ∈ [CutHeight, FlareTop)` 的板根带内，水平半径超过 R 的树皮被裁掉；
  `P.z ≥ FlareTop` 的枝干一律保留（不误伤树冠）；P 是树本地坐标（既有 H=42 遮罩在倒伏
  过程中随树旋转已实测正确，同一坐标系）；
- 默认参数值＝完全不裁，材质行为向后兼容；commandlet 内 recompile 预期失败（无着色器
  编译环境），已按 09-26 使用标志修复的既定模式直接保存，**下次编辑器/PIE 加载时重编**；
- 修改前备份：`trash/treefall-restore-20260928/M_FallingPoplar.uasset.bak`
  （SHA256 `c4880864…a5735cd`）。

### 3.2 C++（`ProductionFallingTree.cpp`）

| 改动 | 内容 |
| --- | --- |
| `fps.Harvest.TreeFallCutAtStump` 默认 0→**1** | 恢复"42 cm 截断 + 断口封盖"为默认：树桩留下（既有链路不变），上半段从砍口倒下，封盖（年轮）挂上；`0` 保留整树倒伏对照 |
| 裁剪参数表 | `CutClampRadiusCm={40.0, 39.8, 26.3, 13.9}`（封盖半宽+0.2）；`FlareBandTopCm={90, 90, 62, 90}`（C 丛生只裁到 62，防误伤分干） |
| MID 传参 | 截断时对全部倒树材质设置 `HarvestCutRadius/HarvestFlareTop`；不截断时 100000/0（遮罩恒 1，等于不裁） |
| `FALLDIAG` | 追加 `clamp_r=%.1f flare_top=%.0f`，运行时可核对 |

### 3.3 效果对照

| 表现 | 09-26 默认（本轮前） | 本轮后默认 |
| --- | --- | --- |
| 倒伏形态 | 整棵原树（含根部）倒 | 树桩留 + 上半段从 42 cm 砍口倒 |
| 倒树底部 | 空心筒口暴露 | `SM_CutCap_*` + `M_FallingCutEnd` 年轮封口 |
| 切口板根 | （不适用） | 带内裁到封盖半径，无支棱树皮 |
| 对照开关 | — | `fps.Harvest.TreeFallCutAtStump 0` 回整树倒伏 |

## 4. 性能

- 零新增 Actor/Tick/Timer/Trace；裁剪是每个倒树材质 MID 两个静态标量参数（一次性设置），
  遮罩着色器多两次 step + 一次 length + saturate（masked 材质逐像素成本可忽略）；
- 封盖/树桩/掉落链路全部复用既有资产与预加载集合（`LoadSet` 已含 `SM_CutCap_*`）。

## 5. 验证状态（如实声明）

### 5.1 首轮交付的材质缺陷与修复（2026-09-28 深夜，用户实测"树皮仍突出"后）

用户实测：截断+年轮封口生效，但**径向裁剪没起作用**（板根树皮支棱如旧）。根因（读 5.8 引擎
源码定论）：首轮补丁在 commandlet 里跑，`connect_material_expressions` 对 R/T 输入脚**静默失败**
（返回 False 不抛异常；当时统一 Inputs 视图未刷新导致找不到新脚），而脚本只检查了"无异常"。
脚空连时自定义节点把 T 读作 0 → `step(0,P.z)≡1` → 裁剪因子恒 1 → 等于没裁。截断与封盖走
C++（DLL 已编入）所以正常——与用户看到的表现逐项吻合。

修复（`Tools/Production/fix_falling_flare_clamp_live.py`，活编辑器桥内执行，日志
`Saved/ProductionTreeHealth/flarefix-live-20260928.txt` + 编辑器日志 15:16 段）：

1. 在活编辑器里重新连接 R/T——`connect_material_expressions` 返回 **True**（引擎源码：
   仅在 `Input->Connect()` 真实执行后返回 True）；
2. `recompile_material` 走完整管线（`PreEditChange/PostEditChange` 抬 StateId → 按新表达式图
   重编 → 更新子实例参数名），返回的"False"实为**空错误数组＝零编译错误**（5.8 该函数返回
   `TArray<FString>` 编译错误，不是 bool——bool([]) 的误读教训）；
3. 保存落盘（编辑器日志 `Saving Package: /Game/Items/HarvestTimber/M_FallingPoplar`）。

资产级复核（`verify_falling_flare_wiring.py`，commandlet）：用 `DisconnectMaterialExpressions`
探针（仅当脚存在且**已连接**才返回 True）证实 R/T 连线已序列化进包，遮罩代码含裁剪因子。
日志 `Saved/ProductionTreeHealth/flareverify-20260928.log`。

### 5.3 第五轮反馈与最终方案（2026-09-29）：默认改为几何真切断

用户第五轮反馈（"要从树干中截断倒下，不是整个模型倒下再生成树桩，本质差别"）。排查两发现：

1. **5.1 的"活编辑器修复"实际把 M_FallingPoplar 的材质图清空了**（EXPR_COUNT 0——整树可见
   的直接原因；commandlet 原始数组写入 + 编辑器 reconcile 的组合事故）。已从
   `trash/treefall-restore-20260928/M_FallingPoplar.uasset.bak`（SHA c4880864…）文件级恢复，
   commandlet 读回验证 15 个表达式、遮罩节点 [O,P,H,F] 原样。**教训固化：材质图编辑只允许在
   活编辑器内做，且每步 connect 必须查返回值、recompile 看错误数组、保存前后做表达式计数守卫。**
2. **FALLDIAG_ASM 实测推翻 09-25 的"重制网格组合数据丢失"假设**：SK_CutUpper_D 与源树
   parts=12/nodes=1250/bones=1687/平移量逐项一致；M_CutUpperMotion 使用标志齐全。几何截断
   路径资产全部就绪。

**最终方案（已落地）**：

| 项 | 内容 |
| --- | --- |
| 默认倒树网格 | `fps.Harvest.TreeFallUseSourceMesh` 默认 0→**SK_CutUpper_\***（42 cm 以上的真切断上半段，自带年轮断面封盖）；树桩原地保留——"倒下的就是被锯下的那一段" |
| 板根裙边 | `M_CutUpperMotion` 淡出遮罩加同式径向裁剪（`O*saturate(step(T,P.z)+step(length(P.xy),R))*step(噪声,F)` + `HarvestCutRadius/FlareTop` 参数，默认 1e5/0 不裁）；全程活编辑器短批次执行：connect 返回 True、recompile 零错误、表达式计数 15→17、保存后重载终验全部通过（`Saved/ProductionTreeHealth/cutpatch-20260929.txt`）；改前备份 `trash/.../M_CutUpperMotion.uasset.bak`（SHA c2f06285…） |
| M_FallingPoplar | 恢复出厂原状（无裁剪参数）；仅在对照模式（CVar=1）使用，设参为无害空操作 |
| 构建 | Game+Editor 双目标 Succeeded（`Saved/BuildEditor/build-geocut-20260929-*.log`） |

**待用户实测**：倒下的是上半段（几何真切断）＋树冠正常渲染＋切口年轮＋裙边裁净。若 09-25 的
"树冠塌三角"复现（成因至今未明，资产证据显示无恙），控制台 `fps.Harvest.TreeFallUseSourceMesh 1`
一键退回材质遮罩路径，无需重编。

### 5.4 活编辑器自检截图（2026-09-29，用户授权"自己检查一遍"）

`Tools/Production/selfcheck_geocut_visual.py`：spawn `AProductionFallingTree` + SK_CutUpper_A 于
(0,0,50000) 高空，自配太阳/天光，SceneCapture2D + `register_slate_post_tick_callback` 逐帧 40 帧采
三相位（A=切口特写·裁剪开 R40/T90；C=全树中景；B=同 A 机位·裁剪关 R1e5/T0），参数与 C++
`InitializeFall` 的 variant-0 表完全一致。产物 `Saved/ProductionTreeHealth/selfcheck_{A,B,C}_*.png/jpg`。
三项判定（AI 视觉模型读图）：

| 检查项 | 判定 | 证据 |
| --- | --- | --- |
| 断面年轮封口 | **通过** | A 图底部浅木色横切面、可见 2–3 圈同心年轮环 |
| 板根径向裁剪 | **通过（对照成立）** | B（裁剪关）底部树皮轮廓波浪外扩/裙边可辨；A（裁剪开）轮廓干净无裙边 |
| 树冠渲染 | **通过** | C 图树冠为密集小叶片簇，**无** 09-25 式大平三角面 |

截图工具链的坑（v2 三张全空镜头的根因，已全部修进 v3）：Python `Rotator` 构造顺序是
**(roll, pitch, yaw)**（按直觉传 (pitch,yaw,roll) 会把相机拧到正下方俯视）；编辑器 spawn 的
SceneCapture2D 根组件默认 Static 移动性，且 Python 侧 `set_actor_location(loc)`/`set_actor_rotation(rot)`
**无默认参数、必抛 TypeError**、异常被 Slate 回调吞掉——相机永远停在出生位水平朝向（三张同构图
黄昏天水图）。修法：根组件+捕获组件设 MOVABLE、`set_actor_location(loc,False,True)`、
`set_actor_rotation(rot,False)` 传全参、begin_phase/on_tick 全体 try/except 落日志。

### 5.5 地图污染事故与修复（2026-09-29 11:21–11:45）

上午截图工具链迭代失败的运行（crash 于 cleanup 之前）在会话世界里泄漏了 transient actor（每轮
1 套 DirectionalLight+SkyLight+SceneCapture2D+树）；**11:21:56 某次地图保存把 28 个泄漏 actor 烤进
了 `Content/GameMaps/DayNight_Lighting.umap`**（9 光照+9 天光+4 捕获+6 树，全部悬在 500 m 高空；
方向光不受位置衰减，9 个太阳进游戏会全场景叠加曝光）。证据：两个先后启动、各自从文件加载地图的
编辑器（34944/7768）读出完全相同的 28 个残留；umap mtime 11:21:56。

修复（11:44）：借当时无打开世界的编辑器 load→按类清扫 BASE±20000→`save_dirty_packages`→重载复
核，BEFORE 28 / LEFT 0 / **VERIFY-RELOAD 0（CLEAN）**，文件 1123077→1035105 字节。改前备份
`trash/map-pollution-cleanup-20260929/DayNight_Lighting.umap.bak`（SHA256
5875674a44fe416ac8d8857c0e0fd0170e03b459d1e93d29eb62f4cf99288cc0）。

教训（已入记忆）：**spawn 瞬态 actor 的工具脚本必须先注册 cleanup 再开始工作**（进程内 try/finally
挡不住编辑器崩溃），且失败重试前先清扫上一轮残留；地图在多会话/守护自动化环境下随时可能被保存，
泄漏物不能指望"反正不保存就没事"。

### 5.6 第六轮反馈"倒木还有一根突出物"与内壁舌头掩码（2026-09-29 13:00–13:40）

用户图判（AI 视觉）：细杆从切口端断面附近斜向上 45° 伸出、光滑无纹理、颜色发黑。离线几何探针
（`Tools/Production/probe_stub_sectors.py`，commandlet 只读）定位：SK/SM_CutUpper 的树干是双层壳
（外皮 r30-46 + 内壁 r15-30）；内壁层本应从 z≈200 才开始，但 **A 变体在 315°–360° 扇区下垂到
z≈80**（942 顶点集中簇），且该扇区外皮密度只有均值一半——倒伏后内壁从外皮缺口露出＝"光滑发黑
细杆"（内表面无光照、无树皮纹理，全部吻合）。B（~330°–15°）、D（~15–45°）有同款小簇；C 丛生
形内壁即真实干身。自检 A 图没拍到是相机在 0° 方位、舌头在背面。

**修法（全链路已落地）**：
- `M_CutUpperMotion` Custom 节点加内壁舌头掩码：`S=step(60,P.z)*step(P.z,Z)*step(wrapDiff(atan2deg
  (P.y,P.x),Y),W)*step(len(P.xy),31)`，`O*=(1-S)`——60 以下不碰（年轮断面封盖）、r<31 只切内壁
  不伤外皮、方位角窗环形回绕；新脚位 **Z/Y/W**（短名＝代码引用名，踩坑：脚位名写成参数全名
  HarvestStub* 会 undeclared identifier×24）连 3 个 ScalarParameter（默认 0＝全关）。
  活编辑器全绿：connect True×3 / recompile 0 错 / 计数 17→20 / 落盘 13:23（38076 字节）/ 重载终验。
- C++ 三表（`ProductionFallingTree.cpp`）：`StubYawDeg={337.5,347.5,0,30}`、`StubYawTolDeg={25,22,0,18}`、
  `StubZMaxCm={210,210,0,210}`（C 关闭）；MID 传 3 参+FALLDIAG 带 stub_yaw/tol/zmax。
  Game（12:57）+Editor（13:04）双目标 Succeeded，DLL 内 UTF-16 参数名已验证。
- 环拍终验（`orbit_find_stub.py`，掩码参数与生产一致）：4 方位（0°/315°/垂直 75°/俯拍）AI 读图
  全过——**无黑杆、树皮完整无天窗、年轮断面完好**。

排障坑（本轮新增）：`-unattended` 编辑器里编辑器态 actor 变换疑似不生效（多轮全废图；去掉该参数
后同脚本一把过）；材质保存被并行编辑器的内存映射挡住（`save_loaded_asset` 返回 False，关掉多余
编辑器即好）；MCP 会话被并发桥调用搞坏后 `-NewSession` 重握手可修；带地图的隐藏编辑器存活时间
也不可控（外部守护清场），自动化要"启动→等就绪→干活→自杀"一条龙。

## 6. 相关文件

- 代码：`Source/FPSGAME/Production/ProductionFallingTree.cpp`
- 探针（全部只读、commandlet 可跑）：`Tools/Production/probe_tree_flare_profile.py`（分带
  剖面/封盖/轮廓）、`probe_falling_materials_detail.py`（材质接线）、`probe_stub_clusters.py`
  （轴心/贴干内簇）、`probe_stub_sectors.py`（扇区×半径带双层壳验证）
- 材质补丁（活编辑器专用，幂等）：`patch_cutupper_flare_clamp_live.py`（径向裁剪基线）、
  `patch_cutupper_stub_mask_live.py`（内壁舌头掩码，§5.6）
- 验证：`selfcheck_geocut_visual.py`（三相位读图）、`orbit_find_stub.py`（环拍找茬）、
  `auto_orbit.ps1`+`probe_asset_ready.py`+`launch_with_map.ps1`（编辑器自动化一条龙）、
  `build_game.ps1`/`build_editor.ps1`（构建包装）
- 修复：`clean_map_pollution.py`（§5.5 地图泄漏清扫）
- 资产：`M_FallingPoplar.uasset`（出厂原状）、`M_CutUpperMotion.uasset`（裁剪+掩码双补丁）；
  回退＝用 trash 备份覆盖回原名
- 技能参考：`skills/ue5-world-interaction/references/tree-harvest-cut-and-fall.md`（当前状态已同步更新）
- 历史工具退役归档：`trash/treefall-tooling-retired-20260929/`（含危险的 commandlet 材质补丁
  废案，勿复用）
