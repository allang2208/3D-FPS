# M4 大弹鼓换弹候选 — 2026-09-10

> **后续重制已接入：** 当前默认版本与真实游戏预览见 [Revision2/README.md](Revision2/README.md)，正式资源是 `/Game/Weapons/M4DrumGripRebuilt`，无需候选参数。下面保留被拒绝版本的历史说明，旧 GIF、MAT 实验和启动方式不代表当前状态。

> **状态：视觉验收失败，用户已拒绝。** 手部扭曲、手臂僵硬，未形成要求的包握和插入动作。以下历史测试只证明部分运行逻辑，不能证明动画质量。不得将此目录的动画或 GIF 作为合格交付或正式替换依据。复查证据见 `Revision2/DIAGNOSIS.md`。

基于项目当前 HK416/M4 换弹动作调整左手张开、接近、抓握、随弹鼓插入及松手回位。保留原动作时长、弹鼓运动轨迹和右手动作。空仓换弹保留后续枪机操作。运行时仍根据原有枪械逻辑调整播放速度。

## 查看

- `M4_drum_normal.gif`：普通换弹，实际游戏运行截图合成。
- `M4_drum_empty.gif`：空仓换弹，实际游戏运行截图合成。
- UE 内容浏览器：`/Game/Weapons/M4DrumGripCandidate`。
- `LS_M4_DrumGrip_reload` / `LS_M4_DrumGrip_reload_empty`：60 fps Control Rig 编辑实验，尚未验收。
- `CR_M4_DrumGrip_MAT`：适配 MAT 手部按钮命名的 FK 控制器实验。
- `M4_DrumGrip_Editable.blend`：被拒绝版本的可编辑源文件；两套 FBX 与导入脚本在同目录。

已验证的编辑源是 `M4_DrumGrip_Editable.blend`。MAT/Sequencer 桥接仍存在姿态同步偏差，不能作为已完成的编辑工作流。运行 `/Game/Locodrome/MAT/Locodrome_MAT` 后可识别身体绑定，但面板选择联动、控制器姿态和源动画的一致性尚未全部通过。`LS_M4_DrumGrip_FK_*` 与 `LS_DrumGrip_FKCheck` 也是诊断资产，不是游戏当前使用的动画。

## 候选在游戏中使用

启动 UE 游戏或编辑器时附加 `-DrumGripCandidate`。它只替换大弹鼓的两套换弹动画，并为换弹过程添加向前、向上各 12 cm 的平滑展示偏移。常规启动仍使用原有正式动作。

自动验证：在项目根目录 PowerShell 执行 `& SourceAssets/M4DrumGrip20260910/run_test.ps1 -Run review`。它创建独立审计存档、安装大弹鼓、触发普通与空仓换弹并截图，完成后退出，不使用玩家正式存档。

## 验证记录

- `runtime-grip_c.log`：两种换弹均通过，`DRUM_GRIP: COMPLETE failures=0`；50 发容量、33/50 发补充扣除、动画中和结束后的弹鼓挂接已检查。
- `animation_report.json`：普通 127 帧/2.1 秒，空仓 163 帧/2.7 秒，60 fps、非循环。源动画右手未改变；锁定阶段接触目标滑动小于 0.00002 cm。
- `import_report.json`：五个关键骨骼按 120 Hz 检查压缩，最大位置误差约 0.0041 cm。
- `mesh_contact_report.json`：7 个抓握关键姿态的 6099 个左手顶点均未进入保守弹鼓圆柱核心。此检查不等于全动作、所有表面的无穿插证明。
- 动图保留了测试地图原有的方向光提示。该提示不影响换弹测试。

这版视觉验收失败。需要重新制作抓握姿态、手腕与前臂运动、接近和插入轨迹，不能将这些问题描述为交付后的细调。

## MAT 兼容修正

MAT 的 `getControlRigType` 原本只查询第一根节点的直接子元素，无法识别该骨架多层根节点下的 pelvis。修改为递归查询，并强制保存资产。原文件备份为 `Locodrome_MAT_before_recursive.uasset.bak`。

序列已有 Spawn 轨道。后续排查发现，应在序列生成模型并初始化绑定后，使用该模型组件进行烘焙；直接使用临时源 Actor 烘焙会留下不正确的预览状态。修正顺序后可显示动作，但精确姿态一致性仍未验收通过。

`native_editable_verified.json` 中 `pass: false` 是保留的失败证据；关闭实验性姿态优化也没有消除偏差。`mat_verified.json` 是较早的结构/关键帧检查，不代表最终视觉验收。当前可用结果为两套已导入 AnimSequence、游戏候选播放和 Blender 编辑源。

## 来源

沿用项目已经导入的 Infima 手臂、当前 HK416/M4 模型、大弹鼓和动作资源。本次没有下载、转授或重新分发第三方模型；MAT 来自用户已经导入的 Fab 资产 843baea2-8298-4b07-8db2-7ca18b026b7c。具体资产权利仍以原始许可及账号取得记录为准。
