# 药水瓶品阶设计候选 V01

日期：2026-09-26
制作方式：内置 image_gen.imagegen，原创概念设计。
阶段：设计总览与三视图概念稿；尚未制作、导入或替换 UE 模型。

## 设计规则

- 瓶型表达品阶：普通、中级、高级、特级，共四套外壳几何。
- 药水用途由液体颜色表达：生命为红色，魔力为蓝色；同品阶的玻璃、金属、瓶塞和外形完全共用。
- 三视图为正面、右侧、背面。图像属于美术概念参考，标注尺寸是建议设计目标，不作为精确工程投影或像素测量依据。
- 保持相近总高度和短瓶颈；下半瓶身留出没有装饰阻挡的抓握区域，适配现有左手抓握、饮用和抛瓶动作的后续制作。
- 瓶塞采用可拔出的软木塞。中级以上只在瓶塞顶部及瓶颈、底缘增加少量金属件，不使用旋拧瓶盖。
- 建模时将瓶壳、液体、瓶塞分开；同品阶 HP/MP 共用模型，通过液体材质颜色参数派生。
- 后续建模再按实际手模统一瓶口、液体内壁间隙、抓握点及准确比例；本轮不改现有道具、拾取、动作或数值。

## 四档造型

| 品阶 | 外形和材料 | 建议高 × 宽 × 深 |
| --- | --- | --- |
| 普通 | 直筒圆瓶、圆肩、透明玻璃、裸软木塞 | 175 × 68 × 68 mm |
| 中级 | 扁梨形、圆润下腹、简洁锡灰金属颈圈、双层玻璃底环 | 180 × 76 × 56 mm |
| 高级 | 扁六棱切面、抛光倒角、银色颈圈与窄底缘 | 185 × 74 × 60 mm |
| 特级 | 圆角盾形水晶、厚抛光边缘、少量浅黄铜装饰 | 190 × 78 × 62 mm |

## 交付图

- [overview](potion-tiers-overview_candidate_v01.png)
- [tier-01-common-orthographic](tier-01-common-orthographic_candidate_v01.png)
- [tier-02-uncommon-orthographic](tier-02-uncommon-orthographic_candidate_v01.png)
- [tier-03-high-orthographic](tier-03-high-orthographic_candidate_v01.png)
- [tier-04-special-orthographic](tier-04-special-orthographic_candidate_v01.png)

完整生成提示词保存在 [prompts.json](prompts.json)。三视图以总览图为造型参考逐款生成；蓝色药水共用所示瓶型。
