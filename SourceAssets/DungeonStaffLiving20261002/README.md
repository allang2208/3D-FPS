# 员工生活区主题样板

用户指定顺序：**生活宿舍区 → 员工更衣淋浴区 → 员工活动区**。

三间独立作者模块，以及按同一顺序连接的完整主题样板。新资产统一保存在
`/Game/Dungeons/StaffLiving20261002`。用户认可 V7 后已加入正式随机池；
当前入口为 `/Game/GameMaps/L_Dungeon_Randomized`，详细记录见末尾生产接入部分。
下列样板进入命令与各轮制作记录为历史内容，样板完成正式接入后归档。

## 进入方式

完整主题：

```text
open /Game/GameMaps/Design/L_StaffLiving_Theme_Subject
```

独立房间：

```text
open /Game/GameMaps/Design/L_StaffDormitory_Subject
open /Game/GameMaps/Design/L_StaffChangingShowers_Subject
open /Game/GameMaps/Design/L_StaffRecreation_Subject
```

返回：

```text
open /Game/GameMaps/DayNight_Lighting
```

这些命令用于本机开发内容；没有新增祭坛菜单或临时打包清单。用户负责试玩；制作过程不启动游戏、PIE或验收渲染。

## 作者入口

1. `Scripts/prepare_design.py`：三间房的尺寸、家具、端口、灯光与连贯样板位置。
2. `Scripts/author_surfaces.py`：原创织物 PBR、地胶、双语标识图集。
3. `Scripts/author_living.py`：后台 Blender 制作、FBX 导出与完整可编辑源保存。
4. `Scripts/import_background.ps1`：按现有资产批次互斥运行无界面 UE commandlet，完成真实导入与地图保存。

局部家具摆放调整可运行 `Scripts/update_source_placements.py`，它只修改本批 Blender 源内的实例，
不重新导出已有网格。导入回执允许同版本续接；不同网格版本需要明确重导方案，不能用过期回执替代实际导入。

作者源：`Authored/StaffLivingTheme_Source.blend`；网格清单：`Authored/manifest.json`。
实际安装记录：`Receipts/install.json`；配置草稿：`Config/modules-draft.json`。
草稿不启用随机生成；当前三主题生成器要求三条固定路线，后续生活主题正式接入时需单独确定主题抽选方式。

当前制作说明：[生活主题样板](../../Docs/Gameplay/dungeon-staff-living-theme-subject-20261002.md)。
最新修整：[墙内厕所、水壶与字体 V6](../../Docs/Gameplay/staff-wall-inset-typography-v6-20261002.md)。
当前源为 `WallInsetV6/Authored/StaffLivingTheme_WallInsetV6.blend`，安装回执为 `WallInsetV6/install.json`。
来源记录：[本批素材](../../ThirdPartyNotices/STAFF_LIVING_THEME_20261002.md)。

## 2026-10-02 表面与安装关系精修 V3

当前精修入口为 `Scripts/author_notices_v3.py`、`Scripts/author_refinement_v3.py` 和
`Scripts/import_refinement_background_v3.ps1`。完整可编辑制作源为
`RefinementV3/Authored/StaffLivingTheme_RefinementV3.blend`，新资源统一落在
`/Game/Dungeons/StaffLiving20261002/RefinementV3`。四张样板地图沿用原来的控制台入口。

复用认可的主神空间深蓝地毯 V2 纹理与有界视差算法，适配地牢地面高度；
复用 Hospital Bed 的床单花纹与法线，并叠加工程内的织物纤维细法线。
床铺有四种烘焙好的凌乱摆放，毛巾及洗衣篮布品也包含实体厚度、缝边和褶皱。
洗手台、镜子使用贴墙背板/挂件；供水、混水、花洒、排水管路按共同接口制作。
六处排水槽使用原有 `room_detail_geometry.grate` 格栅构造，地板与地砖在槽口处真实留空。
公告图集包含值班表、管理条款、卫生要求和活动时间，正文不再用占位线条。

实际资产与地图保存状态见 `RefinementV3/install.json`；旧地图恢复备份在
`RefinementV3/Backups`。制作不运行游戏、测试或验收渲染。
基线 `prepare_design.py` 会重建 V1 配置，后续精修应使用上述 V3 入口。

## 完整瓷砖墙面 V4

用户随后指定：整个员工生活区域取消瓷砖剥落效果。宿舍、更衣淋浴、活动区及两段连接通道
统一采用完整瓷砖墙裙，保留原有釉面、规则接缝、厚度、轻微倒角与门洞裁切。
配置项为 `wall_finish: intact`，仅本主题使用；不修改其他地牢房间的共享剥落作者。

当前完整源为 `IntactTilesV4/Authored/StaffLivingTheme_IntactTilesV4.blend`。
墙面入口为 `Scripts/staff_intact_tiles.py`、`Scripts/author_intact_tiles_v4.py`、
`Scripts/import_intact_tiles_background_v4.ps1`，保存状态见 `IntactTilesV4/install.json`。
该源继承 V3 的地毯、床品、毛巾、公告、供排水等精修。
常用作者入口及摆放更新脚本按配置修订自动选择当前源，地图控制台入口沿用原路径。

## 场景容器搜寻 V1

36 个员工储物柜（宿舍 12、更衣淋浴 24）已保存为可交互的 `ColdSteelSceneContainer`。
初始关门、绿色轮廓；按 E 搜寻后变黄，门打开并保持开启，复用地牢宝箱的取物界面。
每柜一份独立空间，奖励暂空。搜寻/门状态维持本次关卡访问，关闭面板不关门。
组合图及两个含柜独立图已后台保存，活动区独立图不改动。

当前完整源：`SearchContainersV1/Authored/StaffLivingTheme_SearchContainersV1.blend`。
作者入口：`Scripts/author_search_containers_v1.py`；导入入口：`Scripts/import_search_containers_background_v1.ps1`。
常用作者/导入/摆放入口已按 `container_interaction_revision` 选用这一版。
`Config/modules-draft.json` 的 `scene_containers` 记录动态 Actor 描述，仍未注册到正式地牢池。
制作和保存回执见 `SearchContainersV1/install.json`，构建交付记录见 `SearchContainersV1/completion.json`。
详细接口见工程 `Docs/Gameplay/scene-search-containers-20261002.md`。
后台 Editor/Game 编译与资产导入已完成；未启动游戏、截图、渲染或测试。

## 宿舍容器与布局变化 V2

新增员工书柜、开放书架、床头柜三类，共 24 个搜寻容器（6 / 6 / 12）。
书柜下部门打开后保持开启，床头柜抽屉向前拉出 29cm，开放书架直接进入搜寻面板。
沿用现有轮廓反馈、独立容器空间和宝箱界面，奖励继续留空。

六间宿舍在进入场景时从四套布局中分别选择。书桌和柜组采用有净距的墙边位置，
床头柜靠床头，床铺位置和朝向固定。布局只在进入时更新一次，管理器无 Tick。
宿舍独立图及组合图使用相同布局规则，其他两个主题不加入随机摆放。

当前完整源：`DormitoryVariantsV2/Authored/StaffLivingTheme_DormitoryVariantsV2.blend`。
作者入口：`Scripts/author_dormitory_variants_v2.py`；布局规则：`Scripts/dormitory_layout_variants.py`。
导入入口：`Scripts/import_dormitory_variants_background_v2.ps1`；常用入口自动按 `dormitory_layout_revision` 选择。
保存及构建状态见 `DormitoryVariantsV2/install.json`、`DormitoryVariantsV2/completion.json`。
详细接口见工程 `Docs/Gameplay/staff-dormitory-furniture-variants-20261002.md`。
未运行游戏、截图、渲染或测试；正式随机地牢池接入仍保持草稿阶段。

V2 本次 Editor 构建及两图后台保存完成。独立 Game 构建因 `MonsterCombatComponent.cpp`
引用尚未就绪的盲从者怪物接口而失败；场景产物已保存，相关并行怪物文件保留原状。

## 所有容器实体开启动作 V3（当前）

用户确定所有搜寻容器都有活动部位。书架的 V2 直接搜寻方案已替换为下部储物盒向前抽出 32cm，
盒内书籍随部件移动；框体、箱体、导轨、底板、前板和把手分别按结构制作。
其他容器继续使用柜门或抽屉，关闭取物界面后保持打开，所有类型仍使用原轮廓反馈和宝箱界面。

当前完整源：`ContainerOpenPartsV3/Authored/StaffLivingTheme_ContainerOpenPartsV3.blend`。
作者入口：`Scripts/author_container_open_parts_v3.py`；导入入口：`Scripts/import_container_open_parts_background_v3.ps1`。
宿舍独立图及组合图各更新六个书架，不改当前随机布局或床位。常用入口和 V2 入口按当前修订选用 V3。
保存回执：`ContainerOpenPartsV3/install.json`；构建/制作回执：`ContainerOpenPartsV3/completion.json`。
本次 Editor、Game 构建和两图后台保存均完成，先前 V2 的 Game 构建失败是历史记录。
未启动编辑器、游戏/PIE、截图、渲染或测试。


## 咖啡机与杯子精修 V7

咖啡机出杯区域改为后箱、侧板与上罩组成的真实空腔，杯子落在开缝接水格栅上。
杯身重做内壁、厚杯口、底圈与曲线把手；补萃取头、滤篮、双空心出液嘴、手柄、
蒸汽管、仪表、滚花旋钮、温杯格栅、水箱和通风槽。表面采用 V6 拉丝不锈钢与
新制机壳涂层、陶瓷釉面，替换咖啡机上原有共享锈蚀表面。

当前完整源：`CoffeePolishV7/Authored/StaffLivingTheme_CoffeePolishV7.blend`。
作者入口：`Scripts/author_coffee_polish_v7.py`；导入入口：`Scripts/import_coffee_polish_background_v7.ps1`。
只更新休息室独立图及完整主题图中的原咖啡机组合件；安装与保存状态见 `CoffeePolishV7/install.json`。
详细记录：工程 `Docs/Gameplay/staff-coffee-machine-polish-v7-20261002.md`。
没有原生源码修改，未运行游戏、测试、截图或渲染。

## 生活主题正式接入（2026-10-02）

用户已认可整体构建，当前正式模块、67 个搜寻容器装配和 Seed 家具布局已完成。
三条分支改为从四个候选主题中选三个，保留既有主题；生活主题顺序固定。
Editor、Game 构建已成功，生产地图已实际保存；回执在 `Production20261002/Receipts`。
四张生活样板已归档至 `trash/staff-living-subjects-retired-20261002`，安装回执记录 `archived`。

入口：`Production20261002/Scripts/build_native.ps1`，成功后运行同目录 `install_background.ps1`。
完成正式保存后才归档生活区样板，共用资产和最新 Blender 制作源均保留。
详细记录见 [生活主题生产接入](../../Docs/Gameplay/dungeon-staff-living-production-20261002.md)。
车站线路样板已保存，见 [进入命令](../../Docs/Gameplay/dungeon-station-line-subject-20261002.md)。

## 员工活动室厕所宝箱（2026-10-03）

正式 `StaffRecreation` 模块的原东北墙内厕所新增一个标准地牢宝箱，位于室内西南侧靠墙空位；采用现有宝箱模型、碰撞、开启动画及搜寻界面。模块局部位置为 `[1035,-915,0.4]` cm、朝向 90°。已保存生产地图，未恢复已归档生活区样板。

模块源、草稿源和生产作者入口同步保留该宝箱；本批制作与地图保存回执见 [容器增补](../SceneLootExpansion20261003/README.md)。未运行游戏或测试。
