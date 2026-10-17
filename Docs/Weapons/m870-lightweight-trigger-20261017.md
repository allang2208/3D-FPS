# M870 轻量化扳机套件

M870 扳机槽新增专属「特殊改造」：`m870_lightweight_trigger_kit`，名称为「轻量化扳机套件」。原厂选项为「原厂扳机套件」。

| 属性 | 配件倍率 |
| --- | --- |
| 射击间隔 | `fire_interval_mult: 0.75`，减少 25% |
| 后坐力 | `recoil_mult: 0.95`，减少 5% |
| 枪械稳定性 | `stability_mult: 1.05`，提升 5% |

当前 M870 基础间隔为 0.9 秒，仅安装本套件时目录计算为 0.675 秒；这是配置推算，未做实战测量。该间隔仍高于 M870 现有 0.30 秒下限。后坐力与稳定性继续交由现有 `GunsmithSystem::Calculate`、`FWeaponHandling` 计算，不引入额外乘区。

现有 M870 开火动画按实际间隔缩放，`M870PumpPlayRate()`、泵动机械音效、延迟抛壳及服务器闭锁时间采用对应动作速率；本次复用这些运行入口。射击模式与装填动作沿用当前实现。

## 接入

- `Content/ColdSteelData/gunsmith.json`：仅精确更新 `ue_m870` 块，增加扳机槽与套件选项，保留延长管及其他现有改造。
- `Weapons/GunsmithModificationTier.h`：M870 专属特殊改造分类。
- `UI/M4GunsmithLayout.cpp`：复用已有灰阶金属框 `trigger_m1911_lightweight_fast.png`，作为数值改造的代表性扳机图；分类使用现有 `category_trigger.png`。无需另建可见扳机模型或重导手臂。
- 属性卡、总览、物品提示使用现有评估器；安装和拆除继续通过 `gunsmith_parts.trigger` 与现有 Apply/CommitState 保存。
- `SourceAssets/M870LightweightTrigger20261017/catalog_option.py` 是该套件的作者数据源；`integrate_catalog.py` 精确合并正式目录。M870 初始注册脚本也调用同一数据源，避免重建目录时丢失本选项。

## 交付

目录已保存，制作目录包含修改前备份和 `catalog_receipt.json`。后台构建记录为 `build_editor.log` 与 `build_receipt.json`。本次为内部数值改造，未新增或重导 UE 模型资产；未启动编辑器、游戏、自动截图或运行测试，由用户自行测试实际效果。

后台 `FPSGAMEEditor Win64 Development` 构建已完成，返回 `Succeeded`：`Saved/BuildEditor/build-20261017-100731.log`，包含改造界面编译和正式 DLL 链接，共 6 项构建动作。
