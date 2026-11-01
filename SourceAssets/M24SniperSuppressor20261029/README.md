# 狙击枪消音器

M24 枪口槽的独立可选改造件。保留 `m24_factory_suppressor` 存档 ID，已有显式安装记录继续使用；未选择枪口配件的新枪默认裸枪口。枪械基础伤害、换弹、握姿与双瞄具不变。

| 直接属性 | 改造值 | 目录键 |
| --- | --- | --- |
| 后坐力 | -30% | recoil_mult: 0.7 |
| 枪械稳定性 | +20% | stability_mult: 1.2 |
| 子弹速度 | -10% | bullet_speed_mult: 0.9 |
| 开镜耗时 | +10% | ads_percent: 0.1 |

数值参考现有普通、战术及 SVD/SVCh 大口径消音器：为栓动狙击枪保留更多弹速，以较慢开镜换取控制收益。沿用实际消音声、枪口火光和听觉范围分支；不附加大口径消音器的首发致死免警报效果。

## 已有独立资产复用

- 原始部件：M24Modular20261027/author_modular.py 从 `M24_silencer` 独立导出，已从骨骼枪体移除。
- 运行网格：`/Game/Weapons/M24/Surface20261027/SM_M24_m24_factory_suppressor`，保留表面升级材质、原安装空间及 Muzzle 挂点。
- 改造图标：`Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_m24_factory_suppressor.png`，对应已保存的 `T_muzzle_m24_factory_suppressor`，沿用灰阶金属框。
- 裸枪口沿用现有 `none` 选项及统一移除图标。
- 正式数据：`Content/ColdSteelData/gunsmith.json`；配方 `catalog.py` 同时接入原模块化注册入口，防止重新注册恢复旧名与空数值。
- `M24WeaponAssets::FactoryParts` 同步裸枪口，供物品图标配方使用。

本批不重复拆分或重导已有模型和图标。`build.ps1` 编译工厂图标配方的两个调用源文件并链接发布。未运行游戏、静态自检、截图或测试，实机效果由用户体验。
