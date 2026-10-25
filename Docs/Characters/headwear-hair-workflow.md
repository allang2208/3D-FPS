# 头饰与发型可见性

## 2026-10-24 排查与修复

女性角色佩戴 ST6 贝雷帽后长发消失。实际原因是 `head_equipment` 的 `covers_scalp_hair=true`：`FPSPlayerHeadEquipment.cpp` 读取该值，`FPSPlayerBodyAppearance.cpp::UpdateAppearanceVisibility` 将全部带 `HeadScalpHair` 标记的 Groom 隐藏。这个字段没有局部裁切含义，也不是短发替换；眉毛、睫毛和头部网格仍显示。

按物品目录 `equipSlot=helmet` 枚举现有五件，再逐一核对 Jason 与 Kaitlin 两套独立配置。所有装备都通过 `FPSPlayerBodyEquipment.cpp` 的实际头部装备槽进入同一 `UpdateHeadEquipment` 分支；没有另一套衣物网格帽子遗漏。

| 头饰 | 修复前 Jason / Kaitlin | 当前 Jason / Kaitlin | 处理 |
| --- | --- | --- | --- |
| ST6 酒红贝雷帽 | true / true | false / false | 保留所选发型和帽外长发 |
| 野行奔尼帽 | true / true | false / false | 保留鬓角、耳后及后颈头发 |
| 野行翎羽帽 | true / true | false / false | 保留帽外头发 |
| 蓝色尖顶法师帽 | true / true | false / false | 保留帽檐外长发 |
| 灰钢闭面盔 | true / true | true / true | 维持封闭式头盔的整束遮盖 |

本次只按字段事务修改八个 `covers_scalp_hair` 叶字段。发型选择、原生 Groom 及绑定、LOD 映射、模拟参数、头型、帽子网格和挂接变换保持原值。配置检查覆盖五件 × 两种身体；未启动游戏、截图或进行动态穿戴验收，不能由可见性配置推断帽内发丝已无穿模。

## 后续制作规则

- 露出鬓角、耳后、后颈或发尾的帽子使用 `covers_scalp_hair=false`。头顶被帽冠覆盖不等于可以隐藏整套发型。
- `true` 仅用于需要完整隐藏头发的封闭头盔。不能拿整束隐藏解决露发帽的局部穿模，也不能强制替换玩家所选发型。
- 如实际画面仍有帽冠穿发，应针对具体头型、发型和帽口制作局部适配，保留帽外头发及原生绑定；本字段不提供局部裁切能力。
- 男女角色配置分别检查。女性拟合产物保留专用变换，但发布时毛发可见性从当前对应头饰规则取得，避免旧拟合快照带回错误值。
- 原有四款帽子的发布入口，以及工装套装的奔尼帽发布入口，均已改为保留发型。新增帽子按实际覆盖类型设置该字段，再纳入逐项清单。

修复与清单入口：`Tools/PlayerBody/repair_open_hat_hair.py`。本轮回执：`SourceAssets/HeadwearHair20261024/audit-and-publication.json`；包含十行前后值与共享配置写入回执。它检查配置和路由，不代替游戏视觉验收。

配置由 `FPSPlayerBodyComponent::BeginPlay` 读取。已运行角色保留其内存配置；重新进入游戏创建角色后使用修复值，无需重新导入模型或编译 C++。

## 新增炭灰运动帽

2026-10-24 后续新增 `ue_charcoal_sports_cap`（炭灰运动帽）：Jason／Kaitlin 分别使用独立佩戴网格与挂接变换，两份配方均 `covers_scalp_hair=false`。发布脚本为 `Tools/SportsCap/publish.py`，实际资产及配置已保存；该款已加入检查脚本的露发帽清单。上方十行矩阵记录的是首次五款头饰排查，本次没有重跑整批检查或游戏验收。
