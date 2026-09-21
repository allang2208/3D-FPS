# 大旋风外送后摇

当前游戏使用的 V5 动画已接入本目录的 Recover V6：旋转结束后 0.18 秒外送，0.06 秒卸力，再用 0.28 秒回待机。完整设计和实际资产路径见 [开发记录](../../../Docs/Skills/whirlwind-recover-v6-20260920.md)。

`author_recover.py` 读取原 `ImpactV5/Whirlwind_Manny_Editable.blend`，生成本目录完整可编辑 Blend 和 `Export` 中的普通柄 FBX。使用 Blender 5.1.2 后台运行即可制作，不生成预览。

`import_recover.py` 通过项目互斥桥执行，创建独立制作版、烘焙加长柄，再保留当前 V5 备份并只接入 recover。实际加载路径仍是 `A_RuneSword_WhirlwindV5`；本轮接入结果为 `import_receipt.json`。同名已完成的版本会跳过，后续修改应新建修订名。

普通柄源为 `WhirlwindRecover_Manny_Editable.blend`；加长柄完整 FBX 与可编辑左臂关键帧位于 `LongGripExport`。旧 V5 源保留用于回溯。授权二进制和密集姿态数据不公开分发。

已制作并保存两种握柄资产；未测试，由用户测试。
