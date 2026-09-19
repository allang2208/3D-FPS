# 手枪精通 · game-dev 规则迁移

交付：接入 UE 当前技能页与玩法，制作并接入新版冷钢图标；本地单人系统，不新增输入。

## 来源与规则

来源项目 `E:/无尽轮回/长期备份/2026-7-13-1/game-dev`，实际读取 `data/skills.json:pistolMastery`、`src/entities/player/subsystems.js`、`src/entities/player/base.js`、`src/entities/player/update.js`、`src/config/attack-formula.js`、`src/ui/skill-manager.js:addPistolMasteryExp` 与 `src/entities/damageable-entity.js`。

- 初始 1 级、最高 20 级；升级经验 = 当前等级 × 100。
- 每级常驻敏捷 +1，手枪武器伤害倍率 +1%、附加伤害 +1，持手枪时移动速度 +1%。武器贡献先计算并四舍五入，角色物攻另加，避免对角色属性重复乘算。
- 敏捷与巧手加成相加，从技能等级派生；不重复写入基础属性，普通属性分配与存档保持原样。
- 使用手枪击杀 +10、暴击 +5，可叠加为 +15。UE 沿用现有步枪精通的实际要害命中（头部骨骼）作为原暴击修炼的对应入口；普通非要害命中不奖励。不额外增加手枪暴击率或要害伤害。
- M1911、Dan-Wesson 715 的武器分类均为 pistol；步枪与手枪在发射时记录技能归属，子弹飞行中换枪不转移训练经验。杀敌与要害修炼在既有存档事务中一起提交，召唤物和禁修炼目标不计。
- 移速收益在实际手持手枪时用于步行、奔跑、瞄准与蹲行速度；收起手枪或持工具时移除，保留原闪避距离／时长。速度每次从基础配置重算，不随保存累乘。
- 技能存档版本 4，只为旧档补手枪精通，保留原技能等级、经验与物品。

## 界面与图标

复用 ColdSteelSkillPage 的 UMG/Slate 宿主，在全部／被动分类加入手枪精通。概览、当前／下级四项收益、修炼方式卡片和装备生效说明沿用冷钢主题；继续按实际抽屉宽度布局，短标签横排、长文按可用宽度换行，主体滚动并保留返回焦点。状态模型为数据源，页面读取真实进度，提交后刷新派生值并排队升级提示；纹理由 UPROPERTY 保持、Slate 控件释放引用。

图标以当前 `rifle_mastery_cold_steel.png` 为风格参考，使用内置 image_gen 制作单支 M1911 风格手枪、银灰拉丝六边形、石墨底面，不使用旧项目金蓝徽章。图标写入 skills.json，列表、详情与升级通知共用。作者图、完整提示词、来源和原技能配置快照存入 `SourceAssets/PistolMastery20260914/`。

## 实施范围与交付边界

Skills、角色派生属性与移动参数、命中归属与杀敌事务、技能页与敏捷说明、技能 JSON、图标与恢复脚本。完成必要构建，不追加游戏测试、截图或验收，由用户测试。

运行图为 `Content/ColdSteelData/Skills/pistol_mastery_cold_steel.png`，由现有 UFS PNG 读取与打包目录接入；原配置快照、生成图、完整提示词及 provenance.json 位于 `SourceAssets/PistolMastery20260914/`。无需另开编辑器导入纹理。恢复入口 `Tools/UI/prepare_cold_steel_skill_icons.py` 已包含手枪图。

必要 Editor 构建成功：退出码 0，`Result: Succeeded`，生成 `UnrealEditor-FPSGAME-914001420.dll`。日志 `Saved/PistolMastery-ColdSteel-Build-20260914.log`。未启动游戏、未执行实机测试或截图验收；用户保存并重启编辑器后自行测试。
