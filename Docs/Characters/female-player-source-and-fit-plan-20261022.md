# 女性玩家身体选型与适配范围

日期：2026-10-22。用户要求为现有男性玩家增加对应女性角色，并匹配身上装备、背包和动画；随后提出免费开源资源偏好。

用户于 2026-10-23 选择 Kaitlin，已下载角色包、补装 MetaHuman Creator Core Data 并完成 Epic 授权。High 级原生装配、F6 切换、女性配套装备与动作均已本地接入，2026-10-24 补齐联机路径修复、家具眼位和夹克背包配对；实际游戏与联机仍待验收。详见 [Kaitlin 制作记录](kaitlin-player-integration-20261023.md)。本文保留选型历史，不作为测试报告。

此前候选见 [2026-10-23 免费写实候选](female-player-candidates-20261023.md)：Hannah、Skye、Kaitlin；最终采用用户选定的 Kaitlin。下方早期免费来源保留作选型记录。

## 免费候选

| 来源 | 已知内容与许可依据 | 对本项目的用途与限制 |
| --- | --- | --- |
| [Fab：Yinn - Young Asian Female - Rigged](https://www.fab.com/listings/255a83dd-ad1e-420b-b8fb-e59d4f79f22b) | 页面显示 Free；作者说明 MakeHuman / CC0，带基础游戏骨架和面部骨架；列出 Blender、GLB/glTF/USDZ | 免费来源候选；官方展示精细度低于 Jason，不再作为正式玩家首选。尚未读取下载包；实际骨架、许可文件与各附加素材需要在接收制作输入时确定。不是已适配 Jason 的成品。 |
| [MakeHuman / MPFB](https://static.makehumancommunity.org/mpfb.html) | 开源人体制作工具；[官方许可](https://static.makehumancommunity.org/about/license.html)明确核心模型、贴图等资产为 CC0，MPFB 程序 GPL、MakeHuman 程序 AGPL。第三方扩展另按自身许可 | 适合制作固定成年女性体型，按实际比例派生衣物与手部；需要材质、头发和 UE 骨架接入。工具代码许可与导出模型许可分开。 |
| [Fab：Free Pack - Female Base Mesh / PolyOne Studio](https://www.fab.com/listings/ed8bc44c-7edb-4ebb-bc10-1f720798b0b8) | 页面显示免费，提供基础拓扑、UV、T Pose 和多种源格式 | 更偏几何母版。网页未提供足以确认完整 UE 成品、皮肤贴图与开放许可的证据，不将免费等同于 CC0，也不采用商品页疑似笔误的面数作为预算。 |

Yinn 官方展示：[主图](https://media.fab.com/image_previews/listing_thumbnails/ee92bfaf-ea27-4957-b1b6-9b2ffb8b4ee4/21bafa32-b3bb-4a36-a029-1b6d0f35078a.jpeg)。它是卖家展示，非本项目效果图。

2026-10-22 用户追问与 Jason 的质量差距：已阅读两者 Fab 说明并查看官方展示图。Yinn 展示中皮肤明暗较均一、头发偏整块、手臂及面部细节较简化；Jason 来自真人扫描，按 MetaHuman 拓扑重制并使用其骨架，展示的解剖与表面更细。不同灯光与展示方式会影响观感，此结论属于成品展示与制作来源的选型判断，不是同灯光渲染或下载包几何测试。Yinn 的免费开放许可优势不等于与 Jason 同档的主角质量；达到项目现有质量需额外重做皮肤、头发及局部造型，故撤下首选建议。Jason 原包 ML Deformer 能力不直接计作本项目已启用能力，工程初始接入记录明确当时没有接入。

之前搜索到的付费备选为 Quantum Modular Basemesh、Arin、Female Base Body 1，未购买或接入。Quantum 免费样本页面标明 Tall/Masculine，不能当成女性身体免费包。

## 已读取的当前实现

- 身体来自 AsianMale Jason；当前 `player_body.json.body_mesh` 为 `EquipmentFit20261003/SK_Jason_Base`。头型、发型已有存档字段与复制入口，但身体初始化仍读取单一身体和动作目录。
- `FPSPlayerBodyComponent::InitializeBody` 负责身体、骨架坐标转换、全身片段和第一人称自视身体。`FPSPlayerBodyAppearance.cpp` 当前解析头发与头型；增加女性不能只调用换头接口。
- `FPSModularOutfitComponent` 按源网格对应的 `rig_profile` 选择衣物、原生裸手、皮肤和覆盖分区。当前 Jason 全身与各枪械／工具的第一人称原生绑定为不同路径。
- `FPSPlayerBodyEquipment.cpp` 的世界背包映射当前按物品与上衣选择，女性需要自己的身体配置和上衣配对。保留当前背包动态与刚性包体分离机制。
- `ColdSteelInventoryTypes.h` 的 `PlayerHeadId/PlayerHairId`、`ColdSteelProfileRuntime.cpp` 的外观事务和 `FFPSBodyAppearance` 是未来身体选择接入的既有边界；本阶段没有添加尚不可用的女性开关。

## 制作范围

`Tools/PlayerBody/create_female_fit_scope.py` 从当前三份 JSON 生成 `SourceAssets/FemalePlayer20261022/fit_scope.json`。清单记录每件配置的完整配方、路径选择器、衣靴组合、背包按上衣变体、原生绑定注册及全部全身动作映射；它只读取配置和写入制作清单，不加载 UE、不检查资产或运行测试。注册目录中可能同时保留历史路径，不代表所有路径均在游戏当前使用。制作前重新生成以接纳并行修改。

初始快照包含 24 件衣物（5 上衣、7 裤装、6 鞋靴、6 手套），4 背包、4 头部装备、184 个全身动作映射和 25 个注册绑定家族。动画映射不等于 184 个唯一动作资产，也不涵盖所有程序动作与第一人称片段。

1. **固定身体与骨架**：选定成年女性母版，保留原始源与许可，制作皮肤分区、头颈接缝及体型配方。男性 Jason 路径保留。战斗、容量、伤害与移速不因外观性别自行改变。
2. **衣物与裤鞋**：胸肩、腋下、腰臀、裆部与袖口按女性实际几何重制；保留既有物品 ID 和材质身份。身体覆盖分区随目标网格制作；靴型裤脚、野行上衣的实际裤网格配对、法袍内穿裤都要提供女性版本。当前 PantsCompatibility 仅支持 Jason，须先加入女性作者源，不能直接运行去覆盖男性配方。
3. **背包**：四款包体尽量复用，肩垫、胸带、侧带、斜挎带分别重走女性肩胸与衣物表面。保留实际包体尺寸、连接点与刚性结构，为裸身及五类上衣形成目标配方；动态枢轴、包围范围和松弛量随新几何制作，不能只缩小整个背包。
4. **动画**：所有全身映射按女性骨长重定向，另处理程序动作和共享姿态层。重点为脚底支撑、蹲起、翻越、双手握距、抵肩、换弹、弓弦接触、近战、进食与施法。伤害／接触／弹药／施法业务时钟保留，不能按性别任意加速或缩放武器。
5. **第一人称**：由确定的女性手臂母版派生各原生绑定，匹配手套与衣袖。复用现有抓握意图、机械动作及事件时钟，按实际掌指尺寸修接触；覆盖空手、枪械单双持、剑、弓、杖、书、工具及翻越。
6. **性别与外观选择**：在现有档案外观事务中增加稳定身体 ID，与头型／发型兼容表一起解析。角色出生、重生、换图、存档载入和远端复制均应用同一身体配置；旧存档继续选 Jason。匹配加载完后再整体切换身体、衣物、头部和动作；预加载/Cook 收集对应女性资源，避免仅本机可见。

以上为待执行开发项。选型完成及源资源取得后，按此范围制作、必要构建、后台导入与保存；不主动启动编辑器或游戏、不自动验收。最后分别交付源码、构建产物、已保存资产与用户待测内容。
