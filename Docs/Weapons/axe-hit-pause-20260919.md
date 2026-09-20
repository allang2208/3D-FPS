# 伐木斧命中：停住，再晃动抽回

以当前 H4 / V5 + ThumbFix1 源动画重定时，只更新 `HitRecover`。

命中后的时序：

- 0–0.20 s：保持首帧接触姿态，双手与斧头完全停住。
- 0.20–0.23 s：平滑进入原撬柄起始姿态，跳过旧版 75–150 ms 的微震。
- 0.23–0.51 s：沿用原上下撬柄动作，斧刃作为支点；角度依次 0、+5.5、−4、+4.5、−2、0 度。
- 0.51–0.64 s：沿用原拔出动作。
- 0.64–0.92 s：返回持握姿势。

维持现有源 clip 长度 0.44 s / 300 fps、运行回收时长 0.92 s、挥砍接触时刻 0.48 s。运行时映射不变，无需改 C++ 或重新编译。镜头继续用单次重冲击，不随撬柄高频抖动。

统一重定时所有骨骼，保留握点、右拇指、左腕与整臂的已有修正；待机、装备、奔跑和挥空动作不变。没有改采集次数、伤害或资源结算。

作者源和制作脚本：`SourceAssets/AxeHitPause20260919/`。单条导入：`Tools/Production/import_axe_hit_pause.py`。完整姿态家族与攻击导入入口的 HitRecover 来源也同步更新，避免未来导入恢复旧节奏。

## 状态

可编辑 Blend 和 FBX 已导出，参数与导入入口已更新。用户停止运行后，正式 `A_Harvest_Axe_HitRecover` 已通过后台导入并保存；回执为 `SourceAssets/AxeHitPause20260919/import_receipt.json`，成功日志为 `Saved/Logs/AxeHitPauseImport20260919-Retry2.log`，进程退出码 0。

导入脚本修正了 commandlet 模式调用 LevelEditor 的崩溃，以及 UE Array 写入 JSON 回执时的序列化问题。未进行测试、预览渲染或实机验收；本轮没有 C++ 修改，无需构建 DLL。
