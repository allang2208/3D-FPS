# 步枪轴向往复配方

本轮沿当前 UE 压缩 fire / aim_fire 读取枪轴运动，以 M4 的后冲、过零和回弹形状补齐指定枪型。当前结果见 [逐枪说明](../../../Docs/Weapons/rifle-axial-recoil-20261008.md) 的 2026-10-09 实施节。

- `read_motion.py`：M4、HK416、191、A762 的动画与握姿引用。
- `read_remaining_motion.py`：AKM、M16A2、ASH-12、SVD、PKM、201 的动画与握姿引用。
- `make_axial_profile.py`：由本地读数生成 `Source/FPSGAME/Weapons/RifleAxialRecoil.h` 与稀疏 `recipe.json`。源采样为 240 Hz，运行表为 60 Hz 标量曲线；每个时刻扣除对应枪型正在参与姿态的原生项。
- `finish_backend.ps1`：本轮最初的读取/构建入口；仅补做构建时用 `-SkipAssetRead`。后续构建入口为相邻 `RifleAxialRecoil20261009/finish_backend.ps1`。调用前按当前宿主配置 UE 路径。

先通过已有桥或后台 commandlet 读取两个 Python 入口，再运行曲线生成器。网格、动画和密集姿态 JSON 需要本机授权资源，不公开分发。读取结果是本轮冻结输入，不能混用不同模型修订；新的采样、渲染或游戏测试需要用户明确要求。

公开运行表已经足够编译该表现逻辑，无需在游戏运行时读取外部 JSON。公开仓库不含完整 UE Content。ADS、SVD 收尾、PKM 原生项活动时间、ASH-12 去重及“不改弹道/射速”的边界由运行代码和 `recipe.json` 共同记录。

本轮已完成常规 Editor/Game 构建，未游戏验收。过期请求、失败读取及前版本备份见 [归档记录](../../../Docs/AssetArchives/weapon-gunplay-20261009.json)，正式采样与成功构建回执继续留本机。
