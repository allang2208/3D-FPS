# 巧手被动技能与新版技能图标

交付阶段：UE 游戏接入。沿用技能抽屉、角色属性、换弹动作时钟与存档事务，不新增输入或独立技能窗口。当前为本地单人实现。

## 数据与玩法

- 巧手 `dexterousHands`：初始 1 级、最高 20 级，升级经验 = 当前等级 × 100；每级敏捷 +1、换弹速度 +1%。每次完成实际补弹 +5 修炼经验。
- 敏捷从基础属性加技能等级派生，不把奖励重复写入基础属性；现有物攻、攻速、体力恢复公式继续消费总敏捷。
- 换弹耗时 = 枪械与配件耗时 / (1 + 巧手等级 × 0.01)。在每次应用属性时从基础枪械数据重新计算；换弹开始固定本次动作时长，动画、音效、补弹使用同一个时间映射。普通、空仓、弹鼓和手枪共用此入口。
- 实际补入至少一发才记录一次换弹经验，与弹药变化在同一保存事务提交；取消、满弹匣、缺弹不奖励。测试地图现有无限备用弹规则仍可完成换弹并修炼，不生成或消耗库存弹药。
- 技能存档版本升至 3；旧档只补入巧手，保留已有属性、技能与库存，迁移不弹出升级提示。

## 界面与生命周期

UMG 宿主 `ColdSteelSkillPage` 嵌入 Slate；“全部／被动”加入巧手卡片。详情复用概览、修炼条、当前／下级收益与修炼方式卡片；沿用上一轮明确宽度、窄窗重排及滚动／返回焦点规则。数据来自 `UColdSteelStatusModel`，界面只读取真实进度，模型提交后刷新属性并排队升级通知。资源由 UPROPERTY 保持，Slate 引用随页面释放。

## 图标历史与制作

Git 提交 `7d63ee2` 的发布记录明确：原步枪图标已接入，用户选中的 `rifle_mastery_B_M4_v2.png` 仍为候选。当前 `skills.json` 仍指向旧图；之前闪避按旧金边蓝宝石图制作，未沿用用户选择的新风格。

本次以选中的新版步枪图为基准：拉丝银色六边形、石墨内面、中性黑灰、左上柔光、不烘焙文字。巧手由内置 image_gen 生成；正式图标用新文件名接入，保留旧图与候选历史。生成提示词、来源与运行路径记录在 SourceAssets。列表、详情和升级通知共用 skills.json 的图标路径。

- 步枪精通：已选图原样复制到 `Content/ColdSteelData/Skills/rifle_mastery_cold_steel.png`。
- 巧手：`Content/ColdSteelData/Skills/dexterous_hands.png`，手套握弹匣及速度线。
- 闪避：`Content/ColdSteelData/Skills/dodge_cold_steel.png`，侧向闪身及速度线；旧金蓝版保留作历史来源。
- 作者文件、完整生成提示词及来源：`SourceAssets/DexterousHands20260913/`。新的本地恢复入口为 `Tools/UI/prepare_cold_steel_skill_icons.py`。旧 `prepare_skill_assets.py` 只恢复历史图和共用音效，写入旧文件名，不会替换当前新版图。
- 图标通过现有 UFS PNG 加载与 ColdSteelData 打包目录接入，无需另建引擎纹理资产；升级音继续使用既有 player_upgrade.wav。

## 范围与交付

修改 Skills、角色属性应用、换弹完成事务、技能页、角色详情和技能配置；更新图标来源、恢复说明及 UI 技能引用。执行必要构建，不启动游戏、不追加测试或截图，由用户测试。

本次必要构建成功（退出码 0，Result: Succeeded），生成 `UnrealEditor-FPSGAME-913235820.dll`；日志：`Saved/DexterousHands-ColdSteelIcons-Build-20260913.log`。未启动 UE、未实机测试或截图验收。保存并重启编辑器后由用户测试技能、换弹与图标效果。
