# 宿舍家具与布局变化 V2

员工生活区样板增加三类容器：6 个员工书柜、6 个开放式书架、12 个床头柜。
当前书架已按后续用户要求增加实体抽拉储物盒，以下 V2 的直接搜寻描述仅为历史；
当前实现见 `staff-container-open-parts-20261002.md`。
加上宿舍原有 12 个储物柜，共 36 个宿舍搜寻容器；组合图连同更衣区储物柜共 60 个。
这些容器复用已有绿色/黄色轮廓、E 提示和宝箱取物会话，奖励仍留空。

## 家具

| 家具 | 尺寸 | 构造和交互 |
| --- | --- | --- |
| 书柜 | 96 × 40 × 198cm | 涂漆框体、木质层板、上部书籍，下部独立木门沿真实铰链打开并保持开启 |
| 开放书架 | 88 × 34 × 184cm | 金属立柱、背部交叉拉杆、木板、直立和叠放的书籍；E 直接搜寻，无虚构门动画 |
| 床头柜 | 52 × 42 × 64cm | 实体桌面、侧背板、支脚、下部开放层，抽屉向前拉出 29cm 并保持打开 |

书籍有独立封面、书脊装饰、纸页块与页边细线，采用三种封面颜色。
木材、金属、涂漆及橡胶复用工程内现有材质，书籍的纸张/封面材质在本批命名空间保存。
家具、柜门、抽屉使用与结构对应的 UCX 简单碰撞，不用整块封死开放空间。

## 六间宿舍的随机布局

`AStaffDormitoryLayout` 在关卡进入时从四套尺寸化布局中为六间宿舍分别选择一次。
采用打乱的布局袋，前四间不会选到同一套，相邻选择也避免重复。
随机种子默认 -1；指定非负 `RandomSeed` 可复现选择。作者预览固定种子为 20261002。

变化包括：储物柜组在西/东墙之间交换，书柜和开放书架按计划分布在两侧，书桌沿后墙偏移。
床头柜在两张床的床头附近；所有床铺维持原有位置、朝向及布品款式，不参与运行时随机移动。
原有宿舍书桌/椅子静态实例移出批处理，连同柜子共 48 件家具由布局管理器显式引用。

墙边柜按「墙内表面 + 至少 3.5cm 净距 + 柜体半深度」定位，保持贴墙方向；
随机偏移仅沿墙面，在作者允许的 3.5cm 范围内取值。书桌沿后墙，椅子朝向桌面。
书柜/储物柜集中在卧室入口两侧，保持中间门洞和房间中央通行；书柜开门空间、床头柜抽屉行程
包含在布局位置安排中。床头柜贴近床头，因此不强行拉到远离床铺的后墙。
这属于按尺寸制作的安排，不是已运行的穿模/碰撞验收。

布局 JSON 随地图保存，不在游戏中读磁盘；只在 BeginPlay 解析和摆放一次，没有布局 Tick。
可变化家具设置为 Movable，以便这次摆放生效；后续位置固定。家具搜寻状态及独立容器身份不因布局改变。
更衣淋浴区和活动区不新增随机摆放。

## 交付入口

- `/Game/GameMaps/Design/L_StaffDormitory_Subject`
- `/Game/GameMaps/Design/L_StaffLiving_Theme_Subject`
- 资产：`/Game/Dungeons/StaffLiving20261002/DormitoryVariantsV2`
- 完整源：`SourceAssets/DungeonStaffLiving20261002/DormitoryVariantsV2/Authored/StaffLivingTheme_DormitoryVariantsV2.blend`
- 作者：`Scripts/author_dormitory_variants_v2.py` 与 `Scripts/dormitory_layout_variants.py`
- 导入：`Scripts/import_dormitory_variants_background_v2.ps1`
- 保存回执：`DormitoryVariantsV2/install.json`，历史地图/配置备份：`DormitoryVariantsV2/Backups`

保留原有完整瓷砖、床品、地毯、公告、供排水和更衣区容器。
草稿模块记录 `layout_variants`、`variable_static_furniture` 与动态容器；仍没有注册到正式随机地牢池。
后台制作、构建及资产保存情况记录在本批 `completion.json`，未主动运行游戏、截图、渲染或测试。

本次实际保存：五份网格、四份书籍材质和两张地图完成后台导入，退出码 0；`install.json` 为
`samples_saved`，每图由管理器引用 48 件可变化家具。Editor 目标构建成功。
Game 目标的本次场景代码已编译，但完整构建被 `MonsterCombatComponent.cpp` 对
`ABlindSupplicantMonster::CanAttackTarget/PrepareAttack/CombatStoppingRange` 的接口错误阻塞。
保留这批并行怪物修改，未改动它们或以旧文件替换。该 Game 构建失败记录不影响已经保存的样板资产，
也不代表已经运行样板。待项目怪物接口开发完成后再构建 Game 目标。
