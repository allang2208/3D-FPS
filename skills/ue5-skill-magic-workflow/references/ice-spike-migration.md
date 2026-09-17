# 冰锥与多枚投射物魔法

2026-09-15 game-dev 冰锥迁入 FPSGAME。当前代码与资源已接入，未游戏测试或获得视觉验收；不要把制作记录写成已认可标准。详细来源／公式／差异在项目 Docs/Skills/ice-spike-migration-20260915.md。

## 源码读取与数值

读取技能 JSON 后，继续读取 kind（ice-spike-system.js）、共享 bolt-skill-system、magic-craft-helper、修炼与存档默认值、状态实现；不能只按描述制作同名投射物。旧 UI 的独立取整可能不同于实战，面板应共享实际公式。

原版为 floor(30+5L+魔攻×(1.2+0.25L)+智力×(1.2+0.25L))、蓝耗 30、冷却 10 秒。2026-09-16 用户改口径：冰锥不再单独计算智力（与火球一致，只有固定项＋魔攻），总量比原公式**低约 30%**，当前配置 `damageBase 21 / damagePerLevel 3.5 / magicBase 1.4 / magicPerLevel .2917`（固定项×0.7、魔攻系数×0.7÷0.6，因为原式同时吃魔攻与智力），各属性档实测 −26%～−30%；蓝耗改为 30+2×(L−1)，基础冷却与火球一致 12→8 秒（新增 `manaCostPerLevel`、`minimumCooldown`，删除 int 字段）。数量仍为 2+floor((L−1)/5)，1/6/11/16 级分别 2/3/4/5 枚；悬浮 30 秒、射程 12 米、速度 24 米／秒不变。数值在 `Content/ColdSteelData/skills.json`，改数据不需编译。同日补充：击杀目标后其余冰锥穿过尸体继续飞向后方（此前未实现），以及火球公式已接入预留的魔杖乘数 `wandSpellMultiplier`。

## 整组合同

- FPSIceSpikeComponent 管输入队列；FPSIceSpikeVolley 用一个实体管理全部冰锥、一份凝聚时快照和奖励批次。
- 仅首次凝聚成功扣蓝，左手忙时排队不扣。再次按键齐射，所有冰锥在接触帧朝同一个真实瞄准点，各自从当前悬浮位置出发，不拉回手上。
- 悬浮不占手；复用 FPSFireballComponent.TryBeginSpellGesture/CancelSpellGesture 的既有手臂层与占用门禁，时钟按施法速度缩放。不同技能的请求、实体和冷却各自独立，共享手势不得让已准备的火球提前发射。
- 接触／目标终点碎裂，射程终点静默结束；30 秒悬浮到期清除。全部结束后才开始预留冷却与提交经验，飞行途中不开始下一轮。
- 每枚传真实 FHitResult 到共享 MagicHit 上下文，要害与随机暴击遵守 projectile-magic-critical.md。冰屑和小范围粒子不自带 AOE 伤害。
- 原同帧重叠接触保留为一次冰锥直径内的接触群，墙体截止；不要演变为长距离穿透或因低帧率扩大伤害范围。
- 修炼按整组命中事件 H／击杀 K：4H+12K+多次命中10+多杀10。同一敌人被多枚击中计多次命中，每轮两个额外档各一次；暴击修炼、击杀角色经验合并提交。
- 旧存档版本 10 补冰锥进度和冷却字段，保留其他技能与绑定。退出不保存实体，保留预留冷却；不制造迁移升级通知。

## 法杖与状态

仅当前激活的主手法杖提供 `_craftEffects`。凝聚时冻结数量、伤害、魔防穿透、暴击、耗蓝、冷却、射程、施法速度、寒冷、链式和加速参数；装备切换或途中升级不改变这一轮。

普通冰锥无内置寒冷；iceChillSlowPercent 非零才叠层。UCombatStatusFormula 承载寒冷、冻结、链式与加速，UFPSCharacterMovementComponent.GetMaxSpeed 读取状态倍率，不逐帧改写并累乘基础移速。20 层寒冷扣 10 层冻结，冻结阻止继续叠层并使物理承伤增加 50%；怪物受控入口负责中断。旧 2D 冻结冰块画面未迁入。

链式在成功凝聚后消费，结束后按凝聚时法杖配置发放；每层状态时限 +10 秒。施放后加速按配置叠层及增加时长，每层移速 +10%。UI 仅显示状态记录，不代替实际状态逻辑。其他魔法须主动接入这些通用挂钩，不能从冰锥接入推断所有技能互通。

## 资产与交付

首轮 SM_IceSpike 从本地 Epic SM_SimpleProjectile 重塑为 54cm，源文件继续保留。用户随后要求写实升级并批准 5080 管线；当前主冰体已改为 `/Game/Skills/IceSpike/FrostV2/SM_IceSpike_01/02/03`：TRELLIS.2 三视图 seed91571 母版、每种 18,000 面，带母版烘焙法线。可编辑源 `SourceAssets/IceSpike5080_20260915/IceSpike5080_Editable.blend`，完整作者与恢复记录见项目 `Docs/Skills/ice-spike-frost-v2-20260915.md`。SM_IceShard/P_IceSpikeImpact 继续使用首轮本地授权片库副本。

当前冰材质由 M_IceHeart 内芯与 M_IceShell 通透表层组成；不将其描述为完整体积折射。NS_ColdMist 在凝聚／悬浮时持续散发下沉薄雾，发射时增加短促雾量并缩短飞行寿命；NS_FrostCrystals 提供少量悬浮冰晶与飞行拖尾。世界空间粒子出生后不跟镜头旋转；雾的独立宿主在本体消失后停止发射，已有粒子短暂消散。使用 DepthFade 的雾材质必须关闭透明速度输出，避免火球历史棋盘格冲突。此轮已制作、导入并必要构建，未游戏测试或获得视觉确认。

用户后续指定头顶悬浮横排：取消绕身旋转和自转，阵列随视角整体移动，横排槽位保持居中对称。2026-09-16 用户反馈位置太高、只能看到尖端且浮动太小：整排改到相机前方 72 cm，高度按“根部圆盘贴上视锥边界”反算，让整根 54 cm 冰锥完整可见；漂移改为左右上限 7 cm、上下上限 5.5 cm，上下漂移幅度先从高度里扣除，槽距 22 cm。每枚仍用独立连续噪声漂移，随机起点和速度只在凝聚时初始化，不逐帧跳位置或整排同步摆动。从各自实际位置发射，不恢复旧的环身轨道。具体位置参数、现场调参变量和未测试边界见同一 V2 记录。

用户反馈闪光后，实际材质读取确认冰体没有 EmissiveColor，细冰晶原先使用自发光 M_IceMote。当前冰晶已改用受环境光照的 M_FrostCrystalSoft，无自发光输出，并降低粒子数量与 Alpha、延长悬浮寿命、平滑淡入淡出。冰体提高粗糙度下限、减弱 Specular 与法线强度，寒雾降低 Emissive Gain。使用制作器 `-IceLightOnly` 可恢复这些修订；不要恢复旧的短寿命自发光亮点。Niagara CPU VectorVM 的平滑淡入淡出使用展开的 Hermite 多项式，避免本轮遇到的 smoothstep() 编译不支持；此限制不等于材质或 GPU shader 的限制。已完成必要编译，未游戏测试。

GitHub danielpokladek-shaders/cracked-ice 的 RGB 三层 ci_cracks.png 为 MIT，作者 Shader Vault；选用文件及 LICENSE 保留于 SourceAssets/IceSpike20260915/ThirdParty/CrackedIceSelected，打包副本位于 Content/ColdSteelData/Licenses。V2 继续复用该纹理，新增模型使用生成母版及自制导出，寒雾使用已有授权 Epic 素材，禁止改写共享原包。

图标使用冷钢银框、石墨底、冰蓝主体，模型定义统一图源并加入 Tools/UI/prepare_cold_steel_skill_icons.py。美术制作、必要编译和用户实机确认分别报告，默认不启动测试或渲染。

## 恢复链与废案边界

V2 主体替换不代表首轮制作器退役：`build_ice_spike_assets.py` 仍提供裂纹、音频、碎片、命中和冰晶系统模板，先恢复首轮依赖，再运行 `build_ice_spike_frost_v2.py`。模型生成入口使用同目录已冻结的 `trellis-multiview.api.json`，不依赖其他任务尚未发布的生成器。

闪亮的来源要区分冰体材质输入、粒子材质输入和镜面高光；冰体没有 Emissive 不代表周围粒子没有。当前参数是冰锥的偏写实选择，不将“所有魔法关闭自发光”写成通用规则。

旧材质修正前备份已归档至 `trash/skills-magic-20260915`，修正工具的备份位置同步迁移；详见项目 `Docs/Skills/skills-magic-archive-20260915.json`。TRELLIS 原始／纹理母版、可编辑 Blend 和基础素材依赖仍保留。公开源码不包含 Fab/Epic 二进制、完整材质导出快照或流体缓存，许可与本地恢复顺序独立记录。

派生系统只保留自有冰材质那一个渲染器：`NS_RocketTrail` 的 `RocketTrail` 发射器有两个精灵渲染器，索引 1 是例子包里的 `MI_RocketFlareCore`（火箭火焰核心）。2026-09-16 已从 `NS_FrostCrystals`／`NS_ColdMist` 移除该渲染器（导入了火球式暖色高光的根因），重建时由 `build_ice_spike_frost_v2.py` 的 `strip_source_renderers()` 丢弃材质仍指向 `/Game/NiagaraExamples/` 的渲染器；火球自身拖尾保留它。`.uasset` 里出现 `NiagaraLightRendererProperties` 字符串只是派生残留，判断实际渲染要看工具集读回的渲染器列表。

2026-09-16 排列再改：原中轴等距横排会与近战武器位置重叠，现以玩家中轴为对称轴留出空档，两翼阶梯式生成（偶数索引走左翼，奇数多出的一枚也在左翼）。新增枚数永远落在更外面一格，同翼相邻两枚相隔两格，因此 2／4／5 枚等不同等级数量都不会挤在一起；窄视野时槽距按视锥半宽压缩。`fps.IceSpike.WingGap`／`HoverDropCM`／`DriftScale` 为现场调参变量。

2026-09-17 法术统一长按弹道预览：悬浮时按住绑定快捷槽显示红色线段、松手才发射，火球与冰锥共用 `FPSMagicPreview`（预测复用各自的飞行扫掠与穿尸体规则）；凝聚期间的按下仍是原排队行为，E 交互优先级不变，菜单打开会清掉预览。发射几何维持原实现——每条冰锥各自朝准星射线命中点汇聚、到点碎裂或飞完射程静默结束（用户先要求改「同弹道」平行飞行，随后确认表述有误并撤回）。两者起点不同（冰锥在两翼 ±20–64 cm）属于已有排布的固有特性。详见项目 `Docs/Skills/magic-aim-preview-20260917.md`。
