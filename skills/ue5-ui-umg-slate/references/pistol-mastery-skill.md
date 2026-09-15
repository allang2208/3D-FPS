## 手枪精通来源与接入

2026-09-14 以原 game-dev `data/skills.json:pistolMastery`、`skill-manager.js:addPistolMasteryExp`、`attack-formula.js` 和玩家 base/update 为来源：1–20 级，每级常驻敏捷 +1、手枪武器贡献 +1%/+1、持手枪移动速度 +1%；升级经验为等级×100，击杀+10／暴击+5可叠加。UE 使用实际头部要害命中作为暴击修炼对应入口，不额外添加手枪要害伤害或暴击率。

手枪与步枪共用发射快照／命中事务，但经验归属必须随子弹保存，不能在子弹命中时根据当前所持武器决定；杀敌、要害和角色奖励同一次提交。M1911 与 Dan-Wesson 715 均为 pistol。总敏捷叠加巧手与手枪精通，从等级派生，不写回基础属性；持枪移速每次由基础参数重算，持工具时移除，避免保存累乘，不修改闪避距离。存档版本 4 为旧档补手枪精通，保留全部已学技能。

手枪图标 `Skills/pistol_mastery_cold_steel.png` 沿用选定银灰六边形，图标与来源保存在 `SourceAssets/PistolMastery20260914`，恢复脚本 `Tools/UI/prepare_cold_steel_skill_icons.py`。技能页包含四项收益与独立修炼卡，列表／详情／升级提示共用 JSON 图标路径。必要构建与游戏实测分开说明，未要求时不自动测试。
