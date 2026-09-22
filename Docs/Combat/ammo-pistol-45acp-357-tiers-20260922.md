# .45 ACP FMJ / +P / AP 与 .357 MAG SP / JHP / AP

2026-09-22。用户指定：两种手枪口径各加 3 档，沿用现有 7.62／5.56 那套阶梯效果；本轮只做配置与文字说明，图片用占位。

起因：双持手枪长按 R 要弹出左右两个弹种圆盘，但轮盘有前置门槛——**两只手都只有一种兼容弹种时，长按 R 直接走普通换弹**（`FPSGAMECharacterAmmo.cpp` 的 `ReloadPressed()` 分支）。加弹种前 `.45 ACP` 与 `.357 MAG` 各只有一条"普通弹"，所以双枪长按 R 什么都不会出现。详见 [双持手枪：左右两盘弹种轮盘](../../Docs/UI/ammo-wheel-dual-pistols-20260922.md)。

| 口径 | 弹种 | 稳定 ID | 伤害倍率 | 忽略物理护甲 | 等级 | 图片 |
| --- | --- | --- | --- | --- | --- | --- |
| .45 ACP | FMJ | `ammo_45acp` | 1.00 | 0% | 绿阶 | 占位（待制作） |
| .45 ACP | +P | `ammo_45acp_p` | 1.00 | 10% | 蓝阶 | 占位（待制作） |
| .45 ACP | AP | `ammo_45acp_ap` | 1.05 | 20% | 红阶 | 占位（待制作） |
| .357 MAG | SP | `ammo_357` | 1.00 | 0% | 绿阶 | 占位（待制作） |
| .357 MAG | JHP | `ammo_357_jhp` | 1.00 | 10% | 蓝阶 | 占位（待制作） |
| .357 MAG | AP | `ammo_357_ap` | 1.05 | 20% | 红阶 | 占位（待制作） |

数值与 7.62x39mm LP／PS／AP、5.56x45mm M193／M855A1／M995 完全同一套：基础弹 1 倍伤害 0 穿透、中间弹 1 倍伤害 10% 穿透、高阶弹 1.05 倍伤害 20% 穿透。战斗侧没有新增算法，仍走 `CoreCombatFormula::Defense` 的比例穿透与 `ColdSteelSkills::Snapshot(..., bFiredRound=true)` 的发射快照，说明见 [7.62 LP/PS/AP 接入记录](ammo-762-lp-ps-ap-20260921.md)。

## 标识与兼容

- 最低档沿用该组原有 ID：`ammo_45acp` 命名 FMJ、`ammo_357` 命名 SP。因此现有的 .45／.357 备弹、枪内已装填状态、旧奖励条目与旧迁移逻辑直接接着用，**不重新发数量、不改 ID**。与 LP 沿用 `ammo_762`、M193 沿用 `ammo_556` 的处理相同。
- `+P`、`AP`、`JHP` 是新增类型，只进正式弹种目录，不自动赠送、不改掉落与价格；获得后可在弹药袋与 R 轮盘切换。测试时用 F6 开发面板按弹种 ID 发放。
- 兼容组不变：`gunsmith.json` 里 M1911（`ue_m1911`）仍指 `ammo_45acp`，Dan-Wesson 715（`ue_dan_wesson715`）仍指 `ammo_357`，组内共用袋中余额，一把枪的弹匣仍只装一种弹。
- `order` 为 30/31/32 与 40/41/42，组内顺序固定为低档→中档→高档，落在 5.8 mm（20）与 12.7 mm（50）之间。
- 中间档与高档显式 `allow_infinite_reserve:false`：训练场无限备弹不适用，也不能靠长按 R 免费解锁未获得的类型；最低档保留普通弹的无限规则。

## 双持测试路径

`UPistolDualWieldComponent::MatchesEquipment` 要求主手（`Cell 6`）与副手（`Cell 8`／`11`）都是手枪，不要求同一型号：M1911 双持、Dan-Wesson 715 双持，或两者混搭都可以。装配后：

- 任一只手有 ≥2 种兼容弹种，长按 R 0.30 秒即弹出**左右两个圆盘**（左＝副手、右＝主手）；两只手都是 1 种时仍是普通换弹。
- 现在两把手枪各 3 档，所以两只盘都会出现三个 120° 扇区；未获得的档位数量为 0，保留扇区并灰显、不可提交。
- 鼠标在两盘之间可自由移动，指针在哪个盘里就改哪只手；移到两盘之间或盘心取消，Esc 取消，松 R 提交。

## 源码与配置

本轮**没有改 C++**。目录在角色子系统初始化时读取，轮盘、弹药袋、HUD 与 F6 发放列表都按目录动态生成：

| 文件 | 改动 |
| --- | --- |
| `Content/ColdSteelData/ammo_types.json` | `.45 ACP` 组与 `.357 MAG` 组各由一条普通弹扩为三条，带等级名、等级色、图片路径、倍率与穿透 |
| `Content/ColdSteelData/items.json` | 只改 `ammo_45acp`（`.45 ACP FMJ`）与 `ammo_357`（`.357 MAG SP`）两个旧物品定义的名称、描述与 `ue_icon`；新增档位**不加**物品条目（与 7.62／5.56 的先例一致，弹药不占背包格） |
| `Content/ColdSteelData/Icons/AmmoPistol20260922/*.png` | 六个占位图（见下） |

已确认不需要改动的入口：`UI/ColdSteelAmmoRuntime.cpp`、`UI/ColdSteelAmmoWheel.cpp`（按 N 等分，双持时每盘各按自己的组）、`UI/ColdSteelAmmoPouchWidget.cpp`、`UI/ColdSteelAmmoPresentation.cpp`、`Development/ColdSteelDevelopmentTools.cpp`。图标只从弹种目录的 `icon` 字段解析（`UColdSteelStatusModel::AmmoIcon`），物品条目的 `ue_icon` 只用于背包／仓库显示，因此新档位的图片必须写在 `ammo_types.json` 里。

## 图片

`Content/ColdSteelData/Icons/AmmoPistol20260922/` 下六个文件：`45acp_fmj.png`、`45acp_p.png`、`45acp_ap.png`、`357_sp.png`、`357_jhp.png`、`357_ap.png`。本轮未用 image_gen，也未做三视图／模型／拾取物；六个文件都是既有 `Icons/ammo_556.png` 的逐字节副本（1254x1254，1,590,709 字节，sha256 见 [占位清单](../../SourceAssets/AmmoPistol20260922/runtime-images.json)），属于口径正确性无关的临时占位：**六个档位目前是同一张图**，只能靠等级色与名称区分。最终图按 [仅数值弹药的等级图标](../../skills/ue5-item-asset-workflow/references/numeric-ammo-icons.md) 制作并覆盖同名路径即可，无需再改目录；提示词模板与替换要求记在 [来源记录](../../SourceAssets/AmmoPistol20260922/README.md)。

## 交付状态

配置、两个旧物品定义、六个占位图与文档已写入。因为只改 JSON 与 PNG，**没有需要编译的源码改动**；弹种目录在进入游戏／重载关卡时读取，重启游戏（或重开关卡）后生效，不需要重新构建二进制。未运行 PIE、未做游戏内验收：轮盘是否如期弹出两盘、两个盘的扇区数、切弹事务与实际穿透表现由用户实测。