# 所有场景容器保留实体打开形态 V3

用户要求所有容器都带活动部位。本次将此前直接搜寻的 6 个书架改为下部抽拉储物盒，
使员工生活区当前四类搜寻容器都有实体开启动作：

| 类型 | 活动部位 | 打开后形态 |
| --- | --- | --- |
| 员工储物柜 | 侧铰链柜门 | 打开约 100° 并保持 |
| 员工书柜 | 下部门板 | 打开约 100° 并保持 |
| 员工书架 | 下部储物盒 | 向前拉出 32cm 并保持 |
| 床头柜 | 木质抽屉 | 向前拉出 29cm 并保持 |

书架保留上部三层书籍和金属框架，下部设置独立箱体、侧板、背板、底板、装饰前板与把手，
固定框体和箱体两侧各有导轨。原下层书籍移入箱内，随箱体一起移动，打开时露出实际内腔。
独立柜体和储物盒网格分别保留 UCX 结构碰撞；可动部件使用 Movable 和 BlockAllDynamic。
新网格沿用 V2 的木材、涂漆金属、书籍纸张及封面材质，无新增外部素材。

`AColdSteelSceneContainer::TrySearch` 删除直接打开面板的 OpenShelf 分支，并要求实际可动网格。
旧枚举值只用于保留旧资产序列化兼容；若它带有真实部件则走抽拉动画。
首次按 E 变黄色、播放 0.55 秒开启动作，完成后打开原宝箱取物界面；关界面及重复查看不闭合。
运动结束即关闭 Tick，仍按本次关卡访问维持搜寻和开启状态，奖励继续留空。

宿舍独立图及组合图分别替换 6 个书架 Actor 的部件和运动参数；其他容器、稳定身份、
四套随机布局、床位、墙面、床品、地毯及其他主题保持当前制作。
书架拉出方向沿原朝向指向室内；沿用原墙边净距及位置，抽拉行程没有扩大为书柜门的整段扫掠。
该安排属于按尺寸制作，本次未执行穿模/碰撞验收。

## 产物与入口

- 资产：`/Game/Dungeons/StaffLiving20261002/ContainerOpenPartsV3/Meshes`
- 新网格：`SM_Dorm_BookshelfBody_V3`、`SM_Dorm_BookshelfStorageBox_V3`
- 当前完整源：`SourceAssets/DungeonStaffLiving20261002/ContainerOpenPartsV3/Authored/StaffLivingTheme_ContainerOpenPartsV3.blend`
- 作者：`Scripts/author_container_open_parts_v3.py`
- 导入：`Scripts/import_container_open_parts_background_v3.ps1`
- 保存回执：`ContainerOpenPartsV3/install.json`；地图及配置备份：`ContainerOpenPartsV3/Backups`

```text
open /Game/GameMaps/Design/L_StaffLiving_Theme_Subject
```

对应独立图为 `/Game/GameMaps/Design/L_StaffDormitory_Subject`，返回主场景为
`open /Game/GameMaps/DayNight_Lighting`。常用作者、导入及摆放入口已采用 V3 源。
模块草稿同样记录新的储物盒及抽拉行程，正式随机地牢池仍未注册。
本次只后台制作、必要编译、导入和保存，未运行游戏、截图、渲染或测试。

实际交付：Editor 和 Game 的 Win64 Development 目标均构建成功；后台导入退出码 0，
两份新网格及两张地图已保存，`install.json` 阶段为 `samples_saved`。构建与制作记录见
`ContainerOpenPartsV3/completion.json`。这仅记录制作/保存，不表示已运行开启动作或测试通过。
