# 技能图标统一（2026-10-13）

用户要求将魔法、精通及通用技能统一为已采用武技的银色圆角方框。主体沿各自语义：武技保留原人物动作；魔法保留元素图案；精通使用对应武器；巧手等通用技能保留原图案并调整构图比例。

- 本轮覆盖 23 枚图标，另保留上挑、重击、冲刺攻击、大旋风四枚已选图。统一正方形 PNG、银框、石墨底与左上柔光；框外透明，主体完整留框内，不烘焙文字和状态。
- 剑、机枪、霰弹枪、弓精通补齐定义图源，技能页列表／详情恢复同样 48px 图片区域；被动技能不因此变为可拖动主动技能。
- 同名现用 PNG 替换，详情、拖影、快捷栏及升级通知继续共用定义路径；新增精通图片只在技能页初始化读取一次并持有引用，布局变化只更新画刷尺寸。
- 布局、焦点、输入、修炼、伤害、冷却、存档及所有技能数值保持现有行为。窄布局使用已有等级换行与横排短标签。
- 图片制作使用内置 imagegen；源图、提示与替换前副本保留在 SourceAssets/SkillIconUnified20261013，恢复脚本同步本次选用源。后台导入 Texture2D 并保存；不自动打开 UE 或执行游戏验收。

## 落盘记录

- 23 枚正方形图标已完成生成，正式 PNG 在 `Content/ColdSteelData/Skills`，选用源在 `SourceAssets/SkillIconUnified20261013/Selected`。完整提示与生成文件记录为同目录 `generation-results.json`，使用内置 imagegen。
- 补齐剑、机枪、霰弹枪和弓精通，并恢复其列表／详情中的 48px 图标区；手枪与步枪精通换用同框。快速进战将双箭头占位图补为与现有武技一致的无脸练功人物快速出拳动作，其余通用图案保留。
- 13 枚魔法／装备特殊能力、6 枚武器精通及 4 枚通用／快速进战图标已统一。上挑、重击、冲刺攻击、大旋风四枚已采用 PNG 保留原样。
- `Tools/UI/prepare_cold_steel_skill_icons.py` 读取本次 manifest，恢复时使用选用源。UI 继续使用同名定义路径，因此 `meteor_hex.png` 等历史文件名保留，实际图片已为圆角方框。
- `FPSGAMEEditor Win64 Development` 后台构建成功，日志 `Saved/SkillIconUnified20261013/Editor-build.log`；本次变更已进入主模块，DLL 时间为 2026-10-13 11:43:11。
- `Tools/UI/import_unified_skill_icons.py` 已后台导入保存 23 枚 Texture2D，UI 组、sRGB、EditorIcon 压缩、最大 512px。首次导入日志 `Saved/SkillIconUnified20261013/import-assets.log` 退出码 0；导入记录 `SourceAssets/SkillIconUnified20261013/asset-import.json`。快速进战最终动作版通过 `import-quick-combat-final.log` 单项更新保存，退出码 0。
- 未运行游戏、截图、自动检查或 UI 验收。重新进入游戏后读取新 PNG；旧会话已加载的图片缓存不会被文件替换主动刷新。
