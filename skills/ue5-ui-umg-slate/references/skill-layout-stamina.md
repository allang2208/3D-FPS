# 技能页与简洁体力 HUD

FPSGAME 的技能页由 ColdSteelSkillPage 自绘 Slate 内容。抽屉布局通过 SetLayoutWidth 传入实际内容宽度；Root 的明确宽度打断自动换行文本影响期望宽度的循环。短标签、技能名、数值不自动换行，描述通过 WrapTextAt 明确段落宽度。小于 440px 将等级放到身份区下一行，小于 480px 将收益名称和数值分行；不靠缩字号。

修炼方式使用共享 StatusCard/Border 圆角卡片，标题、名称/经验行和底部规则分开排版。步枪精通与闪避共用 TrainingCard，内容取各自配置。

用户已要求底部体力只保留细条与当前/上限数值。使用无背景 HorizontalBox，数值使用 JetBrains Mono；不添加玻璃、模糊、体力标题或恢复说明。体力恢复/消耗详细信息继续留在角色状态页。

这些规则在工程 Docs/UI/ui-cold-steel-design-system.md 与 stamina-dodge-plan-20260913.md 维护。默认仅制作和必要构建，不主动运行界面测试或截图。
