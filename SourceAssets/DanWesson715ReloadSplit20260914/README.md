# 715 当前换弹作者源：模式拆分、强甩腕与稳定左肘

实施细节见 [说明](../../Docs/Weapons/dan-wesson715-reload-split-20260914.md)。当前表现运动重建入口为 `../DanWesson715ReloadMotion20260914/`，提高基础力度并增加右手全程配合；本目录作为空仓分支和接触定义的上游保留。以下采样与构建结果属于 Split 版历史。

制作与接入：`author_actions.py` → `import_assets.py`，原生代码同步使用 `ReloadSplit20260914/Animations`。

- `DanWesson715_ReloadSplit_Editable.blend`：可编辑模型与本轮 27 个动作。
- `Animations/`、`animation.json`：21 段逐发、6 段按起始实弹数选择的速装器 FBX，以及时序和目的路径。
- `import.json`：27 个引擎资产的保存回执；`import.log`：脚本成功、项目已有 GameFeatureData 配置错误使 Commandlet 返回 1。
- `diagnose_source.py` / `diagnose_import.py`：用户所要求的装填位移排查前测，针对旧 Flick 当前动作。
- `diagnose_source_after.py` / `diagnose_import_after.py`：两个对应新动作的 120 Hz 定向后测。源动作前臂的旧 15.58 cm 翻转已消除，新入膛接触窗口的最大相邻骨骼位移约 3.74 mm，UE RAW／COMPRESSED 一致。

只做了用户明确要求的位移排查，未运行 PIE、游戏测试、截图或渲染。必要 Editor 构建已完成：`build-native-final.log` 为 `Result: Succeeded`，FPSGAME / AutoFootstep / AutoFootstepEditor 使用一致后缀 `71404`。编辑器已打开时须重启后使用本轮代码与新动画。

前两次构建遇到并行施法／翻越代码的接口、包含路径和局部变量遮蔽错误，记录在 `build-native.log` / `build-native-retry.log`；相关文件由并行工作修正后本轮重建成功，此任务未修改施法／翻越代码。构建完成不等同游戏内动作或手感已验收。
