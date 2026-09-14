# 715 单发装填作者源

2026-09-14 后续修正：当前换弹重建从 `../DanWesson715ReloadSplit20260914/` 开始，包含空仓／非空仓拆分、增强甩腕与稳定左肘；左开弹巢和固定捏弹手型仍沿用 Flick 上游。本目录保留首次接入来源。

详细行为与时序见 [实施说明](../../Docs/Weapons/dan-wesson715-single-load-20260914.md)，枪匠栏目见 [UI 规划](../../Docs/UI/dw715-reload-device-plan-20260914.md)。

制作顺序：`author_actions.py` → `make_icons.py` → 原生构建 → `import_assets.py`。动作作者脚本复用上一轮 `author_actions.py` 的源骨架、动作采样及手部求解函数；加载升级后的完整 Blend，再添加本轮 21 个动作。`include_upgrade_actions.py` 用于给本轮首次导出的 Blend 合入上一轮动作，后续从作者脚本重建无需额外运行。

- `DanWesson715_SingleLoad_Editable.blend`：可编辑动作与升级模型。
- `Animations/`：引擎用 120 Hz FBX。
- `animation.json`：片段与逐发接触时间。
- `Icons/`：原创分类／装填选项 RGBA 图标。
- `import.json`：资源导入记录。
- `build-native.log`、`build-native-retry.log`、`import.log`：必要构建与导入日志。首次构建遇到并行火球代码的类型错误；仅在 `FPSFireballProjectile.cpp` 的 ImpactNormal 条件表达式补充 `FVector(...)` 显式转换，保留其他并行修改。

默认逐发；`reload_device=dw715_speedloader` 为已应用的速装器改造。保留前版速装动画、音效、模型材质及所有来源许可。未测试，由用户测试。

交付记录：必要 Editor 构建在 `build-native-retry.log` 中为 Succeeded；导入脚本已保存 21 段动画和分类 Texture，写入 `import.json`，并输出 `DW715_SINGLE_IMPORT_COMPLETE`。Commandlet 因项目既有 GameFeatureData 资产管理配置错误返回 1，Python 脚本自身成功返回 0。FBX 导入沿用零时绑定姿势回退警告；这些日志不视为实机画面或手感已通过。此次不修改该项目配置。
