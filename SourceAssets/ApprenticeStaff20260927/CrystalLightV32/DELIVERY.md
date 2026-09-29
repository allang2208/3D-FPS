# 晶辉照明 V32

用户纠正：点灯只播放一次蓄力与收势循环，随后回到正常持杖，灯保持开启。用户同时反馈 V31 抬杖有响应但晶体和环境没有可见发光。

- C++ 将单次动作计时与持续照明强度分离，复用既有 `Raise` / `Raised` / `Recover`，总长 0.74 秒。普攻和施法可接管手臂，并从实际姿态衔接。
- `StaffIllumination.cpp` 点光源增加曝光适配；在法杖姿态更新后统一更新灯光和 MID。
- 五种晶体材质的新增照明分支增加 `EyeAdaptationInverse`。不补偿旧自发光，不改变透明度、基色或粗糙度。
- `install_materials.py` 已在现有编辑器执行，材质编译错误列表为空且保存成功，见 `install-receipt.json`。原包在 `Before/`。此升级同时进入 `CrystalLightV31/material_emission.py`，后续 V22 配方重建会继承。
- `read_light_state.py` 是仅用于本次反馈的只读诊断，没有触发右键、启动 PIE 或进行截图。读数不能代替开启状态的运行验收。

常规原生构建状态见 `Docs/Weapons/staff-crystal-light-20260928.md`。本轮未重新运行游戏或进行效果测试。
