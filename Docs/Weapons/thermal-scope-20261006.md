# 热成像瞄准镜：通用传说改造，模型阶段

用户要求：枪械通用、传说级，默认 1.5 倍，可在 1.5／3／8 倍切换；怪物及火源热成像高亮，主要用于识别隐身怪物；方形瞄具形式，先制作模型并调研 GitHub 显示效果。

## 当前制作范围

原创紧凑方形机身，深石墨涂层、铜色感光镜口压边、红色传说识别嵌片。保留方形大目窗、柔性遮光眼罩、内凹感光窗口、独立电池盒、散热筋、顶部按键与三档滚花倍率旋钮。底座有真实厚度的夹轨斜肩、止退键、两点承托和快拆锁杆，不以几块悬空方块代替接口。

| 制作参数 | 当前值 |
| --- | --- |
| 配件设计 ID／名称 | `thermal_scope`／热成像瞄准镜 |
| 设计稀有度／卡片色 | legendary／red，尚未发布到枪匠目录 |
| 初始倍率／档位 | 1.5×／1.5×、3×、8× |
| 主体长度／目罩宽高 | 99 mm／49.6 × 46.6 mm，侧部控制件另占外伸空间 |
| 后显示面有效尺寸 | 34.4 × 28 mm，独立 0–1 图像 UV |
| 导轨承托面／前向 | 原点 Z=0／+X |
| 视轴离承托面高度 | 37.5 mm |
| 名义夹轨宽度 | 21.2 mm，通用母体基准；各枪适配座仍需在接入阶段制作 |
| 倍率旋钮 | 独立枢轴，保存姿态指向 1.5；后续相对档位为 Blender Y 轴 0°／70°／140° |
| LOD0 总三角面 | 28,432，包含近景倒角、滚花、夹具和实体文字 |

独立零件：镜身 `Body`、安装座 `RailMount`、显示面 `Display`、倍率选择器 `ZoomSelector`。另导出一份完整装配体用于物品展示与后续图标制作；不要在游戏中同时显示装配体与四个分件，否则会重叠。

模型接口：`Mount`、`SightRear`、`SightFront`、`SightUp`、`DisplayCenter`、`ZoomPivot`。位置以作者参数 `authoring.json` 为准，不从包围盒猜测中心或重新补一层安装旋转。显示面是电子屏，不是应当透视到远处的全息镜片；模型阶段只提供低亮待机表面，不含虚构的热目标画面。

## GitHub 显示效果调研

调研日期：2026-10-06。以下为上游文档与许可的调查结果，未安装插件、编译第三方源码或运行其演示。

1. [cem-akkaya/ThermoForge](https://github.com/cem-akkaya/ThermoForge)：最接近本需求的候选。仓库提供热成像后处理 `ThermoForgeVisionPP_M`、热源组件及温度采样接口；支持范围在 README 标为 UE 5.6／5.7。项目采用 [MIT 许可](https://github.com/cem-akkaya/ThermoForge/blob/master/LICENSE.md)，实际使用其代码或资产需附原版权与许可。当前工程是 UE 5.8.2，兼容性尚未验证。
2. [ThermoForgeDemo](https://github.com/cem-akkaya/ThermoForgeDemo)：UE 5.7 示例含热成像视图和动态热源，适合后续参考显示层次与热源表达。它不能直接证明本项目的隐身材质会被正确识别。
3. [droganaida/ue5-postprocess-stencil-demo](https://github.com/droganaida/ue5-postprocess-stencil-demo)：展示 Custom Depth／Stencil 分类屏蔽，能参考目标分类方法；它本身是灰阶排除示例，并非完整热成像效果，当前页面未见独立许可证，不复制其资产。

建议参考 ThermoForge 的热色阶与热源表达，为现有瞄具成像路径制作精简的目标遮罩后处理。没有为了一个瞄具引入整套气候、体积烘焙和 AI 感热子系统。此为结合项目结构作出的设计选择，不是第三方插件的性能测试结论。

上游 README、LICENSE.md 与插件描述文件已保存到 `SourceAssets/ThermalScope20261006/Research` 作为调研快照；第三方代码和资产尚未复制进运行目录。

## 后续显示与接入合同（未实施）

- 普通环境压为冷暗灰，怪物用白热主体及少量黄橙边缘；火源用白黄核心与橙色过渡，分划保持独立清晰。普通画面的光照颜色不作为目标身份判断。
- 倍率使用离散三档，默认 1.5，接入当前 `ScopeOpticalPresentation` 的相机倍率与输入占用；方形有效画面大小不随档位缩小。进入／退出 ADS、换弹和菜单恢复沿用当前瞄具状态路径。
- 当前隐身螳螂在 `MantisM27Stealth.cpp` 中用透明隐身材质替换身体材质。未来目标遮罩必须独立于隐身透明度；需要保持骨架动作同步、只写目标遮罩的几何表示，不能假设已经隐藏的阴影副本会自动写入 Custom Depth。
- 火源按实际火焰／热源对象注册，处理半透明粒子的目标表示；怪物和火源分开标识，不能把所有发光材质或灯光都判断为怪物。
- 实体墙保留遮挡，识别视觉隐身不等于允许隔墙透视。目标注册和显隐采用有界、事件驱动流程，不每帧遍历全部 Actor。
- 枪匠选项、传说卡片与图标、逐枪安装、存档、倍率输入、真实热成像、隐身及火源识别仍属后续接入阶段，本轮没有修改这些运行逻辑。

## 文件与资产

- 分件制作源：`SourceAssets/ThermalScope20261006/Model/ThermalScope_Editable.blend`
- 完整装配 GLB：`SourceAssets/ThermalScope20261006/Model/ThermalScope_Assembly.glb`
- 五份 FBX：`SourceAssets/ThermalScope20261006/Exports`
- 制作参数：`SourceAssets/ThermalScope20261006/authoring.json`
- 作者入口：`Tools/Weapons/ThermalScope20261006/author_model.py`
- 导入入口：同工具目录 `import_model.py` 和 `import_background.ps1`
- UE 目标目录：`/Game/Weapons/ThermalScope20261006/Models` 和 `/Materials`
- 已保存资产以 `SourceAssets/ThermalScope20261006/import-receipt.json` 为准。

本轮已通过后台 commandlet 实际导入并保存五个模型、八份材质，共 13 个资产包。最终生产日志 `SourceAssets/ThermalScope20261006/import-20261006-143641.log`；保存回执状态为 `five_model_assets_and_eight_materials_saved`。目标目录与模型元数据明确标注 `ModelOnly-v1`，没有向枪匠目录发布未实现的功能。

全部模型为本地原创参数化硬表面制作，未使用外部模型或贴图。材质为按金属／橡胶／感光窗口／电子屏拆分的参数化 PBR 与待机显示材质，没有将常量颜色称为烘焙贴图组。遵照用户规则，不自动打开编辑器、启动游戏、截图、渲染或执行验收；由用户后续查看模型和测试游戏。
