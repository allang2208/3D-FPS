# 普通竖劈与冲刺竖劈：左右臂上下握位对调

> 后续用户反馈左手没有完整抓住握柄。左右上下握位保持本版顺序，左手接触继续修正，见 [左手握柄接触](third-person-sword-left-contact-20261010.md)。本版不视为最终姿态已获认可。

用户明确指出前两版仅修改拇指／握距没有解决手臂交叠，要求交换两条手臂的位置。本版限定两个竖劈动作，将左手放到靠护手的原上握位，右手放到靠柄尾的原下握位。

## 制作

源为 `SourceAssets/ThirdPersonSwordGripPair20261010/candidate-actions.json`，制作脚本为 `SourceAssets/ThirdPersonSwordArmSwap20261010/author_arm_swap.py`。

逐帧恢复已有刀身坐标系，交换左右腕沿剑柄轴的高度；右手向柄尾移动约 12.4 cm，左手向护手移动相同距离。保留各手自身原有的组件空间朝向，按各自肩部及原生骨长求最近的肘弯解，再写入左右上臂、前臂、手腕和扭转／修正辅助骨。未直接交换左右骨骼的局部旋转。

两段数据均为 120 Hz、193 帧。身体、腿、手指及原有动作时序沿用制作源，刀身轨迹由挂接补偿保留。

## 运行时接入

新增 `SwordGripSlide` 曲线，记录右手相对默认握位的柄轴位移。`FPSBodySwordPose.inl` 将该曲线与动作过渡、动作权重一起混合，在无动作及法杖分支输出零值。`FPSPlayerBodyMotion.cpp` 在骨骼更新后，以原生刀身枢轴同时抵消右手绕柄旋转和轴向位移。

独立资产目标为 `/Game/Characters/JasonPlayer20261003/KwangSwordArmSwap20261010/Animations/J_Kwang_Overhead` 和 `J_Kwang_DashOverhead`。保存脚本：`Tools/PlayerBody/save_sword_arm_swap20261010.py`；发布脚本：`Tools/PlayerBody/publish_sword_arm_swap20261010.py`。仅在两段资产已保存、运行时支持完成构建后切换 `player_body.json` 的两项引用。

## 当前状态

制作源及 C++ 修改已落盘。编辑器于接入期间自行退出，最初的远程保存连接未建立，随后改用后台 Python commandlet 保存，未重新启动可视编辑器。

两段动画均已保存，`assets-saved.json` 为 `complete: true`；`save-commandlet.log` 记录两段保存成功、`Success - 0 error(s)`，进程退出码为 0。仅两个竖劈引用已通过发布脚本切换，`assets-published.json` 保留前后引用。

工程已完成的 `Saved/BuildEditor/build-20261010-183443.log` 包含本次落盘后 `FPSPlayerBodyMotion.cpp`、`FPSPlayerBodyAnimInstance.cpp` 的编译及普通 `UnrealEditor-FPSGAME.dll` 链接，最终 `Result: Succeeded`。复用该构建结果，不重复提交构建。

未启动游戏、未做预览渲染或自测；编译和保存成功不代表姿态效果已获认可，普通竖劈与冲刺竖劈的实际效果交由用户测试。
