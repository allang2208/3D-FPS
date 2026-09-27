# 法杖蓄力位置前移 V17

按用户要求，将蓄力握点沿相机前向 +X 移动 10 cm：`Raised` 基础位置由 `(39,22,-8)` 调整为 `(49,22,-8)`，仍叠加 V14 的画面右移 4 cm。

- 调参入口：`Source/FPSGAME/Weapons/Staff/StaffCastMotion.h` 中的 `ChargeForwardCm`。
- `Raised` 与发射前 0.035 s 的 `Windup` 同步前移，随后沿既有平滑曲线接入发射接触姿态。抬杖进入及收回继续沿用原混合。
- 原生右臂完整骨链随握点平移，手指抓握与腕部方向沿用当前姿态；杖尖及蓄力光球的 Focus 使用同一接触变换。
- 待机持杖、V16 左手自然摆动、发射接触姿态和施法时长不变。
- `Staff_ChargeForward_V17.blend` 保留 V16 手臂源，新增 `A_Staff_Raise_V17`、`A_Staff_Release_V17` 及四种握把的蓄力/回摆静态姿态。仅锁骨层平移，子级手腕和法杖随动，避免重复偏移。

运行继续使用 C++ 姿态驱动已有手模，不新增 UE 动画资产。构建结果见 `build-receipt.json`。

当前接入状态：用户关闭 UE 后，已完成 `FPSGAMEEditor Win64 Development` 常规构建，25 项动作，16.05 秒，结果 Succeeded；基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已更新。日志：`Saved/BuildEditor/build-20260927-210617.log`。此次 10 cm 调整已编译落盘，下次打开工程使用新版本。

先前 Live Coding 的 UBT 阶段成功但编辑器返回 NoChanges，未生成新补丁；该次尝试已由上述常规构建完成接入。未启动或重启 UE。

未运行游戏、截图、渲染或测试；距离与实际观感交由用户测试。
