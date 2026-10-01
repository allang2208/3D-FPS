# 电矛光柱替换

用户要求参考原项目 `game-dev` 的光柱替换当前电矛闪电。本次只改变电矛发射表现，不改蓄力、自由瞄准、满充保持、未满充散射、伤害、贯穿、感电、修炼或墙面截断。

原版来源：`src/entities/components/thunder-lance-system.js:spawnRailgunBeam`（373ms、widthScale4）与 `src/effects/combat-fx.js:spawnRailgunBeam`。原版主线为40:19:9三层蓝色外辉光／白蓝中层／白热核心，附4个沿轴扫过的加速环；以 Quad.easeOut 淡出。

实现将第一人称空间中的外／中／内光柱直径设为96／45.6／21.6厘米，保留原三层比例；比原2D像素直接按1.5cm换算克制，减少贴脸视野遮挡。几何使用引擎 Cylinder，连续轴线连接当前施法起点与实际墙面截断终点；外层采用视角软边衰减，核心白热。4个加速环沿实际轴线前移，0.373秒按 `(1-progress)^2` 收光并销毁。

`AFPSLightningArc::InitializeColumn` 复用现有有限生命周期和末端无阴影灯，只创建3层柱体及4个环的动态网格组件；保持现有48个短命Arc实例上限。光柱不创建碰撞、导航或伤害逻辑，不保留原分叉闪电主体。雷暴、连锁闪电和过载继续使用 `InitializeArc`。

材质作者 `Tools/Skills/build_thunder_lance_column.py` 仅拥有 `/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceColumn` 与 `M_ThunderLanceCoil`；无外部纹理或模型依赖。全量电系作者 `beam()` 改为调用同一入口。旧 `NS_ThunderLanceBeam` 包保留历史恢复，运行引用已切换，不用全量作者覆盖其他魔法资产。

本轮必要编译、实际材质保存与当前编辑器生效范围记录在 `Saved/ThunderLanceBeam20261001`。不自动启动编辑器、游戏、PIE、截图或运行测试。

Game 目标普通后台构建已以 `Result: Succeeded` 完成；用户选择结束测试、保存并关闭编辑器后，继续后台材质保存和 Editor 构建。运行效果尚未测试。

材质作者 commandlet 已退出码0完成，`column-authoring.json` 记录 Column／Coil 两个正式资产保存；本轮未重建或修改其他魔法的 Niagara 系统。Editor 构建按当前全局构建串行队列等待，最终结果另记在本目录构建日志。

普通 Editor 最终构建 `build-editor-02.log` 已 `Result: Succeeded`、退出码0，正式 DLL 已落盘。构建期间共享 `HundredEyedSlagSpecialAttacks.cpp` 的 `GetPawn()` 返回值触发 `auto*` 推导错误；本轮仅将这一处变量改为显式 `APawn*`，其余怪物制作修改保留，没有改变其攻击行为。

最终 Game 构建 `build-game-02.log` 同样 `Result: Succeeded`、退出码0。两份正式材质、源码、普通 Editor DLL 与 Game 程序均已落盘；未重新打开编辑器、启动游戏、截图或进行运行测试。

用户后续要求更粗、更明显：三层直径加倍为192／91.2／43.2cm，发光9／14／24，保持原Hold后单次线性淡出，环同步增强；十字准星和杖前魔法阵同步优化。原.373秒寿命和玩法范围保留。最新定向保存及构建记录见 `Docs/Skills/magic-readability-and-blizzard-material-fix-20261001.md`，以上96cm与平方淡出属于历史版本。

用户随后要求停留两秒以便观察：`ColdSteelElectricMagicModel.cpp` 的雷枪 `Hit.Duration` 从.22秒改为2秒，柱体及加速环保持完整亮度2秒，然后沿用.153秒线性淡出，总可见时间约2.153秒。伤害仍只在发射时结算一次；不增加持续伤害。材质无需重建，作者回执时长同步为2.153秒。本次必要构建日志位于 `Saved/ThunderLanceHold2Seconds20261001`，未主动启动游戏或运行测试。

两秒停留的 Game 构建 `build-game-01.log` 与普通 Editor 构建 `build-editor-01.log` 均已 Result: Succeeded、退出码0。用户保存并关闭编辑器后完成普通 DLL 落盘，没有重新启动编辑器或运行游戏测试。

用户后续提供彗星亚兹勒截图，要求厚重翻卷能量束且保留雷电爆发。当前运行资产改为ThunderFluxV3的原创宿主／密度场／Body／Filaments，去掉规则光环，保持两秒停留。旧V2包保留恢复；`build_thunder_lance_column.py` 现在调用最新Flux作者，不再生成旧光滑柱体。制作与实际保存／构建记录见 `Docs/Skills/thunder-lance-flux-20261001.md`。
