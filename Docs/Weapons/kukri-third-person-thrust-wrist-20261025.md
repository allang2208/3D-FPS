# 弯刀第三段突刺左腕修订

2026-10-25，针对第三人称三连击最后突刺的左腕扭曲，修订 Jason 与 Kaitlin 两套原生身体动画。

后续状态：用户反馈本版本仍不自然，未认可为完成版本。后续改为迁移原始突刺的完整左臂动作，见 [ThrustSourceArmV6](kukri-third-person-thrust-source-arm-20261025.md)。下述骨姿态数值仅保留为 V5 的制作记录。

## 原因与范围

当前 `Kukri.FullBody.Thrust` 指向 ThrustFistV4。该版本仅修了握拳手指，沿用了 ComboV3 的腕部曲线：左腕抬到护拳位置时，掌向仍固定为待机时朝下的组件空间方向。前臂已经向上，手掌却向下，形成接近直角的折腕和明显轴向扭转。

本次按用户要求读取了当前资产的 SOURCE 轨道及 COMPRESSED 骨姿态。两条路径都出现相同折腕：Jason 最大约 99.18°，Kaitlin 最大约 103.56°。问题已存在于制作曲线，压缩不是本次异常的来源。数值定义为肘到腕的方向与腕到中指掌骨根部方向的夹角，不是手指弯曲角。

## 修改

- 用每套原生骨架的掌面基底建立前臂相对腕姿，护拳随前臂方向抬起。
- 起势、蓄势、发力、缓冲、收回分别设置球面插值曲线；护拳阶段保留 3°～6°的小幅屈腕和轻微滚转。
- 重新烘焙左前臂两根扭转辅助骨，消除旧腕姿留下的扭转。
- 保留 V4 握拳手型、完整肩肘腕位置、右臂与刀路、躯干、双腿、攻击时钟和首尾姿态。

只修改 `hand_l`、`lowerarm_twist_01_l`、`lowerarm_twist_02_l` 的旋转轨道。新作者曲线接触帧的掌臂夹角约 3°，全段最大约 25°～26°位于原始衔接端；这些骨姿态读数不能代替用户的游戏观感验收。

## 制作与接入

作者目录：`SourceAssets/KukriThrustWrist20261025`。

- `prepare.py`：读取当前突刺的源轨道及问题骨骼压缩姿态，不修改已有包。
- `author.py`：生成两套修订动画及 `authoring.json`。
- `save_assets.py`：保存独立 ThrustWristV5 动画包，保留旧 V4。
- `publish.py`：通过 `Tools/PlayerBody/config_transaction.py` 仅替换 Jason 与 Kaitlin 的 `Kukri.FullBody.Thrust` 两个字段。

新资产位于 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/ThrustWristV5/A_KukriCombo_ThrustNaturalWrist`，沿用原有 Cook 目录及 `NativeSwordGrip` 标记。

两套新资产已保存，后台 commandlet 正常退出（exit 0），两个突刺字段已通过配置事务接入。回执保存在本目录的 commandlet、assets-saved、published、delivery 文件中。本轮无需修改 C++ 或重新构建。

配置由 `UFPSPlayerBodyComponent::BeginPlay` 读取，当前已在游玩的角色不会自动切换；结束本次游玩后重新进入即可加载新入口，无需为本修订重启编辑器。未启动可视编辑器或游戏，未进行新动画的运行或画面测试；由用户使用 F6 第三人称／固定第三人称体验。
