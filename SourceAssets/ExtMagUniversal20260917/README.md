# 扩容弹匣 `ext_mag` ——**当前状态：待办，未通过验收**（2026-09-18）

用户判定"**还是没成功**"，并指出姿态/动作适配是我们把握不足的部分，本项降为待办。已完成制作、未通过实机验证。

**待办清单（交接顺序）**

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
