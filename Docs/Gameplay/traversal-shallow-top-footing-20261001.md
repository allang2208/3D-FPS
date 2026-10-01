# 通用攀爬：浅柜顶落脚位置（2026-10-01）

用户要求按配电柜的诊断结果修正通用攀爬。源文件为
`Source/FPSGAME/Movement/FPSTraversalComponent.cpp`，没有修改场景网格、碰撞体或专用标签。

原判定将角色 42 cm 的身体半径同时用于承托采样，且只尝试向内 44 cm 的固定落点。
68 cm 深的配电柜因采样越出柜顶而被拒绝，贴墙位置还会压缩固定落点的身体净空。
此前只读证据保留在 `SourceAssets/DungeonFlueGasStation20261001/CabinetDiagnosis20261001/`。

本次修改：

- Mantle 顶面站立采用胶囊半径一半的脚下承托半径；当前角色为 21 cm，中心、边中点和角向共九点均需真实可行走支撑。仍保留表面起伏条件。
- 身体胶囊仍为原半径 42 cm、半高 96 cm；通过完整胶囊向下扫掠求真正落脚高度，再进行站立净空判断。
- 顶面落点最多尝试六个纵向候选，首先是原落点，其次为根据障碍厚度估算的中部、较靠前位置以及有限的较深位置。每个候选都需完成从起点抬升、越沿和下落的完整身体扫掠；遇到首个合格位置立即结束。
- 只在已找到可抓顶部后进行有限搜索，不新增 Tick、场景扫描、磁盘读取或模型专属位置判断。
- Vault 的背面落点仍使用原支撑范围，专用栏杆的阶梯承托、双向跨栏和自然翻下保留；高度/距离上限及抓取动作不变。

未新增反射字段或改变类布局。常规 Editor 构建回执及源文件备份位于
`SourceAssets/DungeonFlueGasStation20261001/MantleFooting20261001/`。
后台 Editor 构建已成功：首次编译通过本文件，但被同期背包界面字段错误中断；
相关文件更新后再次构建返回 `Result: Succeeded`、`Target is up to date`。
常规 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘，构建详情见该目录的
`Receipts/editor-build-retry.log` 和 `completion.json`。
未启动游戏、运行自动回归或截取画面；由用户在原净化站样板测试。当前样板继续保留。
