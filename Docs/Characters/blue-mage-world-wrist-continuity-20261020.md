# 法袍第三人称空手：手腕接缝与掌根缺面

用户截图显示穿法袍、空手时手腕与袖口之间漏空，部分手部表面也缺失。

## 定位

在用户已有试玩中只读取得当前身体、衣物及材质分区，没有移动角色、切换视角或换装。读取时世界身体部件为 OwnerNoSee，说明该时刻已与截图中的第三人称视角不同；这份记录用于确认当前使用的资产和覆盖状态，不冒充对截图姿态的动态复现。

当前 Jason 内层身体为 `TurnLegContinuity20261020/Jason/SK_Jason_5b5a780d8268_RobeHem`。其 `SkinHands` 显示、`SkinArms` 隐藏，手部使用原皮肤材质，没有使用裙摆裁剪材质。法袍是 `FacingFix20261020/Body/Jason`。

源几何以各侧前臂轴、腕关节为原点量取：

- 袖口最靠手部处约为 -1 cm。
- 已显示的手部分区最靠前臂处约为 -0.40 cm。
- 被隐藏的手臂分区还有表面延伸到腕关节以外约 +0.74 cm。

因此袖口与可见皮肤之间缺少搭接，掌根附近被分到 `SkinArms` 的三角面也会随上衣遮挡一起消失。

## 修复

只改法袍专用内层身体的材质分区，把靠近手腕的原生皮肤三角面重新归入已有 `SkinHands`。恢复范围沿各身体前臂比例计算，为腕关节向前臂方向 3.5–4.5 cm，在法袍袖口内形成约 2.5–3.5 cm 的覆盖搭接。

跨边界三角面按同一边参数切分，插值原 UV、法线和骨骼权重；共享切点，原模型位置不变，不增加填洞圆片。手指和掌形、原动作与手套覆盖规则保留。戴全手套时继续由原 `SkinHands` 覆盖规则处理，第一人称 Owner 身体仍隐藏手部，避免重复绘制手臂。

覆盖当前四种法袍皮肤入口：Body 裸皮、Body 露指配套皮肤、Jason 普通身体及 Jason 鞋靴适配身体。裙摆、腿部完整几何、现行下摆遮罩材质、裤子和靴子映射，以及已升级的第一人称袖子均保持当前版本。

## 交付

作者脚本为 `author_wrist_continuity.py`，保存/接入脚本为 `save_wrist_continuity.py`、`publish_wrist_continuity.py`，只读诊断为 `read_world_wrist_layers.py`。本轮源与回执位于 `SourceAssets/BlueMageRobe20261018/WristContinuity20261020/`。

新资产另存为 `/Game/Characters/ModularOutfit20260924/BlueMageRobe20261018/WristContinuity20261020/`，从当前使用的皮肤资产继承下摆材质和 LOD 配置。只切换四条皮肤映射；无需修改 C++ 或重新构建游戏。

`wrist-continuity-save-01` 后台资产批次退出码为 0，四种身体适配及其 LOD 已保存。`saved_assets.json`、`published.json` 记录完成，四条法袍皮肤映射已切换，新修订标记为 `20261020-native-overlap-v1`。

未启动试玩、截图或执行修复后的动作测试。重新开始试玩后生效，最终手腕衔接与手部外观由用户确认。
