# 魔力球配重、凝碧星核：限定特殊改造

2026-10-09，按用户要求，这两款配重仅供寒晶·双手剑与苍蓝星辉·双手符文剑使用，并归入金色「特殊改造」。

| 选项 | 正式 ID | 允许武器 |
| --- | --- | --- |
| 魔力球配重 | `pommel_mana_orb` | `ue_frost_crystal_sword`、`ue_rune_sword` |
| 凝碧星核 | `ballast_rune` | `ue_frost_crystal_sword`、`ue_rune_sword` |

注意：`ballast_magic_orb` 是现役「疾星配重」的 ID，本次不修改该选项。`pommel_runic` 的符文配重也保持原有适用范围。

## 已落盘修改

- `Content/ColdSteelData/melee-gunsmith.json`：两款选项加入允许武器列表与专属说明；属性、效果、选项 ID 不变。
- `Content/ColdSteelData/shared-sword-pommels.json`：同两款共享模型加入相同允许武器列表，更新主体外观说明。
- `Source/FPSGAME/Weapons/ModularSwordVisual.cpp`：装配共享配重时读取允许武器列表，不兼容的配重不进入该剑的模型目录。持握、改造预览、图标与掉落共用此入口；旧非法选择按既有 `Part()` 回退到该剑原厂配重。
- `Source/FPSGAME/Weapons/GunsmithModificationTier.h`：只有这两把武器 + 配重槽 + 两款 ID 的组合归为 Special，沿用现有金色卡片与「特殊改造」标签。

## 旧配置与生效边界

`LoadMeleeCatalog()` 已按 weapons 字段过滤可选项。已有 `Installed/Normalize/Calculate` 会忽略不兼容选择，停止其属性加成；用户下次正常应用合法改造时，通过原有保存事务移除旧键。没有直接改写用户存档。寒晶与符文剑上的合法旧配置保留。

目录与装配缓存会在新游戏实例初始化时重读。本次未运行游戏、回归、截图或验收，由用户测试。配置与源码已落盘，编译状态单独记录。

## 构建完成

编辑器在接入前已正常退出，热编译没有提交；本任务取消了自己的远程发现等待，转为 `Tools/Build/Build-Editor.ps1` 常规后台构建。`FPSGAMEEditor Win64 Development` 构建成功，`UnrealEditor-FPSGAME.dll` 已链接落盘。

日志：`Saved/BuildEditor/build-20261009-093944.log`；输出摘要：`build-editor-console.log`。12 个构建动作包含当前工作区的依赖，不代表只编译本次四个文件。构建后未打开编辑器、启动游戏或运行测试。下次打开工程并进入游玩时加载新代码和目录。
