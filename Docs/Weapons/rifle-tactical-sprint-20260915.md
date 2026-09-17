# AKM / QBZ191 单手竖枪战术冲刺

最新的左手出镜与奔跑／步行衔接修改及检查，见 [衔接检查记录](rifle-sprint-transitions-20260915.md)。回步行退出现为 0.30 秒，武器动作退出为 0.16 秒；以下时长表保留首次接入记录。

2026-09-17：AKM 左手收回段腕关节反转已按腕部局部松弛修复（仅 AKM，`left_wrist_relax`），见 [AKM 冲刺左腕修复](akm-sprint-left-wrist-relax-20260917.md)；M4 与 QBZ191 数据未动。

## 接入内容

将现有 M4 单手竖枪冲刺扩展到当前 AKM MannyNative 与 QBZ191 Manny。使用现有奔跑状态，按住 W + LeftShift 前进即可进入；松开冲刺、瞄准或开火时落枪回握。速度、体力、冲刺后开火等待继续由角色原有逻辑控制。

每把枪使用自己的原厂、斜握把、垂直握把、侧倾握把、Prism 手挡源姿态，分别制作进入、循环、退出，共 30 个新片段。AKM / QBZ191 装弹鼓时沿用其原厂支撑握姿；M4 保留既有的独立弹鼓动作。

| 阶段 | 源时长 | 动作 |
| --- | --- | --- |
| Enter | 0.30 秒 | 左手先松开、向外下撤；右手带枪竖起 |
| Loop | 0.60 秒 | 右手单手持枪，左手独立摆臂，运行时跟随脚步距离相位 |
| Exit | 0.167 秒 | 沿原路径落枪，左手回到当前握把接触姿态 |

进入和退出共用连续进度，支持中途反向。切枪会更换组件中的动画引用并重置进度；配件变化切换对应握姿。接入时取消这两把枪与新动画重叠的旧冲刺根节点偏移和奔跑晃枪。

## 动作来源与制作

制作前读取各枪当前加载路径、已有源动作时长与腕部、枪口骨骼坐标，并查看已有参考：

- `SourceAssets/AKMSoviet20260911/idle_0_side.png`
- `SourceAssets/QBZ19120260912/fit_idle_0.png`
- `Saved/GunplayUpgrade/m4-sprint-final60/Preview/sprint_comparison.png`

动作顺序沿用本项目 `M4TacticalSprint20260915` 单手冲刺；两把枪分别取各自已制作的握把 idle。具体可编辑来源、动作名、源时长与坐标记录在 `SourceAssets/RifleTacticalSprint20260915/sources.json` 和 `source-poses.json`。

以右腕为中心旋转枪和右手，根据各枪源枪口朝向计算竖枪角度；分别设置 AKM 与 QBZ191 的持枪位置。肩、肘、腕及 twist 骨段一起求解，左手释放只修改手指局部旋转。以 120 Hz 烘焙动画并导出 FBX，不改枪体网格、蒙皮或握把原始动画。

## 文件与交付

- 制作与导入脚本：`SourceAssets/RifleTacticalSprint20260915/author_sprint.py`、`import_sprint.py`
- 可编辑源：同目录 `<枪>/<握把>/<枪>_TacticalSprint_<握把>_Editable.blend`
- FBX：同目录 `<枪>/<握把>/Animations/`
- UE 动画：`/Game/Weapons/RifleTacticalSprint20260915/<枪>/<握把>/`
- 状态组件：沿用 `Source/FPSGAME/Weapons/M4TacticalSprintComponent.h/.cpp`，内部新增步枪类型选择。
- 角色接入：`Source/FPSGAME/FPSGAMECharacter.cpp`；烹饪目录：`Config/DefaultGame.ini`。

本轮同时调整 M4 换弹镜头幅度与节奏，详见 `m4-action-camera-20260915.md`。未运行游戏测试或渲染验收，由用户测试。

30 段 UE 动画已导入并保存，回执为 `SourceAssets/RifleTacticalSprint20260915/import.json`。导入 commandlet 退出码 0，报告 0 个错误、30 个动画 FBX 绑定姿势警告；警告原文保留在同目录 `import-commandlet.log`，没有以导入完成代替游戏姿态测试。此次命令仅为导入进程启用 GameFeatures，供已有 AssetManager 的 GameFeatureData 类型解析使用，没有修改工程插件配置。

已在编辑器关闭期间完成 160 项完整原生重建，退出码 0、`Result: Succeeded`，输出普通 `UnrealEditor-FPSGAME.dll`。构建日志：`Saved/BuildEditor/rifle-sprint-camera-rhythm-20260915.console.log`。重新打开 UE 后使用本次编译结果；未启动游戏或追加测试。
