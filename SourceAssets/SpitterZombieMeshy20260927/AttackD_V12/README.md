# 普通攻击：Attack D / V12（2026-09-29）

**后续修订：** V14 将基础范围统一为 145 cm，V15 为三种近战有效命中追加一层共用中毒。下文“不增加中毒”等表述是当时制作范围；当前以根 README 和 MeleePoisonV15 为准。旧 Before 快照已归档到 trash。

用户选择动画包 Attack D 作为普通近战，按当前瘦长 Meshy 模型微调。完整源动作保留 2 秒、原速、单次播放；不是撕咬，也没有把 Attack A 加为随机或特殊技能。

## 制作内容

- 输入：ZombieAnimationPack 的 UE5 `anim_Attack_D`，经已有 UE 原生 IK 重定向输出 `LibraryMotionV7/Native/A_SpitterLibraryRaw_Attack_D.fbx`。
- 原 Meshy 网格、蒙皮、骨架父链、绿色材质不变；按原骨长重建姿态。
- 保留踏步、躯干转动、右臂挥抓及收势；肩臂的主运动取自 D，没有重新做向前推掌。
- 肘部增加最多 3 度屈曲，以固定局部弯曲轴避免接近伸直时翻转；右侧只在收势加入轻微前臂、手腕跟随，避免推迟主挥击。非攻击侧保留身体带动及小幅滞后。
- 根据当前蒙皮足底取样制作支撑段与双骨腿 IK；使用固定身高补偿，保留骨盆起伏和步内重心转移。足底修正作用于腿部，不随整张网格最低点上下抬动身体。
- 头颈部分补偿到攻击前方，保留源动作点头和倾斜；这是烘焙朝向，不新增运行时眼球跟踪，也没有独立手指动作。
- 起始 0.12 秒和末尾 0.35 秒衔接现有 Idle；不改攻击中间段的时间。仍由现有 AnimInstance 处理行走进入攻击的状态混合。

## 战斗合同

完整长度 2.00 秒，60 fps、121 个采样键；命中窗口 **0.47–0.67 秒**（秒值由现有战斗时钟使用，不取整数帧近似），一次近战命中，收势冷却 0.35 秒。保留蓝图当前伤害与攻击范围，不新增投射物、毒伤或根运动位移。朝向、遮挡、命中去重和受击打断继续沿用原生近战逻辑。

四种移动动画、出生时固定抽取动作与对应步速均不修改。

## 文件与接入

- `author_attack_d.py`：独立制作入口，后台 Blender 执行；不会运行旧 V7 攻击制作循环。
- `SpitterZombie_AttackD_V12.blend`：带原蒙皮的可编辑场景。
- `Final/A_Spitter_AttackD_V12.fbx`：UE 只提取动画，绑定现有 Skeleton。
- `install_attack_d.py`：导入动画、保存 `/Game/Monsters/SpitterZombie/BP_SpitterZombie` 的 AttackClip 与命中时刻，更新当前合同。
- `run_headless_import.ps1`：无编辑器时使用同一批次互斥运行无界面 commandlet；有活编辑器时使用现有 MCP 桥执行安装脚本。
- 正式动画路径：`/Game/Monsters/SpitterZombie/Animations/A_Spitter_AttackD_V12`。
- 保存前配置备份位于 `Before/`。保留旧 Attack A 资产，便于恢复。

**已完成导入与保存**：现有编辑器的 MCP 批次返回 `attack_d_and_blueprint_saved`，新动画及原蓝图已落盘；记录见 `installation.json`、`install-bridge-01.json`。实际保留伤害 30、基础范围 80 cm（既有全局距离倍率下 120 cm），四种移动引用及步速保持原配置。此次不改原生 C++，无需编译或重启。

本次最初的无界面导入在发现已有编辑器后停止，未写资产；随后改走现有编辑器桥成功保存。没有启动、关闭或重启编辑器。

未运行游戏、测试、渲染或视觉验收；由用户试玩确认。
