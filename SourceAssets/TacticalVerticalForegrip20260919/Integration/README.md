# 战术垂直握把：游戏接入

独立配件 `tactical_vertical_foregrip`，显示名“战术垂直握把”，位于前握把槽 `underbarrel`。支持 M4A1、AKM、QBZ-191、ASH-12；原 `vertical_foregrip` 选项保留。

## 属性与数据

用户指定的唯一修正为 `ads_percent = -0.25`。配件单独使用时，开镜耗时是武器基础耗时的 75%；与其他百分比配件按现有 `UGunsmithSystem::Calculate` 规则相加，绝对秒修正另行叠加。不修改后坐力、稳定性、散布或基础武器数值。

`Content/ColdSteelData/gunsmith.json` 的四枪目录已加入选项。描述仅介绍造型/材质；效果提示“缩短开镜耗时”，详情的 −25% 由目录数据计算。实例的预览、应用、撤销与保存/重载沿用现有 `gunsmith_parts` 序列化和选项规范化入口，无需修改存档版本。

## 装配与动作

正式资源为 `/Game/Weapons/TacticalVerticalForegrip20260919/<枪型>/SM_TacticalVerticalForegrip`，枪型目录为 `M4`、`AKM`、`QBZ191`、`ASH12`。

- M4：沿用当前垂直握把的瞄具帧座位，向前 27 cm、向下 8.05 cm，再转到 `WPN_root`。
- AKM：依据既有 `VerticalGripFront20260911/akm/fits.json` 的 `grip_in_root` 将新主体写进既有枪根空间，保留实际 UE 导出的独立转接座、UV 和原金属材质；运行相对缩放 0.01。
- QBZ191：沿用 `QBZ191Mounts::Underbarrel` 垂直族座位和 0.01 单位补偿。
- ASH-12：沿用现有下导轨座位（向前 30 cm、横向 −0.0439 cm、向下 14.0265 cm），再转换到枪根。

夹座的 Z=0 是导轨底面，侧夹肩包在轨缘两侧。主体保持上一轮尺寸，新增/修整的夹肩使总高度约为 10.79 cm；没有缩放手或骨架。AKM 含原有转接座，因此整件包围尺寸更大。

`M4HandstopVisual.cpp` 将该独立选项路由到各枪已有垂直握把组件和动作族，再选择本枪的专用模型。`M4VerticalForegrip.cpp` 补齐切回原垂直握把时的模型/材质恢复。继续使用各枪现有待机、ADS、射击、装备、换弹退握/回握及适用的冲刺/快速近战分支，没有重写动作时序、音效或弹药结算。

制作前已查看现有 `MannyGraspDonor20260912/Delivery/Player_Wrist_Views.png` 及抓握作者参数。新握把的手部贴合与连续动作尚未实机测试，不将历史垂直握把验收视为本模型的新验收。

角色与枪匠展览使用同一装配组件，展览现有逻辑会同步模型、材质、变换和最终配件包围盒；未装备实例继续通过原预览入口处理。

## 材质与渲染

每枪独立的 BaseColor、MetalRough、Normal 均为 2K。聚合物握持区保留深色细颗粒、凹区和防滑法线；金属夹座/紧固件分别参考当前枪身涂层：M4/AKM 使用隔离机匣区域的颜色样本，QBZ191/ASH12 使用各自现用涂层作者参数。M4 的紧固钢件保留自己的金属反射属性，并非原 Phong 母材质的逐像素复制。

MetalRough 的 G 为粗糙度、B 为金属度，R 为未使用白色；未宣称有 AO 烘焙。结构和微表面法线保留自己的 UV0/切线，Blender OpenGL 法线仅在 UE 导入时翻转绿色通道。

四套湿润副本复用现有水膜/水珠方法，新增键合并至 `/Game/Weather/RainVisibility/DA_WeatherPresentation`，保留原映射。AKM 转接座继续复用其既有材质。

`Preview/<枪型>/TacticalVerticalForegrip_Material.png` 为实际模型的 Blender Cycles 材质预览；`underbarrel_tactical_vertical_foregrip.png` 为水平左向、透明背景的 1024×1024 实物图标。AKM 图标包含专用转接座。Blender 预览使用相同干材质贴图，渲染器的反射/色调映射与 UE 不完全相同，预览不是游戏截图。

## 可编辑源与制作入口

- `<枪型>/Source/TacticalVerticalForegrip_Construction.blend`：主体、夹座、紧固件与程序材质。
- `<枪型>/Source/TacticalVerticalForegrip_Editable.blend`：共享安装空间下的高低模及贴图。
- `<枪型>/Source/TacticalVerticalForegrip_Integrated.blend`：正式导出网格；AKM 包含枪根变换与转接座。
- `<枪型>/Export/SM_TacticalVerticalForegrip.fbx`：正式 UE 导出。
- `<枪型>/TacticalVerticalForegrip_Render_Editable.blend`：材质预览与图标相机/灯光。

脚本位于上一级 `Scripts/`：`read_integration_sources.py` → `author_integration.py` → `import_integration.py`；`render_delivery.py -- <枪型>` → `install_icons.py`；`install_catalog.py` 仅新增独立选项。新资产导入和目录安装脚本拒绝重复写入；需要续作时以回执中的已完成部分为准。

## 交付边界

已制作并保存正式模型、材质、三个 LOD 和简单凸包碰撞，并登记 Cook 路径。四张正式图标已导入并保存。导入记录在 `import_receipt.json`，图标记录在 `icon_receipt.json`，目录记录在 `catalog_receipt.json`。

必要的 `FPSGAMEEditor Win64 Development` 常规构建成功（59.68 秒），编辑器已恢复并完成最终图标导入。此前 Live Coding 虽完成编译，但应用补丁时崩溃，因此不记作热更新成功；本次交付使用恢复后的基础 DLL。构建与恢复事实记录在 `build_receipt.json`。

本轮按用户明确要求制作材质渲染和图标，未启动 PIE、未操作用户装备/存档，也未执行玩法回归、动作验收或打包测试。游戏测试由用户完成。
