# 冷钢UI收尾发布记录（2026-09-06）

## 本次发布

当前冷钢标准、完整面板开发工作流、AGENTS/WORKFLOW/DESIGN/registry入口、项目SKILL及公共字体接口。普通UI微软雅黑UI，物品名SimHei，数字Consolas；包括标题字距、物品名称统一加粗和RichTextLabel字体继承。

本机 godot-3d-dev SKILL 及 references/ui.md 已同步去除过时字体/主题指导；项目内 skills/godot-cold-steel-ui/SKILL.md 随Git发布，作为可共享规则。

原始game-dev归档CSS/JS和manifest未修改。清理本轮两份无引用中间代码快照：docs/preview/gunsmith-ui-audit/panel-before.gd.txt、font-before-panel.gd.txt；保留最终截图、对照图、复现脚本与有效资源。

## 验证

在origin/main的独立发布目录运行Godot 4.7.1，使用独立INVENTORY_SAVE_PATH。

- SKILL校验与文档相对链接检查通过。
- --import退出0，但基线部分fir_sapling、lolipop_pines贴图缺失，并有导入退出时资源泄漏报告；未修改这些资产。
- test_ui_tokens.gd退出1：冷钢色板与配置检查通过，远端原有backpack_hud.gd硬编码颜色检查失败；该文件本次未改动，未豁免或删改门禁。
- --quit-after 180退出0，日志无脚本错误。
- test_reload.gd：自动换弹、R换弹均ok=true。
- test_combat.gd：移动、血量、受伤、特效清理true；proj_hit_damage=false，准星检查因status_bar_missing跳过。临时恢复远端原版style.gd复测得到相同结果，随后还原本次字体改动。不能记为战斗全通过。
- 暂存范围只含本记录、规则/技能文档、注册表与ui/style.gd；不包含导入时生成的无关metadata，无新增二进制资源。

## 未包含的工作

共享工作区有24个混合未发布历史提交及其他开发改动。本次从origin/main独立发布，不推送整批历史。全屏枪械改造、时钟、部分背包面板实现及武器/模型依赖仍保留在原工作区；本次不宣称已全部上传，也未重新执行整套视觉审计。后续发布这些功能需单独核对依赖与归属。
