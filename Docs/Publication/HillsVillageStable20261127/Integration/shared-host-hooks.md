# 共享宿主定向接入清单（R46–R54）

以下 10 份共享宿主在 `origin/main` 基线与当前本机工作区之间交织了其他并行开发（火把/焚化/强化/伐木场/瞬步等）。按 `WORKFLOW.md` 第 8 节规定，不将未验收并行改动整文件覆盖到公共主线，仅记录各文件的 `origin/main` 基线与本机马厩/坐骑相关接入点指纹以便精准合并。

| 文件 | `origin/main` Blob | 本机接入概要 | 筛选马厩变更行 |
|---|---|---|---|
| `Source/FPSGAME/Movement/FPSCharacterMovementComponent.h` | `11bc8c16e4` | R48 玩家网格台阶偏移成员 AppliedPlayerMeshStairOffset / ApplyPlayerMeshStairOffset | 2 |
| `Source/FPSGAME/Movement/FPSCharacterMovementComponent.cpp` | `afce421977` | R48 将既有 StairVisualOffset 增量镜像至本机玩家 GetMesh()，非骑乘/蹲伏生效 | 29 |
| `Source/FPSGAME/UI/ColdSteelHUDWidget.h` | `f1b3d03684` | R46/R49/R53 马匹详情抽屉动效、MountBagBoard、永久解散确认弹窗及回调声明 | 85 |
| `Source/FPSGAME/UI/ColdSteelHUDWidget.cpp` | `0c67454df8` | R46/R49/R53 马匹抽屉动画更新、Esc 关闭解散弹窗与 RefreshMountPage 挂载 | 78 |
| `Source/FPSGAME/UI/ColdSteelInventoryRules.cpp` | `b572053465` | R53 变行马匹背包 (Place=4, mount.<HorseId>) 校验与跨容器转移边界 | 59 |
| `Source/FPSGAME/UI/ColdSteelInventoryWidget.cpp` | `a30d9ce5ea` | R46/R53 ConfigureMountBag 变行绘制、双击快装马具及马匹背包拖拽交互 | 12 |
| `Source/FPSGAME/UI/ColdSteelInventoryPresentation.cpp` | `d45fc61d8a` | R46/R53 详情开窗高亮可用马具与马匹背包表头/格数渲染 | 65 |
| `Source/FPSGAME/UI/ColdSteelShopHUD.cpp` | `4403ec55c4` | R49/R52 马市详情抽屉联动与马具商店入口 BeginStableTackSession | 48 |
| `Source/FPSGAME/UI/ColdSteelShopModel.cpp` | `d4a35807ee` | R52/R53b 东门马具铺 StableTackMenu、stable.tack.buy 交易与 NetworkTradeFinished 刷新货单 | 189 |
| `Source/FPSGAME/UI/ColdSteelWarehouseHUD.cpp` | `c13052aebe` | R53 解散确认弹窗期间屏蔽仓库快捷键 | 7 |
