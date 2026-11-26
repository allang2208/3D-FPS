# 作物 V3 本地资产库接入（2026-10-22）

已安装到 `/Game/Props/Crops/V3`，磁盘目录为 `Content/Props/Crops/V3`。
作物为番茄、土豆、胡萝卜、小麦；每种 A/B/C 三套变种，每套三个独立生长阶段。

## 实际交付

| 类型 | 数量 |
| --- | ---: |
| StaticMesh | 36（各含 LOD0/1/2，合计 108 级） |
| Material | 14 |
| MaterialInstanceConstant | 6（Leaf/YoungLeaf × A/B/C） |
| Texture2D | 33（BaseColor/Roughness/NormalDX） |
| uasset 总数 | 89 |

模型路径采用 `/Game/Props/Crops/V3/Meshes/SM_Tomato_VA_Stage1` 等稳定名称。
映射为 `Content/ColdSteelData/crop_models_v3.json`，保存 crop/variant/stage、稳定种子、
实际 UE 对象路径、尺寸、三档面数、材质槽和叶色预设。它是资产目录，尚无种植玩法消费者。
生长阶段切换应保留同一变种和实例变换；可见果实数量不改变逻辑产出。

## 输入和核验

输入只使用 Downloads 中最终五个 `Crops_V3_01` 至 `Crops_V3_05` ZIP，已复制到
`SourceAssets/CropsV3_20261022/Packages/`。CRC 全通过，合并 159 个唯一文件；28 个
重复清单文件字节相同。108 个 FBX 与 44 张 PNG 共 152 个内容 SHA-256 均与包清单匹配。
包中没有 Unreal 导入脚本或可编辑 Blend 源。旧 `export_validation.json` 描述的 GLB
不在本批附件内，不用它宣称本地 FBX 已通过。没有混入 Downloads 的旧 `crops_low_poly.glb`。

Blender 5.1.2 后台逐个回读 FBX，核对实际面数、尺寸、原点、有限数值、UV、法线、切线和材质分布。
12 组三阶段的根部原点均为 (0,0,0)，稳定种子一致，三个阶段的尺寸与 manifest 相符。
胡萝卜成熟根部进入地下，番茄支柱也有地下段；没有用包围盒底端重新居中。

| 成熟作物 | 包围盒总高度（A/B/C 范围，cm） |
| --- | ---: |
| 胡萝卜 | 53.66–62.65（含地下根部约 19.32–22.27 cm） |
| 土豆 | 41.80–48.17 |
| 番茄 | 88.33–101.77（含地下支柱） |
| 小麦 | 77.46–96.48 |

## 修复与 UE 导入

原始附件完整保留。源回读发现 9 个小麦 LOD 的弱/零法线或切线，局部修复版位于 `Derived/Models/`。
进一步检查 UE 编译 RenderData 发现另外需要处理的 LOD 表面基向量，按实际异常顶点局部设置分面法线，
导出显式平滑组与切线到 `EngineBasis/Models/`。具体数量和涉及面见 `Receipts/engine-basis-repairs.json`。
最终实际使用 23 份派生 LOD；与原始 V3 逐三角形匹配位置、UV、拓扑和材质，数值差小于 1e-6。
修复保留几何、UV、面数、材质分布和根部；没有重做阶段形态或减面。

当前项目有并行 Editor/Game 构建及其他 commandlet，因此使用同版本 UE 5.8 的无模块临时宿主
`Saved/CropsV3ImportHost`。全程 `UnrealEditor-Cmd -run=pythonscript -nullrhi -unattended`，
没有打开图形编辑器或游戏，没有加载正在构建的 FPSGAME DLL，也没有保存地图或共享配置。
独立进程重新加载并验证后，安装至原本不存在的正式子目录，逐文件比对 SHA-256。

材质为兼容本项目 Substrate 的不透明双面材质图，支持 InstancedStaticMesh；叶色只作用于 Leaf/YoungLeaf。
水果成熟色、花和茎保持原材质。NormalDX 使用 Normalmap 压缩且不再次翻转绿色通道，
BaseColor 为 sRGB、Roughness 为线性；纹理保留流送。11 张 NormalGL 仅保留在源目录，避免重复导入。
Soil、PotatoSkin 表面保留为独立材质/贴图，但当前 36 个网格没有引用它们。
保留显式三档 LOD，屏幕比例 1/0.45/0.18、作者法线、高精度切线与 UV；未生成碰撞或风动。

## 验证范围与限制

独立 UE 进程检查了全部 89 项资产的重载、36 个网格的三级面数、尺寸、地下 Z 范围、
LOD 阈值、各级段/材质槽、叶色实例与纹理参数，以及持久化 Substrate 材质图的贴图依赖。
GeometryScript 从实际编译的 RenderData 回读全部 108 级的渲染顶点法线、切线、副切线；
最终有限数值和近零向量检查结果见 `Receipts/ue-render-basis.json`。
初次导入的命名模式/平滑组和基向量警告保留在历史日志；不以导入退出码代替上述独立回读。

NullRHI 没有进行 GPU 着色或画面验收；未运行 PIE、游戏、批量种植性能、Cook/打包、
存档或联机测试。没有新建播种、生长、收获、交互或存档系统；没有把模型放进关卡。
未修改用户现有源码、其他配置或资产，未提交/推送 Git。

## 入口与回执

- 工具：`Tools/Crops/prepare_v3.py`、`audit_fbx_v3.py`、两份局部修复脚本、`ue_import_v3.py`、`ue_basis_v3.py`。
- 后台执行：`Tools/Crops/run_v3.ps1 -Phase import`；修复续接使用 `-RefreshLODs`；重载使用 `-Phase readback`。
- 安装与报告：`Tools/Crops/install_v3.py`、`finalize_v3.py`。安装拒绝覆盖内容不同的现有资产/映射。
- `SourceAssets/CropsV3_20261022/Receipts/package-audit.json`：输入散列和贴图尺寸。
- `fbx-audit.json`、`fbx-derived-audit.json`、`fbx-engine-audit.json`：原始与派生 FBX 回读。
- `ue-import.json`、`ue-readback.json`、`ue-render-basis.json`：UE 保存与独立重载。
- `installed-assets.json`、`delivery-status.json`：正式落盘位置、散列与最终范围。

来源按包内声明保留：Crops (low poly)，Bumroker，CC BY 4.0。
https://sketchfab.com/3d-models/crops-low-poly-637198c4b8be41e6aeaca8cea8fb81f4
https://creativecommons.org/licenses/by/4.0/
V2/V3 重制作物几何和叶面贴图；本地增加 UE 材质、LOD 基向量修复与映射。未对外发布素材。
