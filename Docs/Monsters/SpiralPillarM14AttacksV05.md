# 螺柱 M-14 — V05 喷吐与根裙横扫

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。用户授权先制作喷吐与横扫。新增动作、战斗逻辑及蓝图配置已落盘，Editor/Game 后台构建完成；未游戏测试。

## 动作与玩法

| 攻击 | 选择条件 | 时序 | 初始数值 |
| --- | --- | --- | --- |
| 原咬击 | 正面、中心距离不超过 235 cm | 保留 V03 的 1.9 秒动作及 0.86 秒接触 | 原伤害 48、口器范围 105 cm、冷却 3.2 秒 |
| 囊压喷吐 | 正面、400–1000 cm、有口器视线、独立冷却结束 | 2.4 秒；0.65 秒锁定瞄准点；1.10 秒从实际口器发射；释放后收势 | 伤害为物攻 ×0.75，速度 1000 cm/s，弹体行程 1100 cm；减速 25%、2.5 秒；冷却 7 秒 |
| 左右根裙横扫 | 目标偏侧 30–155 度、中心距离不超过 250 cm、脚底高度接近 | 2.2 秒；0.80–1.20 秒接触；选择对应一侧三组根须，起手后锁定朝向 | 物攻 ×0.9；每名玩家每次攻击只受伤一次；共用横扫冷却 4.8 秒 |

横扫的 250 cm 是选择攻击的上限；实际命中仍由正在运动的根须骨段扫掠决定。抬根预警、另一侧支撑、转动及伸出、回收分别制作，使用原骨架与连续权重，根须不使用骨骼缩放。

喷吐瞄准点锁定后不跟踪玩家；近距离仍使用咬击，拉远时喷吐，侧面近身时横扫。行为树保留唯一决策入口，角色只执行选中的攻击时钟。喷吐冷却期间继续追击，不远处站桩等待。前摇可被既有控制打断，死亡停止后续释放并清除本怪物在途弹体。

## 制作边界

- 沿用 V03 Blender 母版，新增三段动画，保留模型、UV、权重及旧动作；V02 死亡与 V04 咬击范围不替换。
- 黏液复用现有流体材质、世界液滴／飞溅池；只接入直接伤害和现有减速状态，不附加中毒、毒池或爆炸。
- 新增专用弹体，命中采用扫掠，实体遮挡和玩家胶囊均参与；装饰雾体不拦截伤害。
- 动画资产、蓝图配置、原生代码和必要 Editor/Game 构建后台完成，不自动打开编辑器或游戏，不运行测试。

## 落盘结果

- 新增并保存 `A_M14_Spit_v05`、`A_M14_RootSweep_PosX_v05`、`A_M14_RootSweep_NegX_v05`，均位于 `/Game/Monsters/SpiralPillarM14/Animations/`。
- 已保存现有 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14` 的三段动作、黏液材质及攻击参数。继续从 F6「螺柱 M-14」入口生成。
- `SpiralPillarM14Attacks.cpp` 承接技能选择、锁定、释放和根须采样；`M14MucusProjectile` 完成弹体、遮挡、直接伤害、减速与特效。共享战斗组件只将 M14 停距转交其距离选择函数。
- 角色中心到目标距离用于选择攻击；横扫命中使用三条根须的实际骨段、18 cm 厚度和目标碰撞形体，每名目标每次横扫只结算一次。单位与左右方向从模型参考骨架转换，不依赖 FBX 左右命名猜测。
- 横扫接触窗口按源动画 30 Hz 采样，默认每次攻击 13 个接触样本，每个样本最多 3 次骨段查询；没有全场角色扫描或新增角色 Tick。
- 每只怪物通常最多一枚在途黏液，默认最大存活约 1.25 秒；每 0.065 秒请求尾滴，每帧最多补发 4 次，复用世界池的 192 液滴、48 雾片、40 湿痕。湿痕仅装饰，不造成持续伤害。
- 减速通过现有状态系统生效、到期和净化；不直接改写玩家基础移动速度。死亡／销毁清除本怪物的在途弹体，受控切换取消未释放攻击。
- 初次 Editor 构建遇到并行共享字段尚未落盘的错误；字段补齐后完成普通 Editor/Game 构建，没有改动相关唐刀实现。
- 导入脚本及所有请求的资源保存成功后，commandlet 在退出清理时于 `URuneSwordComponent` 析构报访问异常，进程退出码为 3。记录为保存完成后的进程异常，不称作整个导入进程正常退出；未修改符文剑代码或进一步排查其根因。[进程回执](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Records/import_process.json) 与 `import_ue_console.txt` 保留完整状态。
- 未启动 UE 图形编辑器、游戏、PIE、截图、渲染或测试；动画观感、实战命中与平衡由用户体验。

制作源：[Blender 母版](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Authoring/M14_Rigged_Animated_v05.blend)。

重建入口：[动作制作](../../Tools/SpiralPillarM14/author_attacks_v05.py)、[后台导入](../../Tools/SpiralPillarM14/import_attacks_v05.py)。

落盘回执：[动画导出](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Records/authoring.json)、[UE 资产保存](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Records/ue_revision.json)、[Editor 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Records/build_FPSGAMEEditor.json)、[Game 构建](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV05/Records/build_FPSGAME.json)。
