# SVCh 精确射手步枪：开发记录（2026-10-17）

> 当前修订见 [2026-10-18 表面、基础握持与 ADS 修订](svch-refinement-20261018.md)。下文保留初版制作历史；当前运行网格已经改为 `Refined20261018/SK_SVCH_Refined_R2`，姿态通过本枪差量接入。

按 [枪械标准工作流](../../WEAPON-WORKFLOW.md) 与 [ue5-weapon-workflow](../../skills/ue5-weapon-workflow/SKILL.md) 从头制作的一把新枪。模型为用户指定的 Sketchfab 低模，骨架与手模沿用已认可的 SVD / V9 裸手体系。

**状态：模型、材质、数据、C++ 接入与后台构建已完成；未做实机、视觉或联机验收。** 按用户全局规则，测试由用户执行。

## 交付物

| 层 | 位置 |
| --- | --- |
| 运行网格 | `/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny` |
| 材质实例 | 同目录 `Materials/MI_SVCH_*`（7 个） |
| 源制作 | `SourceAssets/SVCHSketchfab20261017/` |
| 来源与许可 | [PROVENANCE.md](../../../SourceAssets/SVCHSketchfab20261017/PROVENANCE.md) |
| 模型审计 | `SourceAssets/SVCHSketchfab20261017/audit/report.md`（35 KB，独立复核） |
| 参数头 | `Source/FPSGAME/Weapons/SVCHWeaponAssets.h` |
| 定义 ID | `ue_svch` |

## 制作流程

### 1. 取模型与审计

Sketchfab API 直连下载源包与 GLB。两份独立审计（本会话的 subagent 与主流程）给出了一致的尺寸、分件与坐标结论，记在 `audit/measurements.json`。

关键判断：源 FBX 声明单位为米、几何实际是厘米，且带非均匀节点缩放；GLB 的顶点坐标是干净的原始厘米值。**几何一律取自 GLB**，FBX 仅存档。

### 2. 视模作者化（`author_svch.py`）

- **骨架**：从已认可的 `SVD_Complete_Editable.blend` 取完整 rest 矩阵（100 根骨）。这里踩过一次坑：最早只复制 `head`/`tail` 并把 roll 设 0，导致每根骨的朝向都错，蒙皮被剪切成放射状碎片。改用 `edit_bone.matrix = matrix_local` 后恢复正常。
- **裸手**：通过只读 commandlet 把已安装的 SVD 视模 dump 成 JSON（70,877 顶点 / 101 骨 / 17 槽），再逐三角面把 `MI_Manny_*` 的部分连同顶点权重搬进新文件，共 20,485 顶点 / 37,086 面。手臂几何与权重和游戏里跑的完全是同一份。
- **坐在哪**：SVD 的枪体网格存在 rig 的 **bind 空间**（idle 姿势由 Armature 修改器施加，不烘进顶点）。所以 SVCh 也按 bind 空间就位：把它的握把面板中心 (0.61, −19.14, −6.51) 平移到 SVD 实测的握把中心 (6.07, −14.30, −13.08) cm。扳机残余 4.33 cm，是两枪握把角与扳机行程差造成的，属于可接受的初始值，**需要实机确认**。
- **分件**：按源骨骼把 10 个网格对象归成 6 个语义件（机匣、弹匣、枪机框、保险、弹匣释放钮、实弹），每件刚性绑定到一根 `WPN_*` 骨，权重 1.0。
- **挂点**：用审计实测值反算到 bind 空间，写进骨骼与 `authoring.json`。

### 3. 材质（WS1）

源模型 10 个槽都是「金属度 0、粗糙度 1」的介电平光面，直接进游戏像塑料。按语义分成钢机匣、聚合物弹匣、抛光钢件、阳极氧化小件四类，各自建一个 WS1 实例挂在共享母材质下，于是自动进入淋湿与天气通道。

没有按源图做底色分区，理由见 PROVENANCE：源包没有贴图也没有 UV，10 个槽的线性底色只差 0.0119–0.0400，肉眼不可分，且 WS1 Clean 组本来就会把这个区间压平。

### 4. UE 导入（`import_assets.py`）

这一层花了最多时间，原因是 UE 的 FBX 导入器**会把 7 个源对象合并成一个骨骼网格，并按材质名重新排序槽位**。最初按槽名识别部件，结果手臂材质被绑到枪身上。

最终判据是几何的、可复核的：武器件的三个顶点都刚性绑定在同一根 `WPN_*` 骨上，手臂则是跨多根手臂骨的平滑蒙皮。用「骨骼 + 三角面数」两个精确量定位每个槽，并在脚本里断言手臂面数 37,086、武器面数 6,963、两者之和等于网格总数，任何一项对不上就直接失败。

脚本每次运行会先退役旧资产再重新导入，保证结果不受上一次运行影响。

### 5. 数据接入（`register_data.py`）

四张表各加一条，键 `ue_svch`：

| 表 | 内容 |
| --- | --- |
| `items.json` | 物品定义：物攻 88、弹匣 10、5×2 格、简介 |
| `gunsmith.json` | 枪匠定义：8 槽、base 数值、5 条特性 |
| `combat-weapon-formulas.json` | 伤害公式，沿用 SVD 的属性系数，base 50.5 |
| `modular_outfits.json` | 本视模的手臂 profile，`rig_profile` 继承 SVD |

枪匠的改造选项**直接复用 SVD 的整套目录**：两枪同属一个导轨／枪口／护木接口族，共享 option id 才能让图标、数值行和改造台保持一致。基础数值在 SVD 之上微调（射速 300 ms、威力 88、弹速 545 m/s、有效射程 320 m），并逐条写进 `traits`。

### 6. C++ 接入

新增 `SVCHWeaponAssets.h`，并在下列位置与 SVD 同列：

- `FPSGAMECharacter.cpp`：视模分支、`LoadAKMAnimation`、枪声与机械音、弹鼓守卫、检视、冲刺族、开镜标定、武器状态时长、枪口挂点
- `FPSGAMECharacterProfile.cpp`：装备白名单（漏了这一条枪根本装备不上）
- `RifleHipFraming.cpp`：腰射构图白名单与前移量 10 cm
- `CasingPortCalibration.h`：抛壳口实测位置
- `QuickCombatRifleMotion.h`：枪托近战接触点
- 图标与拾取：`ColdSteelWeaponIcons.cpp`、`ColdSteelIconResources.cpp`、`ColdSteelPickupWeapon.cpp`、`ColdSteelPickupStudio.cpp`、`ColdSteelWeaponIconCatalogCommandlet.cpp`、`FPSConsumableAuditCommandlet.cpp`
- `ColdSteelWarehouseModel.cpp`：军械库发放与配套弹药

## 材质与图标修正（同日更晚）

查图标为什么带着手臂时，挖出一个更严重的问题：**七个部件的材质从一开始就套错了槽**。

**根因：** 首次导入时把 `Interchange.FeatureFlags.Import.FBX` 置 0，走旧 FBX 导入器。旧路径会额外追加 6 个空材质槽，8 个材质的 FBX 落成 14 槽网格。渲染分区按“数组绝对索引”记成 6–13，而部件识别走 Geometry Script 的压缩序号 0–7；两边错位后，我把部件材质写到了分区并不引用的 0–7 上。后果是手臂套着 `MI_SVCH_BoltCarrier` 的抛光钢，枪体也拿了别的部件的材质——图标里那些深色"手臂"正是被打成钢的皮肤。图标按槽名隐藏手臂，而分区指向的槽名是 `svch_boltcarrier`，所以永远命中不了。

**修复（`import_assets.py`）：**

1. 不再关闭 Interchange，走默认导入器（8 槽、名称正确）。
2. 先导入到暂存名 `SK_SVCH_Manny_Import` 再换入正式路径。直接重导到原名不会得到干净对象——导入器会把新材质并进旧资产；而 `delete_asset` 明明返回成功，包却仍被重定向器占着，改名会以"目标已存在"失败。所以换入前先把旧资产改名让位，再删除。
3. 断言导入后正好 8 个槽，槽名以 `SM_SVCH_` / `MI_Manny_` 开头，与渲染分区顺序对齐。
4. 去掉导入后的 `save(mesh.skeleton)`：骨架与其他视模共用且未改动，命令行的保存既非必需也不可靠。

**结果：** 槽位恢复为 0 Body / 1 BoltCarrier / 2 Cartridge / 3 MagRelease / 4 Magazine / 5 Selector / 6 MI_Manny_01 / 7 MI_Manny_02，每个部件绑定自己的 WS1 实例。图标分区日志确认 6、7 被判为手臂并隐藏，取景包围盒从 `X=47.86 Y=120.42 Z=43.86` 收敛到 **`X=5.96 Y=107.31 Z=27.04`**——Y 正好是实测全长 107.31 cm，手臂已完全排除。

图标同时满足标准：枪口朝左（安装姿态前方在画面左侧）、800×320、透明、无彩色灰阶、单件、无手臂。

## 方向修正（2026-10-17 晚）

首版交付后实机发现整枪前后反了。根因是两个坐标错误叠加，都已用测量钉死。

**1. 审计坐标系与 GLB 顶点坐标系不同源。** 审计地标在 FBX 节点坐标系（厘米），网格顶点是 glTF `POSITION` 的原始值。两者长度一致但整体平移：沿枪管 `dx = 18.7444`、向上 `dz = 1.5268`、横向 `dy = 0`。`solve_frame_offset.py` 用枪口端面圆心解出这两个量，并用“照门顶 13.238 + 1.5268 = 14.765”与托底两点交叉验证。此前当成同一坐标系，握把对准量因此错了 18.75 cm。

**2. FBX 往返在 Y 轴取反。** 把导出的 FBX 用 Blender 默认导入器读回（`measure_roundtrip.py`）与 UE 实测逐项比对，得到 `UE = (100x, −100y, 100z)`。作者空间就是 UE 组件空间（米），写进 Blender 必须再取反一次 Y。只取反一个轴会翻手性，因此同时反转三角形绕序，法线才仍朝外。

修正后实测（`probe_orientation.py`，重导入后）：

| 项 | SVCh | 认可的 SVD |
| --- | --- | --- |
| 手臂 `MI_Manny_01` y | −3.66 … 11.22 | −3.66 … 11.22 |
| 手臂 `MI_Manny_02` y | −27.44 … 8.53 | −27.44 … 8.53 |
| 枪体 y | **−92.47 … 14.84** | −94.73 … −0.50 |

手臂包围盒与 SVD 逐位相同，枪口落在 −y，与 SVD 同一朝向。`authoring.json` 另加自检：作者空间包围盒必须等于实测枪口/托底，不等直接报错。瞄距复核 0.5377 m、瞄准线高出膛线 0.0859 m，与审计一致。

**3. 开镜与枪口改用本枪实测点。** 共享 `WPN_*` 标记骨里烘的是 SVD 的位置，本枪此前借用了它。现按 AKMSoviet 的既有做法，在 `SVCHWeaponAssets.h` 给出本枪的照门／准星／枪口／抛壳口（`WPN_root` 空间，米），开镜标定与 `M4MuzzleVisual.cpp` 的枪口位置、轴向改读这组常量。

## 已知限制

1. **没有专属动作**。12 段动作全部指向 SVD 目录。两枪握把位置相差约 5.6 cm，右手与扳机指的实际接触必须实机看；若明显跑位，需要按 `magazine-grip-registration` 的方法重做右手接触。
2. **没有专属音效**。复用 SVD 的 7.62×54R 套件。
3. **眼距 10 cm 是初值**，不是实测。
4. **弹匣内有 600 面实弹几何**留在网格里（材质已绑金属）。减面时应连同 4 根只服务它们的源骨骼一起删。
5. **背包图标已按标准出图**：枪口朝左、800×320、透明、灰阶、无手臂（修正过程见上一节）。
6. **枪体在图标里偏亮**。SVD 的实例带自定义 `SVD_Refined*` 参数压暗表面，本枪直接用 WS1 预设默认值，在图标棚的白色环境下反射偏白。是否调暗要跟其他 WS1 枪一起定。

## 未执行的验收

以下全部**没有做**，按用户规则交由用户测试：

- 实机装备、腰射构图、开镜对齐与滚转
- 换弹、空仓、拉栓、检视、冲刺、枪托近战
- 枪口烟火、曳光、抛壳与命中反馈
- 枪匠改造台的装卸、预览与存档读回
- 联机权威与第三人称
- 视觉：材质在实时光照下的表现、手与枪的接触

## 构建状态

**已成功构建，产物包含本枪全部 C++ 改动（含方向修正后的开镜与枪口接入）。**

- 最新一次：`FPSGAMEEditor Win64 Development` 于 **23:07 发起、23:11 返回 `Succeeded`**（`Saved/BuildEditor/build-20261017-230725.log`，261 秒），含 `SVCHWeaponAssets.h` 的实测瞄点常量、`FPSGAMECharacter.cpp` 的开镜对照门/准星覆盖、`M4MuzzleVisual.cpp` 的枪口位置与轴向分支。
- 更早 22:06:39 的一次成功（`build-20261017-220611.log`）覆盖了视模分支、动画路由、音效、抛壳口、腰射与图标登记；读回当时的 DLL 能检索到 `SVCH_ACTIVE`、`ue_svch`、`/Game/Weapons/SVCH/`。
- 22:08–22:14 的三次失败源自另一会话的在写文件 `FPSUDSBridgeComponent.cpp`（C4456），与本枪无关；该文件修好后 23:11 的构建顺利通过。
- 23:17 之后编辑器被重新打开，二进制被占用，**此后无法再编译**。若还要改 C++（例如查图标手臂的隐藏路径），需先关闭编辑器。

已单独核对、不依赖构建的部分：`/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny`（44,045 面、14 槽、7 个 WS1 实例、骨架为共享 Manny、朝向与 SVD 一致）、`Content/ColdSteelData/Icons/ue_svch.png`（800×320）、四张数据表、`Config/DefaultGame.ini` 的 cook 目录与 `FPSPreloadAssetRegistry.gen.h` 的两条 SVCH 路径。

## 复现

```powershell
$bl='E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$case='D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017'
& $bl --background --factory-startup --python "$case\author_svch.py"
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
    'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript "-script=$case\import_assets.py" `
    -unattended -nop4 -nosplash -nosound
python "$case\register_data.py"
```

## 表面与持握（2026-10-18）

实机反馈：表面是硬面低模、双手没贴住枪。两条按 SKILL 的「几何缺陷先于材质」处理。

**表面。** 源模型是平面着色的低模，且没有任何 UV：

- 全部三角面改为平滑着色，按面夹角 35° 标记硬边，圆柱面（枪管、机匣圆弧）因此平滑，导轨与机加工台阶保持锐利。
- 之前导出用的是 `mesh_smooth_type='FACE'`，即强制逐面平直——这正是满屏硬面的直接原因。已改为 `'OFF'`，导出网格自身的分裂法线。
- 补了 UV。**不能用归一化展开**：WS1 的颗粒与斑驳按物理厘米平铺（`GrainTileCm`），smart project 会把每个岛归一到 0..1，纹理密度随岛大小乱跳，出图是迷彩花斑。改用世界尺度立方投影（一贴图 = 25 cm），表面恢复均匀钢材。
- 0.6 mm 倒角没做成：这个模型是 139 个壳的散件集合，bmesh 找不到足够的双边硬边，`modifier_apply` 在后台又静默取消。保留平滑+UV，倒角留作后续。

**持握。** 先怀疑朝向，于是把只做平移的对准改成按 SVD 实测握持帧的刚体注册（`fit_hold_frame.py`：枪口端面拟合出膛线轴，握把中心对齐，`det=+1`，握把误差 0）。但解出的旋转几乎是单位阵——说明网格位置本来就对，握不住不在这里。

真正的问题在装备档案：`modular_outfits.json` 里本枪的 `hide_source_materials` 还是 SVD 的 `[0,1]`。SVD 的手臂恰好在 0/1，而本枪按 FBX 材质序是好 0 机匣、1 枪机框，手臂在 6/7。于是装备时隐藏的是**机匣和枪机框**，手臂反而留着——运行时同时出现自身手臂和裸手替换件，握持自然对不上。已改为 `[6,7]`，`shirt_covers` 同步为 `[6,7]`，`glove_covers` 清空（自身手臂已隐藏，无需再标覆盖段）。

注意这类索引依赖 FBX 材质顺序，本枪为：0 Body / 1 BoltCarrier / 2 Cartridge / 3 MagRelease / 4 Magazine / 5 Selector / 6 MI_Manny_01 / 7 MI_Manny_02。重建网格后如材质序变化，这里要同步。

## ADS 错位：常量空间用错（2026-10-18）

`UpdateADSPose` 里是 `Root.TransformPosition(Rear)`，`Root` 是累加出来的 `WPN_root` 骨骼变换，所以常量必须是**骨骼局部空间**的点——AKMSoviet::Rear/Front 就是按这个写的。

我给的是组件空间坐标，于是两个瞄点被当成局部点后塌到骨骼原点附近：照门和准星几乎重合，开镜时相机被推到错误的位置，自然对不上。

`local_sight_constants.py` 用 `Skeleton/rest.json` 里 `WPN_root` 的绑定矩阵求逆后重新表达（矩阵是纯旋转+平移，无缩放）：

| 点 | 组件空间（米） | 骨骼局部（米） |
| --- | --- | --- |
| 照门 | (0.0607, −0.1637, 0.0765) | (−0.018240, 0.307448, 0.173925) |
| 准星 | (0.0607, −0.7014, 0.0767) | (−0.018257, 0.845148, 0.174123) |
| 枪口 | (0.0607, −0.9247, −0.0094) | (−0.010752, 1.068448, 0.088351) |
| 抛壳口 | (0.0708, −0.3302, −0.0039) | (−0.021294, 0.473948, 0.092950) |

两组点的间距仍是 0.5377 m、比膛线高 0.0859 m，只是换了坐标系。已改入 `SVCHWeaponAssets.h` 并构建通过（`build-20261018-003421.log`）。
