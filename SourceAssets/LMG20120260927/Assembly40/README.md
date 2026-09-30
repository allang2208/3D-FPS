# 201 Assembly40

继续 H39 用户反馈，修正后照门/导轨接合、右侧生成拉机柄外形、盖下通透、原厂弹匣连接与扳机护圈。实际运行资产沿用原路径，保存状态见 `delivery.json`，详细记录见 [制作说明](../../../Docs/Weapons/lmg201-assembly-20260929.md)。

制作入口依次为 `collect.py`、`read_pose.py`、`model.py`、`install.py`。作者源为 `LMG201_Assembly40.blend`，完整实际保存导出为 `Exports/After_Body.fbx`，后照门为 `Exports/After_RearSight.fbx`。`model.py` 仍使用 R38 的有界建模帮助函数及 H39 可编辑枪体，不能删除这两份制作依赖。

模型导入脚本由已有编辑器进程中的 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript ...` 执行，检查 PIE、目标未保存修改和捕获散列后才更新原路径。私有候选名称带源文件散列，避免复用旧重导设置；保存前副本在 `Before/` 与 UE 私有 `Previous`。

`preview.py` 为制作视图；`read_saved.py` 延续本轮明确的细节检查，使用保存导出和原 idle 第 0 帧生成 `*_saved.png`。两者都不是游戏截图，也不是后续修改的默认测试要求。本轮未修改动画和原生代码。
