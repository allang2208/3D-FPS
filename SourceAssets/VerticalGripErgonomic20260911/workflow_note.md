

## 2026-09-11 实拍包握参考：当前运行修订

当前两成员引用 `/Game/Weapons/M4VerticalGripErgonomic/Vertical` 与 `/Prism`；作者入口为 `D:/FPS3D/FPSGAME/SourceAssets/VerticalGripErgonomic20260911/`，详情见该目录 README。此前 Raised 与 Horizontal 资源保留对照，本轮没有覆盖用户的 `M4ArmsIKEditor` 手工序列。

先保留原待机的肘关节弯曲平面，再重建两段手臂方向并分配前臂扭转；逐骨最短弧对齐不足以保证肘部方向自然。整掌定位后，四指采用受限屈伸平面、有限掌骨内收与联动指节弯曲。拇指先让开、四指松开后退握，路径需要针对新手型重新检查。共用参数在 `arm_profile.json`，成员接触与松指曲线在各自目录，不照搬本例数值到其他骨架。

本轮 18 动画源约束及独立压缩读回通过，688 项游戏检查通过、0 失败，两成员共 892 个手部/配件采样无交叉。原空仓拍击主段的既有指间接触保留并与原源对照，不能宣称整个动作全身零穿模。导入日志的既有 GameFeatureData 配置错误、未打包及静音预览范围见 `acceptance.json` 与 README。此记录表示本轮已接入和验证，不代替用户对手型的后续审美确认。

