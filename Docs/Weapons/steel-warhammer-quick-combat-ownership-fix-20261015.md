# 战锤快速近战只扣体力：运行状态修复

用户在测试中反馈按 F 后扣体力，但没有战锤动作。本轮按该症状做定向排查；没有调整 V3 的动作姿态和时序。

## 证据与修复

- 现有 PIE 中手模可见，正式快速近战资产可加载、长度 0.5 秒；读取原始轨道确认包含准备、直击、回收变化。首次读取时 ASH12 缓存标记为 false，未捕获到该次 F 触发的完整逐帧状态，因此不能将这次读数当作所有失败场景的根因证明。
- 在隔离临时档案中，普通配置的完整角色/工具更新能推进动作和实际武器骨骼。
- 针对保留 ASH12 缓存标记的换武器场景，`before-cached-ash12-trace.txt` 复现相同症状：`begin accepted` 时体力从 150 变为 135、风格为战锤；紧接着 `after owner` 已变为 `phase=0, age=0`，工具下一步恢复 Idle，没有采样任何有效出手帧。
- `ApplyColdSteelProfile` 在切到工具时保留枪械型号标记。`UpdateWeaponState` 原先只看 `bUseASH12` 与枪械自身的 `WeaponState`，直接取消共用快速近战组件，未确认该组件当前归属。
- 现在 ASH12 的取消和推进分支都只接受 `Rifle` / `M4ReferenceRifle` 风格；战锤仍由工具执行器在相机之前推进一次，共用组件不会被旧枪械状态清掉。
- 同时修正锤头标记单位：实测 `WPN_root` socket 的尺度是 100，旧标记又将局部坐标乘 100，导致判定点偏离。运行时头文件与 V3 作者生成式均改为原生局部单位，正式动画无需重导入。

## 文件

- `Source/FPSGAME/FPSGAMECharacter.cpp`：限定 ASH12 对共用快速近战的所有权。
- `Source/FPSGAME/Production/WarhammerQuickCombatMarker.h`：修正锤头局部单位。
- `SourceAssets/SteelWarhammer20261014/QuickCombatHeadThrustV3/author_head_thrust.py`：重制入口使用同一单位合同。
- `Source/FPSGAME/Production/WarhammerSprintAuditCommandlet.cpp`：增加显式 `-QuickCombatOnly` 定向诊断模式，不执行其他冲刺审计；`-CachedASH12` 重现旧型号标记，`-UserEquipment` 只读最近 PIE 档案并在隔离副本装备战锤。
- `SourceAssets/SteelWarhammer20261014/QuickCombatOwnershipFixV4/`：保存修改前文件、逐帧诊断、构建日志和交付回执。未写入用户存档。

## 编译依赖

排查中构建先后遇到并行开发的 HeQue 跳砸定义尚未落盘、体素存档字段尚未落盘，以及篝火展示的 `TObjectPtr` 被 `auto*` 推导等错误。HeQue 和体素文件未由本轮修改；篝火仅修正指针访问写法，龙息诊断源仅调整对应头文件的包含顺序。修改前文件保留在 `Before/`，未运行这些系统的测试。

定向后台复现与正式构建结果以本目录中的回执为准；后台动作时钟/骨骼证据与游戏画面验收分别报告。

## 本轮落盘结果

- `build_receipt.json`：`FPSGAMEEditor` 和 `FPSGAME` 的 Win64 Development 正式构建均为 exit 0，分别完成于 2026-10-15 15:56:28、15:57:51。
- `after-cached-ash12-trace.txt` / `after-cached-ash12-receipt.json`：同一旧枪械标记条件修复后 exit 0，`started=1 advanced=1 sampled=1 finished=1 failures=0`。实际 `WPN_root` 随快速近战序列变化，动作完成后退出占用。修改前同条件为 `advanced=0 sampled=0 failures=2`。
- `-UserEquipment` 的进一步诊断没有运行：先遇到其他项目 commandlet，等待其结束后 UE 编辑器已启动。为保留编辑器现场没有关闭它或另起实例；没有该场景的通过结论。
- 正式 V3 动画未改动、未重新导入；本轮修复进入正式 DLL / Game 可执行文件，作者脚本与锤头标记元数据同步落盘。
- 未启动游戏、截图或进行画面/联网验收。用户此前那次 F 触发没有完整逐帧捕获，因此当前结论是已修复可复现的取消路径，实际使用效果仍由用户复测。
