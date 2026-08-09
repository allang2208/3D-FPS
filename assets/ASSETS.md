# 免费 CC0 美术资产（2026-08-09 批量下载）

本目录下的免费资产全部为 CC0 许可（公共领域，可免署名商用），来源与用途如下。

## 来源与授权

| 分类 | 来源 | 许可 | 说明 |
|---|---|---|---|
| 地表纹理 | [AmbientCG](https://ambientcg.com/) | CC0 | 草/泥/岩/沙四套 PBR 贴图（Color、Roughness、NormalGL/DX、AO、Displacement），含 Godot .tres 材质 |
| 岩石模型 | [Poly Haven](https://polyhaven.com/) | CC0 | 写实岩石 glTF 2K（boulder_01、rock_07、rock_09、rock_moss_set_01） |
| 植被点缀 | [Poly Haven](https://polyhaven.com/) | CC0 | 写实草地/树桩/枯木/热带岛树 glTF（grass_medium_01、grass_bermuda_01、tree_stump_01、dead_tree_trunk_02、island_tree_01/02/03；荒漠 quiver_tree_01、othonna_cerarioides 备选） |
| 天空环境 | [Poly Haven](https://polyhaven.com/) | CC0 | kloofendal 阴天纯天空 HDRI 2K |
| 植被/自然 | [Kenney Nature Kit](https://kenney.nl/assets/nature-kit) | CC0 | 329 个 GLB：树、灌木、草、花、岩石、蘑菇、断木等 |
| 掩体/道具 | [Kenney Tower Defense Kit](https://kenney.nl/assets/tower-defense-kit) | CC0 | 160 个 GLB：木箱、木桶、栅栏、路障、塔、墙、桥等 |

## 目录结构

```
assets/
├── textures/terrain/        # AmbientCG PBR 贴图，Terrain3D 刷地表用
│   ├── grass001/            # Color / Roughness / NormalGL 等
│   ├── ground037/           # 泥土
│   ├── rock063/             # 岩石
│   └── ground080/           # 沙地
├── models/
│   ├── polyhaven/           # 写实岩石 glTF（boulder_01 等）
│   ├── kenney_nature/       # 低多边形植被 GLB
│   └── kenney_tower_defense/ # 低多边形掩体/道具 GLB
└── environment/hdri/        # 环境天空
```

## 使用建议

- Terrain3D 刷地表：在 Asset Dock 的 Textures 里添加 `textures/terrain/*/*_Color.jpg` 作为 albedo，`*_Roughness.jpg` 作为粗糙度，`*_NormalGL.jpg` 作为法线。
- 岩石/植被：`models/polyhaven/*.gltf` 与 `models/kenney_nature/*.glb` 可直接拖进场景，或作为 Terrain3D 植被 instancer 的 Mesh 资产。
- 天空：新建 `WorldEnvironment`，用 `PanoramaSkyMaterial` 加载 `environment/hdri/*.hdr`。
- 模型加载示例：
  ```gdscript
  var rock = load("res://assets/models/polyhaven/boulder_01/boulder_01_2k.gltf").instantiate()
  add_child(rock)
  ```

## 注意

- Kenney 包内含各自 `License.txt`，保留随包文件即可。
- Poly Haven / AmbientCG 素材下载页保留原文件命名，方便溯源。
- 如需更多模型，可继续从 [poly.pizza](https://poly.pizza/)（CC0/CC-BY，GLB 直链）等渠道补充。
