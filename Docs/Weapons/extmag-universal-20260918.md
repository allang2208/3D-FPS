# 扩容弹匣 `ext_mag` 接入记录（2026-09-18）

M4A1 / AKM / QBZ-191 的弹匣槽选项 `ext_mag`：在原厂弹匣基础上加长 6 cm 的扩容件（+10 发、换弹 ×1.25、开镜耗时 +5%）。本页是接入状态记录；逐轮过程与回执在 `SourceAssets/ExtMagUniversal20260917/README.md`。

## 数据与选项

- `Content/ColdSteelData/gunsmith.json`：三把枪 `magazine` 槽都有 `ext_mag`，`stats = {mag_delta: 10, reload_mult: 1.25, ads_percent: 0.05}`，卡片只写基本描述，数值细节在右侧详情行按统一口径显示（见 [枪匠配件调参](gunsmith-attachment-details-20260917.md)）。
- 换弹沿用各枪原厂动画（`bDrumInstalled` 只认 `large_drum`），`UpdateDrumDropVisual` 对 `ext_mag` 早退，不做弹鼓掉落编排。

## 资产与运行路径

| 枪 | 运行网格 | 材质（＝该枪弹匣槽同一材质） | 造型来源 |
| --- | --- | --- | --- |
| M4A1 | `/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440` | `/Game/Weapons/M4InfimaV3/Magazine_Light_001` | M4 原厂 PMAG 延长 6 cm |
| AKM | `…/SM_ExtMag_AKM40` | `/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR` | AKM 原厂 7.62 弯弹匣原位延长 6 cm |
| QBZ-191 | `…/SM_ExtMag_QBZ40` | `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer` | QBZ 原厂 5.8 mm 弹匣延长 6 cm |

- 网格：三件都是**该枪原厂弹匣**的几何原样延长（UV0、法线、底板、刻字均为原厂），插入段与喉部完全未改，因此落位由原厂件本身保证。逐枪机匣涂层烘焙（`M_ExtMag_Finish_*`、`Textures/*`、`finish_install_receipt.json`）保留在磁盘作记录，**已被否决、不再引用**：小配件上的机匣贴图盒式投影在实机里呈花斑，用户判定"材质没统一"。
- 材质：直接绑该枪弹匣槽正在使用的同一材质（M4 为 MIC、QBZ/AKM 为 Material），白色刻字/磨损/金属分区与该枪原厂弹匣同源；回执 `factory_install_receipt.json`。
- 装配代码：`Source/FPSGAME/Weapons/M4DrumVisual.cpp` 的 `ext_mag` 分支，三枪统一座位路径（`seat_t⁻¹`，日志 `frame=weapon`；`EXT_MAG: attached …` 诊断串保留）。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/{ue_m4a1,ue_akm,ue_qbz191}_magazine_ext_mag.png`（专属图优先，共享图 `magazine_ext_mag.png` 作回退）。

## 落位约定（本轮定稿）

1. 直接延长**该枪自己的**原厂弹匣：插入段、喉部平面与座席一概不动，落位由原厂件本身保证，不需要按井口重建坐标系。
2. 三枪统一走「枪体坐标系资产 + `seat_t⁻¹` 座位」（已验收大弹鼓同一约定）。"资产写在插座系 + 座位恒等"在运行时会把配件摆到插座原点，实测离井口约 35 cm，已弃用。
3. 运行时骨架缩放 ×100，座位需带 `0.01` 补偿；用户日志 `EXT_MAG: attached … frame= rel_loc= rel_scale= world_extent=` 是落位判定的第一手证据。

## 状态

- 代码改动已就位；**编辑器占用导致收尾两步待办**：① 平滑过渡版 AKM 网格写入正式资产（当前正式资产为硬切换版，几何同为"AKM 原厂弹匣 +6 cm"），② 两个目标编译。
- **未由用户实机验收**：三枪观感、换弹跟随与图标显示由用户确认。
- 换弹接触：延伸段落在左手握点下方，几何上与原厂接触一致（握点为动画固定值、弹匣刚体挂在同一根骨骼）；如需精修仍需实机观察。
