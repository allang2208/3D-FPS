# 混合主副手：副手斧头快速近战

旧镜像生成器、export.json 和 OffhandHatchetChop.h 已于 2026-11-09 归档至 trash/ConversationCombat20261109 的同名路径。下文生产命令仅是退役历史，不能重跑；当前直接复用原生 PairAttack3KH。

2026-11-07 修订。当前 F 直接在共享剑臂骨架上采样已安装的 `A_TacticalHatchet_PairAttack3KH` 左臂轨道，沿用组合第三击的 `hand_l` 固定握点。约 1.27 秒的快速近战时钟对应原片的 2.05 秒，挥砍音、命中和收刃按同一播放比例换算。手枪副手斧使用配套的左手待机承接收势。法杖副手斧在自己的手模上完成动作。以下镜像导出为旧版记录，生成的 C++ 姿态表已退出运行路径。

2026-11-06。主手手枪或法杖、副手 `weaponType=hatchet` 时，F 快速近战改为左手从上往下劈砍。

- 来源：`SourceAssets/HatchetChop20261102/Clips/HatchetAttack3.json`，现有单手斧三连击第三段。
- `author.py` 将原片右手动作按原生左右骨骼绑定轴镜像到左手，导出 `Source/FPSGAME/Weapons/Kukri/OffhandHatchetChop.h`。153 个关键帧、120 Hz、38/30 秒；不改动来源动画包。
- 首尾接回混合持握姿势，手指与斧柄在同一权重上转换正反握。手枪独立向右下避让；法杖沿现有主手接口避让到下劈收势结束。
- 挥砍音 `.328` 秒，单次技能接触 `.367` 秒，收刃窗口至 `.47` 秒。命中使用实际斧刃端点的中点；技能伤害、消耗、击退、经验和单次去重沿用 F 快速近战。
- 使用第三击的下劈镜头曲线并镜像横向分量，替换突刺背景模糊时序；移除斧头分支的突刺 whoosh 叠层。
- 第三人称发布独立 `OffhandHatchetChop` 动作状态、接触进度以及实际左腕/手指姿态，不选择原手枪弯刀突刺片；手枪副手斧的握柄随同一动作权重转换。
- 弯刀的快速突刺、主手单持斧连击和双持近战连击保留原路径。

生产命令：`python SourceAssets/OffhandHatchetQuick20261106/author.py`，随后 `Tools/Build/Build-Editor.ps1`。

本次使用 C++ 动作数据直接接入现有原生手臂组件，不需要新增或重新导入 Unreal 动画资产。未运行游戏、预览、截图或测试；效果由用户在游戏中测试。

## 构建状态

2026-11-07 后台 `FPSGAMEEditor Win64 Development` 构建成功，最终日志 `Saved/BuildEditor/build-20261107-000620.log`，UBT 返回 `Target is up to date` / `Result: Succeeded`，使用当前最新模块。

前一轮日志 `Saved/BuildEditor/build-20261106-234752.log` 已编译本次动作相关文件，但因螳螂怪物代码缺少类声明失败。该头文件随后已在工作区补齐，因此重新构建并取得上述成功结果；本任务没有改动怪物源码。未启动编辑器、游戏或测试。
