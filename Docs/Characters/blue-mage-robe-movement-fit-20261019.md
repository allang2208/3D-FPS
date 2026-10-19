# 法袍移动后腿靴穿出排查

范围：用户提供的双手锤上下楼梯后腿靴穿出截图，以及弓、长枪、手枪、法杖、近战和采集工具移动时共享的下肢/衣物路径。保持当前收束腰胯、完整小腿、鞋靴和第一人称手臂。

## 已定位的保护缺口

- 旧足部碰撞仅为 foot 到 ball 之间的 4 cm 内缩胶囊，未覆盖鞋底、后跟和鞋尖。五种实际鞋靴的单侧源网格有 6.6–11.4 cm 的最大超出；原始数据见 `SourceAssets/BlueMageRobe20261018/MovementFit20261019/foot-collision-before.json`。
- ball 脚趾骨没有自己的碰撞体。落脚修正会改变脚趾卷曲，鞋尖蒙皮继续跟随 ball，而原碰撞仅随 foot。
- 22 个现行小腿内层中，锁子甲三种裤脚的外沿距小腿轴可达约 11.39 cm，超过旧 9.3 cm 范围；ST6、牛仔与工装也有少量小腿边缘超出候选 9.7 cm。此项记录在 `calf-underlayer-coverage.json`。
- 楼梯足部抬升在 `FPSBodyGrounding` 中上行立即应用、下行缓动；现有连续碰撞已启用，但每帧只有两次布料分步。该差异会增加抬脚经过裙摆时的碰撞采样压力。

截图证明实际穿出；上述源数据证明保护范围存在缺口。尚不能把源碰撞包络检查当作完整 Chaos 动态复现。

## 武器路径矩阵

| 武器分支 | 移动下肢来源 | 上身独立层 | 法袍/裤鞋更新 |
| --- | --- | --- | --- |
| 双手锤 | Warhammer 八向 Walk/Jog，缺失时走共用回退 | Warhammer 持握和动作 | 共用最终身体姿势 |
| 长枪：步枪、冲锋枪、霰弹枪、机枪、狙击枪 | Rifle 八向 Walk/Jog | 本枪握持与机械动作 | 共用最终身体姿势 |
| 手枪、左轮、双持手枪 | Pistol 八向 Walk/Jog | 主副手动作 | 共用最终身体姿势 |
| 弓 | Unarmed 八向 Walk/Jog | Sparrow/Bow 持弓层 | 共用最终身体姿势 |
| 法杖及法书副手 | Unarmed 八向 Walk/Jog | Staff/Book 整臂层 | 共用最终身体姿势 |
| 剑及其他近战 | Unarmed 八向 Walk/Jog | Sword 整臂与动作层 | 共用最终身体姿势 |
| 斧、镐、其他采集工具、空手 | Unarmed 八向 Walk/Jog | Tool/Unarmed 手部层 | 共用最终身体姿势 |

蹲行八方向同走 Crouch；楼梯落脚修正位于共用的 Grounding 与最终姿态输出。依据为 `FPSPlayerBodyActions.cpp`、`FPSPlayerBodyBow.cpp`、`FPSPlayerBodyAnimInstance.cpp` 的实际 Family 和 Clip 选择，不按武器名称猜测。

世界身体是 Owner 身体与裤鞋的 Leader Pose 源；法袍使用 CopyPose 加同一源 Tick 前置关系，保留自己的布料求解。现有代码未发现双手锤分支单独使用旧腿部姿势的入口。截图问题涉及的碰撞缺口同时影响上述分支。

## 本轮制作

足部改为完整后跟至鞋尖的碰撞胶囊，Jason 半径 9 cm、Body 半径 8 cm（按源身体尺度换算）；独立 ball 球体半径分别为 7/6 cm，随脚趾骨一起求值。Jason 小腿半径调为 11.7 cm，Body 保留 11 cm；腰胯和大腿碰撞不变。布料 CCD 保留，分步从 2 改为 4，其他布料参数和可见几何不变。

`save_assets.py` 将布料作者版本纳入续跑条件，防止网格 SHA 不变时误复用旧物理资产。四个新身体资产另存到 `MovementFit20261019/Body`；发布脚本只替换世界/Owner 的 Body/Jason 四条引用。保留旧 HipFit 资产与所有现行 underlayer 映射。

## 证据与状态

- 输入截图、旧 C++ 和目录快照：`MovementFit20261019/Before/`。
- 真实源动作采样：`source-movement-poses.json`；入口 `Tools/BlueMageRobe/inspect_movement.py`。
- 五种鞋靴源蒙皮与碰撞包络对照：`footwear-movement-comparison.json`；入口 `analyze_movement.py`。数据范围为源序列采样，未运行实际楼梯或 Chaos 布料模拟。
- Body 原生小腿/足部覆盖：`body-native-coverage.json`。
- 新资产回执：`saved_assets.json`；发布回执：`published.json`。以实际 completed 字段区分制作、保存与接入。

离线对照已完成：81 个源序列，每条 17 个时刻，共 1,377 个姿势。Unarmed、Rifle、Pistol 各 17 条，Crouch 9 条，Warhammer 19 条，Staff 与 Bow 持握各 1 条。每种鞋靴取约 1,600 个分布顶点并加入极值点，使用完整原生骨骼权重求值；各组新的超出采样点数均为 0。五种鞋靴的全顶点静态检查也均为 0 超出，最小保护余量约 0.45 cm；22 个内层小腿的全顶点截面检查从旧范围的 70,439 个超出点变为 0，见 `calf-underlayer-final-comparison.json`。Body 原生小腿/足部 7,412 个顶点同样处于新范围内。

该对照检验的是实际作者源蒙皮与碰撞体的覆盖关系。楼梯运行时 Grounding、停止移动后的布料状态、最终画面仍属于游戏内动态验收，未由上述数字替代。

## 已完成的接入

`movement-build-02` 的 FPSGAMEEditor 与 FPSGAME 均成功。首轮 Game 构建遇到共享 `FPSPlayerBodyTypes.h` 源行号与生成头文件不同步；重新生成反射代码后完成构建，未改动该共享头文件。资产批次 `movement-import-03` 返回 0，四个 Body/Body_Owner/Jason/Jason_Owner 身体均保存 3 档 LOD，并从实际 ClothConfig 读回 `SubdivisionCount=4`。插件配置通过 ClothConfigBase 返回时，读取使用反射原名 `SubdivisionCount`。

`publish_movement_fit.py` 已发布四条新引用，`saved_assets.json` 与 `published.json` 的 completed 均为 true，calf_underlayers_unchanged 为 true。现有裤鞋、完整小腿、腰胯/裙摆造型、第一人称衣袖与武器动作均保留。此次修订的源码、构建产物及正式 UE 资产已落盘；未启动游戏做楼梯动态或画面验收。

不启动编辑器或游戏，不把后台构建、静态包络或源姿态采样宣称为游戏中的零穿模验收。
