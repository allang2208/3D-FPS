# 双手锤第三人称风车反转

2026-10-17，按用户要求将双手锤风车的第三人称旋转方向反过来。

原 `FPSPlayerBodyAnimInstance.cpp` 用 `HasSwordAction && !HasHammerAction` 排除了战锤的第三人称反转补偿。现在战锤同样使用已有 `FPSBodySwordMotion::WhirlwindVisualYaw`：按旋风实际阶段和圈数，在最终全身根骨骼上追加 `-2 × 实际旋转角`，使角色已有转动与补偿相加后的视觉旋转角变为原方向的相反数。双手、身体、附着武器和服装随同一根节点转动。

继续使用现有 Start / Loop / End 动画与正向播放顺序，准备、发力、收势、双手握持和头部稳定逻辑保留。无需重新制作或导入动画包。第一人称、镜头、伤害扫掠及技能时间沿用当前实现。

修改源文件：`Source/FPSGAME/Characters/FPSPlayerBodyAnimInstance.cpp`。本地和远端角色共用这条动画表现路径。

源码已落盘，正式 Editor 构建成功，已编入 `UnrealEditor-FPSGAME.dll`。构建日志：`Saved/BuildEditor/build-20261017-083921.log`；本批输出：`SourceAssets/WarhammerThirdPersonSevarog20261016/WhirlwindReverseV9/build-editor.log`。未启动编辑器或游戏，未进行运行测试，由用户体验旋转方向。
