# 枪械水平展示与配件取景验收

2026-09-10 回查：进入本次任务前，水平取景实现和 1600×900 首轮实机验收已经完成；本次补齐 1280×720 独立进程复验、查看实际截图，并修复验收脚本未按运行编号保留加长配件截图的问题。

- 默认使用正交侧视，同时对齐枪管和枪身竖直轴，消除持枪姿态遗留的偏航及侧倾。拖动保留双轴旋转，双击或“水平复位”恢复默认。
- 取景包含可见枪体、枪口、瞄具、弹鼓以及递归子配件；根据展示区域宽高比自动居中与缩放，并留出边缘和上下按钮空间。隐藏手臂与隐藏原件不撑大取景。
- 旋转、配件切换及展示区域尺寸变化后重新计算取景；拆掉加长件后恢复较近取景。正交深度矩阵覆盖整套组件，避免深度裁切。

核心实现位于 `Source/FPSGAME/UI/M4GunsmithPreview.cpp`，配件收集位于 `Source/FPSGAME/Weapons/M4DrumVisual.cpp`。本次未重写已完成的原生实现。

验证：既有 `Saved/GunsmithFraming-build.log` 为 Succeeded；既有 `framing-v1-1600.log` 为 51 项通过。本次 `Saved/GunsmithWorkbenchAudit/framing-confirm-720-1280.log` 同样 51 项通过、进程退出码 0。涵盖水平轴向、消音器+全息+弹鼓完整显示、前后加长及嵌套配件、旋转后边界、拆除恢复，以及既有鼠标交互和改造保存回归。测试使用独立 WorkbenchAudit 存档。

前后加长件使用临时方块验证边界，并不代表新增正式枪托资产已经接入。当前结论为开发模式实机验收，未执行打包。

![720p 长消音器与整枪完整展示](../../Saved/GunsmithWorkbenchAudit/framing-confirm-720-1280-long-muzzle.png)

[加长组件旋转检查](../../Saved/GunsmithWorkbenchAudit/framing-confirm-720-1280-extended-rotated.png)
