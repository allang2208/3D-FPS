# 贯穿雷枪：自由瞄准、充能准星与杖前魔法阵

用户要求蓄力瞄准、魔法阵、随进度缩小的准星、未满充散射与统一充能提示。本次只改 `thunderLance` 相关行为和共用进度色入口，雷暴领域数值与运行逻辑保留。

## 交互与数值

- `AFPSGAMECharacter::Turn/LookUp` 原先用 `IsMeleeSkillMovementLocked` 拦截所有输入，误把雷枪的移动锁变成视角锁。现在视角只保持原大旋风／冲刺攻击限制，雷枪仍保持原地，允许鼠标瞄准。
- 从原施法接触点开始 2.5 秒充能。满充不再自动释放，继续保持手势、电团和魔法阵，松绑定键或再次点快捷槽发射。最低有效蓄力仍为 0.5 秒，不足或取消沿用退款／冷却回滚。
- `LanceChargeFraction` 是 UI、材质和实际散射共同读取的 0～1 进度。散射半角初始 6°，`spreadTangent=tan(6°)*(1-progress)`；取圆盘面积均匀样本 `sqrt(FRand())`，沿相机 Right/Up 偏移，再归一化方向。100% 时散射切线为零。
- 实际光束、贯穿目标筛选、墙面截断、命中骨段射线与终点特效都采用同一随机方向，不仅修改装饰电光。原蓄力伤害倍率、感电、击退、修炼和技能持有互斥保留。

## 界面与特效

- `ColdSteelCrosshair` 在雷枪充能时绘制散射圆周和四个收拢短刻度，以实际相机投影换算，覆盖普通武器准星。100% 时仅显示中心点。
- 体力／快捷栏上方的现有动作提示行增加雷枪优先项，从“雷枪充能 0%”递增至 99%，100% 变成“已充能完毕”。Noto Sans SC、阴影、字号与原行相同。
- 红→黄→蓝→绿渐变从 `ColdSteelStaminaHUD` 的原值提取到 `ColdSteelUI::ActionProgressColor`，重击、脚架等原提示与雷枪文字／准星共用，色值和等分阶段保留。
- 新魔法阵 `/Game/Skills/ElectricMagic/ThunderLanceV2/M_ThunderLanceCircle`：54 cm 平面、杖尖前方12 cm、双层反向旋转环、12枚杖形／菱形符文与小内环，白蓝电光随进度增强。纯程序材质，无外部贴图依赖、碰撞、阴影或导航影响；只对所属玩家显示。
- 独立 `UStaticMeshComponent`／MID 在施法接触点创建，沿组件既有 `TG_PostUpdateWork` 同帧更新杖尖与朝向，释放／取消／死亡／退出清理。原电团保留，增加随视角旋转。
- 原 `NS_ThunderCharge` 的复制母版系统是 Once，满充保持后必须切到 Infinite；保留已有短寿命发射器和粒子预算，终止仍由拥有它的技能组件清理，不增加持续伤害或新计时器。

## 作者入口与交付边界

- 作者：`Tools/Skills/build_thunder_lance_circle.py`，原全量 `build_electric_magic_assets.py` 接入同一作者以供恢复。本次只执行魔法阵作者，不重建雷暴、光束、冲击和声音母版。
- 既有电团系统生命周期的局部保存作者：`Tools/Skills/hold_thunder_lance_charge_20261001.py`；对应全量作者 `charge()` 同步无限循环规则。
- UI规划：`Docs/UI/thunder-lance-charge-plan-20261001.md`。
- 资产回执／构建日志：`Saved/ThunderLanceCharge20261001`。
- 后台必要构建和实际保存状态以本次回执为准。未启动游戏、PIE、截图或运行测试，视觉与手感由用户确认。

本次 `build-game-01.log` 与 `build-editor-01.log` 均以 `Result: Succeeded` 完成，普通 Game 可执行文件与 Editor DLL 已落盘。魔法阵作者 commandlet 退出码0，`circle-authoring.json` 已记录正式资产保存。未启动图形编辑器或游戏，不将构建结果称为实机测试。

电团生命周期局部作者 commandlet 同样退出码0；`charge-hold-authoring.json` 记录 `NS_ThunderCharge` 已编译保存为 Infinite。两份特效资产和全部本轮源码已落盘，尚未游戏测试。
