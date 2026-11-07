# M24 原模型后托与轨底承接修订

## 已保存资产

- `CarbonSpine20261104/Meshes/SM_M24_CarbonSpine_Native`、`SM_M24_CarbonSpine_Advanced`：继续使用用户指定的 `Meshy_AI_Carbon_Stock_1105135808_texture.glb`，统一比例、整体下倾 4°；保留原后托主体和碳纤维 UV/法线。仅裁去鼻端约 1.82 mm，重建枪身尾部 25 mm 承接面。前端金属圈使用相应机匣材质。源文件 `M24_NaturalStock.blend`。
- `RailSeats20261106/Meshes/SM_M24_m24_rail_seat_native`、`SM_M24_m24_rail_seat_advanced`：分别制作原厂与先进机匣的轨底承接；保留拱形枪机通道和原有开窗。源文件 `M24_RailSeats.blend`。
- 贴图继续绑定已有 `Meshy1105135808/M_M24_Meshy1105135808`；没有替换用户选中的碳纤维贴图。所有拼合对象的主 UV 层统一为 `UVMap`，防止先前的 UV0 丢失重现。

保存回执见 `saved.json`；旧后托资产保存在 `Before/`。原始 GLB 不改写。

## 本次排查依据

`Inputs/` 来自本次实际在用资产。`rail_profiles.json` 记录两个机匣的轨底断面；先进机匣中央轨底 138.8 mm、外壳顶部 135.8 mm，存在约 3 mm 间隙。原厂轨底和壳体的间隙随前后位置变化。

`optic_contacts.json` 记录七种通用瞄具的实际接触面，装配后均在 144.82988 mm 的既有轨顶，因而不更改瞄准镜位置、Sight sockets 或 ADS。专用 6 倍镜和机械瞄具也通过同一个 M24 装配入口获得承接件。

`M24OpticVisual.cpp` 复用现有受管理的 `AKMOpticBridge` 组件挂载承接；`M4HandstopVisual.cpp` 在机匣变化后同步切换。`ColdSteelIconResources.cpp` 加入对应资源预载，改造台和图标沿用角色装配入口。

## 交付边界

`stock_joint_source.png` 是 Blender 源模型局部预览，机匣使用中性预览材质，不是 UE 游戏截图。资产已导入并保存；常规 `FPSGAMEEditor Win64 Development` 构建成功，已链接 `UnrealEditor-FPSGAME.dll`，结果见 `build.log`。未启动编辑器或游戏，未进行玩法、动作或联机验收，由用户实际查看效果。
