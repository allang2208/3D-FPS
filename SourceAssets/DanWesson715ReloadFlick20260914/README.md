# 715 甩开／甩回与捏弹修正

此目录保留左开弹巢和捏弹手型的上游作者源。当前换弹重建入口已转为 `../DanWesson715ReloadSplit20260914/`，新增空仓／非空仓拆分、强甩腕和稳定左肘求解。此版历史详见 [实施说明](../../Docs/Weapons/dan-wesson715-reload-flick-20260914.md)。

制作顺序：`read_authoring_pose.py` → `author_actions.py` → `import_assets.py`。

此次重做 21 段逐发动作及 2 段速装器换弹。默认／改造选择、原有运行路径、动作时长和弹药／机械音事件不变，不需要原生构建。旧作者目录继续保留，但重建当前换弹应使用本目录，不能以旧脚本覆盖此次方向和手型修正。

源骨架、材质与非换弹动作从上一轮升级 Blend 读取。制作时的参考动作记录在 `authoring-inputs.json`；捏弹模板按真实蒙皮顶端和有限的手指关节自由度制作，参数随 `animation.json` 保存。没有使用图片渲染、PIE、验收或回归测试。

导入记录：23 段动作已保存到现有运行路径，`import.json` 记录结果；日志输出 `DW715_FLICK_IMPORT_COMPLETE` 与 `Python script executed successfully`。Commandlet 因项目已有的 GameFeatureData 资产管理配置错误退出 1，导入脚本自身完成。此次不修改该项目配置，未宣称游戏画面或手感已通过。
