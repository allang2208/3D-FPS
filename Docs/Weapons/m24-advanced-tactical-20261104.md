# M24 先进枪机系统：单战术挂件接口

2026-11-04 已完成代码接入、后台编译、正式资产保存和枪匠目录更新。未启动 UE 编辑器界面，未运行游戏、渲染或验收；游戏表现由用户测试。

## 装配行为

- 安装 `body=m24_advanced_action` 后解锁一个 `tactical` 槽，可选择普通镭射、战术手电或赐福激光镭射，沿用共用选项的属性和特殊效果。
- 原厂枪身下相关选项显示“需先安装先进枪机系统”。切回原厂会同时归一并撤下战术挂件和后握把改造；旧存档通过同一 `Normalize` 路径处理。
- M24 不支持第二战术槽。保留 `inherit_common_options=false`，仅选择性继承共用战术挂件选项。
- 枪身变化刷新战术装配，实际先进底盘网格存在后才启用挂件。拆除时清空挂件静态网格并关闭效果，避免旧部件残留在世界外观清单。
- 复用已有镭射射线、开镜汇聚、遮挡截断、手电照明、持枪显隐和世界/第三人称表现代码；本次没有进行运行验收。

## 正式资产与表面

已保存三个静态网格：

- `/Game/Weapons/M24/Tactical20261104/SM_laser`
- `/Game/Weapons/M24/Tactical20261104/SM_flashlight`
- `/Game/Weapons/M24/Tactical20261104/SM_blessed_laser`

安装座按先进枪机右前侧导轨截面制作，使用闭合夹座、齿间止退横榫和紧固件；通过 `M24Attachments::Mount` 注册到 M24 原生枪根。`Emitter` 与 `AimGuide` 按同一刚体变换生成，运行时使用专用发射轴。

保存三个 M24 私有表面资产：两种普通设备的外壳母材质，以及安装座/石墨金属实例。金属采用当前 M24 底色 `(0.026, 0.029, 0.032)`、粗糙度 `0.48` 和 2 cm 细纹。设备原有位置遮罩转换回源坐标计算，保留镜片、发光孔、黑色非金属和赐福金色饰件；没有修改共享源材质。

## 接入文件与交付记录

`Content/ColdSteelData/gunsmith.json` 仅更新 M24 条目。可重放目录入口 `SourceAssets/M24AdvancedAction20261029/catalog.py` 同步维护单槽和依赖说明；当天已指定的枪机后坐力-15%、稳定性+20%及骨架枪托属性保持。

代码涉及 `M24Attachments.h`、`TacticalDeviceVariants.h`、`GunsmithSystem.cpp`、`TacticalDeviceComponent.cpp`、`FPSGAMECharacterProfile.cpp` 与 `UI/ColdSteelIconResources.cpp`，覆盖依赖规则、原生挂点、效果、预加载和刷新。

制作源：`SourceAssets/M24Tactical20261104/`，包含当前共用设备导出、三个可编辑 Blender 文件、FBX、导入脚本、材质来源和保存记录。`install_receipt.json` 已记录 `complete=true`、三网格与三材质；`catalog_receipt.json` 记录 M24 目录已保存。

后台构建 `FPSGAMEEditor Win64 Development` 成功，耗时 222.17 秒。日志：`Saved/BuildEditor/build-20261104-150211.log`；副本输出：`SourceAssets/M24Tactical20261104/build-console.log`。未运行测试。

本机与仓库 `ue5-weapon-workflow/references/m24-modular-recovery.md` 已同步单槽、依赖归一、安装座、位置遮罩、发射轴和预加载规则。目录在新的游戏实例初始化时读取。
