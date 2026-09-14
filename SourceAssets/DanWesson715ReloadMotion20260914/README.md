# 715 当前换弹作者源：提高基础力度与右手全程配合

本目录保留上一版较快的配合动作，历史方案见 [参数说明](../../Docs/Weapons/dan-wesson715-reload-motion-20260914.md)。当前重建入口为 `../DanWesson715ReloadNatural20260914/`，减少逐发反复摆动并采用缓慢连续持枪曲线，同时修正末发换弹衔接。

制作顺序：`author_actions.py` → `import_assets.py`。

- `DanWesson715_ReloadMotion_Editable.blend`：可编辑模型与本轮动作。
- `author_actions.py` / `animation.json`：提高后的基础值、按阶段驱动的右手运动和原有弹药接触时间。
- `Animations/`：27 段 120 Hz FBX。
- 导入目标继续为 `/Game/Weapons/DanWesson715/ReloadSplit20260914/Animations`，无需修改 C++ 或重新构建。

未测试，由用户游戏内测试。此次没有重复上一轮的位移排查，也没有启动 PIE、截图或渲染。

交付记录：27 段动画已保存到现有引用路径，`import.json` 为回执；`import.log` 输出 `DW715_MOTION_IMPORT_COMPLETE` 和 `Python script executed successfully`。Commandlet 因项目既有 GameFeatureData 资产管理配置错误返回 1，导入脚本自身完成；FBX 延续零时绑定姿势回退提示。此次未修改这些项目设置，未将导入完成表述为游戏效果已验收。重启已打开的编辑器后由用户体验新动作。
