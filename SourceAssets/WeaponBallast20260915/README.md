> **状态（2026-09-15 晚）**：本目录是早期候选源，已被 [模块化拆分](../FrostSwordModules20260915/README.md) 与 [5080 配重锤](../FrostSwordPommels5080_20260915/README.md) 取代，当前仅作为候选与对照保留。下文描述的是当时的设计（Ø34 球、挂件式覆盖安装、自建 `M_Ballast_*` 材质），**不再代表当前运行资产**；运行模型、接口与材质以那两个目录和 `Content/ColdSteelData/frost-sword-modules.json` 为准。

# 武器配重球（2026-09-15）

用户于 2026-09-15 指定“你来建模，做三个配重球”，依据的表单为「改造项目」栏目下的三项：硬化配重、符文配重、魔力球配重。本轮由作者脚本在 Blender 5.1.2 中程序化建模，未使用 5080 生成线。

## 交付物

| 文件 | 内容 |
| --- | --- |
| `build_ballast_balls.py` | 建模作者入口，三个变体与全部尺寸参数都在此 |
| `render_previews.py` | 预览渲染入口，复用同一份几何 |
| `blend/Ballast_*.blend` | 三个变体各自的 .blend 源；`Ballast_All.blend` 为三者并排 |
| `export/*.fbx` / `*.glb` | 导出件，FBX 按 UE 期望的厘米单位写入 |
| `build_report.json` | 每次构建的尺寸、面数、材质槽、非流形统计 |
| `preview/*.png` | 六张透明底预览图 |

重建与预览命令：

```powershell
$blender = "E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
$caseDir = "D:\FPS3D\FPSGAME\SourceAssets\WeaponBallast20260915"
& $blender --background --factory-startup --python-exit-code 1 --python "$caseDir\build_ballast_balls.py"  -- $caseDir
& $blender --background --factory-startup --python-exit-code 1 --python "$caseDir\render_previews.py"     -- $caseDir
```

## 统一安装接口（提案，待确认）

三个变体共用一套接口，以便落在同一个枪匠槽位互换：

- 原点 = 法兰与宿主的贴合面（z = 0），朝宿主方向为 -Z，球体在 +Z。
- 螺纹柱 M6 × 10 mm 沿 -Z；贴合法兰 Ø14 × 3 mm。
- 场景单位为米；FBX 导出为厘米（UE 按 1.0 导入）。

**该接口是我提出的默认方案，不是从实际枪型读出的安装基准。** 确认宿主枪型、插槽轴向和真实接口尺寸后需按配件标准重新校准；当前不宣称已适配任何枪型。

## 各变体

| 变体 | 造型 | 面数 | 包围盒 (mm) | 材质槽 |
| --- | --- | --- | --- | --- |
| 硬化配重 `SM_Ballast_Hardened_Candidate` | 锻打球体，赤道切出六个平面（对边距 30 mm） | 1148 | 34 × 30 × 47 | `M_Ballast_HardenedSteel` |
| 符文配重 `SM_Ballast_Rune_Candidate` | 光球 + 正面刻槽符文：三道竖槽（宽 2.5 mm、深 2.5 mm）交叉两道斜槽 | 1308 | 34 × 33.88 × 47 | `M_Ballast_RuneSteel`（金属，极弱自发光） |
| 魔力球配重 `SM_Ballast_MagicOrb_Candidate` | 顶部镗 Ø18 × 8 mm 沉孔，环形压边 + Ø16 mm 发光内核，核顶高出球面 0.8 mm | 2502 | 34 × 34 × 47.8 | `M_Ballast_MagicHousing`、`M_Ballast_MagicCore` |

共同参数：球径 Ø34 mm。三个变体非流形边与游离顶点均为 0。

材质为本机程序化 Principled 参数，用于候选与预览；UE 内的正式材质、金属区域划分和雨滴接入按 [枪身与配件材质统一](../../skills/ue5-weapon-workflow/references/weapon-finish.md) 另做，本轮未创建。

## 预览

| 图 | 内容 |
| --- | --- |
| `preview/sheet_three_variants.png` | 三件并排总览，1920 × 800 |
| `preview/SM_Ballast_Hardened_Candidate_front.png` | 硬化件正视图 |
| `preview/SM_Ballast_Hardened_Candidate_45.png` | 硬化件 45° 视图 |
| `preview/SM_Ballast_Hardened_Candidate_interface.png` | 安装接口视图（法兰与螺纹柱） |
| `preview/SM_Ballast_Rune_Candidate_front.png` | 符文件正视图（刻槽朝镜头） |
| `preview/SM_Ballast_MagicOrb_Candidate_45.png` | 魔力球 45° 视图（可见发光内核） |

透明背景、三点布光、EEVEE 渲染。预览按用户 2026-09-15 的要求生成，属于本次交付内容。

渲染过程中的读图复核与修正记录：

1. 第一版灯光 220 W 对 35 mm 物件严重过曝，整幅平均亮度 238/255，符文与切面被高光吃掉；降到 30/6/18 W。
2. 地面反光仍把画面拉到 190 亮灰，且相机俯角过小、地平线在画框外，导致整幅几乎全是地面；改为透明底、去掉地面。安装接口那张当时相机跑到地面下方，画面近乎全黑（平均 3.5），一并修正。
3. 符文球的蓝色自发光强度 0.35 使它读成“半透明蓝球”而不是刻纹金属，降到 0.10。
4. 魔力球内核原本缩在 10 mm 深孔内，45° 视角读不到；抬高露出孔口后，`strength 25` 又被 AgX 削成纯白、读图判为“空腔”；最终改为饱和蓝 + `strength 4.0`。

## 冰晶双手剑配重锤材质渲染（2026-09-15 追加）

用户要求：除魔力球外，另外两个用当前冰晶双手剑配重锤的相同材质渲染。

配重锤没有独立材质：`SM_FrostCrystalSword` 只有一个材质槽 `M_FrostCrystalSword`，配重锤只是同一组四张贴图上的一个 UV 区域。所以先量测、再套用：

1. `read_pommel_uvs.py` 导入 `SourceAssets/MeshyMelee20260915/Export/SM_FrostCrystalSword.fbx`，按最长轴（1.0941 m）定位钝头端为配重锤，取末端 4 cm，得 1081 顶点 / 6477 个 UV 采样点。与 `authoring.json` 记录的配重锤 z = -28.235 cm、剑尖 +81.173 cm 一致。
2. 按这些 UV 在四张贴图上逐点取样求均值。
3. 核对 UE 侧连法：`import_frost_sword.py` 把 BaseColor / Normal / Metallic / Roughness 直连对应材质属性，无额外系数或重映射。

量测结果（sRGB 0–255 均值，完整记录见 `pommel_material.json`）：

| 贴图 | 配重锤区域均值 | 区间 |
| --- | --- | --- |
| BaseColor | (93.4, 70.1, 49.3) 暖铜色 | 亮度 27–128 |
| Metallic | 206.9 → 0.811 | 180–221 |
| Roughness | 66.6 → 0.261 | 60–80 |
| Normal | (126.9, 127.2, 254) | 119–157 |

结论：配重锤是**抛光铜色金属**，金属度 0.81、粗糙度 0.26，法线接近平坦。

渲染输出在 `preview_pommel/`：

| 图 | 内容 |
| --- | --- |
| `sheet_two_pommel_material.png` | 两件并排（均值材质） |
| `SM_Ballast_Hardened_Candidate_pommel_front.png` / `_45.png` | 硬化件正视与 45° |
| `SM_Ballast_Rune_Candidate_pommel_front.png` / `_45.png` | 符文件正视与 45° |
| `sheet_two_textured.png` | 对照组：整张剑贴图直接套在球上 |

- **均值材质** `M_Ballast_FrostPommel`：用上面的实测均值做纯 PBR。读图复核为铜色、左侧平面可辨、右侧刻槽可辨、抛光感。
- **整张贴图直套** `sheet_two_textured.png`：把同四张贴图按球体自身 UV 直接套上（等价于在 UE 里把 `M_FrostCrystalSword` 直接指给球）。读图复核为蓝灰、杂乱色块与拉伸/接缝感——球面 UV 会把剑身结晶和护手区域一起采进来。**因此推荐均值金属版本，不建议整张材质直套。**

未做：未导入 UE、未创建材质实例、未替换 `build_ballast_balls.py` 里的现有 `M_Ballast_*` 材质。

## 魔力球改蓝色玻璃（2026-09-15 追加）

用户要求：魔法球配重换成蓝色玻璃材质，可以用剑身材质。

剑身和配重锤一样没有独立材质，仍是 `M_FrostCrystalSword` 的一组贴图；所以先量出剑身区域的实际取值：

1. `read_blade_uvs.py` 沿最长轴做 60 段横截面宽度剖面：低端 28 mm（配重锤）→ 23 mm（握柄）→ **109 mm 峰值（护手，z = 0.000 m）** → 60 递减到 7 mm（剑尖）。护手是唯一峰值，据此定出剑身起点，避免把握柄和护手混进采样。
2. 剑身取护手以上至剑尖前 3 cm，即 0.019–0.782 m，13625 顶点 / 81759 个 UV 采样点。
3. 按这些 UV 在 BaseColor / Metallic / Roughness 上取样求均值。

量测结果（记录在 `blade_material.json`）：

| 贴图 | 剑身区域均值 | 区间 |
| --- | --- | --- |
| BaseColor | (15.9, 159.4, 199.0) 亮青蓝 | 亮度 21–193 |
| Metallic | 42.1 → 0.165（非金属结晶） | 0–210 |
| Roughness | 64.1 → 0.251 | 40–97 |

玻璃做法：BaseColor 用剑身实测色转换为线性 (0.0052, 0.3486, 0.5705)，金属度归零，Transmission Weight = 1、IOR = 1.45、`use_raytrace_refraction` + EEVEE `use_raytracing` 开启，内芯保留自发光并提到 strength 18。管线细节见 `render_magic_glass.py`；`probe_eevee_refraction.py` 是本机 Blender 5.1 折射属性名的探针，说明 `use_raytrace_refraction` / `refraction_depth` 存在而旧 `use_ssr_refraction` 不存在。

输出在 `preview_magic_glass/`：

| 图 | 内容 |
| --- | --- |
| `sheet_glass_clear_vs_frosted.png` | 清玻璃（粗糙度 0.08）与磨砂（剑身实测 0.251）对比 |
| `SM_Ballast_MagicOrb_glass_front.png` / `_45.png` | 清玻璃正视与 45° |
| `glass_transparency_check.png` | 透明性验证：球后立一根亮色标杆 |

读图复核与一次修正：

- 第一版把 `surface_render_method` 设成 `BLENDED`，结果玻璃读成“不透明金属”。该版本应保持 DITHERED 走光线追踪折射，已改。
- 纯色背景下读图仍判“不透明、看不到核心”，与双球对比图的“能看到发光核心”互相矛盾。因此补渲 `glass_transparency_check.png`：球后标杆可见且被折射扭曲，读图判定为**透明**。结论以这张验证图为准，纯背景下的“不透明”属读图工具在无参照物时的误判。

未做：玻璃版本尚未并入 `build_ballast_balls.py` 的默认材质，也未导入 UE。

## 散列（SHA-256 前 16 位）

| 文件 | 散列 |
| --- | --- |
| `build_ballast_balls.py` | `35874988057F7360` |
| `render_previews.py` | `E2B0C35AF07DBCC9` |
| `build_report.json` | `57B2FFC3B8D9F391` |
| `blend/Ballast_Hardened.blend` | `48C19701E4212063` |
| `blend/Ballast_Rune.blend` | `684E8C94514555C2` |
| `blend/Ballast_MagicOrb.blend` | `165733EE5A110F2A` |
| `blend/Ballast_All.blend` | `5257DD29A3EB5C57` |
| `export/SM_Ballast_Hardened_Candidate.fbx` | `799D7497B8CE434D` |
| `export/SM_Ballast_Rune_Candidate.fbx` | `C0ABA7856BFB5214` |
| `export/SM_Ballast_MagicOrb_Candidate.fbx` | `B1A864DA25E94C97` |
| `preview/sheet_three_variants.png` | `8B234ED58937D53F` |
| `preview/SM_Ballast_MagicOrb_Candidate_45.png` | `9D32AEDE9313586B` |
| `read_pommel_uvs.py` | `72B10702B33E16C5` |
| `pommel_uvs.json` | `7B7A920705F897BB` |
| `pommel_material.json` | `7DC9C4D9288C2832` |
| `render_pommel_material.py` | `9D9FA4CE3BB18BFE` |
| `preview_pommel/sheet_two_pommel_material.png` | `41ADF3DDCA171161` |
| `preview_pommel/sheet_two_textured.png` | `979A8DCA0CF7113D` |
| `read_blade_uvs.py` | `061AE99050218244` |
| `blade_uvs.json` | `A330D48CEA779D5B` |
| `blade_material.json` | `2A48F6137C1E99A0` |
| `render_magic_glass.py` | `82A78DF04C22C630` |
| `probe_eevee_refraction.py` | `13947C0921C2FD2F` |
| `preview_magic_glass/glass_transparency_check.png` | `613E619D428D1C24` |
| `preview_magic_glass/sheet_glass_clear_vs_frosted.png` | `64D1D6CAD1586B83` |

## 本轮边界（如实说明）

已完成：程序化建模、三个 .blend 源、FBX/GLB 导出、几何自检（面数、包围盒、非流形、材质槽）、六张预览渲染、渲染后的读图复核。

未完成、也未宣称：

- 未导入 UE，未创建 UE 资产、材质实例或枪匠条目。
- 未绑定任何数值属性；不虚构重量、后坐力或属性加成。
- 未适配具体枪型，安装接口与 Ø34 mm 尺寸均为待确认提案。
- 预览由我渲染，但我本人没有肉眼看过：判读通过读图工具完成，属**定性**检查，不能替代用户验收。

## 待用户确认

1. 宿主枪型与安装位置（导轨下方、护木侧面、枪口段还是枪托配重位），以确定真实接口与朝向。
2. 球径是否需要调整（当前 Ø34 mm）；脚本里改 `BALL_RADIUS` 一行即可。
3. 三种配重的数值差异是否已有定义；有定义再接入枪匠数据。
4. 是否需要授权后续 UE 导入与图标制作。

## 备注

`render_previews.py` 会导入建模脚本，首次运行曾生成 `__pycache__/`；脚本已加 `sys.dont_write_bytecode`，且 `.gitignore` 第 17 行已忽略该目录。当前目录内仍留有一次运行时产生的 `__pycache__`，本机删除操作被策略拦截，未强制绕过，可手动删除。
