# 扩容弹匣 `ext_mag` 接入记录（2026-09-18）

M4A1 / AKM / QBZ-191 的弹匣槽选项 `ext_mag`：在原厂弹匣基础上加长 6 cm 的扩容件（+10 发、换弹 ×1.25、开镜耗时 +5%）。本页是接入状态记录；逐轮过程与回执在 `SourceAssets/ExtMagUniversal20260917/README.md`。

## 数据与选项

- `Content/ColdSteelData/gunsmith.json`：三把枪 `magazine` 槽都有 `ext_mag`，`stats = {mag_delta: 10, reload_mult: 1.25, ads_percent: 0.05}`，卡片只写基本描述，数值细节在右侧详情行按统一口径显示（见 [枪匠配件调参](gunsmith-attachment-details-20260917.md)）。
- 换弹沿用各枪原厂动画（`bDrumInstalled` 只认 `large_drum`），`UpdateDrumDropVisual` 对 `ext_mag` 早退，不做弹鼓掉落编排。

## 资产与运行路径

| 枪 | 运行网格 | 材质 | 造型来源 |
| --- | --- | --- | --- |
| M4A1 | `/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_M440` | `M_ExtMag_Finish_M4` | 原厂 PMAG 延长，逐枪烘焙 M4 机匣涂层 |
| AKM | `…/SM_ExtMag_AKM40` | `M_ExtMag_Finish_AKM` | 同上（AKM 侧按插座系写法） |
| QBZ-191 | `…/SM_ExtMag_QBZ40` | `M_ExtMag_Finish_QBZ191` | QBZ 原厂 5.8 mm 弹匣延长 |

- 网格：UV0 保留原厂结构 UV（结构法线/AO 采样基础），索引 1 为涂层 UV `MagazineCoatUV`（2048² 盒式投影烘焙，物理尺度 M4/QBZ 12×5 cm、AKM 12×2.5 cm，详见 `Reference/finish_bake.json`）。
- 材质：克隆该枪弹匣槽宿主材质后改采涂层 UV，白色刻字用原底色亮度遮罩保留；元数据 `WeaponFinishReference` / `WeaponFinishCoatingUV`，回执 `finish_install_receipt.json`。
- 装配代码：`Source/FPSGAME/Weapons/M4DrumVisual.cpp` 的 `ext_mag` 分支（正式资产名，座位按帧约定；`EXT_MAG: attached … frame=` 诊断串保留）。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/{ue_m4a1,ue_akm,ue_qbz191}_magazine_ext_mag.png`（专属图优先，共享图 `magazine_ext_mag.png` 作回退）。

## 落位约定（本轮定稿）

1. 把配件几何直接表达在该枪的挂点/枪体坐标系里，出井方向与喉部原点写在资产上（本项目原厂弹匣 100% 蒙皮在 `WPN_SOCKET_Magazine`，插座本身在井口下方 5.7–12.1 cm 且轴倾斜 7.1–22.5°，所以「资产按插座系摆放 + 座位恒等」必然错位）。
2. M4/QBZ 走「枪体坐标系资产 + 插座绑定逆」；AKM 走「插座坐标系资产 + `identity/零位移/单位缩放补偿`」（与已验收大弹鼓同一约定）。
3. 运行时骨架缩放 ×100，座位需带 `0.01` 补偿；夹具日志 `Saved/DrumGripAudit/canon_*.log` 记录三枪 `frame / rel_scale / world_extent`。

## 状态

- 两个目标（Editor/Game）已编译；正式资产、材质、图标已落盘。
- **未由用户实机验收**：三枪观感、换弹跟随与图标显示由用户确认。
- 换弹接触：延伸段落在左手握点下方，几何上与原厂接触一致（握点为动画固定值、弹匣刚体挂在同一根骨骼）；如需精修仍需实机观察。
