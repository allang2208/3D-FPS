# 弹药图标接入：有本口径图标就接，没有就留空（2026-09-22）

用户规则（2026-09-22）：**弹药有图标的就接入图标，没有图标的就空着**。本文是该规则的一次全量对账与执行记录。

## 接入机制（先确认再改）

| 字段 | 文件 | 消费方 | 解析方式 |
| --- | --- | --- | --- |
| `icon` | `Content/ColdSteelData/ammo_types.json` | 弹种轮盘、弹药袋行（`ColdSteelStatusModel::AmmoIcon`） | `FImageUtils::ImportFileAsTexture2D(ProjectContentDir()/<icon>)`，**Content 相对 PNG 路径，运行时导入** |
| `ue_icon` | `Content/ColdSteelData/items.json` | 背包格、物品提示、强化面板（`ColdSteelInventoryWidget` / `ColdSteelItemTooltipData`） | 同上；武器另有 `Icons/<Definition>.png` 约定 |
| `icon` | `Content/ColdSteelData/items.json` | 仅 Godot 归档遗留（`res://…`） | UE 侧不读取，保留原样 |

空串即"无图标"：弹药袋行 `if(Row.Icon)` 直接不加图标槽（`ColdSteelAmmoPouchWidget.cpp:174`），轮盘格的图标与凹槽只在 `FramedIcon()` 非空时绘制，所以**留空不需要额外代码**，缺图不会出现破图或空框。

## 对账结果（18 行弹药）

| 组 | 口径 | 现成素材 | 处理 |
| --- | --- | --- | --- |
| `ammo_762` LP/PS/AP | 7.62×39 | `Icons/Ammo76220260921/762_{lp,ps,ap}.png`（专用分档美术，2.1–2.5 MB 写实照片） | 保持接入 |
| `ammo_556` M193/M855A1/M995 | 5.56×45 | `Icons/ammo_556.png`（本口径写实照片） | 保持接入 |
| `ammo_58` DBP87/DBP10/DBP191 | 5.8×42 | `Icons/ammo_58.png`（本口径旧通用图，三发弹） | 保持接入 |
| `ammo_45acp` FMJ/+P/AP | .45 ACP | **无本口径素材** | `icon` 清空 → 留空 |
| `ammo_357` SP/JHP/AP | .357 MAG | **无本口径素材** | `icon` 清空 → 留空 |
| `ammo_127` 普通弹 | 12.7×55 | **无本口径素材** | `ammo_types.json` 本无 icon；`items.json` 的 `icon`/`ue_icon` 原指向 `Icons/ammo_556.png`（跨口径）→ 清空 |
| `ammo_9` 普通弹 | 9 mm | `Icons/ammo_9.png`（三发 9mm 手枪弹，透明底 512²） | **本次接入** `ammo_types.json`（`items.json` 已是该图） |
| `ammo_pkm_762x54r` LPS | 7.62×54R | `Icons/ammo_762.png`（写实弹药盒，盒面只标注 "7.62 mm"，口径通用） | **本次接入** `ammo_types.json` 与 `items.json.ue_icon` |

三处跨口径假图（`.45 ACP`、`.357 MAG` 六行指向 5.56 照片副本；`12.7mm` 指向 5.56）已全部清空。`items.json` 中现有引用为 `res://assets/ui/icons/equip/…` 的条目是 Godot 归档遗留字段，UE 侧不读取，按原样保留。

## 退役与保留位置

- 6 张 `.45 ACP` / `.357 MAG` 占位 PNG（内容为 `Icons/ammo_556.png` 的逐字节副本）退役到 `trash/AmmoPistolIconsRetired20260922/`，附 SHA256 与来源说明。
- 同目录的 6 个 `.uasset`（09-22 10:52 导入）未随本次退役移动，也不再被任何 JSON 引用；如后续要清理需先确认无蓝图/数据资产引用。
- **保留位置**：将来 .45 ACP / .357 MAG / 12.7mm 专用美术产出后，放回 `Icons/AmmoPistol20260922/`（同名即可）或新批次目录，然后把 `ammo_types.json` 的 `icon` 与 `items.json` 的 `ue_icon` 指回对应文件即完成接入，无需改代码。5.56 / 5.8 各档的专用分档美术同理（现有为同口径通用图）。

## 界面表现（留空后的样子）

- 弹种轮盘：该格**不画图标凹槽、不画图片**，只有名称与剩余发数，两行按"无图标分支"在中线 0.67R 附近居中；等级色仍由内圈标识弧表示，当前装填仍由银白标识弧表示。
- 弹药袋行：不加图标槽，名称/数量左对齐，行高不变。
- 背包/提示：`ue_icon` 为空即不画图标。

## 未测试

本轮只做了数据接入（JSON）、源码编译核对与文件级校验：`ammo_types.json` / `items.json` 解析通过、18 行弹药无重复 id、所有非空图标路径均在磁盘存在、跨口径引用为 0；`ColdSteelAmmoWheel.cpp` 单 TU 编译核对退出码 0。**未进入 PIE、未截图、未构建模块 DLL**，轮盘与弹药袋中的实际观感、留空格子的排版效果由用户实测。