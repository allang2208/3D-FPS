# 尼泊尔弯刀第三人称旋风：参考源左臂与阶段衔接 V7

2026-10-25。按用户“先从旋风开始调整，处理动作衔接，左手参考源动作，检查优化”的要求制作。

## 已落盘与接入

- Jason、Kaitlin 各自的 `Whirlwind.Start / Loop / End`，共六个原生 AnimSequence，已通过后台 Python commandlet 保存到 `WhirlwindMeshyV7`。
- `Content/ColdSteelData/player_body.json` 的六个 `Kukri.FullBody.Whirlwind.*` 字段已通过现有配置事务切换到 V7。其余字段未由本次事务修改。
- 输出根路径：`/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/<Jason|Kaitlin>/Animations/WhirlwindMeshyV7/`。名称为 `A_Kukri_Whirlwind_<Start|Loop|End>_SourceMotion`。
- 本次没有修改运行时 C++，不需要另行编译游戏模块。第一人称、技能时钟、伤害、其他攻击和副手待机保持原配置。

## 参考与修改

参考是用户提供的 `C:\Users\allan\Downloads\Meshy_AI_Gray_Full_Body_Manneq_All_Animations (1).glb` 中的 `Axe_Spin_Attack`。取左锁骨、肩、肘平面和腕部的变化，用于单手刀的自由手平衡动作。源文件没有独立手指轨道，左手的放松屈指另外按原生手骨制作；右手保留实际弯刀的原生握柄姿态。

V6 把左手压缩成胸前很小的运动范围。Jason 旧资产的左腕相对胸口范围约为 5.4 × 2.4 × 1.1 cm；V7 的压缩资产约为 46.3 × 22.3 × 18.1 cm。新增抬臂、折肘、横向平衡和回收，保留胸前避让；针对两次转身的快速节奏，收敛腕部翻转幅度并平滑曲线。

两圈使用同一周期曲线，位置和旋转曲线在周期边界连续。起手、旋转、收势使用一致的完整骨架边界姿态；左右脚依次调整支撑，手臂不再被旧的固定护胸解算覆盖。旋转围绕身体中心重建，减少导出原点造成的横向绕行，保留小幅原动作重心变化。

Kaitlin 的共享 Skeleton 参考骨长与实际网格不同。初次保存检查发现最高约 7.7 cm 的制作／解码位置偏差，已改用她实际网格的 bind pose 制作，并为新资产设置对应的 `RetargetSourceAsset`。修订只作用于本次旋风六个新包，没有更改共享 Skeleton 或其他动画。

技能仍为 -720°，准备 0.5 s、旋转 1.066667 s、收势业务时间 0.52 s。资产使用 120 Hz；收势采样长度为 0.516667 s，继续由现有阶段归一化采样匹配业务时间。

## 本次检查范围与结果

按本次明确要求检查了参考源、当前第三人称播放路径、两套实际身体网格的离线蒙皮姿态和六个保存资产的压缩姿态。离线预览仅包含身体网格与弯刀，头部、服装及运行时姿态层不在预览中。

- 六个新资产已实际保存，后台 commandlet 退出码 0。
- 保存后压缩姿态与制作曲线的最大位置偏差低于 0.016 cm，最大角度偏差低于 0.19°。
- 两处阶段接缝：最大位置误差低于 0.012 cm、最大角度误差低于 0.20°；原始制作边界完全一致，残差来自各段独立压缩。
- 循环首尾的压缩关节位置一致。
- **没有运行 PIE、游戏、F6 或联机验收。** 实际游戏镜头、服装覆盖及最终主观自然度由用户复测；不把离线结果当作游戏内验收。

## 可复现文件

- 制作：`SourceAssets/KukriWhirlwindSourceMotion20261025/author.py`
- 保存／检查／接入：同目录 `save_assets.py`、`read_saved.py`、`inspect_saved.py`、`publish.py`
- 保存与接入凭据：`assets-saved.json`、`save_and_read-commandlet.json`、`inspection.json`、`published.json`
- 当前离线姿态拼图：`native-candidate-sheet.png`；参考源拼图：`source-contact-sheet.png`

现有 UE 在接入前已关闭，因此保存使用后台 `UnrealEditor-Cmd`；本任务没有打开或关闭 GUI 编辑器，也没有启动游戏。
