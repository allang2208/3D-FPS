# 斧头与十字镐：单手抓握和采集力度

使用当前 Manny 手臂、已接受的 VRE 成组抓握和已接入的免费斧头/矿镐。原采集表现只有静态工具旋转；本轮加入带手臂的骨骼视模，并为两种工具分别制作待机、步行、装备、空挥和命中恢复。

## 抓握与作者源

按 `ue5-fps-arms-animation` 的姿态接触、GitHub 抓握迁移、整臂优化方法制作。读取并查看既有 `MannyGraspDonor20260912/Delivery/Original_Donor.png`、`Player_Wrist_Views.png`，沿用已接受的 80% 闭合母版；这不是新一轮画面验收。

母版为 `SourceAssets/MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend`。将已接受的左手成组包握按 rest 坐标系镜像到右手，保留 Manny 网格、手指长度、关节局部位置和权重。先确定真实木柄截面中心，再固定整手与工具的关系，联动肩、肘、前臂及 twist 骨骼；左臂自然放低并轻微平衡，不参与工具抓握。

斧头木柄弯曲，不能按工具整体包围盒中心放手。作者握点位于原静态模型约 `(-7.51, 0, -26) cm`；矿镐为约 `(0, 0, -21) cm`。工具保持上轮大小与贴图。整个动作中保持一次选定的圆柱握向，不滑动手指或在击打途中换握点。

本机可编辑源：

- `SourceAssets/ProductionToolGrip20260913/Axe_SingleHand_Editable.blend`
- `SourceAssets/ProductionToolGrip20260913/Pickaxe_SingleHand_Editable.blend`
- `SourceAssets/ProductionToolGrip20260913/Export/`：两个骨骼网格、十条动作 FBX。
- `Tools/Production/build_tool_grip_motion.py` / `import_tool_grip_motion.py`：制作及导入入口。

## GitHub 参考与采用边界

1. [BigAndCrispy/Unity-First-Person-Melee](https://github.com/BigAndCrispy/Unity-First-Person-Melee/tree/592b08e2e1fe81a51f712fa65d806fa3621e2032)：作者将自制模型、声音和动作以 CC0 提供。本机 `RuneSword20260913/Reference/` 已有该固定提交的 FBX、导入设置、动作矩阵、控制器、原画面和声音。原动作是单手剑，不是现成的斧头或矿镐；本轮参考其起势—挥击—回收和持握姿态，少量采用待机轨迹与挥动声音，为采集工具重做主要击打轨迹。原 Slash1/2 为 24 fps 的 0–20 帧、非循环；Idle 0–80 帧、Walk 0–22 帧循环。
2. [VRExpPluginExample GrabAnimation](https://github.com/mordentral/VRExpPluginExample/blob/bf4c7ba554ecbbe614ed3d16669ef53d3f888f09/Content/VRE/Core/GraspingHands/VRHandMeshes/Animations/GrabAnimation.uasset)：复用本机已经迁移到 Manny 的成组指型。源是静态抓握，不把它当作完整挥击动画。
3. [UnrealMeleeAnimationHelpers](https://github.com/Redesigner/UnrealMeleeAnimationHelpers)：参考动画接触窗口、每次攻击清理命中状态的方法。这里仍沿用现有采集准心射线和一次结算，没有引入整套近战碰撞插件。
4. [ProcHitReact](https://github.com/Vaei/ProcHitReact)：参考短时 Hold、Blend Out 和只在需要时更新表现的思路。这里采用独立命中恢复片段，不对第一人称手臂开启物理模拟。
5. [MotionExperiments](https://github.com/josimard/MotionExperiments)：参考阻尼恢复和旋转插值思路；运行时冲刺下压使用依赖时间的指数过渡，命中脉冲在作者阶段烘焙。本轮没有复制或安装该插件。

VRE 仓库 MIT 与 Manny/Infima/Fab 内容许可分别沿用已有来源记录，不能把 CC0 或代码仓库许可套用到整套手臂与工具。原包、派生模型、动作和贴图保留本机，公开仓库只提交本轮作者代码与接入配置。

## 动作与采集时钟

斧头采用右上向左下的斜劈，矿镐采用抬高后向下砸。两者仍为 0.68 秒一轮、0.24 秒接触；不修改原采集次数、产出、射线距离或物品身份。

| 阶段 | 时间 | 表现 |
| --- | --- | --- |
| 起势 | 0–0.13 s | 手臂带动工具向后上方蓄力 |
| 发力 | 0.13–0.24 s | 加速接近接触姿态，挥动声在约 0.156 s 触发 |
| 有效命中 | 0.24 s | 现有采集提交成功后，同刻选择命中恢复、播放命中声和原粒子 |
| 制动 | 斧约 33 ms / 镐约 47 ms | 手和工具一起短暂停留，随后轻微回弹 |
| 回收 | 至 0.68 s | 先退开，再回到待机；空挥会继续顺势挥过 |

每种工具有 Idle 1.6 s、Walk 0.8 s、Equip 0.32 s、Swing 0.68 s、HitRecover 0.44 s。统一 150 Hz 烘焙，使 0.24 s / 0.68 s 落在精确帧；运行时每帧只求值一次骨骼。HitRecover 的第一姿态与 Swing 的接触姿态使用同一个作者变换，手指与工具共用受力坐标。短暂停留只影响视觉，不暂停世界、输入、角色或采集计时。

## 接入与开销

`production_tools.json` 新增视模、动作前缀与挥动声引用。已有外观归一化补齐旧存档这些字段，重新加载即可使用新手部表现。地面掉落继续使用上轮静态网格及矿镐三级 LOD。第一人称只实例化当前工具的一个骨骼视模，工具几何使用低面数 LOD0；原手持静态网格隐藏。

装备时异步加载手臂、动作、声音和粒子；动作由采集组件统一采样，不另启一个动画 Tick。菜单、死亡、攀爬、建造或收起时停止动作求值。原资源提示继续以 0.15 秒间隔更新。新资源目录为 `/Game/Items/ProductionTools/GripMotion20260913`，包含专用于骨骼视模的工具材质，复用既有 PBR 贴图和当前 M4 的 Manny 材质槽。

## 交付状态

两套视模、十条动作、两个骨骼用途材质及挥动声均已保存，回执为 `SourceAssets/ProductionToolGrip20260913/import_receipt.json`。最终导入日志为 `Saved/ToolGripMotion/import-multiprocess.log`，记录 Python 脚本成功；进程仍因工程既有的 GameFeatureData 配置缺失返回 1，不能称为整工程无错误。FBX 导入器重新创建了有效的绑定姿态，实际蒙皮观感仍由用户判断。

导入使用 `-Multiprocess` 避免启动时重复 SDK 探测等待另一构建任务；原生构建通过工程 `Tools/Build/Build-Editor.ps1`，使用普通模块。用户关闭编辑器后，最终构建返回 `Succeeded`（目标已为最新，0 个待编译动作），日志为 `Saved/BuildEditor/build-20260913-222826.log`。这是原生构建结果，不代表游戏内表现验收。

按照用户规则未主动运行游戏测试、PIE、渲染或截图验收；握持构图、手腕外观与力度感由用户进游戏确认。使用 `6` 装备斧头、`7` 装备矿镐、左键采集、`F7` 收起。
