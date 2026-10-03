# Fab 商场角色服装与换装资产调研（UE 5.8 FPS 项目）

调研日期：**2026-09-23**。本机宿主 `D:/FPS3D/FPSGAME`，UE 5.8.2。

本文只做市场侧调研：**Fab（fab.com）上能买到/免费拿到什么，能不能穿到本项目的 Manny 身上，代价是什么。** 引擎内置方案（Chaos Outfit Asset、Mutable、MeshResizing）见姊妹文档 [clothing-system-research-engine.md](clothing-system-research-engine.md)；两者合并后才能给定方向性结论。项目现状锚点（该文第 7 行核对）：玩家全身为 Manny（`SKM_Manny_Simple` / 骨架 `SK_Mannequin`），全身皮肤已换成独立 `SKM_Manny_PlayerSkin`，`Content/ColdSteelData/player_body.json` 的 `outfits` 为空，衣物接入方式为「共用骨架 + Leader Pose + 隐藏身体材质区」。

**本文不写任何代码、不改任何工程资产。**

---

## 0. 取证方法与可信度分级（先读，决定你怎么用这张表）

本次调研遇到一个必须先说明的硬障碍：

> **`www.fab.com` 的全站页面在本会话中一律返回 HTTP 403。** 已实测失败的取回方式包括：直接 `web_fetch` listing 页与 `/channels/metahuman` 频道页、`/i/listings/search` JSON 端点、`/eula`；PowerShell `Invoke-WebRequest` 带浏览器 User-Agent；公共 CORS 代理（allorigins）；`r.jina.ai` 文本代理。`www.unrealengine.com/marketplace/...` 旧商城页同样 403。Fab 无公开可读的商品 API（`api.fab.com` 不存在）。
>
> **直接后果：本文没有任何一个价格是从商品页读到的。** 商品页上的「Personal / Professional 两档标价」、逐商品的许可标签（Standard vs 旧 UE Marketplace License）、以及包内资产清单，**我无法核实**。凡涉及这些，本文一律标注为未核实，不做推测填充。

可信度分级（全文沿用）：

| 级别 | 来源 | 本文用途 |
| --- | --- | --- |
| **A** | Epic 官方文档站 `dev.epicgames.com` | 许可与定价规则、MetaHuman 衣柜与骨架要求、免费内容说明 |
| **B** | Epic 开发者社区论坛（`unreal2.epic-prod-us2.discourse.cloud`）的**卖家产品帖**，帖内带 Fab listing ID | 商品的骨架兼容性、UE 版本、包内容、更新记录 |
| **C** | 搜索引擎返回的标题与 URL（页面本身打不开） | 只能证明「该 listing 疑似存在」，**不足以作为采购依据** |

B 级证据的性质要说清楚：那是**卖家自己发的产品说明**，不是 Epic 的认证。它能可靠回答「这件衣服绑在哪个骨架上」，但不能替代商品页上的许可与价格条款。

---

## 1. 核心结论（先看这五条）

1. **不需要、也不应该为服装引入 MetaHuman 衣柜系统。** MetaHuman 服装是**另一套骨架上的资产**，官方格式要求与 Manny 不兼容；引入它等于把项目推向「换骨架」方向，与已认可的 Manny 第一人称手臂管线直接冲突。详见第 3 节。
2. **「方向甲：留在 Manny」不被资产供给卡住。** 我核验到**多家卖家在同一个商品里同时交付 MetaHuman 绑定与 UE5 Mannequin 绑定**，并且其中至少一家（Lumelle Studio）明确交付 **FBX / Blender / glTF 源文件**。这意味着「买到能直接穿的 Manny 衣服」在市场上是成立的，离线裁剪也有原料。这对姊妹文档第 8 节的方向选择是正向证据。
3. **服装应挂在第三人称全身 Manny 网格上，绝不碰第一人称手臂资产。** 本项目 FP 手臂是一套独立资源（M4 基线），服装属于全身网格的装饰层。两者共享 `SK_Mannequin` 骨架这一事实不构成「必须一起改」的理由，反而是不该一起改的理由。
4. **价格与逐商品许可条款：全部未核实。** 我给出的是 Fab 官方的**规则**（许可类型、两档定价、商业使用边界），不是任何商品的具体标价。
5. **Fab 的限时免费内容近期几期都不是角色服装。** 已核实的 2026-07-28、08-11、08-25、09-08 四期（每期 3 件）全是场景/工具/VFX。**不要把「等限免」当采购策略。**

---

## 2. 已核验候选表

「已核验」= 我读到了 Epic 托管页面上的**产品说明正文**（B 级）并能给出 Fab listing ID。**价格列全部未核实**，原因见第 0 节。

| 名称 | 来源/URL | 价格 | 许可 | UE 版本 | 骨架兼容性 | 是否需要额外插件 | 适配本项目的评估 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Davlet — Sci-Fi Clothing Pack 01–04 Mega Bundle** | [fab.com/listings/81f266e1-e894-477b-bcc3-1516927bb3d0](https://www.fab.com/listings/81f266e1-e894-477b-bcc3-1516927bb3d0)；产品帖 [forum 2687694](https://unreal2.epic-prod-us2.discourse.cloud/t/davlet-sci-fi-clothing-pack-01-04-mega-bundle/2687694) | **未能核实** | 未能核实（Fab Standard License 为默认；需在商品页 Details 区确认是否仍为旧 UE Marketplace License） | 卖家称 **Update 2.1 增加 UE 5.6–5.7 工程**；2.0 起提供 MetaHuman 参数化套装（`.mhpkg`） | **明确双路线**：2.1 的工程含「clothing rig and skinning adapted to the original male Manny rig (UE5)」；同时有 MetaHuman 参数化版本 | 工程版不需要额外插件；`.mhpkg` 版本需要 MetaHuman Creator 插件 | **最贴合 FPS 题材的已核验候选之一。** 单件拆分（Helmet / Jacket / Pants / Sneaker）而非整身，适合模块化。⚠️ 两个坑：(a) 工程文件停在 5.6–5.7，在 5.8.2 需要升级/重导，不能直接迁移；(b) 卖家自述 Fab 只允许上传一个 `.mhpkg`，其余包在 Additional Files 里手动解压 |
| **Lumelle Studio — Short Sleeve Hoodie 01（Rigged & Parametric & Variable & Retopology）** | [fab.com/listings/240347f8-53ff-44a1-a670-a8f1cceb44e3](https://www.fab.com/listings/240347f8-53ff-44a1-a670-a8f1cceb44e3)；产品帖 [forum 2699929](https://unreal2.epic-prod-us2.discourse.cloud/t/lumelle-studio-short-sleeve-hoodie-01-rigged-parametric-variable-retopology/2699929) | **未能核实** | 未能核实 | **UE 5.6 及以上**工程 | **同一商品交付两套绑定**：「Rigged to Metahuman Skeleton **&** UE5 Mannequin Skeleton」；另含「Only 1 Metahuman Vivian Full Body + UE5 Manny and Quin with Skeleton」 | 用 UE 工程/FBX 路线：**不需要**额外插件。用 `.mhpkg`（MetaHuman Creator 衣柜）：需要 MetaHuman Creator 插件 | **本批候选里最适合「可重复管线」的一件。** 交付格式覆盖 **UE 工程 + MHPKG + FBX + Blender + glTF + 4K PBR**，也就是**能拿到 FBX/Blender 源文件离线裁剪与改权重**，完全绕开「商品工程没有 5.8 版本」的问题。含 LOD 与重拓扑。⚠️ 是休闲连帽衫，风格需与项目调性核对 |
| **Polyphoria — Fantasy Armour: Caster / Mage / Sorcerer / Wizard (Metahuman)** | [fab.com/listings/89c0fb19-434f-42d6-94ff-76e71473658c](https://www.fab.com/listings/89c0fb19-434f-42d6-94ff-76e71473658c)；产品帖 [forum 2426426](https://unreal2.epic-prod-us2.discourse.cloud/t/polyphoria-fantasy-armour-caster-mage-sorcerer-wizard-metahuman/2426426) | **未能核实** | 未能核实 | 卖家称「UE5 Update：base components converted to the new UE5 Mannequin rig structure」，并保留 UE4 Mannequin 网格 | 卖家原文：**「the female Metahuman tal nrw is slightly smaller as Quinn, but they use the same bone structure」**——即 MetaHuman 与 UE5 Mannequin **共用骨结构**，这是本文第 3 节的关键证据。但帖内另有旧段落称交付网格「skinned to the UE4 skeleton」，**两处表述冲突** | 不需要额外插件（纯骨骼网格 + 材质） | **不作为采购首选**（奇幻题材，非 FPS）。价值在两点：(a) 提供了「MH 与 Manny 同骨结构」的一手卖家证言；(b) 其 **Character Editor** 换装系统是模块化服装装配的成熟范例。⚠️ UE4/UE5 绑定版本表述冲突，**若要买必须先向卖家确认拿到的是哪一套绑定** |
| **Yusuf Y.Y — LE_Characters_Pack（执法角色包，UE5 模块化）** | [fab.com/listings/3a04f4ae-579a-4a48-a0ba-5fb8aa65a95b](https://www.fab.com/listings/3a04f4ae-579a-4a48-a0ba-5fb8aa65a95b)；产品帖 [forum 2714501](https://unreal2.epic-prod-us2.discourse.cloud/t/yusuf-y-y-le-characters-pack/2714501) | **未能核实** | 未能核实 | 未标注具体 UE 版本（称 Unreal Engine 5） | 卖家原文：**「All characters are fully compatible with the UE5 Manny skeleton and support animation retargeting from Epic and MetaHuman characters」** | 不需要额外插件 | **题材最贴（SWAT / Police / Sheriff / 快速反应 / 保安，明确写「Perfect for: FPS / TPS games」）**，含 5 个模块化角色 + 模块化服装装备系统 + 多级 LOD。⚠️ **重要保留**：帖内列出了 **40 余根附加骨骼**（`base_pelvis`、`base_l_forearmtwist01`、`base_l_breast`、`base_l_bigtoe1` 等），说明其骨架是「Manny + 附加骨」。**把它的服装网格直接挂到纯净 `SK_Mannequin` 上会缺骨骼，需要重定向/重蒙皮，此点未实测。** 且它是「角色包」不是「服装包」，身体可能一起交付 |
| **Yusuf Y.Y — 单件（Realistic SWAT / Modular Security Guard / Riot Police / Modern Police-Sheriff）** | [fab.com/s/10ade9657f7a](https://fab.com/s/10ade9657f7a)、[fab.com/s/fdb64144f2cf](https://fab.com/s/fdb64144f2cf)、[fab.com/s/70c645971780](https://fab.com/s/70c645971780)、[fab.com/s/fa111eef057d](https://fab.com/s/fa111eef057d)（短链来自卖家产品帖） | **未能核实** | 未能核实 | 同上 | 同上（UE5 Manny 骨架 + 附加骨骼） | 不需要额外插件 | 若只想要其中一类装备而不买整包，可拆买。评估同上一行 |
| **Fab 官方 MetaHuman 频道**（路径，非商品） | [fab.com/channels/metahuman](https://www.fab.com/channels/metahuman) | — | — | — | **MetaHuman 骨架专用** | `.mhpkg` 需 MetaHuman Creator 插件 | **本项目应主动避开这个频道。** Epic 官方文档明确把它作为 MetaHuman 衣柜的采购入口（见第 3 节）。它是「换到 MetaHuman」路线的弹药库，不是本项目的 |

### 2.1 已核验的「免费 / 限免」事实

| 项目 | 结论 | 证据 |
| --- | --- | --- |
| Fab 限时免费机制 | **每两周**放出 **3 件**商品，**免费窗口仅两周**（过期恢复原价）。入口 [fab.com/limited-time-free](https://www.fab.com/limited-time-free) | Epic 员工帖（用户组 `Epic_Games_Inc`）[forum 2738884](https://unreal2.epic-prod-us2.discourse.cloud/t/fab-limited-time-free/2738884) |
| 2026-09-08 → 09-22 那期 | Sharur's Normandy Village + PCG Plants、Industrial Infrastructure、RPG - Crafting & Environment VFX。**无角色/服装** | 同上（帖子第 7 楼） |
| 2026-07-28 / 08-11 / 08-25 三期 | Dragon Cave、Surface Forge v1.1、Atlantis Ruins、Nordic Fishing Hut、Voyager: Cover System、Dynamic Spline FX 2、Hyper Attribute Manager 等。**无角色/服装** | 同上（第 1、2 楼） |
| Epic 官方永久免费内容 | Epic 在 Fab 上分发免费内容，**筛选方式为 Price > Free**；官方点名的免费角色美术是 **Paragon 与 Infinity Blade** 系列。**这些不是 Manny 骨架，不能直接用于本项目玩家角色** | [Free Epic Games Content for Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/free-epic-games-content-for-unreal-engine?application_version=5.6) |

> 注：Epic 官方文档只说「用 Price > Free 筛选」，我**没有**核实到一个名为 "Epic Games Content" 的独立 seller 页面 URL。搜索结果里出现的旧商城链接（如 `mannequins-asset-pack`）本次均 403，未核验，见第 6 节。

---

## 3. MetaHuman 与 Manny 骨架：具体回答

### 3.1 Epic 是否提供官方 MetaHuman 衣柜系统？——是，而且是完整的

有，且是正式功能。UE 5.8 文档 [Hair and Clothing Tools](https://dev.epicgames.com/documentation/metahuman/hair-and-clothing-tools?application_version=5.8) 定义了完整流程：

- **Wardrobe（衣柜）**：按槽位分类。头发槽位有 head hair / eyebrows / eyelashes / mustache / beard / peach fuzz；服装槽位按**资产的制作方式**分为两类：
  - **Cloth Outfits 槽** ← `ChaosOutfitAsset`（参数化、可随体型自动缩放）
  - **SkeletalMesh 槽** ← 普通骨骼网格（固定尺寸）
- 穿着方式：双击或 **Wear** 按钮；穿着后成为 **Costume**。
- 首次穿着需 **Prepare**（会把计算结果缓存进 MetaHuman Character 资产，**可使该资产体积显著变大**；可用 **Unprepare** 清理）。
- 支持**自定义衣柜条目**：把资产拖进槽位，或在 Project Settings → MetaHuman Character 插件 → **Wardrobe** 里配置监听的文件夹。槽位与可过滤类的**合法组合是白名单固定的**（`Top Garment` ↔ `ChaosOutfitAsset`，`SkeletalMesh` ↔ `SkeletalMesh`，各头发槽 ↔ `GroomBindingAsset`）。
- 有 **Wardrobe Item Validation**：不通过校验的条目不会穿上。文档给的反例截图正是**「用了不兼容骨架的 Skeletal Clothing Wardrobe Item」**。校验可在 Project Settings 关掉（**仅供不打算分享的自定义条目**），但**提交到 Fab 时永远必须通过**。

### 3.2 关键约束：官方明说 MetaHuman 服装必须用 MetaHuman 骨架

这是本文最重要的一条硬证据。Fab 上架要求文档 [Asset Format and Structure Requirements For MetaHumans on Fab](https://dev.epicgames.com/documentation/metahuman/asset-format-and-structure-requirements-for-metahumans-on-fab?application_version=5.6) 在 **Skeletal Clothing** 一节原文：

> Skeletal clothing must use the **MetaHuman base skeleton, or a very close variant of it**. Bones in the skeleton must not have been **reparented or otherwise reorganized**.

并且在 [Tailoring Your Own Wardrobe Items](https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items?application_version=5.7) 中，Fab 上买到的 MetaHuman 服装一律以 **`.mhpkg` 包**交付，需要 MetaHuman Creator 插件导入（或从 Fab 直接 Add to Project）。

**结论：官方 MetaHuman 服装资产（尤其 `.mhpkg` / Chaos Outfit Asset 形态）不是给 `SK_Mannequin` 做的，不能直接穿到项目的 Manny 上。** 服装槽位的校验机制会主动拒绝骨架不符的条目。

### 3.3 但两套骨架「同骨结构」——所以差距是「网格与绑定」，不是「重定向难题」

这两件事要分开看，很多讨论把它们混为一谈：

- **骨骼结构层面**：MetaHuman 的身体骨骼与 UE5 Mannequin（Quinn/Manny）**是同一套命名与层级结构**。一手卖家证言（Polyphoria，B 级）：*"the female Metahuman tal nrw is slightly smaller as Quinn, but they use the same bone structure."* 生物学差异体现在**比例**（更矮/更瘦）与**网格拓扑**（MetaHuman 有独立的头部/身体合并网格，以及面部、牙齿、眼球、舌头等 MetaHuman 特有骨骼），不在躯干四肢的主骨层级上。
- **资产交付层面**：`SKM_Manny_Simple` 与 MetaHuman body 是**两个不同的 SkeletalMesh，各自绑定到自己的 Skeleton 资产**。UE 里「共用骨结构」不等于「可以直接互换穿戴」——骨骼网格必须在**同一个 Skeleton 资产**（或兼容骨架）上才能直接挂。
- **正因为同骨结构**，Fab 卖家可以低成本地**同一件衣服出两套绑定**，这正是我核验到的 Lumelle Studio 的做法；也是 Davlet 能「把这套衣服重新蒙皮到 original male Manny rig」的原因。
- **动画方向**：Manny 动画要用到 MetaHuman 身上，官方流程是**必须做重定向**——见 [Retargeting Animation Blueprints to MetaHumans](https://dev.epicgames.com/documentation/metahuman/retargeting-animation-blueprints-to-metahumans-in-unreal-engine?application_version=5.6)：复制并重定向 `ABP_Quinn`（IK Retargeter 选 `RTG_Mannequin`，源预览自动填 Manny）、再手工做 **Enable Master Pose** 的组件树改造。文档明确提醒：**该方案不走 IK Rig 的足部着地**，腿部不会贴地，需要额外修。这与姊妹文档第 8 节「方向乙的代价是重做 59 条 Manny 动作的适配与足部/蹲姿 IK」是同一件事的两个说法。

### 3.4 MetaHuman Creator 服装系统在 2025/2026 的实际状态（UE 5.8）

从 [MetaHuman 5.8 Release Notes](https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine?application_version=5.8) 与 [Hair and Clothing Tools 5.8](https://dev.epicgames.com/documentation/metahuman/hair-and-clothing-tools?application_version=5.8) 提炼与本项目相关的四点：

1. **MHC 已内置进 UE 编辑器**（不再是外部 Web 工具），衣柜、参数化服装、校验都在引擎内完成。
2. **5.8 新增 MetaHuman Crowds（实验性插件）**：把 head / body / hair / **clothing** 拆成模块化组件集合，再用 Blueprint 手工或程序化组合，面向 Mass 大规模人群。这是 Epic 把「模块化服装」正式化的方向，但**仍然全部在 MetaHuman 体系内**。
3. **5.8 新增 Mesh-to-MetaHuman**：可把任意拓扑的人形网格一次性转成完整绑定的 MetaHuman（**结果会采用 MetaHuman 的拓扑与绑定**）。也就是说 Epic 给出的「把外部模型接进来」的答案是**同化到 MetaHuman**，而不是让 MetaHuman 资产去适配 Manny。
4. **5.8 新增 `MetaHumanGenerator` MCP Toolset 插件**（给 Unreal MCP server 用，可实例化 MetaHuman Character 资产并读写瞳色/肤色/体型）。项目已有 UE MCP 桥，这条值得记一笔——但目前 MCP 侧只覆盖生成与属性读写，**不包含服装装配**。
5. **时效性坑（影响鞋类资产）**：5.8 文档明确 *"As of UE 5.6, the default +2cm offset applied to all MetaHuman characters has been removed, which means the sole of any footwear will appear beneath the ground plane."* 买 MetaHuman 鞋类时这是必查项。

另外，**卖家侧反复提示该服装系统仍在演进**：Davlet 的 FAQ、Polyphoria 的帖子都写了「MetaHuman 服装系统会随版本变化，我们会跟着适配新标准」。这意味着现在为 MetaHuman 衣柜采购的资产，未来有返工风险。

### 3.5 对本项目的直接结论（回答「能不能只买 MetaHuman 衣服来用」）

**不能直接用。** 三种现实路径与代价：

| 路径 | 做法 | 代价 | 对本项目的判断 |
| --- | --- | --- | --- |
| **A. 只买双绑定/Manny 原生服装** | 直接采购已绑 `SK_Mannequin` 的骨骼网格，走现有「共用骨架 + Leader Pose + 隐藏身体材质区」 | 最低。不新增插件、不动骨架、不动 59 条动画 | ✅ **推荐**。市场供给已证实存在（第 2 节表） |
| **B. 买 MetaHuman 绑定 + 自己重定向/重蒙皮** | 用 FBX 源文件在 Blender 里把权重传/重绑到 `SK_Mannequin` | 中等。需要 DCC 环节与每件衣服的验证；属「体力活」而非技术障碍（因骨结构相同，权重传递路径短） | ⚠️ 备选。仅对「只出 MH 绑定但给了 FBX」的商品可行 |
| **C. 引入 MetaHuman 身体与衣柜** | 换骨架、用 `.mhpkg`、用衣柜校验 | 最高。放弃已认可的全身皮肤材质路线，重做动画重定向与足部/蹲姿 IK | ❌ **不建议**，与「不得破坏第一人称手骨管线」的约束正面冲突 |

**一句话**：MetaHuman 衣物能不能用在 Manny 上——**资产不能，权重能**。差异是骨架资产与蒙皮归属，而非骨骼语义。

---

## 4. 推荐采购/下载清单

排序原则：**先拿能绕开 UE 5.8 版本风险、且已绑 Manny 的；题材契合度放第二位；框架类最后。**

### 第一梯队（先拿，风险最低）

1. **Lumelle Studio — Short Sleeve Hoodie 01**（[listing](https://www.fab.com/listings/240347f8-53ff-44a1-a670-a8f1cceb44e3)）
   - **为什么第一**：它是唯一一件我核验到**同时**满足「双骨架绑定」「UE 5.6+ 工程」「交付 FBX + Blender + glTF 源文件」「含 LOD/重拓扑」的候选。拿到 FBX/Blender 就等于拿到了**离线裁剪与改权重的原料**，这是本项目「可重复管线」最关键的一环，且**不依赖商品是否发布了 5.8 工程文件**。
   - **先做的一件事**：只用它的 FBX + 4K 贴图，在 Blender 里对 `SK_Mannequin` 走一遍「重蒙皮 → 裁剪 → 回导」，把流程跑通。**跑通后再决定是否批量采购同类商品**——这一步的产出是管线，不是衣服。
   - 注意：UV/权重/关节空间需按项目惯例逐项核对（与 `first-person-arms-standard.md` 对新增衣料的要求一致）。

2. **Davlet — Sci-Fi Clothing Pack 01–04 Mega Bundle**（[listing](https://www.fab.com/listings/81f266e1-e894-477b-bcc3-1516927bb3d0)）
   - **为什么**：题材（科幻战术）最接近 FPS，且是**单件拆分**（头盔/夹克/裤/鞋），天然适合模块化装备系统；卖家明确做了「蒙皮适配 original male Manny rig」的工程。
   - **风险与处理**：工程文件停在 **5.6–5.7**，在本项目 5.8.2 上**不要直接迁移**；优先走「重新导入 FBX/资产 + 在 5.8 里重建材质实例」的路径，避免把旧版 Blueprint/插件依赖带进来。另注意其余分包在 Additional Files 里。

### 第二梯队（题材最贴，但需先解决骨架细节）

3. **Yusuf Y.Y — LE_Characters_Pack 或其单件**（[整包](https://www.fab.com/listings/3a04f4ae-579a-4a48-a0ba-5fb8aa65a95b)）
   - **为什么**：明确写「fully compatible with the UE5 Manny skeleton」+「Perfect for: FPS / TPS games」，模块化服装装备系统 + 多级 LOD，是现代战术题材。
   - **买之前必须确认**：卖家列出的 **40 余根附加骨骼**是否只是「身体自带」而**服装网格本身只引用 `SK_Mannequin` 上的骨骼**。若服装引用了附加骨，就必须重蒙皮才能在纯净 `SK_Mannequin` 上使用。**这是购买前的一个具体问题，问卖家即可，成本极低。**

### 第三梯队（框架/参照，非必需）

4. **Polyphoria — Character Editor + Fantasy Armour 系列**：题材不符，但 **Character Editor** 是成熟的模块化换装装配思路，可用于对照本项目 JSON 驱动（`player_body.json` 的 `outfits`）的数据结构设计。**注意**：该系列同时存在 UE4 与 UE5 绑定表述冲突，只作为思路参考更划算。

### 免费/限免的监控策略（不作为主力）

- 关注 **Fab Limited-Time Free**（每两周 3 件、窗口两周），但根据已核实的四期内容，**角色服装出现的概率低**，把它当「顺手捡」而不是「等它」。
- Epic 官方永久免费内容里点名的是 **Paragon / Infinity Blade** 角色美术——**不是 Manny 骨架，不适用于本项目玩家角色**，且属另一套重定向工程。

### 明确不要做的事（保护已认可管线）

- ❌ **不要为服装更换骨架。** 玩家的全身网格、`SKM_Manny_PlayerSkin` 皮肤材质、59 条 Manny 动作、第一人称手臂与 M4 基线，全部建立在 `SK_Mannequin` 上。
- ❌ **不要动第一人称手臂资产来「统一外观」。** 项目文档已明确：*「统一外观不等于跨骨架复制旋转，新增衣料/手套要验证 UV、权重和关节空间」*。服装是全身网格的装饰层，手套/手臂沿用现有 M4 资源。
- ❌ **不要引入 MetaHuman 衣柜/`.mhpkg` 依赖**，除非先决定走方向乙（换身体）。
- ❌ **不要买只有 `.mhpkg` 的纯 MetaHuman 服装**（第 6 节里 Vu. / NDart / DarkTide Studios 那一类），除非明确接受路径 B 的重绑定工作量。

### 采购前核对清单（每件都要问，5 项）

1. **骨架**：交付的是 `SK_Mannequin` 绑定、MetaHuman 绑定，还是两者都有？
2. **骨骼引用**：服装网格引用的骨骼是否**全部**存在于纯净 `SK_Mannequin`？（附加骨、twist 骨、`sharebone` 是红灯）
3. **源文件**：是否含 **FBX**（最好还有 Blender）？——这是绕开版本问题的唯一保险。
4. **UE 版本**：商品工程最高到哪个版本？5.8 是否在列？（**5.8 很新，多数商品止于 5.6/5.7**）
5. **许可**：商品页 Details 区显示的是 **Fab Standard License** 还是**旧 UE Marketplace License**？（后者正在被 Epic 淘汰）

---

## 5. 与引擎侧方案的衔接（不重复，只给接口）

姊妹文档 [clothing-system-research-engine.md](clothing-system-research-engine.md) 已定：**Chaos Outfit Asset 是官方「适配不同体型」的正式系统，但它是围绕 MetaHuman 合并网格 + 测量值契约设计的，默认关闭且为 Beta**。本文的市场侧证据与之一致且互补：

- **市场现实印证了引擎侧的技术判断**：Fab 上「参数化、可随体型缩放」的服装全部以 `.mhpkg` / Chaos Outfit 形态交付，**且官方要求 MetaHuman 骨架**。所以「买参数化服装 → 自动适配」这条路，在 Manny 上目前**没有货架商品**。
- **市场同时提供了替代方案**：Lumelle Studio 这类「双绑定 + FBX 源文件」的商品，把「适配」问题从**引擎内动态求解**转移到**DCC 离线一次性处理**。这与姊妹文档方向甲的「适配用 DCC 离线完成（Blender 权重传递）」完全对应。
- **尚未解决的共享问题**：这些商品是否真的能在纯净 `SK_Mannequin` 上直接使用（骨骼引用是否干净），**本次未能实测**（按项目规则不主动启动编辑器/不验收）。这属于「采购前问卖家」或「买回后在后台脚本里查网格骨骼列表」即可低成本解决的问题。

---

## 6. 未验证候选 / 无法确认

### 6.1 存在性可信但页面未核验（C 级，**不得作为采购依据**）

以下条目来自搜索结果标题或卖家帖的引用，**我没有读到商品页正文**，也无法确认价格、许可、UE 版本：

| 名称 | 已知信息 | 为何未验证 |
| --- | --- | --- |
| **Male Clothing Collection for Metahuman - Male MH & UE5 Skeletons - Rigged** | listing 存在：[fab.com/listings/252b167f-154f-401e-9dd0-5ffd4ba8e475](https://www.fab.com/listings/252b167f-154f-401e-9dd0-5ffd4ba8e475)。标题本身即暗示「MH + UE5 双骨架」，**方向正确** | Fab 页面 403；论坛无对应产品帖可交叉验证 |
| **Female Clothes Collection Metahuman — MH & UE5 Skeletons - Rigged** | listing：[d81cb4a9-2e00-4e81-916f-8b2f9627dfe3](https://www.fab.com/listings/d81cb4a9-2e00-4e81-916f-8b2f9627dfe3) | 同上 |
| **Military Outfit for Metahuman — MH & UE5 Skeletons - Rigged** | listing：[48b50b4b-9bb5-4d43-b07c-fa285123f6c5](https://www.fab.com/listings/48b50b4b-9bb5-4d43-b07c-fa285123f6c5) | 同上 |
| **NANI — Men's Bootcut Jeans & T-Shirt** | listing：[0cfc7453-2736-4b03-959f-f9c8dbb72a88](https://www.fab.com/listings/0cfc7453-2736-4b03-959f-f9c8dbb72a88) | 同上 |
| **Modular Meta Cowboys Pack** | listing：[448a9cc4-ccc8-4b12-a76a-58003448d47e](https://www.fab.com/listings/448a9cc4-ccc8-4b12-a76a-58003448d47e) | 同上 |
| **Aisha \| LOWPOLY MODULAR CHARACTER** | listing：[a5b0527a-e791-4ea5-a121-dea65dbfdf75](https://www.fab.com/listings/a5b0527a-e791-4ea5-a121-dea65dbfdf75) | 同上 |
| **Stylized Nordic Warrior Outfit** | listing：[2028f6d8-6bc8-4ba8-9ac8-df89d39c8077](https://www.fab.com/listings/2028f6d8-6bc8-4ba8-9ac8-df89d39c8077) | 同上 |
| **Modular Medieval NPC V2 - Metahuman** | listing：[4eb02787-c32d-4a10-b36b-bb237cffd738](https://www.fab.com/listings/4eb02787-c32d-4a10-b36b-bb237cffd738) | 同上 |
| **Epic 官方 "Mannequins Asset Pack"（旧商城）** | 搜索命中 `unrealengine.com/marketplace/.../mannequins-asset-pack` | 旧商城 403；且这是 UE4 时代人体模型包，**不是服装** |

### 6.2 卖家帖已核验、但未能提取 Fab listing URL（部分验证）

这些商品的产品说明我读到了（骨架/内容可信），但**没能拿到对应 listing 链接与价格**，因此无法进入第 2 节主表：

| 名称 | 卖家自述关键信息 | 未验证项 |
| --- | --- | --- |
| **Lumelle Studio — Tank Top 01 / Silk Sleeveless Blouse 01** | 同系列，同样「Rigged to Metahuman Skeleton & UE5 Mannequin Skeleton」+ Parametric Cloth Asset | 与我核验的 Hoodie 同卖家同描述模板，**大概率同规格**，但未逐条核验页面 |
| **Nice Pictures — Santa Claus Hat / Gloves / Boots** | 「Parametric + Fixed MH Bodies + **UE5 Skeletons** - Rigged」，即双骨架路线 | listing URL 未提取；题材不符，仅作「双骨架商品确实成规模存在」的旁证 |
| **Clothes Market — 3D Socks / 3D Jeans** | 「All MH Bodies & **UE5 Skeletons** - Rigged」 | 同上 |
| **Vu.（Trinhtuanvu）系列** — 军事战术装、Ranger Survival Outfit、T恤短裤、针织裙、街头球鞋等 | **均为 `.mhpkg` + MetaHuman 骨架**（且配「How to Use MHPKG Assets on Metahumans 5.8」教程） | **属纯 MetaHuman 路线**，本项目不适用；列此以说明该路线在 Fab 上供给量很大 |
| **NDart — Turtleneck Sweater / Casual Jeans** | **MHPKG，MetaHuman 参数化衣柜** | 同上，纯 MetaHuman |
| **DarkTide Studios — US Army Black Ops / SAS / WW1 系列（Metahuman Kit）** | MetaHuman 服装套件，含卖家自述的**已知穿模问题**（披风 clipping） | 纯 MetaHuman |
| **Empty Publishing — Knights 01 Peasant Modular Character** | 模块化中世纪角色，55 MB，「socket-ready」，可搭 gambeson/pants/boots/hat | **未说明骨架**；题材不符 |
| **Roumy2000 — Stylized Character System Starter Pack** | 模块化角色框架（男/女基础角色 + 可换发型/胡须/服装） | **未说明骨架**；风格化，与项目不一致 |
| **Agent Disco — MeshSkinner（Fab 插件）** | 「自动绑定 + 网格蒙皮」插件：丢静态网格、放几个 landmark、一键得到绑定好的骨骼网格，含多套求解器 | **未核验 Fab 页面/价格/UE 版本**。与「可重复裁剪/贴合管线」直接相关，**建议后续单独调研** |

### 6.3 明确无法核实的范畴（不要在别处当成结论用）

1. **任何商品的价格**（Personal / Professional 两档）——Fab 全站 403。
2. **任何商品的逐项许可标签**（Standard vs 旧 UE Marketplace License）——同上。
3. **包内资产清单的完整性**（卖家自述与实际交付是否一致）——需购买后核对。
4. **服装网格引用的骨骼列表**——决定能否直接穿到 `SK_Mannequin`，需下载后用工具查（或问卖家）。
5. **视觉质量、穿模、性能、打包体积**——按项目规则未做任何 PIE/渲染/验收。
6. **"Epic Games Content" 这一具体 Fab seller 页面的存在与内容**——未核实。
7. **UE 5.8 上这些商品的实际可运行性**——多数商品工程止于 5.6/5.7，未做任何升级测试。

---

## 7. 日期敏感性与时效

| 事项 | 时效性质 | 现在的处置 |
| --- | --- | --- |
| **调研基准日 2026-09-23** | — | 本文所有「最新」判断以此为界 |
| **Fab 限时免费轮换** | **每两周换 3 件，窗口两周**。已核实的最后一期为 2026-09-08 → **09-22**（本次调研前一天结束） | **今天（09-23）正是新一期开窗。** 新一期内容我**未能核实**（`fab.com/limited-time-free` 403）。需要人工打开该页确认，且**不要指望出现角色服装** |
| **UE 5.6 移除 MetaHuman +2cm 骨架偏移** | **永久性变更，影响所有旧鞋类资产** | 若将来买 MetaHuman 鞋类：旧偏移下做的鞋会**沉到地面以下**，必须确认作者已适配 5.6+ |
| **UE 5.8 很新（本项目 5.8.2）** | 商品工程的版本普遍滞后 | **优先买含 FBX/源文件的商品**，把「版本兼容」变成「自己重导」，而不是等卖家更新 |
| **MetaHuman 服装系统仍在演进** | 卖家（Davlet、Polyphoria）均声明会随版本适配 | 为 MetaHuman 衣柜采购的资产**有返工风险**；这是不选方向乙的又一理由 |
| **旧 UE Marketplace License 正在被 Epic 淘汰** | 迁移期商品可能仍挂旧许可 | 采购时看商品页 Details 区，别假设 |
| **Fab 的 Personal/Professional 门槛按「购买时点」判定** | 12 个月内数字内容行业总收入是否超过 10 万美元 | 判断依据是**下单那一刻**的状态 |

---

## 8. 风险与法务注意

### 8.1 Fab Standard License 的商业使用边界（A 级规则 + B 级条文转述）

**规则（Epic 官方文档，[Licenses and Pricing in Fab](https://dev.epicgames.com/documentation/fab/licenses-and-pricing-in-fab?lang=en-US)）**：

- Fab 只有两种许可：**CC-BY（免费）** 与 **Standard（免费或付费）**。
- **Standard 分 Personal 与 Professional 两档**，卖家**必须同时提供两档**，价格可同可不同。买家按**过去 12 个月的商业活动总收入**选择：
  - **Personal**：未超过 **$100,000 USD**
  - **Professional**：超过 **$100,000 USD**
- 迁移自旧 UE Marketplace 的商品**可能临时仍适用旧 UE Marketplace License**，会在商品页 Details 区标注；**Epic 正在淘汰该许可，新商品不能再以此上架**。
- 价格由卖家在**预设价位档**里选（全部以 .99 结尾，$0.00 除外），以美元为基准价，部分地区另加 VAT。
- 附带 **NoAI 元标签**：标记为禁止用于生成式 AI 数据采集的资产**不能**用 CC-BY 发布，必须是 Standard 许可。

**商业使用边界（论坛用户引述 EULA 原文，B 级，非我直接核验 EULA 页面）**：

- **允许**：把内容作为组成部分**发布软件应用（例如电子游戏）**给最终用户，直接发行或经发行商；也允许在宣传材料中使用。**Standard 许可允许商业使用，Personal / Professional 只是收入档位，许可文本相同。**
- **禁止**：**以「独立形态」再分发/转售内容**（项目必须「合理地提供超出内容本身的价值」，内容只能是项目的组件而非主要卖点）；不得让第三方把内容并入其自有产品或可导出内容的编辑器/模板；不得逆向工程。
- **协作**：可以私下把内容共享给**同一项目的协作者**（员工/关联方/承包商），协作者不得再分发，协作结束后须删除。
- **插件**另有席位（seat）限制。

> 这些条文来自论坛用户的引述与整理（含一句明确声明「no legal advice」），**不是我的法律结论**。正式采购前应以 [Fab EULA](https://www.fab.com/eula) 原文为准（该页我打不开）。

### 8.2 ⚠️ 盗版镜像站警告（本次调研的实证发现）

搜索「UE 资产名 + 价格」时，会命中 **`uecandy.com`** 这类站点。我已实测其页面：它把 Fab/旧商城的商品（含图片、描述、更新记录甚至买家评论）整站镜像，**以极低折扣「出售」**，页面自带一句 *"Do not use this product in a commercial project without obtaining a license!"* 并回链到 Fab 原作。

- **这是未授权分发站，不是商店。** 从其获得资产**不构成任何许可**，商用会直接违反 Fab 许可条款，且无法回溯来源。
- 本次调研中它意外提供了一个 listing ID（Polyphoria 的官方 Fab 链接），但**我未把它的任何价格/描述当作验证来源**——第 2 节的 Polyphoria 结论全部来自该卖家的 Epic 论坛原帖。
- **处置**：采购一律走 fab.com（或在 UE 编辑器内 Add to Project）。不要用镜像站做价格参考，它的价格与 Fab 现价无关。

### 8.3 待确认的法务项（对本项目尤其关键）

**「Manny 人体模型本身能否随商业游戏发行」——本次未能确认。**

- 项目**玩家角色就是 `SKM_Manny_Simple`**，所以这不是学术问题。
- 我找到的相关社区回答称：UE 的 Game Animation Sample（GASP）等 learning/sample 内容可按 **Epic Content EULA** 商业使用，并给出链接 `unrealengine.com/eula/content`。但：
  - 该回答**来自普通社区用户，非 Epic 员工**；
  - **`unrealengine.com/eula/content` 在我这里返回 403**，我**没有读到 EULA 原文**；
  - 另一条（2023 年）社区说法恰好相反：*「…but not the mannequin models themselves (including Manny and Quinn) as part of your final product」*。
- **两种说法冲突，我无法判定。** 建议：在继续投入服装管线前，**由用户或法务直接阅读 Epic Content EULA 原文确认**。这是一条低成本、高影响的前置检查。本文**不对此下结论**。

---

## 9. 引用来源清单

**Epic 官方文档（A 级）**

- [Hair and Clothing Tools（MetaHuman 5.8）](https://dev.epicgames.com/documentation/metahuman/hair-and-clothing-tools?application_version=5.8&lang=en-US) — 衣柜/槽位/Prepare/校验/自定义条目
- [Asset Format and Structure Requirements For MetaHumans on Fab](https://dev.epicgames.com/documentation/metahuman/asset-format-and-structure-requirements-for-metahumans-on-fab?application_version=5.6) — **Skeletal Clothing 必须用 MetaHuman base skeleton**
- [Tailoring Your Own Wardrobe Items](https://dev.epicgames.com/documentation/metahuman/tailoring-your-own-wardrobe-items?application_version=5.7) — `.mhpkg` 导入流程、Fab MetaHuman 频道
- [Retargeting Animation Blueprints to MetaHumans](https://dev.epicgames.com/documentation/metahuman/retargeting-animation-blueprints-to-metahumans-in-unreal-engine?application_version=5.6) — Quinn→MetaHuman 重定向与 Master Pose 改造
- [MetaHuman 5.8 Release Notes](https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine?application_version=5.8&lang=en-US) — Crowds、Mesh-to-MetaHuman、Unbaked Textures、MetaHumanGenerator MCP Toolset
- [Creating Parametric Clothing for Fab](https://dev.epicgames.com/documentation/unreal-engine/creating-parametric-clothing-for-fab?application_version=5.6) — Chaos Outfit 制作链
- [Licenses and Pricing in Fab](https://dev.epicgames.com/documentation/fab/licenses-and-pricing-in-fab?lang=en-US) — 许可类型、Personal/Professional 门槛、价位档、NoAI
- [Free Epic Games Content for Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/free-epic-games-content-for-unreal-engine?application_version=5.6) — Epic 免费内容（Paragon / Infinity Blade）

**Epic 开发者社区论坛产品帖（B 级，卖家发布）**

- Davlet Sci-Fi Clothing Pack 01–04 Mega Bundle：[topic 2687694](https://unreal2.epic-prod-us2.discourse.cloud/t/davlet-sci-fi-clothing-pack-01-04-mega-bundle/2687694)
- Lumelle Studio Short Sleeve Hoodie 01：[topic 2699929](https://unreal2.epic-prod-us2.discourse.cloud/t/lumelle-studio-short-sleeve-hoodie-01-rigged-parametric-variable-retopology/2699929)
- Polyphoria Fantasy Armour (Metahuman)：[topic 2426426](https://unreal2.epic-prod-us2.discourse.cloud/t/polyphoria-fantasy-armour-caster-mage-sorcerer-wizard-metahuman/2426426)
- Yusuf Y.Y LE_Characters_Pack：[topic 2714501](https://unreal2.epic-prod-us2.discourse.cloud/t/yusuf-y-y-le-characters-pack/2714501)
- Fab Limited-Time Free Content（Epic 员工公告）：[topic 2738884](https://unreal2.epic-prod-us2.discourse.cloud/t/fab-limited-time-free-content/2738884)
- Fab Standard License 商用讨论（含 EULA 条文引述）：[topic 2080626](https://unreal2.epic-prod-us2.discourse.cloud/t/all-free-assets-including-ue-ones-are-now-standard-license-on-fab-meaning-no-commercial-use/2080626)
- Manny/Quinn 商用问题（结论未核验）：[topic 2252927](https://unreal2.epic-prod-us2.discourse.cloud/t/can-i-use-uefn-mannuquinn-in-my-commercial-game/2252927)

**未能取回（403）**

- `www.fab.com` 全部商品页、频道页、搜索 API、EULA
- `www.unrealengine.com/marketplace/...` 与 `www.unrealengine.com/eula/content`
- `gamedev.net` 2026 年 9 月免费资产汇总（Cloudflare 拦截）

---

## 附：本文与姊妹文档的分工

| 问题 | 归属文档 |
| --- | --- |
| 引擎里怎么把衣服贴合/裁剪到不同体型（Chaos Outfit Asset、Mutable、MeshResizing、源码级证据） | [clothing-system-research-engine.md](clothing-system-research-engine.md) |
| 市场上能买到什么、骨架对不对、许可能不能商用、值不值得买 | **本文** |
| 开源工具链（GitHub） | `clothing-fitting-research-github.md`（另行交付） |
| 最终方向选择（留 Manny / 换 MetaHuman / 混合） | 三份报告合并后由用户拍板 |
