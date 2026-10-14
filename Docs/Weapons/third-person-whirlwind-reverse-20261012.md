# 第三人称旋风反向旋转

用户明确要求将第三人称旋风动画的旋转方向反过来。现用 Kwang／唐刀三段动画已在制作时剥离全局转向，整圈旋转来自角色朝向，因此本轮在全身动画输出的根部反转可见转向。

## 修改

- 保留 `skills.json` 的 `turnDegrees=-720`。第三人称全身模型改为相反的 +720°；第一人称镜头和伤害扫掠仍由原执行器推进。
- 第三人称表现状态保留带正负号的圈数，远端表现接收也保留该符号。
- 用执行器同一 `WhirlwindFeel::NormalizedPhase` 计算转向，包括加速、制动和命中停顿。在角色已施加角度 θ 的基础上，给最终全身姿态添加 -2θ，得到反向的 -θ。
- 修正放在握持与姿态求解之后、输出之前，身体、衣物、双手和挂接武器整体转动。起势、收势、脚步和唐刀握柄曲线仍正向播放；原三段资产及引用不变。
- 两圈结束时修正角度等价于 0°；离开旋风状态后不再添加修正，不另开旋转计时器。

## 交付

源码已落盘，以下后台构建均返回 `Succeeded`：

- `FPSGAME Win64 Development`：`Binaries/Win64/FPSGAME.exe`；日志 `Saved/WhirlwindThirdPersonReverse20261012/Game-build.log`。
- `FPSGAMEEditor Win64 Development`：已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`；日志 `Saved/WhirlwindThirdPersonReverse20261012/Editor-build.log`。

用户关闭编辑器后，等待现有后台资产导入进程退出，再完成正式 Editor 构建。未重开编辑器，未启动游戏、PIE、截图、渲染或动作验收，观感由用户测试。

历史方向与唐刀独立握柄修订见 [20261010 记录](third-person-tang-dao-whirlwind-20261010.md)。
