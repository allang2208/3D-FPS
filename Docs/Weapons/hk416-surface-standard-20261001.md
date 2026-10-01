# HK416 材质统一 R01（2026-10-01）

## 已落盘范围

沿用 AKM 的原贴图保留方式，将当前 HK416 Reworked 主枪与配件接入统一表面配方。没有重新导入网格，也没有修改动画、骨架、安装接口或枪械数据。

- 1 个主枪骨骼网格、11 个原装配件、19 个通用配件，共 31 个网格。
- 新建并保存 60 个材质实例、57 个私有材质适配图、1 张细微粗糙度纹理。
- 资产目录：`/Game/Weapons/HK416/SurfaceStandard20261001`。
- 主枪路径仍为 `/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny`。
- 30 个配件仍使用 Reworked20260930/Attachments 和 CommonAttachments20260930/Meshes 中的现用路径。

## 表面处理

保留原作者的 BaseColor 贴图、喷漆、刻字、划痕与磨损信息，对受遮罩选中的金属调整明度、颜色对比和粗糙度。法线、AO、金属度身份、UV0 与配件涂层 UV3 保留；未向贴图添加新的装饰或磨损。

金属粗糙度中心按部件区分：上机匣 0.34、下机匣 0.36、弹匣 0.30、接口 0.42、枪口 0.44、光学器件外壳 0.37、枪托等 0.39、其余配件 0.38。原粗糙度仍贡献细节，并添加 4 cm 物理尺度的细微粗糙度变化。

非金属区域另用聚合物配方，包含大弹鼓外壳、握把和枪托，避免钢材遮罩使其整片跳过。原装表面保留更多原作者色彩，通用配件向深石墨色靠拢。聚合物粗糙度中心为弹匣/弹鼓 0.43、握把/枪托 0.49、其他 0.47。彩色涂装、亮色标记和极暗区域由颜色遮罩降低调整幅度。

独立玻璃、准星、橡胶、凹槽和手臂皮肤材质槽保留。新图复制原有图，原始材质与来源贴图未被覆盖；原作者署名和来源仍见 `hk416-reworked-20260930.md`。

## 湿润与入口

在新私有图中解除原装源图已叠加的湿润包装，颜色、粗糙度、法线各保留一层湿润输入。修正零湿润度仍可能残留水珠的旧节点公式，保留 `WeaponWetness` 参数契约。

向 `/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials` 合并 60 条新实例的自身映射，保留既有映射。实际游戏和改造预览沿用当前网格路径及材质槽；本次无需 C++ 改动或原生模块重编译。

## 制作记录与后续导入

- 配方与制作脚本：`SourceAssets/WeaponSurface20260930/HK416/Refine01/`。
- 源资产快照：`Refine01/Input/current.json`。
- 被修改网格及天气表的备份：`Refine01/Before/`。
- UE 保存回执：`Refine01/apply_receipt.json`。
- 当前材质绑定：`SourceAssets/WeaponSurface20260930/HK416/current_surface_bindings.json`。
- 重新导入绑定函数：`HK416/current_bindings.py`。

Reworked 导入、CommonAttachments 导入和 AttachmentRepair 表面发布入口均在保存网格前应用当前绑定清单；Reworked 天气表发布改为保留已有配件与新实例映射。旧导入脚本仍各自负责原有建模/动画工序，本次未运行这些全量导入入口。

实际后台资产生产日志：`SourceAssets/WeaponSurface20260930/logs/apply_finish.20261001-194537-759.log`，commandlet 正常退出，输出 `WEAPON_SURFACE_HK416_R01_SAVED 60 instances 57 adapters 0 runtime override materials 31 meshes`。

此次只执行制作所需的输入读取、材质编译、导入和保存。未启动编辑器界面、游戏预览、截图渲染或追加测试。外观由用户在游戏中测试；不将后台保存成功描述为运行时视觉验收通过。
