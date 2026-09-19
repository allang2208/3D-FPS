# 垂直握把腕肘衔接优化

依据手臂技能 references/grip-arm-refinement.md 和共振握把 AngledForegrip20260910/WristNatural 案例，保留 Compact75 已有模型、材料、装配、手掌方向、手指局部姿态及退握轨迹，只改变支撑肩带、肘部弯曲平面和随之重建的前臂 twist。

原待机腕轴折角约 47.85°，肘部约 26.82°，表现为腕部折弯而前臂过直。旧共振参数不适合当前垂直握把，因此通过 measure_arm.py 重新采样肩位，再查看 wrist_before.png / wrist_after.png。候选待机腕轴约 12.44°，肘部约 83.28°；这些是该骨架轴线指标，不是人体关节角或单独的验收阈值。

肩带输入 (.12,.20,-.08) m 相对原 M4 源动作，替代部分旧自动伸手补偿，不是在 Compact75 上再额外加此位移。实际相对 Compact75 的肩位差由 validate_arm.py 的 shoulder_delta_from_compact_m 记录。肩带支撑随回握权重退出/返回；骨长、骨骼缩放和手指局部平移保持。

工作流：保留 fit_final.json / release_profile.json / M4_Vertical_Fitted.blend → build_animation.py → validate_source.py / validate_arm.py / check_geometry.py → review_wrist.py → import_assets.py → 新进程 run_validation.ps1 → make_delivery.py。ReferenceWorkflow 是冻结依赖，不是另一个要更新的工程。

最终运行和导入结果以本目录 acceptance.json 及日志为准。

## 完成结果：vertical-wrist-natural-v1

- 九条专用动画已接入 `/Game/Weapons/M4VerticalWristNatural`；运行模型仍为 `/Game/Weapons/M4VerticalGripCompact75/SM_VerticalForegrip`。仅更新动画加载路径和 AlwaysCook 登记，不重导缩小版模型和材质。
- 原生构建 2026095227：Succeeded。新游戏进程 332 项通过、0 失败；446 个真实手套/握把采样无相交。
- 相对 Compact75，九条动作整数帧手腕/手指位置最大变化 0.023982 mm，旋转差检查通过。骨长、缩放、手指局部平移、右侧及原换弹接触段检查通过。
- 待机腕轴 47.8486° → 12.4379°，肘轴 26.8198° → 83.2769°。实际待机肩位相对 Compact75 变化为 (0.06597,0.10618,-0.07326) m；不能将作者相对原源输入 (.12,.20,-.08) m 误报成相对 Compact75 的新增位移。
- 已查看原共振握把实机腕部图、垂直握把修改前后同视角源渲染、当前实机第一人称/腕背/掌侧和换弹返回图。手臂改动按实际外观验收，轴角和零相交不单独代表自然。
- 导入及 UE RAW/COMPRESSED 读回通过。导入进程退出 1，日志为工程既有 GameFeatureData 配置错误；本次没有把端口占用错误从旧报告照抄为当前错误。未做完整打包验收。
- M4_VerticalForegrip_Integrated_Editable.blend 保存九条动作；各动作 Blend/FBX、fit/release 参数和脚本保留。M4_VerticalForegrip_Gameplay.mp4 为 155 个真实游戏画面组成的静音预览。
- 若编辑器仍驻留旧模块，需要重新打开工程加载新版；未强制关闭用户编辑器或恢复其他构建的模块清单。
