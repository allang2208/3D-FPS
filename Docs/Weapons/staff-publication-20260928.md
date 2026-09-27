# 长杖整理、技能与发布恢复

本轮按用户授权，整理学徒长杖制作链并从 `D:/FPS3D/FPSGAME` 普通推送至 `allang2208/3D-FPS` 的 `main`。当前共享分支名保留，不切换或覆盖其他会话的工作文件。

## 公开范围与边界

直接发布独立长杖目录／装配源码、目录配置、预览材质入口、背包图标采集与横竖比例修正、实际裸臂网格的装备 profile，以及作者配方和说明。共享文件只暂存法杖相关段落，不夹带另一任务的工具强化、LMG201、库存交互及其他角色／技能变化。

当前第一人称动作仍依赖本机 V7 原生网格、采样姿态及未发布的共享施法／角色接口。独立运行实现保存为 `StaffPublication20260928/new-runtime-sources.patch`，接口归属和文件散列见同目录 `runtime-handoff.json`；该补丁是交接材料，未自动写入远端编译目录。公开提交不代表完整本机玩法、所有法术或装备切换已经在 Git 克隆中独立集成。

模型、纹理、设计图、Meshy 响应、签名下载地址、密集骨骼／表面数据及 UE 包不公开提交；原始素材商用许可与公开再分发许可分开处理。两份当前生成头 `StaffAuthoredPoseV13.h`、`StaffAuthoredLeftGaitV16.h` 含本机原生绑定和采样数据，同样保留本机，通过作者源恢复。凭据不进入公开配方或回执。

## 当前有效制作链

| 用途 | 入口／保留输入 |
|---|---|
| 模块化几何 | `SourceAssets/ApprenticeStaff20260927/BarkRebuildV21/author_model.py`；读取 V18 Meshy 原始 GLB、V19 的表面／PBR |
| 世界水晶 | `QuartzAimV22/ue_quartz_material.py`、`quartz_parameters.json`；密度变化与切面高光 |
| 预览水晶 | `WorkbenchPreviewV23/install_preview_material.py`；仅覆盖预览副本，解决反向 alpha 下的消失 |
| 手部装备 | `EquipmentIntegrationV24/register_equipment.py`；注册实际 `BarePalmV7/M4/SK_M4_BareArmsV7` 源路径 |
| 目录图 | `IconFramingV25/build_catalog_icon.ps1`；共用当前 UE 图标工作室，输出 canonical 和旧文件名别名 |
| 横竖显示 | `ColdSteelStaffIcon` 与库存绘制／拖动共用尺寸函数；`IconOrientationV26` 保留公式排查记录 |
| 握持及移动 | V10 掌向输入、V13 完整姿态、V14 右移、V16 左手步态、V17 蓄力前移；以及 V7 M4、GripV5 握弓参考 |
| 施法及瞄准 | `FPSStaffCasting.cpp`、`StaffCastMotion.h`；V22 火球／冰锥松手提交预览状态，延续到接触发射 |

UE 当前几何路径仍为 `/Game/Weapons/ApprenticeStaff20260927/Meshes`；保留 BarkRebuildV21 修订副本及 V22 材质，预览材质为 `/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23`。恢复合法本机输入后按上述依赖顺序制作；不得重跑已归档的初始 `wire_staff*` 脚本覆盖当前共享源码。

V24 曾输出 256×320，V25 调整为 256×1024；两轮均未修正按整幅透明画布缩放造成的 F 转向缩小。V26 在目录导入／动态图发布时提取可见范围，画刷 UV 与尺寸同步，再对两个方向使用同一倍率。以 40 像素格为例，旧横放可见长度 72.81、竖放 116.50；新计算均为 139.40 像素。数字是像素和公式证据，不是实机截图。

## 废案和保留理由

156 份旧备份、自动 `.blend1`、无运行引用的 V12／V15 姿态头、旧局部握姿头和一次性接线／关停脚本已移入 `trash/staff-publication-20260928/`。逐项源／目标路径、大小、移动前后 SHA-256、原因和替代物见 [归档清单](../AssetArchives/staff-publication-20260928.json)。

早期目录仍可能被当前作者脚本读取，不按日期或版本号整体删除。当前 Blend、原始 Meshy 来源、骨骼／蒙皮输入、纹理、参考图和历史诊断证据继续留本机。历史文档中的 `Before` 路径通过归档清单追溯。

## 技能与状态

可复用经验已补充到 UE 图标、第一人称手臂／装备、长杖模块化和施法瞄准技能，并同步同一新增内容到个人技能与工程镜像；其他已有章节保持各自状态。

最近本机基础 DLL 构建成功：`Saved/BuildEditor/build-20260928-001542.log`，包含 V26 修正。本轮整理只执行用户要求的归档和发布检查，不重新构建、启动 UE、运行游戏或做视觉验收。完整本机 DLL 的构建结果不能作为精确拆分后的公开源码快照已独立构建的证据。

发布检查：精确暂存 141 个文件；完整暂存差异保存在本机 `Saved/StaffPublication20260928/reviewed-staged.diff`。空白错误检查通过，69 份 Python 配方、2 份 PowerShell 配方及 9 份 JSON 可解析，四项相关技能结构检查通过；凭据／签名 URL 扫描无命中，最大单文件不足 100 KiB。156 份归档已逐项确认原路径移出、目标散列一致。这些是发布检查，不是游戏或视觉测试。
