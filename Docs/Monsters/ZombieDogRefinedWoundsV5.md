# 僵尸犬伤口与残毛衔接 V5

2026-09-19，用户反馈 V4 伤口粗糙、与皮毛衔接不好，并授权按建议精修。V5 保留狼体型、断耳、细皮肤、动作及 AI，修改伤口图层、毛层遮罩和个体分布。

## 当前调整：伤口更明显 V5.1

用户试玩 V5 后反馈伤口太小、太少，已通过正在运行的 UE 编辑器保存以下调整：

- 蓝图目标数量由 3～5 提高至 6～8；沿用生成尝试上限和间距限制，因此空间不足时仍可能少于目标数量。
- 材质中的主伤长轴放大至 1.65 倍，次伤长轴 1.75 倍，短轴均为 2 倍；这些倍率作用于既有图案，不重新制作粗糙噪声边缘。
- 表面厚度覆盖范围扩大为 1.30 倍，以减少曲面将放大图案截短；细凹凸的高度系数保留，未把伤口表面凹凸同步放大。
- 遮罩强度乘 1.22 后限制在 0～1；前几处细疤改为更明显的不规则创面，其余细疤多数改为擦伤或块状创面，少量保留旧疤。转换的创面同时降低愈合系数。
- 血污、碎毛和痂缘随同一图案扩大，脸、脚掌、尾部的排除范围继续保留。

本次直接修改 `M_ZombieDog_RefinedWounds` 的伤口 Custom 节点，以及现有僵尸犬蓝图 `WoundAppearance` 的数量默认值，无需 C++ 构建或关闭编辑器。已存在的犬沿用原数量，新生成的犬采用新数量；位置仍随机。

执行入口 `Tools/ZombieDog/apply_wound_visibility_v51.ps1`，保存记录 `SourceAssets/ZombieDogRefinedWoundsV5/visibility_v51.json`，执行日志 `Saved/ZombieDogWoundVisibilityV51Apply.log`。完整重建入口 `install_refined_wounds.py` 已同步新数量与材质修订。未进行游戏或画面测试，以下段落保留 V5 首版制作参数。

## 伤口图层

新增四种独立 Blender 材质图制作的伤口图案：长撕裂、擦伤、细旧疤、不规则创面。2×2 图集为 2048，每格四周留空，采样限制在格内，避免混入相邻类型。

- `T_ZombieDog_WoundMasks`：RGB 分别为创面、裸皮、干燥痂缘。线性无块压缩存储，保留细边缘。
- `T_ZombieDog_WoundDetail`：RGB 分别为围绕 0.5 编码的浅层高度、外围血污、方向性细纤维。半浮点 EXR 保留浅层高度渐变。
- 图案外形有各自长宽、偏曲、轮廓破损和表面结构，不再共用一个噪声椭圆作为最终外形。椭圆空间只用于定义每个图案的位置、尺寸和厚度范围。
- 创面中心降低红色反差，痂缘偏暗褐，周围裸皮轻微变色。血污延伸到残毛上，剩余毛发只接受血污染色，不混成一层平坦的肉色。
- 创面湿润受中心遮罩、纤维和愈合程度共同控制，局部粗糙度向 0.38 变化；痂缘约 0.72。旧疤颜色靠近皮肤、反光偏干。
- 高度生成专用表面法线，跟随当前蒙皮表面计算，主伤凹陷约 0.22 mm、痂缘凸起约 0.10 mm，另加更浅的细纤维。它是材质凹凸，不是真实几何开洞。

## 皮毛衔接

V4 在毛层自身空间计算伤口，而毛层与身体表面有距离。V5 从同一作者网格计算毛层顶点到下方身体的最近表面点，用 CORNER 属性 `WoundSurfacePosition` 烘焙新的定位图。身体和毛层的同一伤口因此以身体表面为参照。

裸皮、创面、痂缘、血污和毛发移除使用独立通道。裸皮外圈保留碎毛与原有细毛透明纹理，毛发移除受厘米级小毛束变化调制；内部创面清除覆盖毛层。透明裁切阈值改为 0.28。没有新增毛发几何，也没有修改绑定和骨架。

新的定位图仍为 2048 半浮点、无 mip、常驻；轴向和编码与 V4 保持一致：静止姿态 cm，X 向左、Y 向口鼻、Z 向上，最小值 `(-25,-115,-5)`、范围 `(50,210,115)`。同一随机种子的图案继续固定在模型上。

## 随机分布

默认目标数量为 3～5，即一处躯干主伤与两至四处小伤或旧疤。首处只从侧腹、肩背等较宽部位采样；腿与颈部倾向细疤。沿用按真实三角形面积采样、每区最多两处、最小间距和 192 次尝试上限，空间不足时允许少于目标数量。

主伤图案选择长撕裂或不规则创面，定位半轴为 8～11 cm × 4～5.5 cm；小伤为 3～6 cm，腿部短轴更窄。图集图案只占定位范围的一部分，外圈留给裸皮和血污。肩、颈、腿的长轴倾向上下，侧腹和背部倾向顺着身体前后方向，随机偏转范围 ±25°。

`WoundStyle0..7` 向动态材质传递类型、愈合程度与高度系数。原有 `RandomSeed`、`RerollWounds`、零 Tick 和每只犬独立动态材质机制保留。固定正种子可复现 V5 分布；由于分布算法更新，相同数字不承诺复现 V4 的位置。

断耳继续保留原有真实缺口，本版封口改为较干燥的旧痂效果。

## 接入与制作文件

- F6 入口仍为 `/Game/Monsters/ZombieDog/V1/BP_ZombieDog`。
- 新资源目录 `/Game/Monsters/ZombieDog/RefinedWoundsV5`，网格 `SK_ZombieDog_RefinedWounds`、动作数据集 `DA_ZombieDog_RefinedWounds`。
- 4K 毛皮、细皮肤和基础法线继续使用 V4 分层贴图；新网格复制 V4 网格后替换三个材质。动作数据集复制切换前配置，仅改参考网格。
- 原生分布：`Source/FPSGAME/Monsters/ZombieDogAppearanceComponent.h/.cpp`。
- 材质采样：`Tools/ZombieDog/refined_wound_field.hlsl`。
- 制作：Blender 执行 `Tools/ZombieDog/author_refined_wounds.py`；完整模块构建使用 `Tools/Build/Build-Editor.ps1`；UE Python 执行 `Tools/ZombieDog/install_refined_wounds.py`。
- 作者文件：`SourceAssets/ZombieDogRefinedWoundsV5/ZombieDog_RefinedWounds_Authoring.blend` 与 `WoundStamp_Library.blend`。后者保留四种图案的全部可编辑材质节点。
- 贴图与生成记录在同目录；来源继承 `SourceAssets/ZombieDogV1/CREDITS.md`。本次新增图案为项目本地程序化材质制作，没有新增第三方图案下载。

按用户规则仅执行制作、必要构建和接入，不进行游戏、画面或性能测试。本版效果由用户在 F6 生成僵尸犬后试玩判断；记录中的参数属于本次制作值。

制作完成记录：`Saved/BuildEditor/build-20260919-182919.log` 为完整模块构建；`Saved/ZombieDogRefinedWoundsV5Author.console.log` 为贴图和作者文件制作；`Saved/ZombieDogRefinedWoundsV5Install2.log` 记录 `ZOMBIE_DOG_REFINED_WOUNDS_V5_INSTALLED`，切换清单保存于作者目录 `ue_delivery.json`。这些记录不代表视觉或游戏测试通过。
