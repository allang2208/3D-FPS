# 握把抓握母版与配件类别

2026-09-12：用户先认可垂直握把的 VRE 抓握方向，再确认 45° 侧倾握把、棱镜阻手器成功，并要求作为配件标准。此页取代早期逐指拟合、Raised、Horizontal、Ergonomic 的“当前入口”描述。旧动作仍可作为复现与接触时序输入，不能按日期或目录名清理。

## 当前类别与实际路径

| 配件 | M4 动画目录（/Game/Weapons/） | AKM 动画目录（/Game/Weapons/AKMIntegration/SovietFab/） |
| --- | --- | --- |
| 垂直握把 | M4VerticalGripVRENatural/Vertical | GripVRENatural/vertical |
| 45° 侧倾握把 | M4VREGripExtensions/Canted | GripVREExtensions/canted |
| 棱镜阻手器 | M4VREGripExtensions/Prism | GripVREExtensions/prism |

垂直握把与阻手器保留“垂直握把类”关系及独立配置；45° 保留专用分支，但共用同一套 VRE 成组指型。物品 ID、挂点、尺寸、属性和存档不因动画共用而合并。共振/穿孔三角握把继续用原专用动作，不在本轮替换范围。

以 `VerticalGripAnimationFamily.h`、`M4CantedForegrip.cpp`、`AKMAttachmentVisual.h` 的实际引用为准。每族九条：idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。M4 与 AKM 三类合计 54 条；不能把“共用手型”理解成相同挂点矩阵或跨枪完全相同的烘焙序列。

## 作者与适配入口

- 垂直握把：本机 `SourceAssets/MannyGraspDonor20260912/README.md` 与 `Final/`；VRE 原始姿态在 `Donor/`，选定整手配置在 `Opening/0.8/aligned_fit.json`。
- 45° / 阻手器：本机 `SourceAssets/VREGripExtensions20260912/README.md` 与 `Final/`；`fit_static.py` 调整整手，`case.py` 选择配件/原动作，`build_family.py` 保留接触段并生成各族。
- 默认复用已接受手型：四指成组弯曲、拇指横扣，先适配整手方向、握点和原肩肘来向。保留骨长、rest、scale 与手指局部平移；小阻手器按本用户要求整体包在自然拳形中，允许内部穿模。
- 斜握把先定真实本体轴和握点，再调整整手与原腕方向的关系。腕轴近直不证明前臂无扭转；同时查看 twist、肘平面、袖口和玩家正面。80%/90% 闭合与 75% 原腕方向混合为本骨架案例参数，不跨枪机械照抄。

完整执行标准见 [改造配件标准](../../ue5-weapon-workflow/references/attachment-standard.md)，来源与镜像见 [VRE 抓握迁移](github-grasp-donor.md)，斜握把诊断见 [已接受扩展](grasp-canted-handstop.md)。先核对实际源姿态及运行分支，再改接触；保留原普通/空仓与弹鼓接触和业务时钟。

## 验收与保留范围

保留两案例 Final 中的可编辑 Blend、FBX、验证摘要和游戏近景/换弹序列。历史制作轮次分别验证 18 与 36 条源动画及 UE 读回、两组与四组独立游戏运行；用户已认可本次方法。交叠仍有记录，不将成功确认解释为零穿模或打包通过。

旧 `VerticalGripFront20260911` 的垂直原动作、整臂/几何工具与冻结参考，`VerticalGripErgonomic20260911` 和 `CantedGripMigration20260911` 的对应基线仍被当前生成/对照引用，继续保留。明确拒绝的前伸拇指输出、完全闭合早期动作、严格沿轴扭臂试验及自动备份已按任务清单归档到本机 `trash/grasp-workflow-20260912/`；不从 trash 恢复当前运行母版。
