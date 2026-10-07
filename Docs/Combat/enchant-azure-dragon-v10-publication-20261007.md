# 苍龙 V10 整理发布（2026-10-07）

用户要求：废案全部放入 trash，更新 git，把有用的内容沉淀到对应 SKILL，按推送与仓库整理规则检查后推送到 `allang2208/3D-FPS` 的 `main`。

## 当前状态

V10 运行中：Fab 龙爪（`/Game/Weapons/AzureDragon20261004/ClawFab`）与屏幕空间能量条（`HudV10`）。用户 2026-10-07 确认 V10.10 特效合格、V10.11 斩击类判定延伸到爪尖“成功”。V10.12–V10.15 只完成构建和资产保存，尚待用户体验：
- V10.12：复查修复；
- V10.13：联机他人可见；
- V10.14：到期粒子消散；
- V10.15：所有消失途径接入消散。

逐版记录见 [V10 文档](enchant-azure-dragon-v10-20261006.md)。

## 实际归档

本机 `trash/azure-dragon-retired-20261007` 收纳 **113 份文件，26,437,728 字节**，其中 19 个 UE 包、54 份作者源和中间件、40 份旧运行日志：
- Coherent V9：作者源、导出和 11 个 UE 包（龙爪与能量柱）。用户 2026-10-05 判定不合格，已被 V10 取代。
- VisibilityV5：V9 共享爪材质的可见性补丁。
- V9 共享爪材质 `M_AzureDragonClaw` 及其 `AzureDragon.hlsl`。
- 根目录 V9 转发脚本 `install_rig_ue.py`、`rig_claw.py`。
- V10.1 原创 Blender 龙爪：作者脚本、安装脚本、HLSL、Blend／FBX、5 个 UE 包。用户要求改用库中 Fab 爪后已不再使用。
- V10.8 起不再使用的余烬和 Fab 旧爪痕材质（HLSL 与 UE 包）。
- 一次性的材质用途补丁和火焰包探测脚本、Blender 自动备份，以及被后续运行取代的安装日志（每个目录保留最近一次）。

**UE 包的处理**：先通过资产注册表确认这 19 个包在这组之外没有任何引用者，也没有未保存修改；移动时编辑器已关闭。逐文件移动前后 SHA-256 一致。原路径、目标、字节数、散列、原因和替代物见 [归档清单](../Publication/AzureDragon20261007/archive-manifest.json)；恢复时按原路径回迁。顺带删除了 2026-10-05 归档后残留的空目录。

**仍在使用的依赖，保留未动**：Fab 原模型及元数据、`AzureDragonClaw.blend`、指位数据、共享法线图集，`ClawV10/Textures` 的脉络和烟雾贴图（烟雾贴图已无运行引用，作为同一作者脚本的产物保留），以及 HudV10 生成源与认可设计图。

## 入口调整

- 原创爪安装脚本里的贴图导入拆成 `ClawV10/install_textures_ue.py`。所有权标签不变，原来保存的两张贴图仍可替换。
- 根目录 `install_ue.py` 只导入共享法线。
- 根目录 `install_current_ue.py` 改为 V10 链：共享法线 → 贴图 → HUD → Fab 爪。
- 根目录 `run_build.ps1` 转到 `ClawV10/run_build.ps1`。
- `install_fab_ue.py` 与两份 README 已同步。

以上恢复入口本轮未执行，没有产生新的 UE 保存。

## 代码依赖修正

死亡加速消散原本引用另一会话尚未提交的 `FPSPlayerDeathMotion.h`。为了让本次提交可以单独成立，改为本地常量 `PlayerRespawnSeconds=2`，注释说明它对应 `UFPSCombatHealthComponent` 的 2 秒重生计时。

## 发布与知识沉淀

- 直接从 `D:/FPS3D/FPSGAME` 普通推送 `HEAD:main`，遵守 WORKFLOW 第 7、8 节和 [武器发布规则](../../skills/ue5-weapon-workflow/references/publication.md)。
- 提交树用临时索引搭建，不改动共享暂存区。
- 共享文件只按 hunk 选入苍龙相关部分：符文剑组件、上挑、联机 PlayerState、第三人称身体同步、附魔提示和面板、附魔数据、打包目录、SKILL 和待办。其他会话同一文件里的未提交改动不提交，包括磐螭、裂空飞行参数、剑基础距离、庄家、旋风圈数、死亡动作、全自动扳机和其他打包目录。
- 公开内容：苍龙 C++、附魔数据与文案、原创配方、HLSL、文档、SKILL 和归档元数据。
- 不公开：Fab 派生模型／贴图、百炼生成源图、Blend／FBX、UE 包、trash 实体和机器回执。
- SKILL 沉淀：
  - 武器工作流的 [苍龙现状与做法](../../skills/ue5-weapon-workflow/references/azure-dragon-pending.md)（已同步个人安装镜像），以及武器 SKILL 和附魔卷轴参考中的苍龙条目；
  - 联机 SKILL 新增第十三节：剑技在客户端禁用、临时增益申报与服务端复原、转发命中本地返回 0、长判定线的 `TraceStart`、纯表现状态搭身体同步。这一节写入共享工作区后，已随另一会话的提交 `84f42fd3` 一起发布，本次提交不再改动该文件。
- **基线变动**：暂存期间 `main` 被其他会话推进了两次（`95e33ca0`、`84f42fd3`）。第一次在旧基线上建出的本地提交还没推送就已丢弃，分支指回 `84f42fd3`，所有混合文件都在新基线上重新生成。

## 执行程度

- 归档和散列核对已实际完成。
- 苍龙代码在完整工作区里的 Game／Editor 构建记录来自此前各轮；本次常量修正后又构建了 Game 目标（结果见发布检查记录）。
- 提交只包含按 hunk 挑选的子集，没有在独立工作树里单独编译。所选部分引用的符号已逐一确认存在于 HEAD 或本次提交中。
- 没有运行游戏、PIE、渲染、功能测试或验收。
