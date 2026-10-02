# 员工生活区场景容器搜寻 V1

本次在生活区样板的 36 个储物柜接入 `AColdSteelSceneContainer`：宿舍区 12 个、更衣淋浴区 24 个。
组合样板和对应两个独立样板使用同一套资产、E 交互及现有随机地牢宝箱的取物界面。

## 使用和状态

进入关卡时柜门关闭，柜体及柜门外轮廓呈绿色。准星在 250cm 眼部射线范围内命中柜子，
沿用统一小浮窗「员工储物柜 · 搜寻」。按 E 后轮廓立即变黄，柜门在 0.55 秒内绕左铰链打开 100°，
动画结束后弹出取物界面。关闭面板、移开视角及重复查看都不会关门。
再次按 E 直接查看同一容器；开启动画期间不重复触发。
搜寻/开门状态维持本次关卡访问，重新进入场景重新初始化；尚未新增跨关卡柜门状态存档。

面板直接调用 `UColdSteelHUDWidget::OpenChestLootStorage`：标题「员工储物柜 · 搜寻物品」，
右侧背包和左侧独立容器空间沿用原宝箱/仓库界面与事务。每柜一页，容器键为
`SceneSearch.<无 PIE 前缀的地图名>.<roomId.partId>`；不同柜子及不同样板地图不会混用空间。
离开柜子 240cm、关闭或销毁锚点时，由现有面板生命周期结束会话。
柜门开完时若玩家已离开或打开其他面板，不强行抢占界面，可返回柜前按 E 再次查看。
奖励表后续设计，本次不抽取地牢宝箱奖励、不自动发放物品、不放测试奖励。

## 可复用制作接口

`ColdSteelSceneContainer.h/.cpp` 持有独立柜体、铰链和柜门组件。柜体使用真实侧板、背板、
层板及支脚的简单碰撞；门的碰撞随铰链转动。资产沿用原有金属和涂漆材质、UV 尺度、百叶和把手。
`ContainerId`、`Caption`、`StoragePages`、`OpeningDuration` 和 `OpenedYaw` 可以按具体容器设置。
没有空闲 Actor Tick；只在柜门动画的 0.55 秒期间临时启用。

轮廓由 `M_Staff_ContainerOutline_V1` 的屏幕空间 CustomDepth/Stencil 提供，201=未搜寻绿、202=已搜寻黄。
每个含柜样板只有一个专用无限范围后处理体积，8 个有限邻域采样，描边宽度 1.6 像素，保留柜体表面。
使用场景深度遮挡，不透墙描边，也不覆盖更近的第一人称手臂/枪械。现有第一人称技能 stencil 231 不改动。
将此类用于其他地图时，也要绑定这份后处理材质；仅设置 stencil 不能产生可见描边。

## 产物和入口

- 组合图：`/Game/GameMaps/Design/L_StaffLiving_Theme_Subject`
- 宿舍图：`/Game/GameMaps/Design/L_StaffDormitory_Subject`
- 更衣淋浴图：`/Game/GameMaps/Design/L_StaffChangingShowers_Subject`
- 资产：`/Game/Dungeons/StaffLiving20261002/SearchContainersV1`
- 当前完整源：`SourceAssets/DungeonStaffLiving20261002/SearchContainersV1/Authored/StaffLivingTheme_SearchContainersV1.blend`
- 后台作者：`Scripts/author_search_containers_v1.py`
- 后台导入：`Scripts/import_search_containers_background_v1.ps1`
- 保存回执：`SearchContainersV1/install.json`；原地图备份：`SearchContainersV1/Backups`

完整源继承 V4 的完整瓷砖以及 V3 地毯、床品、毛巾、告示和供排水。只迁移原储物柜，
活动区独立图没有柜子，不新增容器或改动它。草稿模块的 `scene_containers` 单独记录动态 Actor，
不能再将柜门合并为普通静态实例；本轮仍属于样板接入，没有注册到正式随机地牢生成池。

本轮仅制作、必要构建、后台导入和保存；没有启动编辑器、游戏/PIE、截图、渲染或测试，体验由用户测试。

实际交付：`FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 构建成功，
后台导入退出码 0，`install.json` 阶段为 `samples_saved`。三张地图分别保存 12、24、36 个容器 Actor，
两份网格和轮廓材质均已落盘。构建/制作回执为 `SearchContainersV1/completion.json`，不代表运行时体验通过。
