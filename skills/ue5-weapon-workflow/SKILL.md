---
name: ue5-weapon-workflow
description: 开发和维护 UE5 枪械与近战武器，包括双手剑、轻重攻击、连击、突刺、格挡、第一人称弓与可替换部件表（弓体／弓弦／箭台按槽名改造），以及新枪与手模接入、枪匠配件、ADS、机械部件、音效、武器数据与装备存档闭环。用于 FPSGAME 的武器标准工作流；手臂姿态与换弹精修转 ue5-fps-arms-animation。
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。


## FPSGAME 性能开发约束（2026-09-23）

接入武器、配件、伤害面板或背包图标时，读取 [性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md) 的属性缓存、材质用途和图标部分。展示资源按配方异步准备，保留有界重试、缓存及目录图回退；静态附件材质不要错误继承骨骼用途。

# UE5 武器标准工作流

## 统一模型生成入口（2026-09-13）

新制枪械或改造配件的参考图、三视图、5080 生成、候选选择、高低模及接口适配，先用 [通用模型生成工作流](../asset-model-workflow/SKILL.md)，再按本技能接续机械分件、枪匠、手模和游戏接入。按真实连接面装配，不以整体包围盒代替挂点。


本 FPS 项目于 2026-09-10 全面转向 UE5，当前本地宿主为 `D:/FPS3D/FPSGAME/FPSGAME.uproject`（已验证 UE 5.8.2）。Git 远端 `3D-FPS` 的 main 已以根目录 `FPSGAME.uproject` / `Source` 发布 UE5 当前源码；本地 Git 根目录就是 `D:/FPS3D/FPSGAME`，直接在这里开发、提交和推送 `origin/main`；E 盘旧仓库与发布副本已归档，不再作为同步入口。默认新功能落在 UE 工程。用户明确要求维护旧原型时才使用 Godot 实现。此选择不改变其他项目的引擎。

## 按任务读取

- 普通／消音开火声、连射变体和仅改音色的响度处理：[枪械音效与消音分支](references/weapon-audio.md)。

- 枪托／握把快速近战的跨枪适配、腕臂和 recover 衔接：[快速近战接触与收势](../ue5-fps-arms-animation/references/quick-melee-contact-recovery.md)。保留命中时钟与技能合同，以各枪当前待机为归位目标。
- 双持手枪快速近战的状态仲裁、单次接触、改造件转枪和腕臂恢复：[双持快速近战](../ue5-fps-arms-animation/references/dual-pistol-quick-melee.md)；双手剑冲刺下砍及竖直冲击：[过顶下砍伸展](../ue5-fps-arms-animation/references/overhead-reach-wrist.md)。

- 近战武器拆分、可替换护手/握把/配重锤、剑身符文与长柄联动：[近战模块化与改造接口](references/modular-melee.md)。
- 原生符文漏色、明灭渐隐、语义色彩、限定改造与旧配置迁移：[剑身符文](references/rune-surfaces.md)。

- 自动连射中断、单持/双持切换、档案刷新和动作状态隔离：[武器状态刷新与输入归属](references/weapon-state-refresh.md)。

- 近战武器、双手剑、轻重攻击、三段连击、突刺和格挡：[近战标准](references/melee.md)。双手动作转手臂技能；未获满意的格挡不能作为成功母版。

- 手枪接入、末发/空仓状态、小型配件或拔枪打断：[手枪标准](references/pistols.md)，从 M1911 案例沉淀，具体尺寸和时长按新枪重新测量。

- 衣物/手套装备的第一人称制作、贴合、袖口及独立换装：[第一人称手套与衣物标准工作流](../ue5-fps-arms-animation/references/first-person-equipment-workflow.md)。按认可的 V7 裸手制作原生骨架派生，复用动作；默认裸手、区域覆盖、装备数据与布料物理边界按该合同接入，测试仅在用户明确要求时执行。

- 准心、散布、后坐力、枪口烟火、曳光、抛壳及表面命中/落血：[Gunplay 与 Niagara 验收](references/gunplay-vfx.md)。

- 新枪、模型/材质、枪匠或瞄具：[接入与装配](references/integration.md)。
- 配件图标制作、方向统一、单件机瞄或全面图标审计：[改造配件图标标准](references/attachment-icons.md)，采用已接受的实际模型水平左向规则。
- 制作或修改改造配件：[改造配件标准](references/attachment-standard.md)，覆盖生成修整、装配、展览、真实包握、换弹回握和游戏验收；2026-09-12 用户确认 VRE 成组抓握迁移成功；握把分支优先复用已接受手型并适配整手与腕臂，小阻手器按用户许可整体包握。配件数值口径、卡片/详情说明分工（描述只写基本描述、百分比由目录倍率推导并显示在详情行旁）与当前 ADS/握把数值表见该文档「配件数值与说明分工」。
- 在原厂件基础上加长/改造的配件（扩容/加长弹匣、延长枪管、导气管等）：[加长件改造规则](references/extmag-lengthening.md)——按原件曲线坐标延续完整纹路，处理截面差异与 UV 对应；避开抓握区，不将旧弧管或直接复制焊接视为定稿。
- 调整武器基础数值（有效射程、射击间隔、伤害、弹速、弹匣）或比较 DPS：[武器基础与强化系数调参](references/weapon-formula-balancing.md)，改 `base` 即改面板/实战/提示，配件倍率只按目录相乘。
- 写或改武器的**详细介绍**（`items.json` 的 `desc`）与**特殊性质**（枪匠目录的 `traits`）：[武器说明文字与「特殊性质」段](references/weapon-copy-and-traits.md)。用户 2026-09-22/23 已定格式：`desc` ≤200 字、写来历/特征/用法、现实武器参考百科、虚构武器编背景、**不用"最/第几档"等排行词、不引用别的武器型号**；`traits` 放枪匠目录因此免迁移，`icon` 决定提示里的颜色。
- 跨枪型复用瞄具、枪口、安装座或统一枪钢：[跨枪型瞄具与材质](references/cross-weapon-optics.md)。
- 新枪、新改造件或跨枪复用的材质制作：[枪身与配件材质统一](references/weapon-finish.md)，每枪以自身当前主体为基准，覆盖配件金属区域并保留非金属与光学区域。
- 瞄具、倍率、镜内视野和开镜面板：[瞄具成像与验收](references/optic-presentation.md)，先定成像与可用视野，再制作模型。
- 手臂、抓握、甩弹匣、普通/空仓换弹、拉栓、装备、奔跑及拍击：[手臂动画技能](../ue5-fps-arms-animation/SKILL.md)。
- 继续当前 M4：[当前案例与证据](../ue5-fps-arms-animation/references/m4-baseline.md)。先核对实际加载路径，不能按文件夹的日期或 Final 名称选资产。
- 原生编译/运行或用户反馈“没有应用”：[UE 验证操作](../ue5-fps-arms-animation/references/validation.md)。纯文档更新只检查内容、链接及技能元数据，不启动游戏。
- 第一人称**弓**、以及不用 AnimBP 的相机空间武器（弓／采集工具／法杖同族）：部件表拆分（弓体／弓弦／弦上箭按槽名寻址）、
  `bow_part_<槽名>_*` 数据键与表现签名重载、程序化细杆占位口径、参考手／肘轨迹、阶段秒数与实际片段采样合同、
  5.8 headless 导入字段位置与 C++ 编译陷阱：[第一人称弓与部件表](references/first-person-bow-parts.md)。
  手型／掌面／弦接触另读 [弓手型与弦接触](../ue5-fps-arms-animation/references/bow-hand-string-contact.md)；仅在用户要求检查时运行 `Tools/Bow/check_bow_consistency.py`。
- 伐木斧、矿镐的双手装备、低伤害自卫、采集范围与旧存档迁移：[采集工具战斗接入](references/harvesting-tools.md)。
- 砍树木材占 1×2、掉落全程只用短原木 `SM_PoplarLog_Solid_A`、图标按枪械剪影居中离线栅格化：[木材掉落与图标](references/harvest-wood-drop.md)。不要用场景捕获导出当图标交付。
- 整理废案、更新 Git 或用户授权推送：[清理与发布](references/publication.md)。

## 执行主线

**项目默认手模（用户于 2026-09-25 更新）**：所有新枪、新武器及新增动画，统一以用户认可的当前 V7 裸手、裸臂为开发和默认显示基准。采用 `SourceAssets/ModularOutfit20260925/BarePalmV7/` 的母版及对应原生骨架派生资产；保留手型、腕臂线条、皮肤材质与既有接触，按本枪绑定制作动作。基础视模直接保存裸手；手套、衣袖通过装备外观适配并复用动画。原版战术手套仅保留为可装备恢复版本。此规则替代 2026-09-10 的默认手套条款，具体见 [认可的裸手基准](../ue5-fps-arms-animation/references/accepted-bare-hands.md)。

1. 读取宿主 AGENTS、当前文件、资产引用和用户选择。当前宿主已有独立 Git；按精确路径检查并暂存，逐块修改共享源码，不回退并行工作。新增候选用独立目录和资产名。
2. 查看现有游戏中的枪和动作，再检查源模型。记录型号、手模、骨架、活动部件、材质和许可；区分网格外观、动作轨道、运行时姿态层及游戏状态问题。
3. 在候选中完成必要修改、导出、导入检查，然后更新实际运行引用并进行相关输入/视听回归。用户已授权修改与接入时完成整个闭环；单独选型或预览不自动扩展为正式替换。
4. 模型、手、贴图、动作和声音分别记录来源许可。已有资产合法复用与允许公开分发源包是两回事；沿用原许可证文件，不能把 HK416 动画的许可套给 Infima 手模或音频。
5. 保持武器层级与挂点：枪体主根驱动整体，弹匣、扳机、枪机、拉机柄及枪机释放件各有明确的机械身份。禁止用静态网格居中/逐件缩放流程破坏蒙皮视模。
6. 动画姿态、播放时长、机械事件、音效与补弹业务共用明确的时间映射。更换动画不改变弹药结算、拥有权、输入打断或移动合同。普通弹匣与弹鼓分别识别、分别验证。
7. 交付实际游戏预览、可编辑源、导出/导入入口和简短验收记录。证明“已应用”需要新进程实际加载和相关行为，不只依靠编译、资产存在或静音图片。
8. 数值与说明分开维护：卡片描述只写基本描述，增减百分比由目录倍率推导后显示在详情行旁，`effects` 与 `stats` 必须同义同数；改基础数值（射程、射击间隔等）时同步枪匠总览、详情行与物品提示三处显示。武器的详细介绍与特殊性质按 [说明文字与「特殊性质」段](references/weapon-copy-and-traits.md) 的格式生成；`desc` 是物品实例快照、改完必须经"构建 → 重启编辑器 → 进一次游玩"才会在旧存档显示，`traits` 放枪匠目录则直接生效。

## 标准的层次

上述是可复用方法；M4 的 2.1/2.7 秒、接触帧、480 Hz 烘焙和具体资产路径是当前案例参数。换枪时重新测量接触、局部轴、眼距和动作时长；保留用户选择的型号，不为方便动画擅自换成 HK416。

个人技能目录为维护源；本机 UE/Git 工程的 `skills/ue5-weapon-workflow`、`skills/ue5-fps-arms-animation` 保留同版镜像。更新时同步两者并检查散列，不在各副本分别演化不同标准。直接在 D 盘提交推送，遵守项目 AGENTS/WORKFLOW 的精确暂存规则；仅必要时临时隔离，不常驻额外仓库。

- 战术手电、镭射及光学杂点处理：[战术灯与镭射](references/tactical-devices.md)。

## 武器公式与DPS调参

调整基础攻击、强化成长或比较DPS时，读取 [武器公式与DPS调参](references/weapon-formula-balancing.md)。

## 数字弹药与生成枪体精修

- 弹药袋、弹种兼容组、切弹事务和射击穿透：[数字弹药袋与切换弹种](references/ammo-pouch-and-types.md)。
- 生成枪体的机瞄、漏面、接口、近景法线及分区涂层：[生成枪械近景精修](references/generated-rifle-refinement.md)。

## PKM 退役经验（2026-09-22）

早期 Meshy `PKM20260921` 分支已被用户判为废案；拆分、可见内面、材质与归因边界见 [生成枪械近景精修](references/generated-rifle-refinement.md#失败案例pkm-全系列已退役2026-09-22)。上述退役只覆盖该生成分支，不包括后续 `PKMLowpoly20260922`。继续用户低模模型的分件、材质、弹链与脚架部署时读 [PKM 低模重建](references/pkm-lowpoly-mechanics.md)；当前低模分支的制作与用户验收状态分别记录。A762 等既有成功案例保持其原适用范围。

## 环绕飞剑与施法连发

处理 G 键环绕飞剑、连续发射手势或蓝色碎裂时，读取 [环绕飞剑连发](references/rune-blade-burst.md)。
