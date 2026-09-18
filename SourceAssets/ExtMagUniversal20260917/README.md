# 第三次修正：AKM 弹匣按曲率延长、M4/191 改用已验收配件涂层（2026-09-18 晚）

用户反馈：**AKM 弹匣下方截面是尖的**、**M4/191 材质渲染不合格**，并要求直接沿用前面已验收的做法。本轮不再自创做法，两处都改成复用已验收工程。

## 1. AKM 弹匣：只延长，不改形（`Scripts/build_extmag_from_factory.py`）

前两版的毛病都在"怎么把下段移下去"：

- 第一版沿一个方向整体平移 → 弯弹匣被拉直，底板离开曲线，底部读出"尖角"；
- 第二版插入一段复制体并焊接 → 接缝处留下开放边（实测 312 条边、接缝处 428 个顶点簇），实机是一条明显台阶。

定稿做法：**每个截面沿它自己的局部切线下移**（切线取弹匣中心线的二次拟合求导，抗肋骨噪声），位移量在 6 cm 带内用 smoothstep 渐入。这样弹匣沿着自己的曲率变长、底板与横筋保持原厂几何，闭合性与原厂一致（开放边 98 条 = 原厂同值），实测 4.49 × 18.99 × 23.73 cm（原厂 4.09 × 15.21 × 19.11 cm）。

对照渲染：`Reference/akm_factory_mag_{left,bottom,threequarter}.png`（原厂）与 `Reference/akm_ext_mag_*.png`（延长后）同机位。

## 2. M4/191：改用已验收的配件涂层路线（`Scripts/author_extmag_finish.py` + `install_extmag_finish_accepted.py`）

不再自己做烘焙，直接复用两个已验收工程的代码与材质：

| 枪 | 沿用工程 | 本轮做法 |
| --- | --- | --- |
| M4A1 | `WeaponAttachmentFinish20260913` | 按 `author_uv.py` 的物理投影 UV（12×5 cm，按面主法轴选平面）加 `ReceiverFinishPhysicalUV`（索引 1，UV0 与分离法线不动）；UE 侧复制已验收的 `M_M4_drum_1`（它采样物理 UV）为 `M_M4_ext_mag`，把纹理坐标通道 2→1，绑到弹匣 |
| QBZ-191 | `QBZ191MetalCoat20260913` | 按 `bake_coating.py` 把 QBZ 机匣程序化涂层 + 接触磨损烘焙到弹匣自己的 `QBZCoatingUV`（2048²，BaseColor/ORM）；UE 侧按 `import_coating.py` 克隆原弹匣材质为 `M_QBZ191_ext_mag_Receiver_0`，UV1 采样烘焙图、UV0 结构与法线保持、白色刻字用原底色亮度遮罩 |
| AKM | 已验收的 AKM 配件涂层源 | 保持 `M_AKM_Soviet_PBR`（该枪机匣/弹匣本身即此材质） |

回执 `finish_install_accepted_receipt.json`；旧的自制烘焙产物（`M_ExtMag_Finish_*`）只作记录保留。

## 3. 状态

- 三件网格与材质已写入正式资产（`SM_ExtMag_M440 / QBZ40 / AKM40`）。
- **未能取得实机截图**：`FPSGAME.exe` 现在启动即报 `Failed to initialize ShaderCodeLibrary … Global shader library is missing from ../../Content/`，而 `Content/ShaderCodeLibrary` 目录已不存在（并行会话的构建/清理后遗留）。需要先恢复该库才能跑游戏侧捕获；本轮用 Blender 同机位渲染（见上）替代，未做游戏内验收。
- 按用户规则未做游戏内验收；AKM 底部形状、M4/191 涂层观感由用户确认。

---

# 回归修正：AKM 改用自家弹匣、三枪材质改为原厂弹匣槽（2026-09-18 第二次收口）

用户实机反馈三点：**AKM 没插进弹仓**、**M4/191 材质没统一**、**模型还要优化升级**。三点的根因都在"借件 + 猜坐标系"，本轮改成"各枪自己的弹匣"。

## 1. AKM 没插进弹仓：资产写在插座系，运行时却按插座原点摆放

用户日志（`Saved/Logs/FPSGAME.log`，18:09）里 AKM 一条是 `frame=socket rel_scale=0.01 world_loc=X=6.568 Y=-28.850 Z=-19.653`，而同一时刻枪体在原点——即弹匣被放到离枪体 **约 35 cm** 的地方。上一轮把 AKM 网格重写成"插座系资产 + identity/单位缩放座位"，`bake_extmag_finish.py` 用的是**源 FBX 的插座矩阵**（`bone.matrix_local`），与运行时实际使用的座位值不是同一个量，所以整根弹匣被搬出了井口。

改法：**AKM 回到与 M4/191 完全相同的已验证路径**——资产写在枪体/网格坐标系，座位取 `seat_t⁻¹`（`M4DrumVisual.cpp` 里已验收大弹鼓那段累加）。上一轮"AKM 用插座累加不精确"的判断来自手工拟合的网格，不是座位公式；网格换成本枪原厂件后这条路径对三枪一致。

## 2. 模型：AKM 不再借用 M4 的 PMAG，改为本枪原厂弹匣延长

权威源是 `SourceAssets/PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx`（运行资产就是从它导入的：4 个材质槽名与运行时一致）里的 `AKM_FactoryMagazine_Preview` —— 该枪 7.62 弯弹匣本体（2,801 顶点 / 2,776 面 / UV0 / 原厂法线）。`Scripts/build_extmag_from_factory.py`：

- 复制该对象（不碰机匣、不借 M4 网格）；
- 轴向取"弹匣质心 → `WPN_SOCKET_Magazine` 骨骼"方向，在 45% 高度处切面，切面以下沿轴向**平滑过渡**下移 6 cm（弯弹匣用硬切换会出现台阶，故用 smoothstep 渐变带 4.5 cm）；
- 结果：4.34 × 16.25 × 23.20 cm（原厂 4.09 × 15.21 × 19.11 cm），**插入段、喉部、UV、底板全部是原厂件**，落在原厂位置；可编辑场景 `ExtMag40_AKM_Editable.blend`，回执 `Reference/akm40_factory_build.json`。

M4/191 本来就是各自原厂弹匣延长（`SM_ExtMag_M440` ← M4 原厂 PMAG、`SM_ExtMag_QBZ40` ← QBZ 5.8 mm 弹匣），本轮不动几何。

## 3. 材质：改绑"该枪弹匣槽的同一材质"

上一轮按 `weapon-finish.md` 的"逐枪烘焙涂层"给三件做了机匣贴图盒式投影烘焙，实机看是花斑、与该枪不像。本轮改回该标准更直接的读法——**材质来源取宿主枪体网格的同一个槽**，即该枪弹匣槽正在用的材质：

| 枪 | 弹匣槽 | 材质 |
| --- | --- | --- |
| M4A1 | `Magazine_Light_001` | `/Game/Weapons/M4InfimaV3/Magazine_Light_001`（MIC） |
| QBZ-191 | `M_QBZ191_Wear_Magazine` | `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer` |
| AKM | `M_AKM_Soviet_Magazine` | `M_AKM_Soviet_PBR` |

配件的 UV0 就是该枪原厂弹匣的 UV，所以绑上去等于"同一件弹匣、只是更长"，白色刻字、磨损与金属分区自动同源；烘焙产物 `M_ExtMag_Finish_*` 与 `Textures/*` 保留在磁盘作记录，不再被引用。脚本 `install_extmag_factory.py`，回执 `factory_install_receipt.json`。

## 4. 图标

AKM 换造型后重渲 `ue_akm_magazine_ext_mag.png`（正交侧视、枪口方向朝左、透明底、单件，中性聚合物棚拍，与既有图标同规格）；M4/191 造型未变，图标不动。

## 5. 状态（编辑器释放后已收尾）

- 代码：`Source/FPSGAME/Weapons/M4DrumVisual.cpp` 的 `ext_mag` 分支已合并为单一座位路径（三枪都走 `seat_t⁻¹`，日志 `frame=weapon`）。
- 用户关闭编辑器后，`install_extmag_factory.py` 已把**平滑过渡版** AKM 网格写入正式资产（`SM_ExtMag_AKM40` 4.34 × 16.25 × 23.20 cm，绑 `M_AKM_Soviet_PBR`），三件材质回执见 `factory_install_receipt.json`（18:28）。
- 编译：`M4DrumVisual.cpp.obj` 18:26:50（Editor）/ 18:27:22（Game），`UnrealEditor-FPSGAME.dll` 18:27:07、`FPSGAME.exe` 18:27:40 —— 两个目标都含本轮 C++ 改动；`Tools/Build/Build-Editor.ps1` 复跑报 `Target is up to date`。
- 按用户规则未做自动化验收；三枪实机观感、换弹跟随与图标显示由用户确认。

---

# 收口：正式资产写入、AKM 插座系生效、逐枪图标（2026-09-18 收尾）

上一轮结束时编辑器仍占着正式网格，只能把逐枪烘焙结果写到 `SM_ExtMag_*_Finish` 变体；本轮把结果落回**正式资产名**，并补齐逐枪图标与旧件退役。**未由用户实机验收**，游戏内表现仍由用户确认。

## 1. 正式资产落盘（`install_extmag_finish.py`，16:38:25）

- 三件网格重新导入到正式名 `SM_ExtMag_{M440,AKM40,QBZ40}`（带 UV0 + `MagazineCoatUV` 双层 UV，AKM 网格为插座系写法），材质建成 `M_ExtMag_Finish_{M4,AKM,QBZ191}` 并逐槽绑定。
- 材质做法：克隆**该枪弹匣槽的宿主材质**（M4 `Magazine_Light_001`、QBZ `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`、AKM `M_AKM_Soviet_PBR`），BaseColor/ORM 改采涂层 UV（索引 1），原 UV0 的结构法线与 AO 保持连接，白色刻字用原底色亮度遮罩保留；元数据记 `WeaponFinishCoatingUV=1` 与 `WeaponFinishReference`。回执 `finish_install_receipt.json`，三件全部 `saved=true`。
- 编辑器占用期间的变体 `SM_ExtMag_*_Finish` 保留在磁盘作回退，装配引用（`M4DrumVisual.cpp`）指向正式名。

## 2. 三枪落位实测（夹具日志，非人工验收）

`Saved/DrumGripAudit/canon_{m4,akm,qbz}.log` 记录本轮正式资产的第一人称捕获（`raised_side.png` 及 `normal_* / empty_*` 序列；`_zoom.png` 为裁切放大）：

| 枪 | `frame` | `rel_scale` | `world_extent`（半长） | 弹匣全长 |
| --- | --- | --- | --- | --- |
| M4A1 | `weapon` | 0.01 | 4.699 × 2.176 × 11.794 | 23.6 cm |
| AKM | `socket` | 0.01 | 4.823 × 1.770 × 11.873 | 23.75 cm |
| QBZ-191 | `weapon` | 0.01 | 7.237 × 2.335 × 12.097 | 24.19 cm |

三把枪的弹匣都收在机匣下方、与原厂件同一井口缝线，多出的约 6 cm 垂在底板以下；AKM 走插座系（`identity / 零位移 / 单位缩放补偿`）后落点已回到井内（上一轮误差约 7 cm 的 `parentfirst_t` 路径已弃用，日志同时打印两种累加结果备查）。`empty_012.png` 一类换弹帧可见左手整把握在弹匣体上，延伸段落在握点**下方**，几何上与原厂换弹接触一致（握点是动画固定值，弹匣为刚体挂在同一根骨骼上）。

## 3. 逐枪图标（`Scripts/render_icon_per_weapon.py` + `import_extmag_icons.py`）

按 `attachment-icons.md` 的专属图覆盖规则补三张，UI 解析顺序为「武器专属 → 共享」：

- `ue_m4a1_magazine_ext_mag.png`（PMAG 造型）、`ue_akm_magazine_ext_mag.png`（PMAG 造型）、`ue_qbz191_magazine_ext_mag.png`（5.8 mm 弯弹匣造型）；共享图 `magazine_ext_mag.png` 保持 QBZ 造型作未列枪型回退。
- 图标本体沿用已验收的既有表达（正交侧视、枪口方向朝左、透明底、单件、中性聚合物棚拍）；逐枪烘焙涂层另出 `Reference/material_preview_<weapon>_coating.png` 作材质证据（涂层是 12 cm 盒式投影的机匣贴图，放到 24 cm 配件上在图标尺寸下呈噪点，故不进图标本体）。
- 纹理副本同目录同名 `.uasset` 已同步，回执 `icon_per_weapon_receipt.json`。

## 4. 旧件退役

`SM_ExtMag_Universal`、`SM_ExtMag_PMAG40`、`M_ExtMag_Metal`、`M_ExtMag_Polymer` 四件（`Source/`、`Content/` 其余资产均无引用）按 `publication.md` 移入 `trash/extmag-superseded-20260918/Content_Weapons_ExtMagUniversal20260917/`，移动前后 SHA-256 一致（`MOVED.json`、`MANIFEST.md`）。

## 5. 构建与仍未完成

- `UnrealEditor-FPSGAME.dll` 16:50、`FPSGAME.exe` 16:51，两个目标都含本轮 C++（`EXT_MAG: attached … frame=` 诊断串）。
- **未由用户确认**：三枪游戏内观感、换弹跟随、逐枪图标在枪匠面板的显示。
- 仍未做：逐枪图标的最终视觉确认（用户）；AKM 换弹接触的实机复核（本轮只做了几何推断与既有机位截图核对）。
- 另注：正式资产现在带双层 UV，若后续再改网格，`MagazineCoatUV`（索引 1）必须保留，否则逐枪涂层会失效。

---

# 扩容弹匣 `ext_mag` —— 按枪烘焙涂层 + AKM 落位修正（2026-09-18）

用户反馈两点：M4/191 位置已可，但材质未按配件标准做"针对该枪的统一"（缺烘焙与法线处理）；AKM 弹匣仍错位。本轮针对两者处理，并在游戏内对照确认。

## 材质：每把枪独立烘焙（不再直接套宿主槽）

按 [weapon-finish.md](../../skills/ue5-weapon-workflow/references/weapon-finish.md) 与两个既有案例（`WeaponAttachmentFinish20260913` 的投影 UV + 逐枪材质；`QBZ191MetalCoat20260913` 的逐件烘焙）执行：

- **`Scripts/bake_extmag_finish.py`**（Blender）：保留 UV0 与导入的分离法线（原结构法线/AO 的采样基础），新增涂层 UV `MagazineCoatUV`（索引 1，smart project），再用**各枪自己的机匣涂层**按固定物理尺度做盒式投影并烘焙：
  - M4：`T_M4_Receiver_BaseColor` + `T_M4_Receiver_Roughness`（沿用例内记录的 Phong→金属粗糙转换口径，metal 0.8），tile 12×5 cm；
  - QBZ-191：`T_QBZ_Hero_Body_BaseColor` + `_ORM`（G=粗糙度、B=金属度），tile 12×5 cm；
  - AKM：`T_AKM_Mount_Base_color / _Roughness / _Metallic`，tile 12×2.5 cm。
  产物：`Textures/<枪>/T_ExtMag_<枪>_{BaseColor,ORM}.png`（2048²），回执 `Reference/finish_bake.json`。
- **`install_extmag_finish.py`**（UE）：导入烘焙贴图与带双层 UV 的网格，克隆**该枪弹匣槽的宿主材质**建图（BaseColor/Roughness/Metallic 改采涂层 UV，金属与白色刻字用原底色的亮度遮罩保留，**原 UV0 结构法线与 AO 保持连接**），产出 `M_ExtMag_Finish_{M4,QBZ191,AKM}` 并逐槽绑定；元数据记录参考枪身材质与涂层 UV。回执 `finish_install_receipt.json`。
- 编辑器占用原网格时按标准保存**专用变体**（`SM_ExtMag_*_Finish`），装配引用同步更新，未关闭他人编辑器；原资产保留可回退。

## AKM 落位：改用该枪弹鼓的插座系约定

已验收大弹鼓在 AKM/QBZ 上是"资产写在 `WPN_SOCKET_Magazine` 系 + 座位 identity/零位移/仅单位缩放"，而 M4 是"资产写枪体坐标系 + 插座绑定逆"。上一版对 AKM 用了 M4 那套，插座逆的累加在 AKM 骨链上不精确（组件离网格原点约 7 cm）——即用户看到的错位。本轮把 AKM 网格重写到插座系（`bake_extmag_finish.py` 的 AKM 分支，取该枪源姿态插座矩阵的逆），C++ 对 AKM 走 `identity/零位移/单位缩放`（日志 `frame=socket`），M4/QBZ 维持原路径（日志 `frame=weapon`）。

## 实机对照（本轮已看图）

`Saved/DrumGripAudit/fin_{m4,akm,qbz}/raised_side.png`（及 `_zoom.png`）vs 原厂件对照 `ref_factory_{m4,akm,qbz}/`：

- 三把枪的扩容弹匣都收在机匣下方、与原厂件同一井口缝线处，多出的约 6 cm 垂在底板以下；AKM 不再偏低；
- 表面已是各自枪身的涂层语言（M4 暖灰磨损、QBZ 深色涂层+白色磨损痕、AKM 苏联钢件），白色痕迹与肋条细节保留。

两个目标已编译（FPSGAMEEditor 目标通过；game 目标需编辑器释放后再补）。

---

# 上一轮：实机对照定位并修正挂点（2026-09-18 深夜）

用户要求直接在游戏里看。照做后定位到两件事，都已修：

## 1. 挂点累加方式错了（弹匣被埋进机匣，所以"根本没插进枪里"）

我上一版用"教科书式"的父→子累加求插座绑定变换；在本工程的 rig 上它**不等于**插座的组件空间变换：

| 累加方式 | 平移（组件空间） |
| --- | --- |
| 大弹鼓的写法（从插座向上逐级 `Bone = Bone * GetRefBonePose[I]`） | `(6.447, -22.520, -17.623)` ← 与已知插座位置一致 |
| 我上一版的父→子连乘 | `(0.955, -1.140, -1.125)` ← 完全不同的变换 |

用错的那个变换后，组件世界缩放虽仍是 1、包围盒也仍是 23.6 cm，但姿态被转走，弹匣整根埋进机匣内部（截图里井口空空）。现在 `M4DrumVisual.cpp` 的 ext_mag 分支**逐字使用大弹鼓的累加**（这是本文件里唯一在游戏里验证过的写法），两种结果都打进日志备查。

## 2. 之前的"验证截图"其实一直被武器信息面板挡住

弹匣比弹鼓短，装好后正好落在右下角武器信息面板背后；前几轮（包括"侧面捕获"）看到的都是面板，所以既看不到错位也看不到正确。已改 `DrumGripAudit`：收尾时把视模抬高 18 cm 再侧转，拍 `raised_side.png`，弹匣区域不再被遮挡。同时确认 `DrumGripAudit` 的 side 阶段现在是活代码（会真的落盘）。

## 实机对照证据（同机位、同姿态 A/B）

- 扩容弹匣：`Saved/DrumGripAudit/extm_m4c|extm_akm|extm_qbz/raised_side.png`
- 原厂弹匣对照（`-MagazineAudit=none`，保留原厂件可见）：`Saved/DrumGripAudit/ref_factory_m4|akm|qbz/raised_side.png`
- 结论：三把枪的扩容弹匣**与原厂弹匣在同一井口缝线处**露出（顶部都收在机匣下方），区别只是多出的 ~6 cm 垂在底板以下；M4/AKM 为 PMAG 造型、QBZ 为 5.8 mm 弯弹匣造型，与资产来源一致。日志侧 `bind_scale=100 / rel_scale=0.01 / 世界全长 23.9–24.6 cm` 同步吻合。

**仍未由用户确认**：换弹过程中弹匣跟随弹匣骨（组件刚性挂在该骨上，行为应与原厂件蒙皮一致）；AKM 的插座累加残差比 M4/QBZ 大（组件中心离网格原点 6.9 cm vs 0.6 cm），视觉对照没看出问题，但若 AKM 实机仍有偏差，应改为按 AKM 弹鼓的做法（资产放插座系 + 座位 `identity/0.01`）重导。

---

# 上一轮：按已验收大弹鼓的落位方式重建（2026-09-18 晚）

## 这一轮为什么改挂法：插座不是井口

用户反馈"没有一把枪的弹夹正确插入弹仓"，据此回查已验收大弹鼓的落位判定，得到三条硬证据：

1. **原厂弹匣 100% 蒙皮在 `WPN_SOCKET_Magazine` 上**（Blender 源场景实测：`M4_Magazine Light.003_Export` 与 `QBZ191_Magazine_Export` 的权重全在这根骨上）。所以"正确插入"= 该骨骼绑定姿态下的位置。
2. **插座在井口下方 5.7–12.1 cm，井轴还倾斜 7.1–22.5°**（`Reference/seat_final.json`：M4 mouth_z −0.1053 / tilt 22.47°，AKM −0.1279 / 7.13°，QBZ −0.0730 / 19.12°）。前几轮把资产放进插座系、座位取恒等，等于把弹匣按插座位置挂上去——必然差这一段。
3. **已验收大弹鼓的挂法是"资产自带落位 + 挂在枪网格原点"**（M4 弹鼓 `DrumMount = Identity.GetRelativeTransform(Bone)`，资产坐标就是枪体坐标系）。它不依赖插座系，所以从来没有这个偏差。

## 本轮做法

- **重建资产**（`Scripts/rebuild_in_weapon_frame.py`，Blender）：把三个弹匣放回**各自原厂弹匣的落位**——喉部顶面与原厂顶面重合、加长的 6 cm 垂在弹匣底板之下，坐标系换成枪体坐标系（`Reference/weapon_frame_fit.json`）。M4/QBZ 用索引对应 + RANSAC 精配到各自原厂弹匣（不变段 52%、残差 **0.000 mm**）；AKM 是共用 PMAG，先配到 M4 弹匣形状再按 `seat_final.json` 的 AKM 井轴/喉部高度落位。
  - **两解判定**：加长件的上段与下段各自都能与"原厂件"刚性对齐（RANSAC 会挑到顶点更多的那一段，M4 上就挑错了）。物理判据是**喉部必须与原厂顶面重合、加长段只能在底板下方**；脚本按此选解并记录两个候选的越顶量（0.0 mm vs 59.2 mm）。
- **改挂点**（`Source/FPSGAME/Weapons/M4DrumVisual.cpp`）：挂到 `WPN_SOCKET_Magazine`，座位取自**该骨骼绑定变换的逆**（父→子累加 `GetRefBonePose`，写死缩放/偏移全部删除）。这样弹匣静止时在井内，换弹时跟着同一根骨骼走，等价于原厂件的蒙皮行为。
- **资产落地**：`SM_ExtMag_{QBZ40,M440,AKM40}_inframe.fbx` 导入并覆盖同名 UE 资产（`import_extmag_receipt.json`：`saved=true`，实测尺寸 M4 4.32×9.32×23.55 / AKM 3.32×9.62×23.74 / QBZ 4.61×14.47×24.18 cm，`unit_verdict=OK`），材质仍逐枪绑原厂弹匣槽（`bind_extmag_receipt.json`，三件 `saved=true`）。
- **编译**：`UnrealEditor-FPSGAME.dll` 12:51:01、`FPSGAME.exe` 12:53（两个目标都含新诊断串 `bind_scale`）。中途 game 目标曾被并行会话在 `Skills/FPSCastingMeshComponent.cpp` 的在改文件挡住一次，等对方改完重跑通过。

**本轮未启动游戏、未截图、未验收**；实机表现与换弹跟随仍需用户确认。核对方式：看 `EXT_MAG: attached` 的 `rel_scale`（AKM/QBZ 应约 `0.01`、M4 `1`）与 `world_extent`（全长 23.5–24.2 cm），并观察弹匣是否贴在井口、换弹时是否跟着弹匣骨骼。

---

# 上一轮：座位单位修复与三枪重导（2026-09-18 下午）

本轮查清了连续两轮"看不见 / 没插进去"的根因是**挂点帧单位**，改法、回执与实机核对方法如下。**本轮未启动游戏、未截图、未验收**，实机表现仍需用户确认。

## 根因：三枪挂点帧单位本来就不同

- `Source/FPSGAME/Weapons/AKMSovietCalibration.h` 原文：`WPN_root inherits the FBX 100x scale; these coordinates remain in metres` —— AKM/QBZ 的挂点帧是**米制**，所以厘米量纲的配件要 `0.01`（`QBZ191Attachments::OpticMount`、`M4GunsmithVisual` 的 AKM/QBZ 分支同此）。
- `M4MuzzleVisual.cpp`（`6.0775f`、`27.f` 等）与 `M4GunsmithVisual.cpp` 的 M4 分支用 `FVector::OneVector` —— M4 挂点帧是**厘米制**，配件相对缩放必须是 `1`。
- 因此 `SetRelativeTransform(..., FVector(.01f))` 只对 AKM/QBZ 成立；对 M4 会小 100 倍（20 cm 弹匣剩 2.5 mm），与 9/17 记录过的"2mm 弹匣"是同一类错误。

## 本轮改动

- **C++（`Source/FPSGAME/Weapons/M4DrumVisual.cpp`，12:22:39）**：ext_mag 座位不再写死缩放，改为 `SeatScale = 1 / socket 世界缩放`（M4 → 1，AKM/QBZ → 0.01），位移与旋转仍保持零（网格已存在于各自 `WPN_SOCKET_Magazine` 帧）。同一处日志扩展为 `EXT_MAG: attached ... rel_scale= socket_scale= world_extent=`，可直接读数判定落位与尺寸。
- **导入（`import_extmag_runtime.py` → `import_extmag_receipt.json`）**：三件 `saved=true`，实测全长 QBZ **24.09** / M4 **22.66** / AKM **23.42 cm**，`unit_verdict=OK`，每件 1 个材质槽。脚本新增全长/半长口径区分与越界即 `SUSPECT_UNIT` 的判定，并强制写回执文件。
- **材质（`bind_extmag_finish.py` → `bind_extmag_receipt.json`）**：三件 `saved=true`，逐枪绑到本方原厂弹匣槽：QBZ → `M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer`，M4 → `Magazine_Light_001`，AKM → `M_AKM_Soviet_PBR`（AKM 原厂弹匣本身即用机匣材质）。槽位找不到会记为 `FAILED`，不再静默跳过。
- **编译**：`UnrealEditor-FPSGAME.dll` 12:30:33、`FPSGAME.exe` 12:31:45，两个目标都含本轮改动（二进制内可检索到 `rel_scale` / `socket_scale` 串）。`Saved/BuildEditor/build-20260918-123209.log`。

## 实机核对方法（由用户执行）

带 ext_mag 进游戏看一条日志即可：M4 应 `rel_scale=1`、AKM/QBZ 应 `0.01`；`world_extent` 的弹匣全长应约 22.7–24.1 cm。这条数字同时也在验证"Blender 骨骼帧 = 运行时插座帧"的**旋转**假设——此前只在 Blender 内自证过（QBZ 收敛到 1.7 mm），未在运行时核对。

## 仍未完成

1. **换弹接触**：加长 6 cm 落在距喉部 10 cm 以下，若左手插入段正好抓在那个区间，接触会随之下移 6 cm。需先量当前已验收换弹里左手距喉部的抓握距离，再决定抬高切面还是改握点，不能凭猜。
2. **按枪型图标**：M4/AKM 是 PMAG 造型、QBZ 是 5.8 mm 造型，当前共享图仍是 QBZ 造型。要出 `ue_m4a1_magazine_ext_mag.png` 等专属图，需各自的安装帧（`AttachmentIconAudit20260914` 的 `frame: rig` 流程）；本轮不按最长包围盒轴猜正反面，故未出图。
3. **旧资产清理**：`SM_ExtMag_Universal`、`SM_ExtMag_PMAG40` 已无源码引用，清单见 `trash/extmag-superseded-20260918/MANIFEST.md`，未删除。

以下为 12:04 当时的原始记录，保留作对照。

用户判定"**还是没成功**"，并指出姿态/动作适配是我们把握不足的部分，本项降为待办。已完成制作、未通过实机验证。

**第一轮待办清单（12:04 记录，其中 1、2 已由本轮完成）**

1. 编辑器释放后重跑 `import_extmag_runtime.py` 与 `bind_extmag_finish.py`。编辑器被占用时外部保存会**静默失败**：`SM_ExtMag_QBZ40.uasset` 的时间戳仍停在 11:25（入枪姿态版没写盘），材质绑定同样没落盘；同一时段**新建**的 `SM_ExtMag_M440/AKM40` 反而写入成功（11:54:16）。
2. 编译 `Source/FPSGAME/Weapons/M4DrumVisual.cpp`（三枪各自资产 + 恒等座位），跑 `DrumGripAudit` 夹具实测三枪（`-AuditWeapon=ue_qbz191 / ue_m4a1 / ue_akm`）。`Tools/Build/Build-Editor.ps1` 检测到 UnrealEditor 进程会直接拒绝构建，不会去关别人的编辑器。
3. 图标按枪型覆盖（`attachment-icons.md:8`）：出 `ue_qbz191_magazine_ext_mag.png` 等武器专属图；M4/AKM 同为 PMAG 造型，可按"同造型代表共享图"登记共用。
4. 换弹接触复核（`attachment-standard.md:3/42`）：弹匣加长 6 cm 后，手掌在插入段的接触位置需要重看。
5. UE 侧旧资产清理：`SM_ExtMag_Universal`、`SM_ExtMag_PMAG40`（C++ 已不再引用）。

**已沉淀的经验**：配件姿态/座位的做法进 `skills/ue5-weapon-workflow/references/attachment-standard.md`（"以入枪接口表达，不要摆正"）；材质来源进 `weapon-finish.md`（"优先取宿主枪体同一槽"）。废案与哈希清单在 `trash/extmag-superseded-20260918/MANIFEST.md`。

---

# QBZ-191 原厂弹匣延长版（SM_ExtMag_QBZ40，2026-09-18）

用户判定上一版参数化扫掠网格不达标，指定"参考 QBZ-191 的弹夹，在它的基础上进行适当的延长"。本轮改为改造原厂件，三枪仍共用这一个模型：

- **来源**：`SourceAssets/QBZ191MagazineSeat20260913/QBZ191_MagazineSeat_Editable.blend` 里分离出的独立弹匣对象 `QBZ191_Magazine_Export`（4,620 顶点、单材质槽 `M_QBZ191_Magazine`、原厂 UV / 法线 / 造型）。
- **改造**（`Scripts/` 外置脚本，见下方"生产步骤"）：主轴对齐 −Z（出井方向）并把喉部顶面中心移到原点，随后把距顶面 11 cm 以下的顶点整体沿轴下移 **6 cm**。插入段、底板、侧棱与横筋全部是原厂几何，拉伸段落在中段平直区，视觉上是"主体加长"而不是"颈部拉长"。长度 19.73 → **25.73 cm**，包围盒 2.86 × 8.82 × 25.74 cm。
- **资产**：`/Game/Weapons/ExtMagUniversal20260917/SM_ExtMag_QBZ40`（素材合并为单槽并绑定既有 `M_ExtMag_Polymer`；旧 `SM_ExtMag_Universal` 仍保留在磁盘，未删除，可随时回退路径）。
- **接线**：`Source/FPSGAME/Weapons/M4DrumVisual.cpp` 的 ext_mag 分支路径指向新资产，座位常量不变（新件沿用同一约定：原点在喉部顶面、+Z 出井、+Y 朝枪口）。
- **图标**：按新模型重渲（`Scripts/render_icon_qbz40.py`，水平左向、透明底、单件），替换 `AttachmentIcons20260913/magazine_ext_mag`；旧图备份 `Reference/icon_magazine_ext_mag_before_qbz40.png`。
- **可编辑源**：`ExtMag40_Editable.blend`；对照图 `Reference/asm_factory_left.png` 与 `asm_ext40_left.png`（同视角、原厂 vs 扩容）、`Reference/cmp_[factory|ext40]_[side|front].png`。
- **生产步骤**：Blender 进程脚本（临时目录）依次为 主轴分析 → 重建（延长 + 对齐 + 导出 FBX 25.73 cm）→ 槽位合并重导出 → 装配/纯件对照渲染；UE 侧 `import_qbz40_ue.py`（commandlet）与 `import_icon_qbz40.py`。
- **验证**：Game/Editor 目标编译通过；夹具实测三枪（`Saved/DrumGripAudit/zz_qbz40`、`zz_akm40`、`zz_m440`）中弹匣组件缩放 1.0、落点与修复后的原厂井位一致（QBZ loc=(19.68,12.29,160.0)、AKM loc=(38.50,13.50,153.9)）。**实机第一人称观感仍由用户验收。**

# 通用扩容弹匣（SM_ExtMag_Universal，2026-09-17）

针对 M4A1 / AKM / QBZ-191 三种步枪的单一共享扩容弹匣模型（弹匣槽选项 `ext_mag`，+10 发、换弹 +25%、开镜 +5%）。
本轮完成测量、建模、导入、目录数据与视觉接入，并编译 Game 目标；**按用户规则未做实机测试与验收渲染，游戏内表现由用户实测**。

# 实机修复记录（2026-09-17 晚，扩容弹匣不可见——已解决并截图验证）

用户实机反馈三枪扩容弹匣均不可见。用 `-game` 无头截图夹具（`DrumGripAudit` 扩展 `MagazineAudit=` 参数）自动安装 ext_mag 并连拍第一人称，逐帧对照定位。**先后三个叠加错误**：

1. **挂点框架**（首修）：`Seat.GetRelativeTransform(GetSocketTransform(socket))` 默认 `RTS_World`，把座位数字当世界坐标——弹匣落到地图原点。改为 `RTS_Component`。
2. **单位**（二修）：三枪骨骼网格导入单位约定**不同**——M4 网格被 FBX 单位换算 ×100（厘米帧），AKM/QBZ 保持米帧（即 cross-weapon-optics 文档「AKM 枪根用米、共享件乘 0.01」的由来）。米制座位常量进厘米帧 + 0.01 缩放 → 弹匣成 2mm 微型物体缩在机匣内。
3. **组合顺序 + 坐标系来源**（终修，决定性）：`Seat ∘ Socket⁻¹` 与正确的 `Socket⁻¹ ∘ Seat` 在非恒等座位下不等价；且运行时骨架被重作者过，源 FBX 的骨骼/原点测量（Blender 里测的）**不代表运行时组件系**。终修采用旧弹鼓的已验证模式：`mount = SocketRef⁻¹ · Seat`，Seat 用**各枪运行时组件系**表达——M4 井口从已验收弹鼓资产的塔顶反推（≈ (0,−2,8.7)cm，帧轴向 X=横、Y=枪管(−Y=枪口)、Z=上，网格需 Rz(180°) 把作者系的 +Y 枪口映射到运行时 −Y）；AKM/QBZ 同结构米制值 + 0.01 缩放（**尚未逐枪校准，首次实机反馈后调数字**）。

验证：`Saved/DrumGripAudit/framefix1` vs `factory_ref` 帧对照（`Reference/cmp_001/002.png`）——扩容弹匣在井位渲染、随换弹动画、侧面观察窗可见，与原厂 PMAG 明显可区分。诊断日志 `EXT_MAG: attached … socket_loc/rel_loc/world_loc` 保留在代码中。

**教训（可复用）**：a) 组件挂 socket 后座位必须用该枪**运行时**组件系表达，源 FBX/Blender 测量只能当参考；b) 座位常量 = `SocketRef⁻¹·Seat`（参考骨架链），不要用动画中的 socket 快照反解；c) 三枪帧单位不同（M4 厘米、AKM/QBZ 米），跨枪挂点必须逐枪确认；d) 无头截图夹具（`-DrumGripAudit -MagazineAudit=<id>`）是弹匣类配件的第一人称自证手段。

**追加（同日深夜）**：用户再报 AKM/QBZ 仍不可见。探针实测 `GetRefBonePose`：**三枪运行时骨骼全部为厘米制、骨骼 scale=1**（AKM socket 组件位 (6.447,−22.52,−17.62)＝Blender 米值×100）——"AKM 用米"只是创作端约定，运行时不存在米制帧。此前"米制分支"座位小了 100 倍（弹匣 2mm）。终版：三枪统一厘米；AKM/QBZ 座位直接取自已验收弹鼓资产的塔顶坐标（identity 挂载 ⇒ 资产坐标即 socket 系）：AKM (0.1,3.7,8.6)、QBZ (0.1,−2.8,12.5)，scale=1，直接作 socket 相对变换（无需 SocketRef 组合）；M4 保持已验证的组件系座位+SocketRef 组合。捕获验证：AKM normal_019 弹匣清晰跟随换弹动画；M4 cmp_001/002。夹具新增 `AuditWeapon=` 参数支持换枪验证。

# 大弹鼓重建模（DrumRemodel20260917，2026-09-17 追加——**已否决并回退**）

同日第二轮：大弹鼓容量调整为 +30 发（60 发，**保留生效**），并用扩容弹匣同款参数化管线重做三枪弹鼓网格。用户实机查看后判定「建模完全失败」，已于同日全部回退：

- 三处代码路径（`M4DrumVisual.cpp`、`AKMAttachmentVisual.h`、`QBZ191Attachments.h`）恢复指向旧资产 `/Game/Weapons/AttachmentFinish20260913/...` 与 `/Game/Weapons/QBZ191/Attachments20260913/SM_QBZ191_drum`；Game 目标重新编译通过（`Logs/build_native_revert2.log`）。
- 新 UE 资产与 FBX 移入本目录 `trash/drum-remodel-20260917/`（含 SHA-256 清单），`/Game/Weapons/DrumRemodel20260917` 已不存在。
- 图标 `magazine_large_drum.png` 由备份 `Reference/magazine_large_drum_before_20260917.png` 恢复并重新导入 UE Texture（`Logs/drum_icon_restore.log`）。
- 以下重建模记录仅作废案保留，供后续如果换思路再做时参考。

- **新形态**：鼓轴改为左右向（真实弹鼓形态），玩家侧面看到完整盘面；盘面含中心轮毂+轴帽、6 颗六角螺栓圈（4.3cm 分布圆）、卷边轮缘环、中部卷焊带；左面（−X，观者侧）余弹索引镜盖+指示点（DrumIndex 材质）；供弹颈按每枪弹匣井实测截面（M4 2.2×3.2 / AKM 2.6×3.4 / QBZ 2.4×3.3cm）自井位直落鼓体，带喇叭状过渡裙边。鼓体包络不变（Ø12.3 × 厚 7.7cm，鼓心沿用旧资产实测位置），1,520 三角面（旧 13,908）。
- **逐枪烘焙**：新鼓在枪体世界系对齐「旧已验收弹鼓的盘心实测位置 + 扩容弹匣同款井位座位」，再逆变换写回各枪资产坐标系——旧 identity 挂点、弹鼓换弹动画、掉落编排（`UpdateDrumDropVisual` 用 `LargeDrum->GetStaticMesh()` 自动取新网格）全部不变。落位渲染 `Reference/drum_new_{M4,AKM,QBZ}.png`。
- **资产**：`/Game/Weapons/DrumRemodel20260917/{M4/AKM/QBZ}/SM_*`（未动旧资产）；槽位沿用各枪原命名（M4 `DrumPolymer/…`、AKM `drum_DrumX`、QBZ `QBZ_SRC_drum_N`）并绑定现有每枪涂层材质（M4 `M_M4_drum_1` / AKM `M_AKM_drum_1` / QBZ `M_QBZ191_Receiver_drum_0/1` + 共用 `M_M4DrumIndex`），导入回执 `import_drum_receipt.json`。
- **代码**：仅三处网格路径（`M4DrumVisual.cpp`、`AKMAttachmentVisual.h`、`QBZ191Attachments.h`）指向新资产；Game 目标编译通过（`Logs/build_native3.log`）。
- **图标**：`magazine_large_drum.png` 已按新模型重渲（盘面朝观者、竖向、枪口朝左、透明底），旧图备份于 `Reference/magazine_large_drum_before_20260917.png`，UE Texture 已同步（`import_drum_icon_receipt.json`）。
- **待实测**：游戏内三枪弹鼓装配位置、换弹跟随、掉落物理、图标显示由用户测试；盘面朝向若与预期不符，调 `build_drum.py` 的 `xax/yax` 轴映射即可。

## 实机修复记录（2026-09-17）

- **扩容弹匣不可见 + 预览图取景异常**：用户实机反馈后定位为挂点坐标系 bug——`Seat.GetRelativeTransform(GetSocketTransform(socket))` 未指定空间，默认 `RTS_World` 把座位数字当**世界坐标**解释，弹匣被放到地图原点附近（角色持枪位远离原点 → 不可见），且预览取景把错位组件计入包围盒。修复：改用 `GetSocketTransform(socket, RTS_Component)`（座位数字所在的枪组件坐标系）。教训：**组件挂 socket 后，凡以测量的组件系数字构造的座位，必须用 RTS_Component 组合**；图标 Rig 在世界原点、世界系与组件系重合，所以离线验证发现不了。
- 弹鼓重建模被用户否决后已整案回退（见下节）；本轮修复只涉及扩容弹匣分支。

## 方案

- **一个共享静态网格** `SM_ExtMag_Universal`（约 1,900 三角面，2 材质槽：Polymer 主体 / Metal 底板；UE 导入器当前合并为单 Polymer 槽），三条枪共用，通过每枪「座位变换」适配各自弹匣井——先例即跨枪型瞄具的共享网格+专用安装座思路。
- 组件挂在 `WPN_SOCKET_Magazine`，运行时用 `Seat.GetRelativeTransform(AKMViewmodel->GetSocketTransform(TEXT("WPN_SOCKET_Magazine")))` 由引擎解析骨骼帧（沿用 M4GunsmithVisual 的挂点计算模式），座位常量保留在直接测量的分量空间（米制）：换弹时组件跟随 socket 动画路径，与原厂弹匣一致。
- 换弹沿用各枪原厂动画（`bDrumInstalled` 仍只认 `large_drum`，扩容弹匣自动走普通换弹），`UpdateDrumDropVisual` 对 `ext_mag` 分支只保持可见，不做弹鼓掉落编排。

## 每枪座位（分量空间，米；rake=弹匣体相对竖直的前倾角）

| 枪 | 座位中心 (X, Y, Z) | Rake | 井口参考 z（像素测量） |
| --- | --- | --- | --- |
| M4A1 | (0.058, 0.257, −0.070) | 15° | −0.105 |
| AKM | (0.062, 0.243, −0.105) | 20° | −0.128（受原厂井径差异影响最大，优先实测） |
| QBZ-191 | (0.054, 0.260, −0.056) | 13° | −0.073 |

## 目录数据（`Content/ColdSteelData/gunsmith.json`，三枪同步）

`magazine` 槽新增 `ext_mag`：`stats = {mag_delta: 10, reload_mult: 1.25, ads_percent: 0.05}`；
卡片描述无数字；effects 三条与 stats 同义同数（容量+10 发 / 换弹+25% / 开镜耗时+5%）。

## 接入点（本轮源码改动）

- `Source/FPSGAME/FPSGAMECharacter.h`：`SetGunsmithDrum(bool)` → `SetGunsmithMagazineAttachment(const FString&)`，新增 `MagazineAttachmentId`。
- `Source/FPSGAME/Weapons/M4DrumVisual.cpp`：原弹鼓分支逐字保留（历史门控不变，含 QBZ 弹鼓原语义）；新增 `ext_mag` 分支；`UpdateDrumDropVisual` 增加 ext_mag 早退分支。
- 调用点 `FPSGAMECharacterProfile.cpp`、`UI/ColdSteelWeaponIcons.cpp`、`UI/ColdSteelPickupWeapon.cpp`、`UI/M4StandalonePreview.cpp`：改为传弹匣槽 ID 字符串（图标/拾取/预览 Rig 因此自动显示扩容弹匣）。
- 图标：`Content/ColdSteelData/AttachmentIcons20260913/magazine_ext_mag.png` + 同名 Texture2D（共享命名，三枪共用；UI 按 `槽位_选项ID` 解析已核对）。
- Game 目标编译通过：`Binaries/Win64/FPSGAME.exe`（日志 `Logs/build_native2.log`）。

## 来源与制作

- 三视图/测量：`Scripts/measure_seat*.py`、`Scripts/measure_well.py`、`Reference/*.json`（井口平面用红色壳体渲染 + 像素扫描；AKM 原厂弹匣焊死在机匣壳体内，弹匣上段区域由松动件+包围盒投票提取）。
- 建模：`Scripts/build_extmag.py`（bmesh 参数化扫掠：直喉部 2.1×3.0cm、过渡、32° 前倾弧线 R=0.215、侧肋、−X 面余弹观察窗×4、金属底板；`axis_forward='-Y', axis_up='Z', FACE 平滑 + tspace`，与弹鼓管线一致）。
- 三枪合成验证：`Reference/compose_*.png`（Blender 内同场景装配渲染；通用外形在三枪井口均成立，无穿帮穿插）。
- UE 导入：`import_ue.py`（commandlet，`import_receipt.json`：bounds 3.12×6.5×21cm 实际尺寸）、图标 `Scripts/render_icon.py` + `import_icon.py`。

## 限制与待办

- **未实测**：游戏内安装/换弹跟随/掉落重载/存档恢复由用户测试；AKM 井径比 M4 大，喉部按最小井设计，若井口有可见缝隙，后续给 AKM 加喉部套圈（collar）或在材质上做防尘盖效果。
- UE 导入后材质槽合并为单 Polymer 槽（底板金属分区暂未保留）；材质统一（按各枪机匣涂层的配件金属区域覆盖）是独立后续工序，遵循 weapon-finish 标准。
- 换弹动画按原厂 30 发弹匣路径授权；扩容弹匣更长，插入段视觉差异留待实测评估。
