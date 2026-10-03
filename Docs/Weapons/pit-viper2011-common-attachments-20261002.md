# Pit Viper 2011 通用改造接入

按 2026-10-02 用户要求接入现有手枪通用改造，通用图标复用共享资源。制作、导入及保存使用后台 Blender / UE Python commandlet；没有打开 UE 编辑器、运行游戏或做验收。

| 类别 | 改造 | 运行接入 |
|---|---|---|
| 瞄具 | `holographic`、`panoramic_red_dot`、`eoth_holographic` | 按本枪滑套表面制作封闭安装座，随 `WPN_Slide` 运动，ADS 读取本件 `AimCenter` |
| 枪口 | `true`、`tactical_suppressor`、`brake`、`multi_caliber_suppressor` | 对接本枪补偿结构出口，统一本件 +X 膛轴，以 `Muzzle` / `AimGuide` 给出出口位置与方向 |
| 弹匣 | `ext_mag` | 沿原件实测壳体方向加长 18 mm；保留供弹、卡笋和抓握区；15 + 3 = 18 发；切换时隐藏原钢壳和底板 section |
| 战术件 | `laser`、`flashlight` | 按本枪下导轨与设备肩部采样制作封闭安装座，原光孔、发射器和遮挡逻辑延用 |
| 握把防滑纹 | `pistol_grip_granular`、`pistol_grip_diamond`、`pistol_grip_quickdot` | 共享手枪表面处理材质；本枪双侧贴合网格，仅覆盖握柄表面 |

共 13 个通用几何改造选项，使用 11 个网格（防滑纹三选项复用同一贴合网格）。此前快速扳机数值改造保留。沿用现有通用 ID 与倍率，单持、双持及法杖副手均使用同一武器装配入口；实例装备、草稿应用及存档继续使用现有枪匠合同。

运行目录 `/Game/Weapons/PitViper2011/Attachments20261002`，由当前 `/Game/Weapons/PitViper2011` Cook 目录覆盖。可编辑 Blend、FBX、接口数据、来源路径及导入脚本位于 `SourceAssets/PitViper2011Attachments20261002`；`import_receipt.json` 记录实际保存包、材质槽与显式插座。导入成功后才发布 `gunsmith.json` 中本枪的选项和 `pistol_grip_surface` 绑定。初始枪械目录生产脚本在后续重建时会保留已落盘的通用改造，不会退回原厂限定目录。

配件金属部分引用本枪当前 `MI_PitViper2011_h_190` 及弹匣 WS 派生材质。源 UV0、镜片、分划、激光孔和橡胶区域保留，枪口内腔保留消光材质；战术件以源 `MetalRegion` 标记分离金属面。物理涂层 UV 单独制作，未用金属覆盖光学分区。

图标使用 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms` 共享库。通用改造优先共享金属框图，原厂选项保留本枪图，分类入口优先共享分类图。三张已有手枪防滑纹图和扳机分类图一次提升为共享键；快速扳机直接复用现有共享图。没有新图生成、图标渲染或整套逐枪复制。解析规则与缓存已在 `M4GunsmithLayout.cpp` 实施，并同步至仓库和个人 `ue5-weapon-workflow` SKILL。

构建结果见同作者目录的 `build_receipt.json` 与 `Saved/BuildEditor/pit-viper2011-attachments-20261002.log`。运行表现、视窗遮挡、开火和换弹期间接触，以及改造应用/存档行为未测试，交由用户测试；资产保存和编译结果不代表实机验收。
