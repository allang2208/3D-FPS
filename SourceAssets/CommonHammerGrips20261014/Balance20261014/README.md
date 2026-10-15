# 通用握持包覆：用户确定数值

| 配件 | 攻击速度 | 攻击体力消耗 | 韧性伤害 | 重击蓄力速度 |
| --- | ---: | ---: | ---: | ---: |
| 斜纹速握包覆 | +15% | −10% | −15% | — |
| 叠革缓震包覆 | — | −25% | — | — |
| 菱编蓄力包覆 | +5% | +10% | — | +25% |

「/」与「—」按不变处理，物理伤害不变。维护源为 `../BuildV1/catalog.py`；`apply_balance.py` 只把这三个 ID 的 stats／effects 写入正式 `common-hammer-grips.json`，不重导或替换美术资产。

战锤目录新增 `heavy_charge_speed_bonus` 的读取，沿用 `FMeleeModifiers` 的增量叠加。`ColdSteelTool::Evaluate` 集中计算 `HeavyChargeSpeedBonus` 和 `HeavyChargeSeconds`，既有蓄力附魔与物品增量使用同一加法口径。时长为基础秒数 ÷ (1＋总加成)，保留最短 0.2 秒限制。例如单独装备菱编包覆，基础 2 秒变为 1.6 秒。

`ApplyToolStats` 使用统一计算后的时长，客户端蓄力进度、动画采样、提前释放的续接与服务端满蓄判定沿用同一个 `BluntChargeSeconds`。新增蓄力速度不乘到重击释放／收招时钟，也不把普通攻速重复乘入蓄势。

攻速、体力消耗、韧性伤害沿现有战锤评估与权威出手快照结算。工作台详情、总览及物品提示补充直接的蓄力速度加成，继续使用同一 Evaluate，不额外展开各段派生伤害。

本轮涉及 C++，执行必要的后台 Editor／Game 构建，结果保存于本目录。没有修改模型、图标或动画，没有启动／关闭交互编辑器，没有运行游戏、测试或验收。构建状态与实机行为分别记录。

## 本轮构建结果

- Game 完整构建 `Succeeded`，耗时 62.03 秒，保存了新的 `FPSGAME.exe`，日志为 `game-build.log`。
- 等后台 UE 进程释放文件后，Editor 构建执行 174 项动作，最终 `Failed (OtherCompilationError)`，耗时 286.91 秒。错误为 `ColdSteelQuickSlot.cpp:308` 的局部 `Item` 重名，`FPSGAMECharacter.cpp:1020/1028` 的 `ProductionTools` 未声明，以及 `ProductionBluntWhirlwind.cpp`／`ProductionToolMotion.cpp` 的旋风 Focus 方法缺少声明。日志为 `editor-build.log`。
- 这些错误位置不在本次数值改动的代码段；未回退、覆盖或修补其他正在变化的旋风／快捷栏代码。构建结束时交互编辑器已重新打开，保持该进程不动，Editor 二进制尚未更新。
- 因此本轮交付为正式数值配置、结算／UI 源码以及成功的 Game 构建。使用 Editor／PIE 时仍需等待工程编译问题解决并重新构建，不能把 Game 成功写成 Editor 已完成更新。未进行实机测试。
