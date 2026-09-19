# 丘陵河岸生态、水流与树木再生

2026-09-13。接入当前 UE 5.8.2 宿主 `D:/FPS3D/FPSGAME`，现有温带丘陵地图和世界种子继续使用。按照用户规则，仅开发、资源制作及必要构建，未进行游戏、性能或视觉测试。

## 河道与地表

保留原有优先级排水、汇水量选路和出生区域保护。增加连续河宽噪声及左右岸不同宽度；由曲率区分内弯浅滩、外弯深槽。河岸从水边向原丘陵在约 15–32 m 范围内平滑过渡，原来统一的 4 m 陡岸平台改为变化的缓坡和滩地。河床继续为可涉水尺度，目标深度限制在 25–90 cm；这是生成参数，不是实际碰撞验收结论。

水面仍按地形格准确裁剪。地形、碰撞、植物栖息地和水面共用同一数值河道。新横截面会改变旧种子河道附近的局部地形与植被，但不清除世界 GUID、采集记录、掉落和库存。

## 资源选择和栖息地

已读取两个 Fab 商品页，并从本地原始 uasset 提取作者已有缩略图来判断形态；没有为选材启动地图或生成新场景渲染。原缩略图带有作者的顶点颜色显示，因此未据此宣称游戏材质表现已通过验收。

| 来源 | 本次选用 | 放置规则 |
|---|---|---|
| [temperate Vegetation: optimized Grass Library](https://www.fab.com/listings/8b68642e-35f4-438e-82b4-799fc2228303) | `grass_02_01_mesh`、`grass_04_01_mesh` 高草形态 | 水位上方约 -16 至 65 cm 的浅湿带；高速段减量，沿岸成团并留缺口 |
| 同一草库 | `grass_09_02_mesh`、`grass_10_01_mesh` 穗状草形态 | 岸外约 0.8–20 m 的较干滩地，与现有草甸衔接 |
| [tropical Vegetation: Ground Plants](https://www.fab.com/listings/ef6db212-dfcf-4a50-8ade-fbca49963240) | `tropicalPlant_05_01`、`tropicalPlant_05_02` 小型丛叶形态 | 潮湿林缘低密度点缀，缩放 0.40–0.72；不作为植物学物种鉴定 |

热带包的木瓜状、大芋叶植株不加入温带丘陵。商品页只给草种数量，没有对应的中文物种名；本次不把编号模型硬标为已鉴定的芦苇或狗尾巴草。

所有选用模型复制到 `/Game/WorldGeneration/TemperateHills/RiverEcology`；保留原 LOD、纹理、顶点色和 Pivot Painter UV，修改自有材质副本的亮度/饱和度并增加距离淡出。原始包和演示蓝图不改动、不额外接入。

河岸植物沿用 16 m PCG 草格、16 m × 2 m 条带生成、60 m 生成半径及既有草实例淡出。两岸独立噪声、约 18 m 湿地斑块和约 3 m 草团控制密度，避开出生区域与主要通道。普通草从岸外逐渐恢复，不再给整条河岸留统一空白带。新增六个网格软引用纳入已有草资源异步载入和资源保留流程。

## GitHub 借鉴与水材质

| 参考 | 阅读所得及采用范围 |
|---|---|
| [weigert/SimpleHydrology](https://github.com/weigert/SimpleHydrology)，[water.h](https://github.com/weigert/SimpleHydrology/blob/master/source/water.h) | README 标示 MIT；源码将动量、汇水量、侵蚀沉积关联。本次沿用已有汇水骨架，用曲率和坡度推导横截面/视觉流速；没有移植其粒子侵蚀求解器。 |
| [JaccomoLorenz/godot-flow-map-shader](https://github.com/JaccomoLorenz/godot-flow-map-shader)，[许可证](https://github.com/JaccomoLorenz/godot-flow-map-shader/blob/master/LICENSE.md) | MIT，作者 Jaccomo Lorenz。参考 RG 流向和双相偏移混合，限制累积纹理拉伸。以 UE 材质独立实现，不加载 Godot 项目。 |
| [Scrawk/Tiled-Directional-Flow](https://github.com/Scrawk/Tiled-Directional-Flow/blob/master/Assets/TiledDirectionalFlow/Shaders/TiledDirectinalFlow.shader) | 源码标注 Frans van Hoesel 2010、Creditware。参考将方向/速度信息交给几何、减少每像素流场推导的思路；没有复制其四块拼接 shader。 |

新水面顶点 RG 编码世界流向，B 为速度/160 cm/s，A 为河床深度/100 cm。材质使用世界坐标与世界空间法线，顺河弯流动；近岸降速，外弯相对加速。两组法线和泡沫均使用双相循环混合，避免单向滚动无限累积拉伸。深度衰减决定浅水/深水色和透明度，几何岸边及石头接触处用 DepthFade 收边，碎泡受浅水、速度与纹理共同控制，避免整条白边。

自有水材质：`/Game/WorldGeneration/TemperateHills/RiverEcology/M_RiverFlowWater`。参数包括 `FlowSpeedMultiplier`、`RippleStrength`、`FoamAmount`、`ShallowTint`、`DeepTint`、`AbsorptionPerCm`。这是视觉水流场；没有新增游泳、浮力、洪水、水量守恒或障碍绕流求解。纹理采样和透明渲染成本没有进行帧率测试。

## 树木生长周期

默认完整周期 6 个游戏日。生长时钟按当前天气管理器 `RealSecondsPerGameDay` 换算；没有天气管理器时按 2160 秒/天。当前默认一天 36 分钟，对应完整周期约 216 分钟（3.6 小时）在线游戏时间。切地图后继续累积，暂停及关闭游戏不推进。

| 砍倒后时间 | 表现和采集 |
|---|---|
| 0–1 天 | 保留原树桩，暂未萌芽 |
| 1–2 天 | 原位开始长出小树，原高度的约 4%→18%；树桩逐渐缩退 |
| 2–4 天 | 原高度的约 18%→55%，平滑长高 |
| 4–6 天 | 原高度的约 55%→100%，成熟前不能再次砍伐 |
| 6 天起 | 恢复正常 3 击采集和原木奖励，再砍倒开始下一轮 |

采用现有四种黑杨的原模型连续缩放，保留物种、树冠和材质；未制作独立幼苗拓扑或枝条生长动画。树根保持贴地，附近树干碰撞随高度缩放。再生树使用独立实例组件管理整个后续生命周期，PCG 跳过这些稳定 ID，因此成熟无需重新生成整片森林。局部视距 256 m，每秒最多增加 8 个再生树实例，已存在实例更新变换；近处 96 m 范围维护树干碰撞。

配置：`DA_TemperateHillsStreaming` 的 `TreeDormantDays=1`、`TreeMatureDays=6`。每次砍倒把当时周期写进该树记录；后续调整只影响新一轮砍倒，避免已生长树木突然变高/变矮。

持久化位于现有角色档案的 `TreeGrowthVersion`、`TreeGrowthDay`、`TreeGrowth`。每棵树以原世界 GUID 和候选 ID 记录砍倒时间、休眠天数和成熟天数，和采尽/奖励在同一档案事务保存。旧档中已经砍倒的树从首次加载新版时开始新周期；石矿和土壤的有限采集规则保持原实现。在线时钟跟随原档案自动保存（约 5 秒一次）及正常退出保存。

## 制作入口与交付范围

作者脚本：`Tools/WorldGeneration/build_temperate_river_ecology.py`。先构建 Editor 模块，再以 Python commandlet 执行。脚本只制作自有资源并修改现有丘陵数据资产相关字段，不载入地图或运行游戏。被修改的既有资源备份于 `Saved/RiverEcologySources/BeforeAuthoring-*`。资源制作记录写入同目录的 `authoring.json`。

当前河流顶点数据和新水材质需要配套使用。恢复工程时执行旧 hills/streaming/rivers/grass 作者步骤后，再执行本次脚本。Fab 原始资产及衍生二进制只保留本机，源码说明不代表原始资源可公开再分发。

未运行测试、PIE、游戏回归、性能测量或新场景截图/渲染，由用户重启编辑器后在原丘陵世界自行测试。

本次执行结果：Editor 原生构建完成（`Saved/RiverEcology-NativeBuild.log`，Result: Succeeded），资源作者脚本执行完成并保存模型、材质和数据资产。作者 commandlet 因工程既有的 `GameFeatureData` AssetManager 配置错误返回 1；同期还有并行武器资源尚未生成的加载警告。这些信息保留在 `Saved/RiverEcology-Authoring.log`，不将 commandlet 返回码写作干净通过，也没有为此改动其他任务的配置或武器资源。

后续河岸加密升级见 [密集河岸植物（2026-09-14）](dense-riverbanks-20260914.md)。当前植物配置以该文及 build_dense_riverbanks.py 为准。
