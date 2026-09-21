# 战术冲刺左臂遮挡修订 V3

2026-09-21 整理：已替代的动画输出及临时源码／编译快照按清单移到 `trash/melee-sprint-retired-20260921/SourceAssets/` 对应路径。当前为 V4 六条移动片段 + V5 两条0.25秒前摇攻击片段；下文旧输出位置与瞬发说明保留为历史。V4作者与导入入口已限定移动片段。详见 `Docs/Weapons/melee-publication-20260921.md`。

后续用户要求准备条满格后才举剑、0.5秒过渡及同步枪械冲刺节奏；最新 V4 源与接入记录见 `../MeleeTacticalSprintReady20260921/README.md`。本目录保留V3左臂避让源。

2026-09-21。用户反馈左臂遮挡过多，并确认进入冲刺和持续冲刺两段都明显；要求研究 GitHub 的适用方案并调整姿态。

## 本轮依据

读取 V2 的实际作者解算后，标准柄左肘在视模坐标 `(-0.0089, 0.1744, -0.0683)` 米，长柄为 `(-0.0047, 0.1689, -0.0694)` 米。坐标为右、前、上：左肘处在镜头正前方约17cm、眼线下约7cm。V2 虽然后移了双手，腕轴对齐目标仍将左肘带到前方，左前臂横穿画面；其制作目标缺少视野约束。

## GitHub 方案与取舍

- [ozz-animation IKTwoBoneJob](https://github.com/guillaumeblanc/ozz-animation/blob/master/include/ozz/animation/runtime/ik_two_bone_job.h)，MIT：将手部目标、肘部 pole、骨架弯曲轴以及轴向 twist 分开。其[实际实现](https://github.com/guillaumeblanc/ozz-animation/blob/master/src/animation/runtime/ik_two_bone_job.cc)先处理两骨长度对应的弯曲，再对齐目标和弯曲平面。适合借鉴职责分离。
- [orangeduck/Motion-Matching 的 ik_two_bone](https://github.com/orangeduck/Motion-Matching/blob/main/controller.cpp)：两骨长度与目标通过几何求解，另传入 fwd 控制弯曲方向。适合作为固定握点、独立控制肘向的第二个实现参考。
- [Unity 官方动画绑定工作坊](https://github.com/Unity-Technologies/animation-rigging-workshop-siggraph2019/blob/master/Assets/AnimationRiggingWorkshop/Editor/TwoBoneIKAutoSetup.cs)：手部 target 与肘部 hint 分别设置。它是 Unity 示例，不能直接作为 UE 插件安装。

本轮只借鉴这些实现的解算思路，没有复制第三方源码或新增插件。画面空间避让是本项目新增的作者约束，上述仓库没有自动保证当前手模视野的成品方案。

## 实际修改

- 保留 V2 持续冲刺时的武器位置、水平前指、两种握距及双手握柄矩阵；保持手指、骨长、蒙皮。
- 左肩相对 V2 后收6.3cm并降低0.8cm，左肘引导改到胸前下部。离线作者在满足肩腕距离和原骨长的肘部圆周上选择方向，同时考虑腕轴弯曲、收肘位置和摄像机视域。
- 避让计算对上臂、前臂加入厚度，中央视野遮挡权重更高；不是只把肘骨点移出准心，也不隐藏或缩小手臂网格。厚度为作者代理，不能当作最终像素遮挡率。
- 进入冲刺先后收并绕向右侧，再抬升和转平剑身，减少由低位直接斜举穿过中央的路径；左肘提前收下。退出沿同一制作路径回到原待机。
- 两种握柄的进入、循环、退出和接下劈共八条动画重做；时长、120Hz采样、1.22秒瞬发攻击起点和1.31秒接回原下劈保持。
- 约束只用于 Blender 离线制作，烘焙为原动画资产。C++、60°攻击判定、伤害、移动和体力没有修改，没有新增运行时求解成本。

## 文件与交付

`author_sprint.py`、`motion.json` 为可编辑作者入口；`Standard`、`LongGrip` 下保存 Blend、完整骨轨道和导出 FBX。前两版作者源分别保留在 `../MeleeTacticalSprint20260921/`、`../MeleeTacticalSprintRearCarry20260921/`。

已通过项目桥保存两种握柄共八条动画并导出 FBX，回执为 `import-sprint-02.txt`、`import_receipt.json`。首次导入因当前 PIE 活跃而没有写入；为完成资产编辑，通过 `LevelEditorSubsystem.editor_request_end_play()` 结束游戏后继续保存，未关闭编辑器或重新启动 PIE。

`import_sprint.py` 仅更新本任务两种握柄的 `TacticalSprint20260921` 四类片段。没有运行游戏测试或验收渲染，最终画面和手感由用户测试。
