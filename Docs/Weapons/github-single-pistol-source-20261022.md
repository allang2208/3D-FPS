# 单持手枪改用选定 GitHub 动作源

用户选择 [ZenXChaos/ThirdPersonShooter-AnimationSets](https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets)，不购买此前推荐的Fab包。源固定到 `f19adc2ece4cab0f89c9236223abb97d4d2badea`，原始FBX、README和Unlicense已保留，许可副本在 `Content/ThirdPartyNotices/ThirdPersonShooter-AnimationSets-Unlicense.txt`。

## 范围

替换五款支持手枪的第三人称右手单持、左手单持的待机／移动上身、开火及换弹。第一人称手臂资产和双持Twinblast路线不变。混合装备下法杖／书加副手枪及近战、施法、进食、翻越等外部动作仍保留原来的所有权。

## 资产制作

- 源有11段站姿／蹲姿待机、移动、射击及换弹Init/Loop/End。原文件为FBX 6000，只带有权重点、没有多边形；用引擎配套Autodesk FBX SDK保留轨道并转成FBX 2014，制作仅用于导入的骨架载体。载体不会成为玩家模型。
- 原始站姿换弹收尾与蹲姿换弹起手使用不同局部骨轴，不能直接复用Idle的源Skeleton。两者分别保留源绑定后重定向；其余9段共用原Idle源绑定。
- FK重定向保留完整肩、上臂、前臂、手腕和手指，关闭IK目标求解。目标目录为 `/Game/Characters/JasonPlayer20261003/GitHubSinglePistol20261022/Retargeted`。
- `player_body.json` 仅增加／更新11个 `SinglePistol.Source.*` 叶键，使用配置事务写入器；Cook只显式引用重定向输出目录。

## 运行接入

- `FPSBodySinglePistolSourceLayer.inl` 在现有腿部步态之上播放完整源上身，开火取原射击片段的局部旋转差量；动作切换混合完整姿态。
- 单持源生效时，跳过 `PistolHandTarget`、通用腕点两骨IK、`FitStaffArm`、`FitLeftPistolCarryFromRight` 和 `FitSinglePistolReload/Arm` 等旧腕臂覆盖。瞄向通过完整上身转动实现。
- 左手主握镜像整个本地骨链及辅助骨。只让持枪手指沿用对应枪的握把适配，操作手保留源手指。
- 左右换弹都使用现有动作时钟；左轮逐发复用Init/Loop/End，循环次数来自原换弹计划。主手单持补齐已有 `RightHand` 展示字段，与副手使用相同数据格式，没有新建补弹事务或改写伤害协议。

## 状态与边界

源是左轮动作家族，普通弹匣枪复用其完整手臂动作并沿用原机械时钟，不等于源包天然包含每把半自动手枪、弹鼓、弹巢及装填器的精准接触。没有把这一点写成已验收。

本轮未启动GUI编辑器、游戏、PIE、截图、几何回归或主客机测试。资产保存、配置接入与编译回执在 `SourceAssets/GitHubSinglePistol20261022/`；最终完成状态由该目录的 `delivery.json` 单独记录，用户视觉认可未取得。

## 落盘结果

- `import-source-06` 正常退出0：源骨架依赖及11段原始动作保存完成。
- `retarget-02` 正常退出0：共用绑定的重定向保存完成；随后发现并分离两段特殊绑定。
- `retarget-end-bind-02` 正常退出0：站姿收尾和蹲姿起手分别从自己的Skeleton重定向并保存。为避开正式Editor链接，使用已有独立模块副本，仍经共用资产批次互斥，只写本次新目录。最终运行模块由下列正式构建生成。
- `published.json` 记录最终11个角色键、目标uasset散列及配置事务回执，两段特殊绑定均引用修正版。
- 原两段错误共用绑定输出移至 `trash/github-single-pistol-bind-20261022/`，源／目标和散列见 `retired-common-bind.json`；不保留在显式Cook目录内。
- 正式Editor：`build-editor-02.log`，Succeeded，42.79秒。正式Game：`build-game-01.log`，Succeeded，7.90秒。
- 本轮编译时修正了动画求值器类型，应使用项目现有的 `FAnimNode_SequenceEvaluator_Standalone`。全项目另一阻塞位于 `MonsterRagdollPhysics.cpp`：UE5.8 `GetBodySetup()` 返回基类，不能直接访问 `AggGeom`；仅补充到现有 `USkeletalBodySetup` 的类型转换，未调整怪物物理参数，修改前文件已保存。

上述为制作、保存、接入和编译结果，不是游戏动作自然度或联机验收结果。
