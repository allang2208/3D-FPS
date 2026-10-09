# 研究员 M-05 V05：特殊状态与衣物同步过渡

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

用户认可 V04 基本效果后授权复查，并要求继续处理。V05 补齐复查确认的三项问题：独立骨架未接倒地／起身、眩晕循环未接入、攻击结束缺少姿态过渡。

## 制作

- 以 V04 作者文件为母版，保留基础顶点、拓扑、UV、材质、权重及原 120 个衣物形态；不重新平滑已认可衣面、不叠加基础撑开量。
- 从当前 Nurse 共用库取得 `Hit_Knockback`、`LayToIdle`、`ProneToIdle`、`Dizzy`，保持源骨骼动作和时长，将独立副本绑定研究员骨架。共用库原资产保持原样。
- 为这四段制作 111 个新衣物形态，外套和前襟／口袋／胸牌／纽扣同步；沿用固定衣物坐标、局部解剖碰撞分带以及空间、时间平滑。眩晕修正首末衔接。
- 原四段 V04 基础动画继续使用，新增四段放在 `Animations/V05`，明确绑定 `Knockdown.FallClip/GetUpClip/ProneGetUpClip` 和 `Combat.DizzyClip`，保留共用骨架一致性保护。
- 网格总计 231 个衣物形态；完整身体 199621 三角面，穿衣组合 219505 三角面，161 骨，19 个独立衣物作者对象。

## 动画播放代码

`NurseZombie.cpp` 仅在角色具有 `FacelessResearcher` 标签时使用已有 `UFatZombieAnimInstance`：待机／移动切换约 0.24 秒混合、攻击进入约 0.10 秒，保留原命中时钟与移动速度。步态仍计入原片段的播放倍率；连续受击复用播放器、重新捕获当前姿态，首次受击约 0.07 秒混合，重复受击约 0.04 秒，避免重置受击时钟后重播过期快照。

`FatZombieAnimInstance.cpp` 的快照节点为研究员同时保存当前有效的 FRS 衣物曲线，并将其随骨骼快照一起混合。采样在已有过渡事件执行；不新增角色 Tick、资源加载或独立运行时布料模拟。对快照节点的访问限定为研究员明确使用的原生播放器类型，避免把其他派生播放器的不同代理布局误当成同一结构；其他角色保留既有播放分支。

本次没有新增反射字段或修改蓝图父类；运行入口仍为原 `BP_FacelessResearcher` 与 F6“研究员 M-05”。

## 文件与实际完成状态

- 作者：`Authoring/FacelessResearcher_V05.blend`。
- 输入：`state_source.json`、`Motion/`。
- 新曲线：`state_curves.json`、`state_manifest.json`。
- 导出：`Delivery/`，包含完整身体、独立衣物及运行组合 FBX，衣物与组合同时有 GLB。
- 记录：`export_receipt.json`、`build_receipt.json`；实际 UE 保存以 `ue_delivery.json` 与 `import_process.json` 为准。
- 源码修改前副本：`SourceBackup/`，仅供追溯本轮差异，不覆盖当前并行修改。

两份 V05 网格、四段新增状态动画、研究员骨架和原角色蓝图共 8 个资产已由无界面 commandlet 保存，`ue_delivery.json` 为 `stage: saved`，`import_process.json` 记录退出码 0。最终代理类型保护改动已完成 Editor／Game 两个常规目标构建，`build_receipt.json` 记录两项退出码均为 0。Editor 构建曾因已有编辑器占用暂停；用户保存并退出后完成最终编译，没有主动打开或重启编辑器。

制作入口依次为 `export_states_v05.py`、`tailor_states_v05.py`、`prepare_states_import_v05.py`、`import_states_v05.py`，位于 `Tools/FacelessResearcher/`；构建使用 `build_states_v05.ps1`，后台保存使用 `save_states_v05.ps1`。再次制作时继续保留 V04 基础数据。

未启动游戏、PIE、截图或渲染。构建和资产保存不等于特殊状态及过渡已通过实机验收，最终表现由用户测试。
