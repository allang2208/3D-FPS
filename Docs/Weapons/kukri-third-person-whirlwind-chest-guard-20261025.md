# 弯刀旋风：外伸持刀臂与胸前护手

2026-10-25，用户否定既有旋风姿态，要求先修复旋风：持刀手外伸，另一只手架在胸前，整体自然。本轮制作 WhirlwindGuardV5，覆盖 Jason、Kaitlin 各自的 Start／Loop／End 三段。

## 姿态与衔接

- 右腕沿胸肩的侧外方向伸出，略向前、略低于肩；肩腕距离按每套身体真实臂长的 94.8%～95.8%设置，保留肘部弯曲，不锁直肘。
- 左拳置于肩中心前方约 18 cm、下方约 14 cm、向右约 3 cm（随身体比例调整），形成胸前护手；肘部向下、稍离身体，拇指朝上。握拳手指沿用已有原生手型。
- 肩胛小幅配合，双臂位置随当前胸部转动；以原生肩肘弯曲平面解算整臂，掌向沿实际前臂建立，前臂扭转辅助骨同步烘焙。
- 原生刀柄安装关系中刀尖轴与掌骨纵轴接近垂直，因此按自然腕姿持刀，不再强制刀尖和前臂完全共线。右臂外伸与握刀方向分别按真实关节及挂点处理。
- 起势左手先到胸前，右臂随后沿浅弧展开；旋转中只保留小幅随发力变化的松紧和高度变化。收势右臂先回收，左手稍后放松。三段使用一致衔接姿态，最后回到原待机。

本次改动限定于双侧锁骨、上臂、前臂、手腕和前臂扭转辅助骨旋转。既有躯干、重心、交替支撑脚、技能角度时钟继续作为身体动作基础；没有修改第一人称、伤害规则、旋风圈数或剑气参数。

## 文件和资产

制作目录：`SourceAssets/KukriWhirlwindGuard20261025`。`author.py` 读取原旋风作者数据和原生骨架，核对当前配置仍指向该制作输入，再生成两套 `*-actions.json`；旧版本及依赖输入保留。

新资产目录：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/WhirlwindGuardV5`。三段分别为 `A_Kukri_Whirlwind_Start_ExtendedGuard`、`A_Kukri_Whirlwind_Loop_ExtendedGuard`、`A_Kukri_Whirlwind_End_ExtendedGuard`，沿用现有 Cook 目录和 `NativeSwordGrip` 标记。

`save_assets.py` 通过既有命名互斥在后台保存新包；`publish.py` 使用 `Tools/PlayerBody/config_transaction.py` 仅更新两套角色的六个旋风字段。保存、配置接入和交付状态记录在 `assets-saved.json`、`published.json`、`delivery.json`。

六个新动画已保存，后台 commandlet 正常退出（exit 0），两套角色的六个旋风入口已通过配置事务接入。没有 C++ 改动，无需原生编译。未启动可视编辑器或游戏，未进行渲染、测试或观感验收。已有游玩角色的配置在 `BeginPlay` 读取，结束当前游玩并重新进入后加载新旋风入口。
