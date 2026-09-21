# 巫婆 V04：可保留外观、人体、长袍与动作分层

2026-09-20。用户否定 V03 的穿裙、僵硬和悬脚后制作的新候选。V03 是历史失败方案，不能作为已认可步态或身体模板。未启动 PIE、测试或验收渲染。

## 保留资产的实际拆分

`Authoring/LayeredV04/Preserved` 中每项有独立 `.blend` / `.fbx`，沿用同一坐标与原骨架：

- `Hat`：帽子；`Head_Hair`：头部与头发。
- `Hand_Left` / `Hand_Right`：原始左右手，各自独立。
- `UpperRobe`：原上袍、袖子；`LowerRobe_Reference`：原下袍参考，保留原始拓扑与 UV，不再作为游戏下半身。
- `Staff` / `PoisonBottle`：独立道具。法杖采用 V02 已居中握点的源文件。
- `Original_Uncut.blend`：未切分母版，保留恢复边界。
- 原始 PBR 贴图和 `source_partition.json`：原始面/顶点索引可追溯。头发仍与头部分组，不能宣称已逐根拆发。

`Fitted` 中另外保存用于 V04 的各层 `.blend` / `.fbx`。左右手游戏层沿用 V02 局部蒙皮/卷握修形，与上述原始保留层分开；没有新增手指关节。

## 人体和衣服

采用工程已存在的 Nurse 女性脚/小腿拓扑与蒙皮，替换 V03 的简化腿管及融合脚。护士源模型在裙子遮住的大腿与膝部缺面，因此隐蔽部位改用本地 Epic Quinn 的腿/膝拓扑，按巫婆骨段配形并映射到原 24 骨。身体来源、原始权重和拟合脚本保留；不能称为一键保留完整护士人体，也不是 Meshy 新生成的人体。

外层下袍重建为连续、开口的 2640 顶点网格，独立几何、独立材质槽；上端压在保留的上袍下，腰部固定，下摆留运动空间。重投影原巫婆基础色、粗糙度与金属度，沿用灰褐旧布风格。旧 UV 的切线法线不直接复制到新 UV；Blender 源使用粗糙度细节的微弱凹凸，UE 当前采用实际褶皱几何和投影 PBR。原头、帽、手与上袍保留原 UV、材质和分裂法线。

UE 使用引擎自带 Chaos Cloth，不依赖 KawaiiPhysics 或付费 Fab 插件。腰部固定带、逐渐放开的 MaxDistance、腿部碰撞、CCD 与自碰撞在 `AWitchMonster::PrepareCombatPhysics` 中制作并保存到 V04 专属资产。布料是实时模拟，未对其运行稳定性和性能进行测试。

## 动作和接地

干净来源为本地 `ANMS_ZombieFemaleWalk01Forward`，工程已有 `Saved/NurseZombie/locomotion-contact-sheet.jpg` 提供步态参考。`Tools/Witch/retarget_layered_v04.py` 创建 UE 原生 IK Rig / IK Retargeter；未拟合的重定向 FBX 保留在 `RetargetedRaw`。最终动作另存，未覆盖来源动作。

行走保留源骨盆、脊柱与左右腿运动，叠加现有 Meshy 待机的持物手臂参考，不再使用 V03 的对称程序脚轨迹或冻结躯干。源周期 3.2667 秒，位移 73.1585 厘米，对应移动速度约 22.3955 cm/s。原地转换和播放率与此匹配。

活体动作按实际蒙皮脚掌最低点调整骨盆高度；模型绑定姿态的脚底平面为 Z=0，角色对齐不再依赖下摆包围盒。此项解决制作坐标中的平地接触，**未新增坡地脚掌 IK / 脚锁系统**。死亡保留原始后倒轨迹。

五段最终 FBX 在 `Delivery/LayeredV04`，可编辑动作源在 `Authoring/LayeredV04`：Idle 2 秒；Walk 3.2667 秒；CastPoison / ThrowPoisonBottle / DeathBackward 各 1.5 秒。施毒 0.535714 秒、掷瓶 0.75 秒、死亡 0.9 秒交接布娃娃的业务合同保留。输出 60 FPS；精确释放时间仍由 C++ 时钟决定。

## UE 与来源边界

专属目录 `/Game/Monsters/WitchMeshy/LayeredV04`，独立骨架、物理资产、材质、模型和动作。F6 继续使用稳定 ID `Witch` / 原生 `WitchMonster` 类，原来的 Witch 导航规格和生成入口保留。

Meshy 原始任务与下载复用，没有重新生成或扣费。Nurse 是用户已有本地授权素材，来源包未附可公开再分发的凭证；Quinn 来自工程已有 Epic 示例。派生源仅留在本工程，未作为 CC0 宣称或公开上传。旧 Meshy 输出、V01、V02、V03 均保留。

模型、五段动作、材质、骨架和物理资产已导入保存；Chaos Cloth 已创建并绑定下袍，当前编辑器 F6 默认值与原生路径均切至 V04。必要常规编译成功，日志 `Saved/BuildEditor/build-20260920-150739.log`；编辑器已正常重新打开。实际保存阶段、布料接入及 F6 切换记录见 `ue_layered_v04.json`。

构建结果与游戏表现分开报告；所有穿插、持杖观感、斜坡接地、布料效果和布娃娃表现仍由用户试用，当前版本不代表已获认可。
