# 扩容弹匣 `ext_mag` 接入记录（2026-09-18）

M4A1 / AKM / QBZ-191 的弹匣槽选项 `ext_mag`：在原厂弹匣基础上加长 6 cm 的扩容件（+10 发、换弹 ×1.25、开镜耗时 +5%）。本页是接入状态记录；逐轮过程与回执在 `SourceAssets/ExtMagUniversal20260917/README.md`。**2026-09-18 第七轮**：用户实机反馈"191 与 M4 的弹匣建模错误、有错误截断"，查证为第五/六轮"切带复制"路线在接缝处必然错位（两环 1.8–2.5 mm 不共形，硬钉会把表面揉皱），已改为**弧管重建**（按弹匣自身切线切一刀，沿自身弧度推进 6 段生成延长管，首环复用切面顶点，接缝间隙 0）；FBX 与离线对位已完成，**UE 安装因编辑器被并行会话占用而待补**（见下）。AKM 仍是第四轮前的逐截面切线（拉伸带），属待统一项。

## 数据与选项

- `Content/ColdSteelData/gunsmith.json`：三把枪 `magazine` 槽都有 `ext_mag`，`stats = {mag_delta: 10, reload_mult: 1.25, ads_percent: 0.05}`，卡片只写基本描述，数值细节在右侧详情行按统一口径显示（见 [枪匠配件调参](gunsmith-attachment-details-20260917.md)）。
- 换弹沿用各枪原厂动画（`bDrumInstalled` 只认 `large_drum`），`UpdateDrumDropVisual` 对 `ext_mag` 早退，不做弹鼓掉落编排。

## 资产与运行路径

| 枪 | 运行网格 | 材质（＝该枪弹匣槽同一材质） | 造型来源 |
| --- | --- | --- | --- |
| M4A1 | `/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440` | `/Game/Weapons/M4InfimaV3/Magazine_Light_001`（＝该枪弹匣槽材质；2026-09-18 第五轮由 `M_M4_ext_mag` 改绑） | M4 原厂 PMAG 延长 6 cm |
| AKM | `…/SM_ExtMag_AKM40` | `/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR` | AKM 原厂 7.62 弯弹匣原位延长 6 cm |
| QBZ-191 | `…/SM_ExtMag_QBZ40` | `/Game/Weapons/QBZ191/Attachments20260913/Materials/M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`（＝该枪弹匣槽材质；2026-09-18 第四次收口改绑，见下） | QBZ 原厂 5.8 mm 弹匣延长 6 cm |

- 网格：三件都是**该枪原厂弹匣**的几何原样延长（UV0、法线、底板、刻字均为原厂），插入段与喉部完全未改，因此落位由原厂件本身保证。逐枪机匣涂层烘焙（`M_ExtMag_Finish_*`、`Textures/*`、`finish_install_receipt.json`）保留在磁盘作记录，**已被否决、不再引用**：小配件上的机匣贴图盒式投影在实机里呈花斑，用户判定"材质没统一"。
- 材质：直接绑该枪弹匣槽正在使用的同一材质（M4 为 MIC、QBZ/AKM 为 Material），白色刻字/磨损/金属分区与该枪原厂弹匣同源；回执 `factory_install_receipt.json`。
- 装配代码：`Source/FPSGAME/Weapons/M4DrumVisual.cpp` 的 `ext_mag` 分支，三枪统一座位路径（`seat_t⁻¹`，日志 `frame=weapon`；`EXT_MAG: attached …` 诊断串保留）。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/{ue_m4a1,ue_akm,ue_qbz191}_magazine_ext_mag.png`（专属图优先，共享图 `magazine_ext_mag.png` 作回退）。

## 落位约定（本轮定稿）

1. 直接延长**该枪自己的**原厂弹匣：插入段、喉部平面与座席一概不动，落位由原厂件本身保证，不需要按井口重建坐标系。
2. 三枪统一走「枪体坐标系资产 + `seat_t⁻¹` 座位」（已验收大弹鼓同一约定）。"资产写在插座系 + 座位恒等"在运行时会把配件摆到插座原点，实测离井口约 35 cm，已弃用。
3. 运行时骨架缩放 ×100，座位需带 `0.01` 补偿；用户日志 `EXT_MAG: attached … frame= rel_loc= rel_scale= world_extent=` 是落位判定的第一手证据。

## 状态

### 弧管重建（2026-09-18 第七轮）

- 构建：`Scripts/build_extmag_arc_tube.py` → `FBX/SM_ExtMag_{M440,QBZ40}_arc.fbx`，回执 `Reference/arc_tube_build.json`。M4 4.14 × 8.42 × 23.49 cm（切面法线与轴线夹角 3.55°、弧弯 5.27°、环 76 顶点）、QBZ 4.55 × 13.42 × 24.42 cm（13.74°、5.91°、环 313 顶点），两件 `seam_gap_mm = 0.000`。
- 离线对位审查：`Scripts/render_dupb_review.py` → `Reference/dupb_review_{M4,QBZ}_{factory,ext}_{side,front,top,bottom}.png`；延长件无横向错位、无接缝揉皱，弧线连续、底板在末端。
- 取舍：延长段为干净弧管、**不带肋纹**（原厂肋在切面处停止、在底板继续）；若要求肋纹连续需另行生成肋环。
- **已装入 UE**（22:16，运行中编辑器 MCP 直连）：读回 M4 `4.139 × 8.420 × 23.494 cm` / 5783 顶点 / 4372 三角 → `M4InfimaV3/Magazine_Light_001`；QBZ `4.551 × 13.421 × 24.424 cm` / 15618 顶点 / 11675 三角 → `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`。旧件备份在 `/Game/_ExtMagSuperseded/*_round5`，回执 `install_extmag_arc_receipt.json`；离线备选入口 `install_extmag_arc.py`。**未进游戏、未由用户实机验收**。

### 复制带重建 + UE 安装（2026-09-18 第五轮）

> 已被第七轮取代：该路线的接缝必然错位（用户实机看到"错误截断"），仅作废案记录。

M4/QBZ 的延长段从"拉伸带"改为"复制带"：切出一段**整数肋距**的干净带体（M4 1.212 cm、QBZ 0.819 cm 肋距），沿"下环→上环"的刚性变换整段复制到下方、删掉原底板段后焊接，**不拉伸任何顶点**；插入段与换弹抓握区保持原厂几何。构建脚本 `Scripts/build_extmag_duplicate_band.py`，数值见 `Reference/duplicate_band_build.json`，同机位对照 `Reference/dupb_{M4,QBZ}_{pair,band}.png`。

装入运行中的编辑器（MCP 直连）：旧件先备份到 `/Game/_ExtMagSuperseded/{SM_ExtMag_M440,SM_ExtMag_QBZ40}_round4`，再 `delete → import_file（复制带 FBX）→ set_material → save_assets`。读回：M4 `4.322 × 9.359 × 23.609 cm` / 5946 顶点 / 5359 三角、槽 `Magazine Light_001` → `M4InfimaV3/Magazine_Light_001`；QBZ `4.566 × 14.516 × 23.870 cm` / 12058 顶点 / 11867 三角、槽 `M_QBZ191_Wear_Magazine` → `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`。回执 `install_extmag_dupb_receipt.json`。

- M4 材质口径本轮统一：与原厂件同源（原厂弹匣原位延长、UV0 未改）→ 直接绑该枪弹匣槽材质，与 AKM/QBZ 一致；旧 `M_M4_ext_mag` 保留在磁盘但不再引用。
- **AKM 未并入本轮**：仍是逐截面切线渐入（带内表面被拉伸），弯弹匣的刚性复制需要绕曲率中心，尚未做。
- **未进游戏、未由用户实机验收**；`Saved/ExtMagEditor/*.png` 是第四轮图，对应已被替换的网格。

### 编辑器直连取证与 QBZ 材质改绑（2026-09-18 第四次收口）

上一轮的未做项（编辑器内视觉取证）已用运行中编辑器的 MCP 直连走完：三把枪的扩容弹匣与枪体都以原点恒等变换摆进关卡（等价于运行时"资产写在枪体坐标系 + socket 链座位"），黄昏关卡临时加一盏 SpotLight 打亮，逐枪拍"装扩容件 / 装原厂件"同机位两张对照；截图后删除全部临时 Actor 并恢复相机位姿。

判定结果：M4、AKM 落位与弧度通过、表面与原厂件同源；**QBZ 表面不合格**——机匣涂层烘到弹匣后，弹匣上出现机匣刻字/面板线摊成的黑斑，与原厂弹匣明显两种表面。已把 `SM_ExtMag_QBZ40` 的材质槽改绑**该枪弹匣槽正在用的材质**`M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`（该件本就是原厂弹匣本体原位延长、UV0 未改），保存成功、同机位复拍与原厂弹匣一致。

证据与实测数值见 [扩容弹匣资产记录](../../SourceAssets/ExtMagUniversal20260917/README.md) 第四次收口一节；图片在 `Saved/ExtMagEditor/`（`*_lit_side_right.png` 与 `*_factory_lit_side_right.png`、`*_cmp_*.png`）。

- AKM 改为**按弹匣自身曲率延长**（每截面沿局部切线渐入位移，闭合性与原厂一致），网格已写入正式资产；M4/191 材质改为**沿用已验收配件涂层路线**（M4 物理 UV + 复用 `M_M4_drum_1`；QBZ 机匣涂层烘焙 + 按 `import_coating.py` 克隆）。回执 `finish_install_accepted_receipt.json`。
- 游戏侧截图暂不可用：`FPSGAME.exe` 报 `Failed to initialize ShaderCodeLibrary`（`Content/ShaderCodeLibrary` 缺失），本轮以 Blender 同机位渲染（`Reference/akm_*`）替代，未做游戏内验收。
- **未由用户实机验收**：三枪观感、换弹跟随与图标显示由用户确认。
- 换弹接触：延伸段落在左手握点下方，几何上与原厂接触一致（握点为动画固定值、弹匣刚体挂在同一根骨骼）；如需精修仍需实机观察。
