# 苍龙：未达标、待返工

2026-10-05 用户体验 Coherent V9 后反馈“不是很合格”，本轮登记待办、归档废案与整理源码，不继续制作。当前能量条和龙爪动作均未获认可；模型保存、五指骨架存在及原生构建完成不代表视觉或挥击动作合格。

待办见 [Docs/Backlog](../../Docs/Backlog.md)，整理范围见 [本轮发布](../../Docs/Combat/enchant-azure-dragon-publication-20261005.md)。

## 暂留的当前实现

- `CoherentV9` 保留作者脚本、HLSL、恢复入口及本机 Blend／FBX／保存回执；运行代码仍引用 `/Game/Weapons/AzureDragon20261004/CoherentV9` 的十一份资产。保留用于恢复和后续返工。
- 原始 `Original/Fisto.glb`、Fab 下载元数据、`AzureDragonClaw.blend`、`Export` 法线图集及指型定位数据留在本机。V9 作者还依赖本机突变体 3 的爪型参数，详见 V9 README；公开仓库不含这些授权输入或密集数据。
- 认可设计图已完整移到 `References/azure-dragon-energy-approved.png`，散列与原图相同。它是返工参考，不再承担已退役 V7 的贴图输入。
- `AzureDragon.hlsl` 与 `install_ue.py` 只恢复共享爪材质／法线；`VisibilityV5` 当前安装器只更新共享爪材质，不恢复已退役的 EnergyV3。

保留九次成功攻击激活 30 秒、同次动作只充能一次、范围延伸 50%、原物理通道翻倍与原角色物理攻击值另行魔法结算。左右双爪交替、两倍尺寸与侧面待机角度继续保留。当前参数和模型表现仍属未达标原型。

## 恢复顺序与边界

本轮没有重新运行下面的制作、导入或构建入口。已有十一份 V9 资产保存和 Game／Editor 构建记录来自上一轮，详见 `CoherentV9/install-receipt.json` 与 `Saved/AzureDragonCoherentV9/delivery.json`；构建覆盖当时完整工作区，未单独构建本次公共提交快照。

需要重新制作时，在合法本机输入齐备后依次执行：

1. Blender 执行 `author_model.py`，生成原模型适配母版和法线；Python 执行 `finger_landmarks.py`。
2. `CoherentV9/run_author.ps1` 生成当前爪和能量模型。根目录 `rig_claw.py` 兼容入口转发 V9 爪作者。
3. 根目录 `run_install.ps1` 执行 `install_current_ue.py`，先共享材质，再 VisibilityV5 的爪可见性参数，最后 V9。`install_rig_ue.py` 仅转发 V9 安装器。
4. 根目录 `run_build.ps1` 转发 V9 原生后台构建入口。沿用已有编辑器的桥互斥；不存在编辑器时使用适用的后台 commandlet，不主动启动 GUI、PIE、游戏或验收。

## 废案与公开边界

RigV2、EnergyV3、EnergyV6、ReferenceV7、CombatV4、DualClawV8、旧修复／构建入口和静态输出已移入本机 `trash/azure-dragon-retired-20261005`。117 份文件含 17 份旧 UE 包，共 14,079,388 字节，移动前后 SHA-256 一致；[归档清单](../../Docs/Publication/AzureDragon20261005/archive-manifest.json)保留原路径、目标、原因与替代物。当前 V9、共享材质和合法原始输入未归档。

原爪来自用户选定并下载的 CaptainHC [Fab Dragon Claw](https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a)，本机来源声明在 `Content/ThirdPartyNotices/AzureDragonClaw.txt`。公开 Git 仅保存原创制作配方、HLSL、原生源码、数据、待办、SKILL 和归档元数据；不公开 Fab／Epic 派生网格、PBR、设计图、骨架供体数据、Blend／FBX、UE 包或机器回执。恢复项目需自行取得相应输入，本仓库不是可独立运行的完整资产发行包。
