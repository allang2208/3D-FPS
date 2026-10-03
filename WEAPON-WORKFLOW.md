# UE5 武器与手臂标准

**改造图标标准（2026-09-30）**：枪械、弓、法杖、近战与工具统一使用精致金属方框、四角铆钉、银色内环和部件主体。原厂件不加禁止标识；无配件使用中性减号。成图包含边框，UI 不重复套框。详见 [制作与接入规范](skills/ue5-weapon-workflow/references/attachment-icons.md)。

**默认手模（用户于 2026-09-25 更新）**：新增动画和新武器统一以已认可的 V7 裸手、裸臂开发，基础视模默认也是这套。手套、衣袖适配裸手并复用动作。作者源与接入规则见 [认可的裸手基准](skills/ue5-fps-arms-animation/references/accepted-bare-hands.md)。

当前工程入口为根目录 `FPSGAME.uproject`，完整本机宿主及 Git 工作目录都是 `D:/FPS3D/FPSGAME`，直接在该目录提交和推送。

- [近战武器标准](MELEE-WEAPON-WORKFLOW.md)：双手握持、轻重攻击、连击、真实突刺跨步、命中判定与防御；包含已接受的 [模块化拆分与改造接口](skills/ue5-weapon-workflow/references/modular-melee.md)。
- [M4 枪托砸击（快速进战·步枪版）](Docs/Weapons/m4-stock-melee-20260918.md)：作者源 clip 路线（六握把配置各一条）、Blender 对位胶片、命中探针取枪身前段；未实机测试。
- [枪械标准](skills/ue5-weapon-workflow/SKILL.md)：模型/许可、骨架/挂点、ADS、枪匠、装备与存档。
- [木弓五槽改造 V13](Docs/Weapons/dark-bow-modular-v13-20260926.md)：整根弓胎、独立握把缠带、动态弦、实体箭台、木制瞄具；箭矢使用单独 arrow 槽。改造台、保存、手持装配及动态图标已接入，资产已保存、后台构建成功，未实机测试。
- [基础与附加伤害统一规则](Docs/Weapons/weapon-damage-standard.md)：属性附伤先计入武器面板，命中时共同应用攻击倍率，再按物理／魔法防御独立计算基础与附加两笔结果。
- [手枪标准](skills/ue5-weapon-workflow/references/pistols.md)：末发/空仓、快速拔枪输入、精确装配、换弹时钟、展示和材料生命周期；[M1911 开发审计](Docs/Weapons/m1911-development-audit-20260913.md) 记录本次修复及检查范围。
- [枪身与配件材质统一](skills/ue5-weapon-workflow/references/weapon-finish.md)：每枪以自身当前主体涂层为基准，统一所有改造件的金属区域，保留非金属、刻字与光学消光层；跨枪复用分别制作材料变体。
- [M4 / AKM 材质补齐记录](Docs/Weapons/attachment-receiver-finish-20260913.md)：当前专用变体、保留区域、作者入口与本轮资源检查范围。
- [M1911 通用配件与动作时间](Docs/Weapons/m1911-shared-attachments-timing-20260913.md)：全息／全景红点／消音器、套筒与枪管安装、实际片段时长和手枪拔枪输入中断。
- [M1911 后部涂层与新枪雨滴](SourceAssets/M1911RearRain20260913/README.md)：后部钢件统一，以及 M1911／QBZ191 本体和改造件的天气材质接入。
- [M1911 红色激光与手电](SourceAssets/M1911Tactical20260913/README.md)：机匣下方装配、枪型专用烤蓝材质、战术功能与雨滴接入。
- [手臂动画](skills/ue5-fps-arms-animation/SKILL.md)：自然抓握、甩匣、取弹插入、拉栓、MAT 和音效。
- [改造配件标准](skills/ue5-weapon-workflow/references/attachment-standard.md)：2026-09-11 用户接受的棱镜流程，统一模型修整、安装、展览、包握与换弹回握验收，取代旧配件制作方法。
- [SVD 扩容弹匣](Docs/Weapons/svd-extended-magazine-20260927.md)：从本枪原厂弹匣延长，10→20 发；保留口部内腔和当前换弹动作，接入专用模型、图标与原厂恢复，未实机测试。
- [M1911 扩容弹匣](Docs/Weapons/m1911-extended-magazine-20260927.md)：从本枪原厂弹匣延长，7→10 发；装填耗时 +10%、开镜耗时 +5%，单持／双持装配与灰阶图标，资产已保存，构建状态见记录，未实机测试。
- [当前 M4 合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)：参数应用前核对实际 C++ 加载。
- [AKM 配件接入记录](SourceAssets/AKMAttachments20260911/README.md)：机匣桥座、两种下导轨、弹鼓与枪口件的独立安装，以及专用握把动作和运行验收。
- [ASH-12 接入](Docs/Weapons/ash12-integration-20260917.md)：oden 套件装配到共享 Manny 手臂、7 段动作、C++ 分支与数据接入；普通/空仓换弹已统一为斗牛犬编排，空仓拉栓按参考视频改为掌面向下上盖抓法，空仓换弹右臂 twist 辅助骨已改为保留相对 twist，ADS 右手穿模待实机截图定位，未进游戏实测。
- [M16A2 发布与恢复](Docs/Weapons/m16-publication-20260920.md)：三连发、M4 换弹/近战复用、空仓拉机柄、通用配件及四款枪托封口；已获用户确认，保留最终作者依赖链。
- [M4 / M16 换弹左手抓握精度修复](Docs/Weapons/m4-m16-reload-grip-precision-20260925.md)：把抓握存成弹匣自身壳坐标系的关系再跨枪搬运，替换 M16 移植里手估的武器空间常量偏移；12 条换弹重导。方法沉淀见 [弹匣抓握跨枪配准](skills/ue5-fps-arms-animation/references/magazine-grip-registration.md)。
- [AKM / A762 换弹拇指扭曲修复](Docs/Weapons/akm-a762-reload-thumb-twist-20260925.md)：抓握把拇指根部绕自身轴扭了 67°，按 SVD 经验只重做拇指三条轨道（根部纯 swing）；30 条换弹重导。判据与改法沉淀见 [异形弹匣自然抓握](skills/ue5-fps-arms-animation/references/irregular-magazine-grip.md)。
- [A762 大弹鼓供弹塔修复](Docs/Weapons/a762-drum-neck-20260925.md)：大弹鼓是 AKM 鼓套壳，塔身上段被 smoothstep 仿射重映射压出折角；改为线性过渡 + 原厂弹匣外包络重建并重导。经验见 [跨枪套用供弹塔](skills/asset-model-workflow/references/modular-part-interfaces.md#跨枪套用供弹塔用线性过渡不要-smoothstep-仿射a762-大弹鼓-2026-09-25)。
- [发布规则](WORKFLOW.md#8-仓库整理与推送) 与 [资产恢复](Docs/AssetSetup.md)。

M4 普通/空仓都甩掉旧弹匣、镜头外取新匣、左手包握插入；空仓保留拍击，装备按其拉栓动作处理。手枪按实际源动作和机械状态适配，M1911 采用拔枪与空仓套筒释放，支持装备途中开火和 ADS。不同枪型重新校准接触和时序，个人技能源与工程镜像保持同步。
