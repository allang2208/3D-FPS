# 赛博朋克公寓：对岸海湾夜景接入

2026-10-22 已导入并保存 `/Game/GameMaps/L_CyberpunkApartment`。用户在第二版背景图后要求继续，本轮完成 UE 场景接入。

## 画面与接入范围

- 采用「站在近岸高层，隔着宽阔水面看对岸连续城市」构图，海湾方向为 UE 世界 +Y。
- 以 `T_CyberpunkBayNight_V02.png` 为风格和构图来源，使用内置 imagegen 延展出完整球面环境 `T_CyberpunkBayNight_Environment_V01.png`，用于侧窗、阳台斜向和上下视野。提示词在 `brief-environment.txt`。
- 将完整环境贴到明确经纬 UV 的球面，在同一视点烘焙六张 90° 方向贴图，再封装为 UE 原生 TextureCube。使用 BC7、sRGB 和 mip 链，单面 1024；源全景为 1774 × 887，不将重采样描述成新增源细节。
- 复用随机地牢入口的单 Cubemap 采样、Unlit/Substrate 和有限盒投影方式；亮度参数 `NightLuminance=1.0`。没有实时 SceneCapture、运行时城市生成或逐件 Tick。
- 新背景 Actor：`Bay_NightEnvironment`。无碰撞、无投影，不向距离场和动态间接光注入整片发光背景；保留光追反射可见性。没有修改全局 Lumen/硬件光追开关。
- 停用旧 `CITY_blocks`、`CITY_bridges`、`CITY_fog`、`CITY_ground`、`CITY_horizon`、`CITY_signs`、`CITY_traffic`；保留 `CITY_our_tower`、窗框、玻璃、阳台、室内及现有交互。
- 背景是烘焙远景，水面倒影属于图像。盒投影只提供近距离移动时的近似视差，不是可以驶入或走入的城市/海湾。

## 已保存资产

```text
/Game/Props/CyberpunkBayBackdrop20261021/T_CyberpunkBayNight_Cube
/Game/Props/CyberpunkBayBackdrop20261021/M_CyberpunkBayNight_Cube
/Game/Props/CyberpunkBayBackdrop20261021/MI_CyberpunkBayNight_Apartment
/Game/GameMaps/L_CyberpunkApartment
```

所有制作源和回执位于 `SourceAssets/CyberpunkBayBackdrop20261021/`：

- `bake_environment.py`、`Authored/CyberpunkBayEnvironment.blend`、六面 PNG：生产纹理制作源。
- `pack_cube.py`、`Authored/T_CyberpunkBayNight_Cube.dds`、`cube.json`：原生 Cubemap 封装。
- `install_background.py`：导入、材质和地图更新；可复用 `apply_saved_background()`。
- `bake-receipt.json`：六面生产烘焙完成记录。
- `installed.json`：实际资产及地图保存回执，包含停用旧布景、保留楼体、亮度和备份位置。
- `Backups/20261022-000412/L_CyberpunkApartment.umap`：接入前地图。

公寓基础重建入口 `Tools/AssetPipeline/cyberpunk_apartment/35_install_level.py` 已挂接该背景；只有真实 `map_saved` 回执存在时才重放本轮替换，避免重建恢复旧城市远景。

## 使用与验收边界

```text
open /Game/GameMaps/L_CyberpunkApartment
```

返回主场景：`open /Game/GameMaps/DayNight_Lighting`。

本轮未主动启动 UE；发现编辑器已运行后，通过 `mcp_call_codex.ps1 -PythonScript` 的批次互斥，在现有进程中完成导入与保存。六面烘焙是资产制作，不是游戏验收；没有启动 PIE/游戏、进行验收截图或性能测试。窗外实际亮度、侧窗观感和游戏性能由用户体验。
