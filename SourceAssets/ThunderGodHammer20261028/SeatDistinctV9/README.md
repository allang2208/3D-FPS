# 雷神之锤两款专属锤座差异化 V9

用户授权：保留原设计语义，增加贯雷、疾雷实装模型的区分度；从雷神之锤剔除破势古印座、鸣雷疾驱座及对应模型适配。其他武器的通用改造继续保留。

## 实体结构

| 锤座 | 原设计语义 | 本轮几何调整 |
| --- | --- | --- |
| 贯雷 | 闭合回环、旋转投掷和召回 | 前后双面的厚锻闭合椭圆护环，连续交织嵌银回纹，厚实回折肩部，保留原厂平顶和中央圆徽 |
| 疾雷 | 引雷、举锤蓄力和指向落雷 | 三枚上扬折线引雷冠，中间高、两侧低，冠脚嵌入原厂顶盖，内收肩部，保留中央圆徽 |

中央原厂符印、锤头侧面接口及柄颈接口受保护。贯雷外形约 13 × 13.6 × 14.8 cm；疾雷约 13 × 11.8 × 18.9 cm，冠顶比原厂顶盖高约 4.1 cm。尺寸为该独立锤座的局部包围盒，不是整把锤子的尺寸。

两款继续使用原有 4K 底座 PBR，新增护环与引雷冠各有 2K BaseColor / ORM / Normal。保留源网格自定义法线，UE 使用完整精度 UV、Mikk 切线与显式 Nanite 切线。新增冠体和护环为封闭实体，材质不使用双面显示掩盖缺面。

可编辑源：`ThunderSeats_DistinctV9.blend`。运行网格：`/Game/Weapons/ThunderGodHammer20261028/SeatDistinctV9/Meshes/SM_ThunderGodHammer_head_mount_<id>`。保留原网格叶名称，继续匹配疾雷的武器环绕闪电目标。

## 图标

`Icons/<id>_source.png` 来自当前实际模型的独立灰阶图标作者场景；`Icons/<id>_framed.png` 由内置 imagegen 按当前模型和已认可金属框母版生成。一项一图，灰阶金属方框、四角铆钉、银色内环、深灰底。生成提示和源场景一并保留。

实际运行 PNG 与 Texture2D：`/Game/ColdSteelData/AttachmentIcons20260913/ue_thunder_god_hammer_head_mount_<id>`。保存为 UI 组、Editor Icon 压缩、sRGB、NeverStream、无 mip。具体落盘见 `icon_import_receipt.json`。

## 两款通用特殊锤座退出雷神之锤

- `thunder-god-hammer-gunsmith.json` 的 head_mount 列通过 `excluded_options` 排除 `ancient_breaking_seal_seat` 和 `storm_drive_seat`。
- `WarhammerGunsmith.cpp` 在合并共享选项时应用武器专属排除项。共享库自身保持完整，因此其他锤子仍可使用。
- 雷神之锤模块表移除这两项；旧实例的无效锤座通过既有规范化流程回落原厂。AncientSeal 和 StormDrive 的直接安装判断同步排除雷神之锤，避免仅隐藏选项而遗留被动。
- 精确移除 `SeatInlaidC6` 中这两项对应的 2 个 Mesh、2 个 Material、6 个 Texture 包；保留 3 款普通锤座、其他武器适配及共享图标。备份路径、原文件大小与哈希、已删除资产列表见 `retirement_assets_receipt.json`。
- 可编辑 C6 源中的对应两对象及其专属 FBX、PBR PNG、NPZ 另行归档并移除；源规则只保留 3 款普通锤座。混合源的完整原副本及所有退役文件保存在 `trash/thunder-seat-retired-20261031`，详见 `retirement_source_receipt.json`。历史版本、历史导入回执不作为当前运行版本，也不在本次清理范围。

## 交付边界

GuanLei / JiLei 仍为传说改造；既有伤害、被动、投掷、召回、蓄力及落雷玩法保持原设置。本轮更新实体外形、专属图标、锤座适用范围及失效选项处理。

必要后台 C++ 构建见 `build-20261031-125543-receipt.json`；实际资产导入保存见 `import_receipt.json`；两份运行目录更新见 `publication_receipt.json`。没有主动启动 UE 图形编辑器，没有运行游戏、追加测试或验收渲染。生产图标素材不代表游戏内视觉验收，最终装配观感由用户在游戏中确认。
