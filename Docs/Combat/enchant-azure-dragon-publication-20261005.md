# 苍龙整理发布与返工待办（2026-10-05）

用户明确认为 Coherent V9 “不是很合格”。苍龙能量条与龙爪蒙皮／动作均登记为未达标、待返工；本轮只整理和发布，不继续尝试新模型或新动作。[待办](../Backlog.md)保留能量空间效果、突变体式收指抓掠及后续用户确认三项。

## 当前暂留

运行代码仍引用 V9 的十一份已保存资产；当前作者源、共享爪材质与原始 Fab／Epic 输入保留本机，供后续恢复。九次成功攻击激活 30 秒、一次动作只充能一次、延伸范围、物理翻倍与独立魔法伤害、左右两爪交替等既有合同保留。保留不表示模型、能量外观或动画获认可。

恢复源见 [AzureDragon README](../../SourceAssets/AzureDragon20261004/README.md) 和 [V9 制作记录](enchant-azure-dragon-coherent-v9-20261005.md)。认可设计图从旧 EnergyV6 输入目录移到 `SourceAssets/AzureDragon20261004/References/azure-dragon-energy-approved.png`，内容未变；[迁移记录](../Publication/AzureDragon20261005/retained-reference.json)记录散列。

## 实际归档

本机 `trash/azure-dragon-retired-20261005` 已收纳 **117 份文件，14,079,388 字节**：100 份旧作者／导出／中间文件及 17 份旧 UE 资产。包括 RigV2、EnergyV3、V6 近似、ReferenceV7、旧 CombatV4／DualClawV8 入口、修复脚本与静态输出；没有移动当前 CoherentV9、共享材质／纹理、原始输入或返工参考。

UE 旧包先读取资产引用并确认没有废案集合外的引用；通过现有桥批次互斥卸载这些旧包后逐文件移动，没有另起 GUI、关闭已有编辑器或覆盖未保存资产。源码通过 PowerShell 原生文件操作移动，源／目标绝对路径限定在本次目录。所有移动前后 SHA-256 相同，旧路径和原因见 [总清单](../Publication/AzureDragon20261005/archive-manifest.json)。恢复时按清单原路径回迁；被当前兼容入口占用的旧路径需先保留当前文件，不能直接覆盖。

根目录旧绑定／安装／构建脚本已先归档，再用 V9 兼容入口重建。共享基线作者不再导出未使用静态爪 FBX，基线安装不再导入旧静态资产；VisibilityV5 当前只处理共享爪材质。上述恢复入口本轮未执行，不产生新的模型或 UE 保存记录。

## 发布与知识沉淀

直接从 `D:/FPS3D/FPSGAME` 向指定 `allang2208/3D-FPS` 的 `main` 普通推送，按 WORKFLOW 第 8 节与 [武器发布规则](../../skills/ue5-weapon-workflow/references/publication.md)检查远端、待推历史、精确暂存、完整 diff、敏感信息、大文件、许可、脚本语法和文档链接。共享文件只提交苍龙片段，其他任务的未完成代码／暂存内容保持。

公开内容包括苍龙 C++、卷轴／掉落／提示数据、当前原创配方、HLSL、历史说明、待办、SKILL 与归档元数据。授权模型、贴图、参考图、密集姿态／蒙皮数据、Blend／FBX、UE 包、trash 实体及机器回执留本机；源码发布不等于完整资产交付。[发布目录](../Publication/AzureDragon20261005/README.md)列出具体范围。

SKILL 在个人安装和仓库镜像的 [苍龙待办与归档](../../skills/ue5-weapon-workflow/references/azure-dragon-pending.md)同步沉淀：复用武器实例充能、动作时间与双通道伤害结构、局部指骨坐标方法；记录 V6／V7／V9 失败边界，不将被否定的外观与动作升级为认可模板。

## 执行程度

117 份废案已实际归档并核对散列，17 份 UE 包已实际移出旧 Content 路径。十一份 V9 资产与 Game／Editor 构建是此前完整工作区的记录，不是本次公共快照的新构建或视觉证明。本轮仅做用户要求的整理与推送检查；没有运行游戏、PIE、渲染、功能测试或验收，由用户后续测试。
