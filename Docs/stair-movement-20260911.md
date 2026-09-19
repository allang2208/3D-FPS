# 自动上阶和墙边测试楼梯

## 范围

`UFPSCharacterMovementComponent` 替换玩家的原生移动组件实例；自动上阶上限由 50 cm 改为 40 cm。沿用 UE 的 `StepUp` 胶囊扫掠、顶部净空、可行走坡度、组件上阶权限及失败回滚。没有额外水平位移，没有自动跳跃，也不调用手臂攀爬动作。40 cm 以上可使用已有跳跃/攀爬规则。

第一人称相机与持枪模型挂在独立 `StairVisualRoot` 下。只补偿成功上阶与贴地修正的离散高度变化，以 cm/s 为单位线性归零，连续台阶可以累计；停止后准确回到零，不用弹簧。常规最低补偿速度 220 cm/s，随水平速度提高到其 0.75 倍。斜坡主体运动、移动平台、蹲伏胶囊变化、跳跃和落地不作为台阶修正。传送清除残余补偿。

碰撞体仍执行 UE 的离散安全上阶；连续线性过渡作用于本地第一人称视角和手臂。这与旧 Godot 的碰撞/视角分层方法一致，不能把视角平滑称为胶囊本身沿斜线移动。当前单机验收；没有新增 RPC。台阶起跳的判定修正位于原生移动组件，在执行物理的角色上同样生效，不依赖本地镜头偏移。

额外修复台阶起跳：记录上一移动帧是否有向上的台阶修正；若从该状态主动起跳，仅在上升期间拒绝把圆角接触当成有效落地，继续走原生碰撞滑动。下降后恢复原生落地判断，普通平地跳跃不受该条件影响。

## Godot 参考

从当前仓库标签 `archive/godot-before-ue5-20260910` 读取 `scripts/player.gd` 的 `STEP_HEIGHT=0.5`、`_try_step_up`、`_try_step_down`、`stair_visual_displacement`。旧实现上/前/下测试后还会多前移一个胶囊半径，本轮使用 UE 原生行走距离，不移植额外前移。

## 测试场地

执行 `Tools/SceneTests/create_stair_course.py` 可在 `/Game/GameMaps/DayNight_Lighting` 的 `TraversalTest_High` 侧边创建或更新测试区：

- 蓝色六级楼梯：每级 20 cm 高、60 cm 深、220 cm 宽，总高 120 cm，顶部有平台。
- 黄色 40 cm 对照块：按住前进可以直接通过。
- 红色 45 cm 对照块：不能自动上阶，需要跳跃。

场景对象统一在 `Movement/StairWalkTest` 文件夹；脚本按标签更新，重复运行不生成副本。几何与材质均为本轮使用 UE 基础方块创建，无外部素材依赖。场景坐标记录于 `Saved/StairMovement/course.json`。修改前的地图及 SHA-256 留在 `Saved/StairMovement/Before`。

## 复现与数据

`Tools/SceneTests/run_stair_acceptance.ps1 -RunId <唯一名称> -Hz 60 -Render` 启动真实游戏和隔离存档，经 PlayerController 注入 W/Shift/Space 输入。14 组用例覆盖 20/40/40.5/45 cm、连续上下阶、斜向、冲刺、蹲伏、低天花板、跳跃、停止、斜坡、禁止上阶组件。每帧输出实际胶囊/镜头位置、偏移和速度到 `trajectory.csv`，结果及实机帧在同次运行目录。另以 30/120 Hz 检查帧率影响。

初始失败点：默认相机直接挂在胶囊上，`StepUp` 和 `AdjustFloorHeight` 的高度修正在一帧内传给相机；相机自身的相对位置插值不能抵消父节点跳高。

## 验收结果

- 主宿主 `FPSGAMEEditor Win64 Development` 已成功编译。最初并行怪物模块缺失实现，使用临时目录完成一次隔离构建；实现到齐后回到主宿主成功编译。临时目录及散列清单已归档到 `trash/stair-movement-20260911`。
- 为解除主宿主的编译阻挡，对并行 `PoisonMaggotMonster` 仅拆开多变量 `static constexpr` 声明，并将伤害参数 `Instigator` 及函数内对应引用更名为 `EventInstigator`，避免 MSVC DLL 导出和继承成员遮蔽错误；数值与行为不变。
- `render60-v2`：14 组、95 项检查，零失败，进程退出 0。
- `render30-v2`：14 组、95 项检查，零失败，进程退出 0。停止用例明确检查松开后制动停止，而非要求已经松键的角色强行继续走到整级顶部。
- 60 Hz 的连续上下楼梯最大镜头高度速度均为 337.5 cm/s（每帧 5.625 cm），水平速度不超过原来的 450 cm/s；冲刺对应 525 / 700 cm/s。独立斜坡用例的台阶偏移为 0。
- 原有墙面实机回归 `stair-regression`：4 组翻越/登台/攀高墙用例零失败，进程退出 0。
- 120 Hz 起跳失败并非按键持续时间：统一 60 ms 后仍能复现。`jump120-probe.log` 记录 `STAIR_JUMP accepted=1 ... vz=650`，同一帧随后出现 `STAIR_UPWARD_LANDING ... vz=633.34`，接触台阶上沿 `(50200,0,10040)`。因此修正 `IsValidLandingSpot` 的上升期台阶接触，而非添加自动跳跃或延后输入。
- 修正后的 `accepted-120`、`accepted-60`、`accepted-30`：各 14 组、95 项检查，均零失败，进程退出 0；最终合计 285 项通过。
- 一次复测在游戏开始前被既有 NiagaraEditor `EdGraphPin::OwningNode` 断言中断，保留日志并重跑；它没有被计入玩法通过结果。
- 测试地图已保存，六级楼梯起点 `(1029.94, 270.03, 0)` cm，黄色对照块中心 `(829.94, -129.97, 20)` cm，红色对照块中心 `(1259.94, -129.97, 22.5)` cm。创建脚本输出 `STAIR_COURSE_SAVED` 并写回地图；commandlet 退出 1 来自工程已有 `GameFeatureData` 资产管理配置报错，未作为玩法验收通过依据。
- 首次 `-nullrhi` 游戏测试在既有 `UColdSteelWeaponIcons::Readback` 崩溃，后续全部采用真实渲染。没有修改武器图标系统。60 Hz 动画预览和轨迹图为 `Saved/StairMovement/stairs-runtime.gif` 与 `trajectory.png`。
