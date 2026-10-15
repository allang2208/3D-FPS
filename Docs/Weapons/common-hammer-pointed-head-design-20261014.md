# 尖头锤：锤类特殊通用改造概念

用户要求先出设计图，随后明确两头都做成尖头、取消尖喙，并提供此前细长棱面图要求精修。V4 已按后续“开始建模”要求制成左右对称、直线收尖的实体棱脊尖头，带纵向凹槽与细分棱面，模型和正式图标已后台导入并保存。当前按用户表格配置物理伤害 +30%、攻击速度 +5%、攻击体力消耗 +15%、韧性伤害 −25%，攻击附带 15% 物理防御穿透，见 [BalanceV2](../../SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/BalanceV2/README.md)。

当前精修设计图 V4（本机文件 `SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/ConceptV4/faceted-double-spike-design.png`，不随 Git 发布） 由内置 image_gen 依据 用户参考图（本机文件 `SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/ConceptV4/faceted-tip-reference.png`，不随 Git 发布） 编辑生成，[提示词](../../SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/ConceptV4/prompt.txt) 同目录保存。包括锤头近景和完整装配示意。

旧设计图（已归档，见[清单](../Publication/WarhammerMods20261015/archive-manifest.json)） 为“一端锤面、一端尖喙”的已替代方案，仅保留历史，不作为当前建模依据。修订图已尝试用内置 image_gen 编辑，但工具返回内容审核拦截（`moderation_blocked`，输出阶段 `illicit`），未返回图片。修订提示词与失败记录（已归档，见[清单](../Publication/WarhammerMods20261015/archive-manifest.json)） 已保存。

用户随后要求重新生成，双侧直圆锥版本第二次仍未返回图片，当次记录（已归档，见[清单](../Publication/WarhammerMods20261015/archive-manifest.json)） 保留。之后按用户“换个设计”的要求生成 短棱锥方案 V3（已归档，见[清单](../Publication/WarhammerMods20261015/archive-manifest.json)），再依照用户新参考精修为当前 V4。V1、V2、V3 均为历史过程，当前制作参考使用 V4。

## 外形

- 名称：双棱尖头锤。稳定 ID `pointed_hammer`，作为 `hammer_heads` 槽的一套左右头替换件；品质为特殊改造，设计身份属于锤类共享目录。
- 两侧为大小和形状一致的棱脊尖头，沿同一横向轴背向伸出，保持镜像对称；根部紧凑，细长棱面连续汇向居中的尖端。
- 按用户新参考增加纵向凹槽、凸起棱脊和细倒角，作为完整实体上的起伏，不做悬浮薄片。取消平锤面、尖喙、弯钩、下垂尖端和附加倒刺。
- 金属沿用写实锻钢，槽内略暗、棱边略亮，表面使用细锤痕与克制磨损；不添加宝石或发光装饰。
- 当前锤头近景与完整装配示意同步使用双侧精修尖头。中央锤座、连接环和既有柄部沿用前版；后续建模按实际宿主复用其模块。

## 实装接口与边界

首个适配宿主为锻钢战锤，左右连接面沿用当前 `warhammer_factory_v1` 的实际边界，作者轴为锤头横向 X、柄向 +Z。保留原装头部 X ±4 cm 的安装面及至 ±7.5 cm 的连接颈，新棱脊体从连接颈向两侧延伸。模块运行偏移沿用 Z 92.5 cm。中央锤座、套箍、长柄、包覆、配重和握点沿用现有模块。

该方案已加入 `common-hammer-heads.json`，锻钢战锤通过现有共享选项库和 `warhammer-modules.json` 加载。后续兼容锤使用独立的真实接口适配，共享设计身份、数值与正式图标。当前数值沿用现有直接属性倍率，未新增独立特殊效果或攻击机制。

正式图标由最终模型的单侧实体制作灰阶素材，再由内置 image_gen 按认可的金属框母版合成；运行模型仍同时替换两侧锤头。作者场景、FBX、图标输入与提示词、导入回执及构建记录见 [BuildV1 交付说明](../../SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/BuildV1/README.md)。未运行游戏测试，实际装配与视觉效果由用户测试。
