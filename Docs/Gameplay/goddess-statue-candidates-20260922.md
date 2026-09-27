# 女神石像 Sketchfab 备选（2026-09-22）

> **结果（2026-09-22）**：用户选定**备选 2 Diana（noe-3d.at）**，已完成下载、归一化、UE 导入与地牢摆放。
> 接入记录见 [女神石像接入](goddess-statue-integration-20260922.md)，案例目录 `SourceAssets/DungeonGoddessStatue20260922`。
> 下文保留检索与筛选过程。

## 1. 需求来源

| 项 | 内容 | 出处 |
| --- | --- | --- |
| 用途 | 地牢事件道具 F2「女神像」，事件①增益／治疗 | [房间资产清单](dungeon-room-asset-list-20260920.md) 第 100 行 |
| 参考风格 | 写实石像，可参考 Roman 柱族风格 | 同上 |
| 场地 | 遗迹事件室 16×16 m，净高 3.8 m；工业包围下的石构破口、加固梁柱 | [工业向美术方向](dungeon-art-direction-industrial-v1-20260920.md) |
| 前置状态 | `DungeonProps20260920/goddess_statue` 等 11 类 5080 生成资产已整批否决退役 | [5080 生成物品整批废案](dungeon-5080-retirement-20260922.md) |

结论：需要一个**真写实、可商用、能直接接进 UE 的女神全身石像**，替换已退役的生成版。

## 2. 筛选口径

1. **真扫描／写实**：作者描述可追溯到博物馆、文保机构或明确摄影测量流程；**排除 AI 生成**（自述 `Meshy`、`AI-assisted`、`generative` 的一律不用，避免重演 5080 生成资产被判不合格的问题）。
2. **授权**：只要 CC-BY 或 CC0（可商用 + 署名）；CC-BY-NC / NC-SA / NC-ND 全部排除。
3. **可下载**：Sketchfab `Downloadable = true`。
4. **主体**：女性神祇全身像优先，属性可读（弓、权杖、命运之轮）；残缺与风化可接受，且与埋藏遗迹方向一致。
5. **预算**：≤ 约 500k 三角面、贴图套数少，Nanite 直用或常规 LOD 都能接。

检索方式：Sketchfab 公开 Data API v3（`/v3/search`、`/v3/models/{uid}`），共扫描 12 组检索词 + 16 个女神名 + 授权过滤，去重后 200 余条，逐条核对授权、面数、贴图与描述来源，并对入围件下载多角度预览实际看图。

## 3. 三个备选

### 备选 1（首选）｜Venus de Milo — urbandave

| 项 | 值 |
| --- | --- |
| 链接 | https://sketchfab.com/3d-models/venus-de-milo-dcd6110a7be14cab861c7ee187b9061c |
| 三角面 / 顶点 | 382,476 / 191,252 |
| 贴图套数 | 1 |
| 授权 | CC Attribution（可商用，需署名） |
| 来源 | 2022 年 7 月于巴黎卢浮宫拍摄的摄影测量扫描（真品扫描，非重建、非 AI） |
| 热度 | 2,998 浏览 / 18 赞 |

**为什么合适**：全世界辨识度最高的女神石像，任何玩家一眼就认得出这是「女神像」，事件锚点几乎不需要额外引导。断臂与风化本身就是真品状态，直接契合遗迹埋藏方向；正立面清晰、轮廓在 3.8 m 净高房间里读数好。贴图只有 1 套，材质改造（做青苔、积尘、局部破损）成本低。

**风险**：名气过大，可能显得"太现成"；真品高 2.02 m，导入后需核对实际比例。

### 备选 2｜Diana — noe-3d.at

| 项 | 值 |
| --- | --- |
| 链接 | https://sketchfab.com/3d-models/diana-ea77e1d0442244aeb3d558a08ccdfc1a |
| 三角面 / 顶点 | 500,726 / 251,498 |
| 贴图套数 | 1 |
| 授权 | CC Attribution（可商用，需署名） |
| 来源 | 奥地利 Waldreichs 城堡入口处狩猎女神狄安娜像的摄影测量扫描；作者为专业文保扫描团队 noe-3d.at |
| 热度 | 5,410 浏览 / **163 赞**（本批候选里社区验证度最高） |

**为什么合适**：完整的神庙式构图——女神 + 弓 + 背后箭袋 + 脚边猎犬 + 一体式基座，作为事件房焦点比单独立像更有"祭坛"感。石质表面与风化层次是所有候选里最扎实的，远中近景都成立。作者机构长期做文物扫描，质量可信。

**风险**：501k 面是全批最重的一档（Nanite 可用，常规 LOD 需重建）；贴图仅 1 套，分辨率需在下载页确认。

### 备选 3｜Statuette of Nemesis — Opus Poly

| 项 | 值 |
| --- | --- |
| 链接 | https://sketchfab.com/3d-models/statuette-of-nemesis-0475bf9619084670b41b9a8475506d32 |
| 三角面 / 顶点 | 62,608 / 31,296 |
| 贴图套数 | **5** |
| 授权 | CC Attribution（可商用，需署名） |
| 来源 | 盖蒂别墅（Getty Villa）报应女神涅墨西斯像；女神右脚踏在被征服者身上，左手持命运之轮 |
| 热度 | 930 浏览 / 30 赞 |

**为什么合适**：全批最省性能的可用女神像——63k 面却有 5 套贴图，多实例摆放、低配档和 LOD 链都毫无压力。属性叙事强（命运之轮 + 脚踏罪人），很适合做成"祈祷／献祭"类交互事件的识别符号。米黄色石质，做旧与破损改造的余地大。

**风险**：尺寸是小雕像（非真人等高），需按目标高度放大；细节密度低于前两件，特写会露怯。

## 4. 三选对比

| 维度 | 1 Venus de Milo | 2 Diana | 3 Nemesis |
| --- | --- | --- | --- |
| 辨识度 | ★★★ 最高 | ★★☆ | ★★☆ |
| 写实扫描质量 | ★★★ | ★★★ | ★★☆ |
| 遗迹契合度（残缺风化） | ★★★ 天然断臂 | ★★★ | ★★☆ |
| 性能（面数） | 382k | 501k | **63k** |
| 贴图套数 | 1 | 1 | **5** |
| 构图完整度（含基座／属性） | ★★☆ | ★★★ | ★★☆ |
| 授权 | CC-BY | CC-BY | CC-BY |
| 适合定位 | 事件主像 | 祭坛焦点 | 多实例／轻量档 |

## 5. 备用池（三选都不合时）

| 件 | 面数 | 贴图 | 授权 | 说明 |
| --- | --- | --- | --- | --- |
| [Venus Verticordia（菲茨威廉博物馆）](https://sketchfab.com/3d-models/venus-verticordia-2f551fe5aa6346878834805787d1dbdf) | 500,000 | 1 | CC-BY | John Gibson 1833–38 年大理石维纳斯，博物馆级扫描，201 赞 |
| [Caryatid（3Dystopia）](https://sketchfab.com/3d-models/caryatid-ancient-greece-collection-fc0ac58d0ab14c3a939da89063f8f57e) | 452,518 | 2 | CC-BY | 女像柱，字面对应"Roman 柱族风格"，可兼作柱式神龛；背面为作者补形 |
| [Photogrammetry - Female colossal head : Junon](https://sketchfab.com/3d-models/photogrammetry-female-colossal-head-junon-1be27eeae21d43a1a6ee0b4bbcc73a15) | 303,028 | 1 | CC-BY | 公元 1 世纪塔索斯大理石朱诺巨像头，风化与地衣最重，最适合做被掩埋的巨像残件 |
| [Diana the Huntress](https://sketchfab.com/3d-models/diana-the-huntress-2d0ac3c9a7e84ad1b85908742614fad0) | 343,291 | 1 | CC-BY | 1760 年 Lytham Hall 园林雕像，含猎犬 |
| [Pergamene Cybele](https://sketchfab.com/3d-models/pergamene-cybele-5c2bf78512324c8aa1205dfe66b44631) | 54,511 | 4 | CC-BY | 母亲神库柏勒，古风偶像感强、面数低 |
| [Statue of Mary Magdalene](https://sketchfab.com/3d-models/statue-of-mary-magdalene-69071d2b9b3c4263893b8e9a82d7bdc7) | 35,862 | 2 | CC-BY | 全批最轻的立姿长袍女性像；题材为基督教圣像，非古典神祇 |

## 6. 已排除（含原因）

- **AI 生成**：`Venus de Milo` by chrissayer（描述自述 AI-assisted reconstruction）、`Empress Livia as the goddess Ceres` by gustavo.rfaria17（自述用 Meshy 生成）——与刚退役的 5080 生成路线同类，不进入候选。
- **非商用授权整批排除**（可看不可用）：Geoffrey Marchal 的 `Goddess`／`Athena Lemnia`／`Wounded Amazon`／`Nike Samothrace`、noe-3d.at 的 `Flora`／`Hygieia`／`Muse`／`Vestalin`／`Ceres`、Ancient World 3D 的 `Aphrodite Kallipygos`／`Knidos`／`Townley`、大英博物馆 `Statue of a woman`、STUDIO DUCKBILL `Fountain of Benzaiten` 等。
- **主体不可辨识／只剩碎片**：`Draped Female Statue Delos`、`Small Statue of Artemis, Delos`、`Torso of Aphrodisias`、`Estàtua de Ceres`（无头无臂躯干）、`Broken Basalt Statue of Aphrodite`。
- **非石像或非女神**：Green Tara（坐佛，CC0）、Goddess Isis（青铜）、各类 Athena 猫头鹰与狮像。

## 7. 接入注意（选定后再做）

- 三件均为静态网格、无骨骼无动画，可直接走 `asset-model-workflow` 的导入路径。
- 导入后**必须核对真实尺寸**并按 ~2.0 m 目标高度缩放（Nemesis 是小雕像，缩放幅度最大）。
- 碰撞：按静态复合碰撞处理，基座与地面接触关系需与埋藏土石对齐。
- 材质：保留原扫描漫反射作为底色，再按项目规范叠加风化／积尘／苔痕；不要直接把原始扫描材质当最终材质。
- **署名**：三件均为 CC-BY，正式接入时把作者与链接写入 `ThirdPartyNotices`。

## 8. 检索记录与预览

- 对照图（此处为三选并排，多角度）：`D:\FPS3D\_sketchfab_goddess\picks.jpg`
- 全候选缩略图对比：`sheet1.jpg`、`sheet2.jpg`、`sheet3.jpg`
- 决赛圈多角度：`final_A.jpg`、`final_B.jpg`、`final_C.jpg`
- 原始检索数据：`_sketchfab_goddess\details.csv`、`finalists.csv`、`_sketchfab_goddess\goddess_names.csv`
- 以上均为检索工作产物，未放进仓库，也未下载任何模型本体；模型需登录 Sketchfab 免费账号在各自页面下载（可选 glTF／FBX／OBJ 等转换格式）。

本轮只做检索与看图筛选，未下载模型、未导入 UE、未做验收；最终选用由用户决定。
