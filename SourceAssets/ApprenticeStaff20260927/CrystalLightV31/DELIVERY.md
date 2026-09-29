# 晶辉照明制作源

- `material_emission.py`：默认关闭的材质自发光参数增量接入，保留原材质输出及透明度；同样被 V22 水晶重建配方引用。
- `install_materials.py`：对原装水晶及冰、火、圣光、雷电四种替换晶体的现用材质增加控制参数、编译并实际保存。执行前包备份位于 `Before/`。
- `install-receipt.json`：本轮五个材质实际保存回执，`complete=true`，编译错误列表为空。
- 后台 commandlet 日志：`Saved/staff-crystal-light-v31-materials.log`。使用渲染 RHI 编译，不以 NullRHI 保存替代实际材质编译。

运行时 MID 的默认开关为零，照明时渐变至 3；点光源和姿态由 `StaffWeaponComponent` / `StaffIllumination.cpp` 驱动。透明度仍沿用 V20 恢复值，不改工作台预览材质。

完整玩法、构建及未测范围见 `Docs/Weapons/staff-crystal-light-20260928.md`。未运行游戏、预览、截图或验收测试。
