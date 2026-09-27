# 恢复左轮原检视并适配 M1911

用户否定 `PistolSpinInspect20260927` 转枪检视，要求恢复左轮原动画并复用到 1911；随后明确双持恢复改动前，不播放检视。

- 左轮单持恢复 `/Game/Weapons/DanWesson715/Upgrade20260914/Animations/A_DW715_inspect`，原资产未修改。
- M1911 单持使用 `/Game/Weapons/M1911/RevolverInspect20260927/Animations/A_M1911_inspect`；空仓用同目录 `A_M1911_inspect_empty`。
- 原动作来自 `DanWesson715_Upgrade_Editable.blend` 的 `DW715V2_inspect`，保留 4.966667 秒时长、动作顺序和手部轨迹，120 Hz 烘焙。
- 通过枪根和原始待机握点配准到 M1911，使用它自己的肩腕骨长与枪柄握姿；套筒、弹匣等机械骨保持各自正常／空仓状态。没有加入新转圈、配件分档或左右手错拍。
- 作者场景以 M1911 对应原生 BarePalmV7 裸手为可见手模。制作源：`SourceAssets/M1911RevolverInspect20260927/`。
- L 键仅触发单持检视。双持的检视预加载、播放方法和射击占用已撤回。此前单持时钟修正保留；空仓动画在装备阶段预载，按键不加载文件。
- 旧转枪目录已从运行时和 AlwaysCook 配置移除。退役源文件和 27 段旧动画在 UE 关闭窗口移入 `trash/pistol-spin-inspect-rejected-20260927/`，共 76 个文件；`manifest.json` 记录原路径、归档路径、大小、SHA-256 和替代实现。

两段新 M1911 动画已在现有编辑器会话导入保存，见该制作目录 `import.json`。未修改原左轮动画、未启动游戏或执行动画验收测试。编译结果见同目录 `build-status.json`。

热编译遇到 LiveCodingLimitError，未应用回退。排队取得 UE 批次后已完成旧资源归档，但 UE 随后被重新打开，常规构建因 DLL 被占用而未启动；等待用户关闭后继续。
