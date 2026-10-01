# A762 原厂 / 幻影握把扳机让位 — GripClearance09

2026-10-01 用户反馈 R08 原厂与幻影后握把的前下方仍挤入扳机区域。本轮仅调整这两款握把的前缘；已保存正式资产及独立 R09 版本，未测试、未渲染、未运行游戏。

## 修改

- 在 `WPN_root` 装配坐标中，将接颈前下部平滑向后收，最大局部位移 11.5 mm；不是整把握把平移。
- 变形只作用于 Z=-44～12.5 mm、Y<36 mm 的前部区域，在上下边界及后侧平滑归零。上端连接面、后侧轮廓和下部握持区保留。
- 解析计算变形雅可比的逆转置来调整原自定义法线，保持与曲面一致，不整件重新计算法线。
- 原厂修改 1,916 个顶点、3,985 个三角面的角法线；幻影修改 8,449 个顶点、10,173 个三角面的角法线。
- 不增删面，不重拓扑；原有 UV、材质槽、骨骼、动画和安装变换由当前网格原样保留。

## 资产与源

- 正式枪体：`/Game/Weapons/A762/Integrated20260920/SK_A762_Manny`，294,008 个三角面。
- 正式幻影握把：`/Game/Weapons/A762/Accessories05/Meshes/SM_A762_phantom_reargrip`，49,622 个三角面。
- 独立版本：`/Game/Weapons/A762/GripClearance20261001/`。
- 可编辑源：`A762_GripClearance09.blend`；幻影源：`Exports/SM_A762_phantom_reargrip_R09.fbx`。
- 本轮输入及原资产备份：`Input/`、`Before/`。采集当前正式资产后生成稀疏编辑计划，写回当前源网格，不重装 R08 整套资产。
- 制作入口：`author.py`、`author_blend.py`；接入入口：`install.py`，经 `../WeaponSurface20260930/run_ue.ps1` 的批次锁执行。
- Accessories05 批量配件制作入口在 R09 已安装时引用本轮幻影 FBX；均衡、防滑继续使用 R08。

## 保存记录与未测试边界

`install_receipt.json` 的 `complete` 为 `true`，四个文件（两个正式资产、两个独立版本）的文件哈希与保存回执一致。保存脚本明确输出 `Python script executed successfully` 并请求正常退出；随后 UE Python 清理阶段发生访问异常，日志为 `../WeaponSurface20260930/logs/install.20261001-150236-124.log`。没有追加重新加载、模型验收、截图或游戏测试；实际扳机空间及持枪效果由用户测试。
