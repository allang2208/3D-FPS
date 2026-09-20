# M16 换弹回位与枪托接口修复（2026-09-20）

2026-09-20 用户已确认本次修复成功。整理与发布范围见 [M16 发布记录](m16-publication-20260920.md)。下方进程、构建和读取结果是修复当时的记录，不代表后续会话的实时状态。

## 换弹收尾

用户已认可当前动作主体，本次保留现有动画、弹匣接触和空仓拉机柄动作。

读取实际 UE 压缩动画的末帧：基础/握把/弹鼓相关换弹末帧 WPN_root 与各自待机位置相同，握把派生版本只有约 0.0014 cm 的浮点误差。问题位于 `AFPSGAMECharacter::UpdateViewmodel`：换弹期间 `M4ActionFramingAlpha` 一直指向动作展示位置，只有退出换弹状态后才以指数滤波回到腰射位置，叠加于已经回到待机的骨骼姿态。

修复限定 M16：普通换弹源动画第 108–126 帧（60 fps，0.30 秒）线性回收展示偏移；空仓换弹第 143–162 帧（约 0.317 秒）回收，保留第 143 帧之前的拉机柄接触。通过 `ReloadSourceTime` 使用当前换弹速度映射，覆盖普通弹匣、扩容弹匣、弹鼓与握把组合。动作完成时清除旧换弹片段和展示偏移，避免残留姿态继续参与待机。

## 四种 M16 枪托

检查范围：原厂接口，以及 skeleton、qr_performance、core_stock、tactical_telescopic 四种 M16 改造件。

原厂枪托与机匣在根坐标 Y=0.041045 m 处共用 106 边轮廓。隐藏原厂枪托后，该机匣切口外露。旧改造件只有内半径 17 mm 的空心圆圈，其截面无法覆盖机匣的完整轮廓，且与较细的缓冲管之间留下通孔。

本次移除四种改造件的旧空心圈，使用机匣原始 106 点轮廓制作闭合端板、缓冲管过渡肩和闭合后端面。前端嵌入机匣约 0.40 mm，后端与现有枪托支杆相交封口。保持枪托主体、安装坐标、材质槽、UV0–3 和主体分裂法线。原厂装配的对应切口本身匹配，不修改原厂外观。

核心枪托额外修补三个局部微裂缝，影响范围分别约 0.305、0.127、0.147 mm。四种修复模型的几何检查均为 0 开放边，4 个 UV 通道；已逐个查看接口源模型渲染。该检查不代表游戏内材质或动作验收。

## 可编辑源与接入

- 源目录：`SourceAssets/M16RecoveryStocks20260920/`
- 可编辑文件：`M16_ClosedStockInterfaces_Editable.blend`
- 模型重建：`repair_stocks.py`，只读取旧母版并重建四种枪托；不重跑整套配件迁移。
- 导出：`Meshes/SM_M16_<variant>.fbx`
- 接入脚本：`install_stocks.py`，保留原运行时材质绑定，源改变冲突时停止。
- 目标仍为 `/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_<variant>`，不改枪匠数据和存档标识。
- 原资产备份：已归档到本机 `trash/m16-retired-20260920/SourceAssets/M16RecoveryStocks20260920/PreviousAssets/`。
- 诊断：`runtime_sources.json`、`stock_topology.json`、`repaired_topology.json`；修复参数 `repairs.json`。

四种资产均已导入并保存，记录见 `installation.json`。回位源码与 19:00:46 编译生成的目标文件内嵌 SHA-256 一致；当前编辑器进程 78632（19:08:30 启动）已加载 19:08:01 更新的常规 `UnrealEditor-FPSGAME.dll`，证据见 `native_object_source.json` 和 `integration_receipt.json`。

本次两次附加 Live Coding 请求分别遇到动作数限制、其他模块 `WitchMonster.cpp` 的 C3487 错误，均未作为编译成功依据；上述源码/目标文件及后续常规模块加载记录是 M16 修改的接入依据。未启动游戏回归，实际操作效果交由用户测试。
