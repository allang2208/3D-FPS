# 感电的：史诗近战前缀

用户要求（含本日概率调整）：所有近战武器可附魔；近战命中后有 25% 概率向 5 米内随机一名敌人放电，本次近战击杀时改为 100%；闪电击杀后向该敌人周围 5 米内全部敌人放电，击杀可继续连锁；参数取 10 级与玩家闪电等级的较高值；剑身环绕现有闪电风格的电弧。

## 当前修订 V3：撤回实体圆箍表现

用户截图明确否决 V2 加亮后的观感：几道粗硬的暗色圈，缺乏闪电感。下文“三道持续细环”和“圆环提高持续不透明度”仅保留为历史记录，不作为认可基线。V3 尚未经过用户实机判定。

- 材质故障：`M_ElectrifiedOrbit` 的 SM6 编译日志报 `The material can contain only one Temporal Responsiveness node`，发生默认材质回退。UE 5.8 的 `DeleteAllMaterialExpressions` 遍历期间删除同一列表，会残留旧节点；作者脚本改为先取节点快照再逐个删除，只创建一个响应输出。
- 保留现有资产路径以兼容软引用，网格内容替换为两个有缺口的折线弧段及三个短分叉；覆盖角约 163°，管径约为旧版三分之一，端点收细。每组 612 三角形，三个可复用组件，不存在闭合圆环几何。
- 材质采用不受光照影响的加法发光、紫色边缘与蓝白亮芯；按错开的时间段短闪、随机熄灭，并沿电弧产生移动缺口。碎弧沿刃长约 15%–85% 移动并绕刃旋转，不再固定在三个截面上。
- 主体闪电改为 24 段不规则折线、0.35–0.72 圈的刃部绕行，0.065 秒保持、0.115 秒消退，0.095–0.15 秒生成下一条；宽度系数 0.032、亮度 56。每次放电换形，避免螺旋弹簧感。
- 绑定故障：原 Spline DI 的 AttachParent 查找使用最外层 `GetAttachmentRootActor()`；电弧附着武器后，该 actor 是角色，无法据此找到电弧自己的 spline。新版本通过 `User.BladeSpline` 显式传入每条电弧自己的 `Path`，保留真实武器挂点、局部空间及检视跟随。
- 新作者辅助入口 `RainAssetEditor::BindSplineUserObject` 声明对象参数、强制编译实例参数布局，再设置编译后生成的 spline 接口，最后更新 DI 运行数据。`build_electrified_melee.py` 必须以此作为最后编译步骤；在编译前修改旧缓存接口会被 Niagara 替换，不能当作成功绑定。
- 仅系统含有 `Detail` 发射器时设置该发射器边界，消除武器专用副本上每次放电都报告找不到发射器的问题。
- 保留每把持有武器至多一盏短距离、无阴影的闪光灯，以及 25%/100% 概率、伤害和世界连锁规则。

制作入口：`Tools/Skills/build_electrified_orbit.py`、`build_electrified_melee.py`；原创网格与材质源仍在 `SourceAssets/ElectrifiedOrbit20260930`。本轮不启动游戏、不截图、不进行实机验收，交由用户测试。

V3 交付记录：网格/材质已保存，回执 `Saved/ElectrifiedMelee/orbit-v3-authored.json`；最终 Niagara 由后台 commandlet 编译并保存，日志 `Saved/Logs/ElectrifiedV3-Binding-20260930.log` 记录 `User.BladeSpline` 与 8 个接口绑定，回执 `Saved/ElectrifiedMelee/assets-authored.json`。正式 Editor 构建成功：`Saved/BuildEditor/build-20260930-153449.log`；正式 Game 构建成功：`Saved/BuildEditor/electrified-v3-game-20260930.log`。本轮基础二进制已落盘，取代下文旧版“基础 Editor DLL 尚未重建”的状态。期间保留并行开发源码，未修改怪物、图鉴或采集系统逻辑；仅在共享构建失败后等待其源码更新并重建必要中间产物。

## 数据与实例

- `electrifiedMelee` / `enchant_scroll_electrified`，史诗、前缀；800 魔法粉尘、卷轴价格 4000，沿用同阶卷轴规则与正式卷轴图标/掉落模型。
- `restriction: melee` 使用 `ColdSteelInventory::IsMeleeWeapon`，包含剑类、`weapon_melee` 和当前作为近战使用的斧/镐；枪械、枪托打击、弓、法杖、铲地不会获得此触发。
- 四处数据：`enhancement.json`、`items.json`、`dungeon_loot.json`、`tooltip-reference.json`。沿用现有 `_enchantData.prefix` 与 `_enchantEffects` 实例保存；替换前缀重建效果，不增加存档模式，也不修改玩家闪电技能等级。

## 命中与连锁

- `ColdSteelSkills::Snapshot` 从本次近战所用物品捕获三个附魔键；共享 `ApplyHit` 对非致命近战接触只判定一次 25% 概率，通过后排队；近战直接击杀使用 `FWeaponDamageResult::bKilled` 跳过概率判定，必定排队。击杀标记在其他 on-hit 效果前捕获，不把后续附加效果击杀算为本次近战直接击杀。物理护甲将伤害降至零仍可进行 25% 判定；采集节点不放电。
- `UFPSMeleeLightningComponent` 独立于主动闪电组件。成功触发时取 `LightningStats(max(最低等级, LightningProgress.Level))` 快照；从目标中心 500 cm 内随机选另一名敌人。近战击杀只提高触发概率，首跳仍是随机单目标；闪电击杀后才进入群体分发，不再判定 25%。概率属于公共触发规则，既有附魔实例直接采用，无需重新附魔。
- 闪电造成直接击杀后，从被击杀者位置向 500 cm 内所有未命中敌人分发；每代间隔 0.06 秒，没有固定跳数上限。同一轮共享已命中集合，排除原近战目标，避免合流重复伤害或循环；新的一次近战命中可以重新放电。
- 复用当前 `ApplyLightningHit` 的电系魔法伤害、防御、暴击、眩晕、感电层数/时间、过载数值。范围与分发规则由附魔覆盖技能的普通目标数限制；其余逐跳衰减沿用技能（当前 10%，同一代按相同深度计算）。
- 满层过载沿用技能自身范围与伤害，可触发后续击杀分发；同样遵守本轮不重复命中。免疫状态不会被强制附加眩晕或感电。
- 以 Pawn 球形重叠、Actor 去重、距离和墙体可见性选敌；排除玩家、友方、伙伴、死亡和不可伤害对象。身体不挡住群体分发，墙体仍遮挡。
- 自动触发不扣 MP、不占主动技能冷却/左手、不额外训练主动闪电；击杀经验和地牢击杀沿用正常闪电奖励事务。命中事务退栈后再处理队列，避免武器修炼和附魔递归。

## 表现与资源

- 敌人之间复用 `/Game/Skills/Lightning/NS_LightningChain`，紫色外缘/亮芯；世界电弧同屏最多 32 个，不附加动态点灯。数量预算只影响显示，不截断伤害目标或跳数。
- 剑身专用 `/Game/Weapons/ElectrifiedMelee/NS_ElectrifiedBlade` 由 `Tools/Skills/build_electrified_melee.py` 从现有闪电复制，保留两个 CPU ribbon 和原材质配色，移除 Detail 发射器，改局部空间；不修改主动闪电原资产。
- 用户本日进一步要求“闪电与旋转圆环环绕剑身／近战刃部”，改为三道持续细环与短促电弧两层表现。三环位于刃长约 20%、50%、80%，小幅轴向浮动，约 11–14° 倾斜并交错方向旋转；环上各有两段沿周向流动的电荷亮尾。色彩为紫色软边与偏白亮芯，不改现有世界连锁配色。
- 三环共享原创圆环 `OrbitV2/SM_ElectrifiedOrbit` 与材质 `OrbitV2/M_ElectrifiedOrbit`，实际半径随刃长限制在 3.2–6.5 cm，中心环略大。每环 1,536 三角形、共三个持久组件；装备时创建、每帧只跟随当前刃部变换，材质自身驱动电荷流动，不每帧重建几何或创建材质。无碰撞、阴影和动态灯，仅持有者可见。
- 电弧在同一三环包络内绕行 1.65–2.15 圈，32 段细折线，0.12 秒保持 + 0.20 秒消退，约 0.16–0.21 秒生成下一条；随生命周期继续绕刃旋转。电弧与三环共同跟随当前刃部坐标系，换装、替换前缀、隐藏、死亡和世界退出清理。
- 圆环作者入口 `Tools/Skills/build_electrified_orbit.py`，完整原创 OBJ 与 HLSL 源位于 `SourceAssets/ElectrifiedOrbit20260930`；材质使用曝光补偿、软边和轻微接触渐隐，深度遮挡仍生效。两份新增资产与原 Niagara 一起异步准备，不在挥击时同步读盘。
- 附魔有独立的武器局部挂点：模块剑以真实 `ModularSword` 剑身为父级，使用该剑身的局部刃部数据，不读取攻击辅助轨道；整体蒙皮剑将参考姿态刃部点换算到 `WPN_root`，随后直接跟随该骨骼。`Tools/Skills/build_electrified_tool_anchors.py` 从斧镐刚性武器顶点导出 `ColdSteelData/electrified-tool-anchors.json` 中的 WPN_root 局部坐标；组件启动时缓存，运行期绑定该骨骼。原模型、手臂、蒙皮和动作不变。
- 素材异步加载，视觉随机独立于选敌/暴击随机，空闲组件关闭 Tick。

## 交付状态

### 电流可见性与暗处发光加强

用户反馈电流、闪电不够明显，要求增加亮度、闪光及黑暗环境中的发光效果。

- 武器电弧宽度系数由 0.024 提至 0.042，基础亮度由 26 提至 48；保持 0.14 秒、渐隐 0.22 秒。初生电火花和约 0.082 秒的二次小闪使亮度短促变化，不改变武器附着层级。
- 圆环提高持续可见度、亮芯宽度与不透明度，保留紫色边缘；专属材质增加 `Flash` 参数，与最新武器电弧的闪光包络同步。
- 复用电弧已有点灯组件，同一武器仅最新一条电弧的灯可见，旧电弧继续消退但不叠加照明。灯挂在武器刃部中段，145 cm 衰减半径、60 lm 强度基数，包络约 27–81 lm 后随尾部渐隐；无阴影、无间接光注入、无体积雾散射。用于暗处照亮剑身、手部和近处表面。
- 附魔世界连锁线的普通/过载宽度分别从 0.65/0.35 调为 0.80/0.48，基础亮度从 50 提至 68；不为每个世界连锁目标增加点灯。主动闪电技能仍使用默认亮度 50。
- 此次不增加实例字段或反射布局，只调整函数与材质。原始 25%/100% 触发、连锁目标与伤害规则保持不变。

本次通过已有 UE 桥结束阻止资产写入的 PIE，保留编辑器；已保存圆环材质，未重新启动 PIE、未进行画面测试。保存记录 `Saved/ElectrifiedMelee/glow-apply-20260930-02.json`。

当前编辑器 Live Coding 成功并应用补丁：`Saved/ElectrifiedMelee/glow-livecoding-20260930-01.json`。编辑器保持打开，基础 Editor DLL 尚未进行常规重建，补丁状态不等同于基础 DLL 落盘；关闭编辑器后后续常规 Editor 构建会合入这些源码改动。

独立 Game 目标已常规构建成功，`Binaries/Win64/FPSGAME.exe` 已链接落盘；日志 `Saved/BuildEditor/electrified-glow-game-20260930.log`。

### L 键检视跟随修正

用户反馈三环和电弧在检视时留在原位。旧实现将三环设为绝对世界变换、挂到角色根上，电弧也通过每帧复制世界变换移动；符文剑的视觉定位还复用了 `SwordTraceFromAnimation` 的战斗辅助轨道。这些轨道不作为实际剑身的视觉挂点。

本次改为 `GetEnchantmentBladeAttachment` 提供真实父组件、骨骼名和局部挂点：

- `UFPSMeleeLightningComponent` 创建一个随武器移动的 `BladeAnchor`。三环为其子组件，只更新局部绕刃旋转与轴向浮动，不再设置绝对变换。
- 所有尚未消退的武器电弧 Actor 直接附着同一 `BladeAnchor`，自身 Tick 只修改局部旋转。武器动作、镜头和父组件的后续变换由附着层级传递。
- 电弧与 Niagara 采用前置 Tick 依赖，顺序为武器姿态、附魔挂点、电弧局部旋转、Niagara；保留现有局部空间 ribbon 资产，不改世界连锁电弧。
- 隐藏、换装或挂点变化时清理旧圆环、电弧与挂点，再按新武器重建；不修改放电概率、伤害、选敌与连锁规则。

本次仅修改原生源码与说明，无需重做或重存 Niagara、圆环网格、材质。Editor / Game 后台构建均成功，日志分别为 `Saved/BuildEditor/build-20260930-134608.log` 和 `Saved/BuildEditor/electrified-weapon-bind-game-20260930.log`；未运行游戏或检视验收。

源码、四处附魔数据、专用 Niagara 与工具定位数据已保存。`FPSGAMEEditor` 与 `FPSGAME` 必要构建成功，记录分别为 `Saved/BuildEditor/build-20260930-010537.log`、`Saved/BuildEditor/build-game-electrified-melee-complete-20260930.log`。Niagara 保存记录为 `Saved/ElectrifiedMelee/assets-authored.json`，定位数据已输出到 `Content/ColdSteelData/electrified-tool-anchors.json`。

本日追加的概率调整与物品说明已落盘，并完成 `FPSGAMEEditor` 和 `FPSGAME` 构建；记录分别为 `Saved/BuildEditor/build-20260930-124911.log`、`Saved/BuildEditor/electrified-probability-game-20260930.log`。

本日追加的旋转圆环 V2 已保存材质与网格，制作回执 `Saved/ElectrifiedMelee/orbit-v2-authored.json`，后台制作日志 `Saved/Logs/ElectrifiedOrbitV2-Author-20260930.log`。最终 `FPSGAMEEditor` 与 `FPSGAME` 构建均成功，记录分别为 `Saved/BuildEditor/build-20260930-130855.log`、`Saved/BuildEditor/electrified-orbit-v2-game-20260930.log`。本次还最小修正了 `FPSGAMECharacter.cpp` 全息瞄具读取处阻断构建的局部变量遮蔽与 `TObjectPtr` 指针推导错误，仅明确 `const UStaticMesh* OpticMesh` 并同步三处变量引用，保留原瞄准逻辑。

未主动打开或重启交互编辑器，未启动游戏、未运行测试、未进行截图或视觉验收；连锁手感及实际电弧观感由用户测试。
