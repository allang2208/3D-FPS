# 双刀第三人称上挑 V1

后续更新：当前双持上挑已切换到[双手剑下半身与端正躯干版本](kukri-uppercut-sword-lower-20261027.md)。本页保留副手动作来源与 V1 制作记录。

双持此前使用单持 `Kukri.FullBody.Uppercut`，其左手是胸前护拳，通用副手保留规则还会舍弃作者左臂。现为 Jason、Kaitlin 各制作一条独立 `Kukri.FullBody.Dual.Uppercut`，副手承担持刀避让和躯干配合动作。

主挥击沿用用户 Meshy `(3).glb` 中 `Charged_Upward_Slash` 的现有原生适配 V5，保留主手上挑、躯干发力与脚步。左臂从当前双刀专用待机进入，在主刀上挑之前向身体左侧外移，随后随躯干上提，再连续回到同一待机。此副手运动是配合动作，不新增第二段伤害或接触时钟。

副手采用本角色骨长与原生肘部弯曲平面，连续搬运肘部方向，保持新双刀待机的手腕局部关系和握柄手指。上臂与前臂辅助骨从最终姿态生成。刀柄挂接和手指接触沿用当前双刀装备映射；不使用旧空手护拳，也不翻转副刀握持。

两条动画均为 120 Hz、153 帧，接触和释放标记保持原 V5 的 0.350 秒、0.433 秒；运行中仍由现有武技变速与命中暂停时钟采样。第一人称、单持上挑、双持待机和旋风资产不修改。

## 接入

作者目录为 `SourceAssets/KukriDualUppercut20261027`。`author.py` 读取当前已接入 V5 上挑与双持待机的作者文件，核对保存回执后生成双持动作；`save_all.py` 在现有编辑器的 MCP 互斥批次内保存两个独立资产；`publish.py` 通过共享配置事务仅增加两个 `Kukri.FullBody.Dual.Uppercut` 角色键。

资产位于 `/Game/Characters/JasonPlayer20261003/Kukri20261024/ComboV3/{Jason|Kaitlin}/Animations/DualUppercutV1/A_Kukri_Dual_Uppercut_NativeDualRise`。

运行时修改限于 `FPSPlayerBodyAnimInstance.cpp`：实际装备副手弯刀且新资产可用时选择双持上挑，否则使用原单持上挑；只有选中新双持上挑时才允许作者动画控制完整左臂，避免通用副手保留规则覆盖配合动作。

两个资产已保存，配置已接入。2026-10-27 续办的 `FPSGAMEEditor Win64 Development` 正式构建已成功，退出码 0；完成 `UnrealEditor-FPSGAME.dll` 链接，双持上挑的动作选择与完整左臂控制逻辑已进入新模块。构建回执见 `SourceAssets/KukriDualUppercut20261027/editor-build-resume-result.json`，日志见同目录 `editor-build-resume-console-20261027-183716.log`。这表示制作、保存与编译接入完成，不代表游戏视觉效果已验收。

此前 18:14 的构建因 `Source/FPSGAME/UI/ColdSteelIncineratorStorage.cpp:45-46` 的 UE 5.8 JSON 共享字符串键类型错误失败。该文件已由独立更新修正，本任务未修改它；续办等待已有 Game 构建结束后提交正式 Editor 构建，现已解除阻塞。旧失败回执 `editor-build-result.json` 与旧日志保留作为历史，当前交付状态以 `delivery.json` 和 `editor-build-resume-result.json` 为准。

未主动启动或关闭编辑器，未运行游戏测试、预览渲染或视觉验收。效果由用户测试，未打包、提交或推送。
