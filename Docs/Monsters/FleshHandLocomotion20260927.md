# 大小手移动僵硬修订

用户反馈移动僵硬，沿当前绿色皮肤手、掌心正面与腕部着地姿态调整。作者源显示旧 Walk 用小幅腕部旋转、腕骨缩放与整组手指同步摆动；本次将表现重点改为交替承重、掌部滞后与指节松弛。不改移速、骨架、权重、掌心朝向、碰撞、导航、攻击、冲锋和受控动作。

## 新动作

- 大手 `A_FleshHand_WalkWeighted`：69 帧／60 Hz，即 1.15 秒循环。腕部左右滚动最大 6.8°，推进前倾与回弹错开；掌部反向滞后，手指从食指至小指依次延迟，远端指节再落后于近端。源模型根部左右偏移不超过 1.8 cm，额外抬升不超过 1.8 cm；大手缩放 2 后分别为 3.6 cm。
- 小手 `A_FleshHand_WalkScurry`：42 帧／60 Hz，即 0.7 秒循环。承重、横摆和抬升幅度为大手源动作的 64%，循环更快，按现有缩放 0.65 呈现轻快小步。
- 全骨骼缩放恒为 1，取消旧移动动作中的腕骨缩放。保留张掌轮廓与自然微屈，不复用冲锋的闭拳姿态。
- 每帧在 Blender 源网格上计算最低点，将接地补偿转换到根骨局部坐标；游戏中不进行顶点扫描、额外射线、IK 或布娃娃。循环由周期函数生成，密集线性关键帧避免插值过冲；无持续前向根位移和 root-motion 提取。
- 旧 `A_FleshHand_Walk` 和原作者文件保留；新动作以两个独立资产绑定到大小手 `MoveClip`。

## 播放衔接

仅修改 `AFleshHandMonster::SetState` 与其移动播放率下限，复用现有 `UFatZombieAnimInstance` 的可选循环过渡参数，不改变共用动画实例或其他怪物行为。

追击与返回共用同一移动片段，二者切换保留当前相位和播放率。起步时继续播放出场待机循环，再混入当前移动片段；停止时原移动循环在混合过程中继续推进。大手起步混合 0.20 秒／停止 0.24 秒，小手 0.14／0.18 秒。受击、攻击等打断仍从实际姿态快照衔接。

大手普通速度 259.2 cm/s、参考速度 216；小手 324 cm/s、参考速度 270，保持满速播放率 1.2。低速播放率下限由 0.6 降至 0.15，仍使用既有播放率平滑，减轻低速时动作频率与位移脱节。这里只调整动画表现，不添加转向/位移力，不改原有制动逻辑。

## 制作与接入

- `SourceAssets/FleshHand20260926/author_locomotion.py`：制作两段骨骼循环、导出 FBX，保存 `Locomotion/FleshHand_Locomotion.blend`。
- `install_locomotion.py`：导入新片段，处理既有 FBX 根单位约定，仅保存两个蓝图的 `MoveClip` 引用。原蓝图保留于 `Locomotion/BeforeAssets/`。
- 完整 `install_ue.py` 最后调用移动安装器，避免原始动作全量重建覆盖新绑定。
- 生产回执 `Locomotion/authoring.json`、`Locomotion/installation.json`；构建与导入日志同目录。

本次常规构建返回 `Succeeded / Target is up to date`（`Saved/BuildEditor/build-20260927-135022.log`）；后台 Python commandlet 已导入两个动画并保存两个蓝图（`Locomotion/import.log`，退出码 0，`Locomotion/installation.json` 为 `assets_saved_and_bound`）。

未主动打开编辑器或启动试玩、截图、渲染、性能采样。离线接地计算属于动作制作，不代表真实场景坡面、转弯或画面验收；最终观感交由用户测试。
