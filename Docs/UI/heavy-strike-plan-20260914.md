# 重击技能与符文剑调参

复用 ColdSteelSkillPage 的 UMG/Slate 页面：现有主动分类新增重击卡，详情显示当前/下级倍率、蓄力秒数、力量与五档修炼。沿用窗口缩放、纵向滚动、返回焦点及资源释放。图标使用动态 PNG，与快捷栏共用 skills.json 定义；无新弹窗。

数据由技能模型派生，经验结算通过 CommitState 保存并广播升级通知。卡片只发详情或拖放请求，快捷栏复用交换、解绑、E 优先交互和持久化。持枪显示“需近战”，蓄力显示百分比，动作中显示占用，体力不足变暗。

图源 SourceAssets/HeavyStrike20260914/heavy_strike_cold_steel.png，由 imagegen 参考现用步枪精通与暴击图标重新生成：统一拉丝银色六边框、石墨凹面、中性灰金属重剑冲击浮雕、左上柔光，无文字。替换用户否定的方框碎石场景版；旧图已移至 trash/heavy-strike-20260914/SourceAssets/HeavyStrike20260914/PreviousSquare。正式引用 Content/ColdSteelData/Skills/heavy_strike_cold_steel.png；本次发布的独立恢复脚本 Tools/UI/restore_heavy_strike_icon.py（本机通用脚本仍包含此图）。

本轮不启动 UI 或执行回归测试，由用户体验。
