# 双弓与锻钢双手剑开发及恢复记录

## 正式内容

- **双弓**　高地长弓「观峰」3–6 倍镜的滚轮变倍、固定准星及共用瞄准灵敏度。双弓箭矢和山鸣的附加箭使用有效射程、射程外下坠与伤害衰减，箭矢荧光用于看清落点。山鸣保留原有装备 ID、弦影箭与三段雪山累计，弦身使用光束模型。见[弓的制作与恢复清单](Bow/)。
- **锻钢双手剑**　F6 物品、通用改造、五种原厂图标，以及镂空、处刑两款剑身，环链、鱼尾两款配重。处刑使用宽根、尖锋和配套护手。鱼尾采用攻击版「乘隙」。环链的点按为普攻，长按蓄满松开改为横扫。普通重击沿剑刃轨迹取目标，横扫覆盖身前 180°；两者基础距离均为 3.6 米。见[双手剑的制作与恢复清单](Sword/)。
- **钢材、握柄与符文**　[全武器钢材及旋风配对](../SharedTwoHandMaterials20261122/README.md)记录 11 月 22 日最新的 52 个包。刀身符文沿原遮罩流动；预览对真正的皮革材质槽补光。星陨天枢与双曜星环使用各自原来的 PBR 纹理和制作配方，包含旋风变体。见[符文、护手及原厂图标的版本指纹](appearance-recovery.json)。

## 恢复入口

11 月 22 日后续修订涵盖四张专属改造卡与三张共用握把材质。恢复这七项时使用[本版文件、图标键、材质用法和 SHA-256](F:/FPSGAMEData/ArtProduction/ForgedSteelGreatsword/WorkbenchAppearance20261122/published.json)。原厂五图继续使用本目录的历史指纹。

正式工程从 `D:/FPS3D/FPSGAME` 打开，资产位于 `F:/FPSGAMEData/Content`，游戏内使用原 `/Game/...` 路径。Git 收录可公开的脚本、配置、源码、版本清单和共享文件的定向补丁。Meshy 原模型、正式 UE 二进制及其依赖由本机资产库提供。取回旧版本时先用条目里的包名与 SHA-256 对照，再按该条目的顺序恢复。

11 月 21 日抢救留下的 `F:/FPSGAME-Recovery-Work-20261120/ForgedSteelThread20261121` 下有 `Bows-recovered.zip`、`ForgedSteelGreatsword-recovered.zip` 及 `recovered-entries.json`。这些压缩包用于找回当时的输入；后续的光束弦、宽根尖锋、鱼尾攻击特性与 11 月 22 日钢材分别以各自最新发布回执为准。锻钢三视图的定稿是 `SourceAssets/ForgedSteelGreatsword20261120/ReferenceV4/ForgedSteelGreatsword_V4_ThreeViews.png`。

## 联机与画面记录

11 月 21 日的正式工程使用独立进程运行监听主机、客机和重连。双弓飞行和观峰各覆盖每端 60 ms 延迟、5% 模拟丢包。剑的回执记录了出手后换装、破韧判定、逐目标去重、环链横扫和重连。观峰在 1600×900 离屏使用真实滚轮事件，14 个镜内景物特征点测得 6 倍 / 3 倍的尺度比为 2.00211，准星横向跨度在两端均为 86 像素。材质批次另有进程内观察者绑定记录。公网、独立服务器及第三台远端旁观机仍待实机覆盖。

本机历史回执位于 `F:/FPSGAMEData/ArtReviews/ForgedSteelGreatsword/ConversationNetwork20261121/summary.json` 和 `F:/FPSGAMEData/ArtProduction/BowOptics/ConversationNet20261121/review.json`。这次归档复核了发布内容和归档文件。开发期结果以上述原回执为准。

## 本机归档

- 早期弓、双手剑、握柄与符文的检测图、废案、日志和制作宿主可从 [D/F 原路径与归档路径逐件对照](F:/FPSGAMEData/trash/BowSwordConversation-20261122/inventory.json) 找回。旧回执中的相对截图路径也可按原绝对路径查询这份索引。
- 三视图、旧原厂图标等 12 个生成缓存位于[设计稿缓存清单](F:/FPSGAMEData/trash/BowSwordConversation-20261122-ImageDrafts/cleanup-manifest.json)。保留的新版原厂母图、确认版三视图与定形的镂空剑身稿由对应制作源管理。
- 11 月 22 日的材质检测图和临时制作宿主见[材质归档清单](F:/FPSGAMEData/trash/SharedTwoHandMaterials-20261122/cleanup-manifest.json)。Git 临时发布目录的移动记录位于 `F:/FPSGAMEData/trash/BowSwordConversation-20261122-Publication/cleanup-manifest.json`。
