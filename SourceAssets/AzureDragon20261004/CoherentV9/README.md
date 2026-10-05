# 苍龙实体能量与收指挥爪 V9

> 用户于 2026-10-05 体验后判定“不是很合格”：当前为未达标待返工的暂存实现，不是合格母版。资产保存／构建记录不代表认可。本轮只登记待办、归档和发布，不继续优化。

2026-10-05，用户否定 Reference V7 的平面／立体混合观感，并要求参考突变体 3 的收指挥击。

- `author_energy.py`：九段实体棱晶、具有颈部鳞片／角／牙／眼／龙须的实体龙首、有厚度的螺旋符文带及闭合曲面火舌。所有组件共享一个原点，四个材质统一苍青色、亮边、透明度和明暗；不采样设计图，不使用正对屏幕的火焰平面。
- `author_claw.py`：五指各三节加腕根／掌骨，保留 CaptainHC Dragon Claw 原几何与图集。借鉴本机 Mutant3 `claw_skin.json` 的解剖弯曲轴和 PIP／DIP 内钩，重新分配连续关节权重，保留指甲的末节刚性权重。0.6 秒动作包括微钩待机、抬腕、收指、抓下、随势回收。
- `AzureDragonEnergy_SolidV9.blend`、`AzureDragonClaw_RakeV9.blend`：可编辑母版，`Export` 中有四个静态 FBX、蒙皮 FBX、动画 FBX、面数与绑定参数。
- 四份 `Energy*.hlsl` 与 `FlameMotion.hlsl`：底部充能、九段读数、苍炎独立摆动与长度／亮度随充能增加。火舌使用导入顶点色存储起点、纵向参数和独立相位。

制作：`run_author.ps1`。保存：`run_install.ps1`，沿用运行中的编辑器和批次互斥；无编辑器时才使用无界面 commandlet。原生：`run_build.ps1`，默认 Game／Editor；DLL 占用时保留现有编辑器，不自动关闭或重启。

UE 新资产位于 `/Game/Weapons/AzureDragon20261004/CoherentV9`，共十一份（四模型、四材质、龙爪模型／骨架／动画）。沿用既有 `/Materials/M_AzureDragonClaw` 与 VisibilityV5 可见性修正，不执行旧基线安装脚本重置共享材质。

依赖原型 `../AzureDragonClaw.blend`、`../Export/finger-landmarks.json` 和项目 `SourceAssets/Mutant3Khaimera20260923/claw_reference_20260923/claw_skin.json`。只借鉴爪型参数，未复制或重新发布 Paragon 模型／整身动画。原 Fab 来源及许可保持在 `Content/ThirdPartyNotices/AzureDragonClaw.txt`。

实际完成程度以 `install-receipt.json` 和 `Saved/AzureDragonCoherentV9/delivery.json` 为准。后台编译、资产保存与运行观感分别记录；本轮未运行游戏、测试或渲染，交由用户测试。
