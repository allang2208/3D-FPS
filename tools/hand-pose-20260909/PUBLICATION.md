# 发布检查 · 2026-09-09

目标：origin/main，https://github.com/allang2208/3D-FPS.git。
独立 worktree 从 242eee2 建立；原 master 相对该远端落后 34、领先 25 个提交，未推送那些无关提交，也未改写原分支。

本次内容仅 tools/hand-pose-20260909 代码证据归档和枪械技能的新分卷/入口。没有替换远端运行脚本、模型、贴图、存档或其他工作。

- Godot 4.7.1 本地完整工作区 --headless --import 完成，无 Parse/Compile/Script Error；退出有已知资源/RID 清理提示。
- --headless --quit-after 180 退出 0，仅引擎 banner；它是冒烟命令记录，不作场景功能通过证据。
- test_combat：投射物伤害、移动、血量、受伤、特效清理检查 true；ADS HUD 因 status_bar_missing 跳过，不能将最后汇总 ads_hidden=true 当成此项已测。
- test_reload：自动换弹与 R 键换弹均 ok=true。combat/reload 均记录 WarehousePanel 缺失的已有测试场景集成提示，未扩大范围修理。
- test_held_hand_pose：255 姿态与 326 松手样本，failures=0；dummy renderer 材质提示属于无头后端，未据退出码掩盖断言。
- skill-creator quick_validate：Skill is valid；引用的新增 Markdown 文件存在。
- 发布内容通过明确路径清单、源快照一致性、许可证、文件大小与 git diff --cached --check 检查。

归档不含第三方可提取资产；其依赖不足以在干净克隆独立重现完整动画枪械。运行数字来自本地完整工作区，原始日志附于 evidence。新技能总结可复用合同，不将这些固定样本扩大为无限输入的穷举保证。
