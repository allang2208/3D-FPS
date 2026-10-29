# 尼泊尔弯刀：Meshy 参考旋风第三人称

## 制作源

- 用户文件：`C:/Users/allan/Downloads/Meshy_AI_Gray_Full_Body_Manneq_All_Animations (1).glb`。
- 工程保留源：`SourceAssets/KukriMeshyWhirlwind20261025/Meshy_Gray_Mannequin_All_Animations.glb`。
- 使用动作：`Axe_Spin_Attack`，2.5 秒，一整圈；其余 Running、Walking、Sit_Lie_Bed、sleep 未接入。
- 原文件是用户提供的 Meshy 导出，不将其标为 CC0，也不据此推断公开再分发许可。

## 本次制作

为 Jason、Kaitlin 分别生成原生骨架的 Start／Loop／End，目录版本为 `WhirlwindMeshyV6`。

骨盆重心、脊柱、头部、跨步和脚部转动取自源动画。适配当前负向旋转时，镜像身体与步态并对应左右腿；右臂仍使用原始右臂的胸部空间运动节奏，再调整成向外展开的单手扫击。原斧击中双手跨胸、举斧的轨迹不直接用于单手弯刀。左手以胸前防护为中心，随源动作轻微起伏，肘部保留弯曲。

旋转仍是两圈，使用现有执行器的 `turnDegrees=-720` 和加减速相位。以源骨盆转向建立单调的取样映射，缩短源动作末尾回待机的停顿；骨盆处只剥离一次全局转向，避免 Actor 旋转与动画重复相加。第一人称、技能耗时、伤害、剑气和命中暂停未改。

源模型没有独立手指骨。右手按现有 Kukri 原生握刀姿态、实际掌心挂接和有限手指链 IK 生成握柄姿势；游戏现有装备手指层继续使用同一握持来源。左手使用原生握拳和拇指对握姿势。手掌沿前臂自然延伸，刀刃朝向由完整手臂和实际握柄坐标决定；没有把弯刀刀尖强行对齐前臂。前臂 twist 辅助骨一并生成。

左拳的前方距离使用两套实际身体网格的胸部包络制作；右手保持在身体外侧。起势、收势采用错开的落脚时间及胸部空间手部过渡，三段端点连续。

## 接入范围

只替换 `Content/ColdSteelData/player_body.json` 的六个字段：

- Jason：`clips.Kukri.FullBody.Whirlwind.Start`、`Loop`、`End`。
- Kaitlin：`body_variants.kaitlin.clips` 下对应三个角色。

使用 `Tools/PlayerBody/config_transaction.py` 按字段写入；旧 V5 资产和其他动作保留。

## 制作与交付记录

作者源和回执均位于 `SourceAssets/KukriMeshyWhirlwind20261025/`：

- `read_source.py`、`source.json`：读取 GLB、源文件 SHA-256 和 120 Hz 原始曲线。
- `author.py`、`*-actions.json`、`authoring.json`：原生轨道、源时间映射及接入前角色路径。
- `save_assets.py`、`run_commandlet.ps1`：通过现有 UE 批次互斥，在后台建立全新动画包。
- `assets-saved.json`、`save_assets-commandlet.json`：实际保存路径及 commandlet 退出状态。
- `publish.py`、`published.json`：六个动作角色的本地接入事务。
- `delivery.json`：本次完成状态；本地接入不代表 Git 发布。

本次不启动 UE 编辑器或游戏，不执行运行测试、截图或渲染验收。完整服装组合下的穿插与实际播放自然度仍由用户体验确认；不以数学约束或资产保存代替实机观感结论。开始新的游玩实例后，可通过 F6 第三人称／固定第三人称查看当前配置动作。
