# 感染矿工：放大矿镐、拖镐与前倾砸地

2026-09-13。用户认可前一版单手挥镐方向后，要求矿镐增大 25%、待机和移动时拖在身后，并让攻击连贯地前倾砸地。本版以已认可 `PickaxeSingleHand/Delivery/InfectedMiner_Editable.blend` 为源，不恢复旧斧击或早期自编攻击。

## 模型与动作

矿镐的木柄和镐头整体围绕原握持点缩放 1.25 倍：柄长 0.96→1.20m，镐头跨度 0.72→0.90m。已认可的镐头方向延续；人物身体、手部几何、静止骨架、蒙皮、成组手指抓握及 PBR 材质保留。

待机、移动使用原躯干与腿部动作，左手移到侧后方，让镐尖贴近身后地面。腕部、前臂、上臂作为完整链进行局部姿态适配；骨长、绑定和手指姿态不重新制作。循环末帧回到各自首帧。

攻击延续此前 EBS 单手合成版本的举镐与前挥方向，起点、终点统一到拖镐待机姿态。前挥后半段增加从腰部开始的前倾，并将持镐手下压，使镐尖于动画约 0.8 秒接触地面；之后抬离地面、收回侧后方。腿部保留现有支撑，不通过整体压低模型制造砸地效果。

这是用户指定的动作适配：拖镐、接地和腰部跟随由本地制作，不能把整段称为未经调整的原生动捕。地面以角色局部平面为参考，尚未实现随坡面实时变化的地形 IK。

| 状态 | 时长 | 循环 |
|---|---:|---|
| Idle | 79/30s | 是 |
| Walk | 31/30s | 是 |
| Attack | 54/30s（1.8s） | 否 |

伤害窗口为 22/30–25/30s（约 0.733–0.833s），围绕落镐阶段；继续由既有权威战斗时钟执行 24 点单次伤害、150cm 范围、打断和死亡取消。没有引入另一套伤害计时器。

## 状态衔接

`UMinerStateAnimInstance` 使用切换时的当前姿态快照、Sequence Evaluator 和 0.16s 平滑混合。进入攻击时仍由已有战斗时钟直接指定动画时间；攻击末尾进入拖镐 Idle，在冷却中也保留待机动画。Idle/Walk 可从当前步态相位过渡，不直接跳到新片段首姿态。

`ANurseZombie` 仅提取三个可覆盖的动画播放、攻击定位、移动速率接口，默认实现沿用原行为。感染矿工覆盖这些接口使用混合呈现。受击仍使用现有 Combat 的单片段播放，恢复普通状态时重新接回矿工动画实例。

## 资产与制作入口

新 UE 目录 `/Game/Monsters/InfectedMiner/DragGround20260913/`，模型 `SK_InfectedMiner_DragGround` 和三动画 `A_Miner_DragGround_Idle/Walk/Attack` 绑定到原 `BP_InfectedMiner`。村庄仍通过原 `InfectedMiner_Village_01` 生成，不新增实例或改写地图。

本机交付目录 `SourceAssets/InfectedMiner20260913/DragGround/Delivery/` 包含可编辑 Blend、模型 FBX、三动画 FBX 和 `rebuild.json`。旧已认可版本继续保留。

1. Blender 执行 `Tools/InfectedMiner/author_drag_ground.py`：缩放矿镐、制作姿态与动作、导出。
2. 必要构建 `FPSGAMEEditor`，接入状态混合呈现。
3. UE Python 执行 `Tools/InfectedMiner/import_drag_ground.py`（可用 `-NullRHI`）：沿用原 Skeleton、材质、顶点色及 Physics Asset，导入新资源并绑定原蓝图。
4. 延续用户的动画预览请求：`render_default_preview.py -- --drag-ground` 和 `package_default_preview.py --drag-ground` 输出攻击预览；追加 `--state Walk` 输出移动预览。两个 GIF/MP4 位于 `DragGround/Previews/`。这些是离线模型预览，不能替代游戏内状态切换结果。

必要构建已完成，日志 `Saved/InfectedMiner/build-drag-ground-final.log`；资源接入日志 `Saved/InfectedMiner/import-drag-ground.log`。攻击与移动 GIF/MP4 已生成。

本轮未运行游戏、战斗或回归测试，由用户重启编辑器/游戏后在村庄试玩。脚本、元数据和相关代码发布到 Git；商店源资源、派生网格和动画二进制只留本机。
