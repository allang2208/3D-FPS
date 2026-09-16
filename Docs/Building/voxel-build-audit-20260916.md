# 建筑系统运行期验收 `-VoxelBuildAudit`（2026-09-16）

## 运行

```
UnrealEditor.exe D:/FPS3D/FPSGAME/FPSGAME.uproject <已开放建造的地图> -game -VoxelBuildAudit -windowed -ResX=1280 -ResY=720
```

日志里看 `VoxelBuild: PASS/FAIL ...` 与结尾的 `VoxelBuild: COMPLETE checks=N failures=M`；跑完自动 `quit`（与背包/仓库等既有验收同一套模式：`AFPSGAMEPlayerController::BeginPlay` 里按命令行参数建运行器 + 定时器驱动，`UVoxelBuildAudit` 逐项执行）。需要玩家与已开放建造的地图（`DayNight_Lighting` / `L_Normandy_FPS_Test` / `L_MilitaryTrench_FPS_Test` / `L_TemperateHills_Initial`）。

## 负责的功能（每一项 = 一个玩家可见契约）

| # | 检查 | 覆盖的玩家可见行为 |
| --- | --- | --- |
| 1 | 调色板资产可加载；`wood/stone/marble` 的密度、抗压、抗拉、抗剪、耐久与 `UVoxelBuildPalette::Physical()` 逐项一致 | 防止承重数值被无声改回（本周改过 3 次：强度翻倍、抗剪 300 kPa、重量 1/4） |
| 2 | 过载曲线：1.05× → ≈28.6 s、1.5× → 20 s、2× → 15 s、重度过载下限 3 s（与解算器共用 `VoxelJointStrength::OverloadSecondsToFailure`） | "过载不再瞬间崩塌、约 30 s 后失效"的手感契约 |
| 3 | `voxel_block_wood/stone/marble` 存在于 `items.json`，且 `Icons/wood|stone|marble.png` 图标文件在位 | 拆除/残骸回收发放的方块能在背包里正常显示 |
| 4 | 在玩家脚下真实地面放置 1 格 → `Undo()` 报回该材质且方块数回落 | "撤销 = 拆掉最近一批建造并把方块还给你"（不再恢复旧方块、不可刷取） |
| 5 | 再放 1 格 → 直接拆除报出同样的材质 | "右键拆除的方块进背包"的数据来源 |
| 6 | 编辑后建筑存档文件存在且非空 | 建筑改动确实落盘（配合 `Tools/Building/read_voxel_save.py` 可看内容） |

## 不负责

视觉、手感、帧率、多人、倒塌物理的真实观感、大结构承重收敛速度——这些仍然由用户实测。数值类断言只用公开接口，不替代实机验收。

## 与其它工具的分工

| 工具 | 作用 |
| --- | --- |
| `Tools/Building/run_voxel_stress_probe.ps1` | 离线复算材质强度与净跨契约（不需要引擎、不需要玩家） |
| `Tools/Building/read_voxel_save.py` | 读存档：范围、层数、材料、损伤、断键、残骸、构件 |
| `Tools/Building/audit_voxel_placement.py` | 无头复现放置判定（自建地板逐格试放） |
| **`-VoxelBuildAudit`（本次新增）** | **在真实游戏进程里跑材质表/过载曲线/物品目录/放置-撤销-拆除闭环/存档落盘** |
