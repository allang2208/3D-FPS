# 可调式战术后托：模型、数值与枪械接入

用户于 2026-10-06 要求使用朴实名称并开始建模。现名为「可调式战术后托」，传说品质、红色卡片身份保留。设计参考为 `SourceAssets/LegendaryStock20261006/Design/concept-02.png`；原图内旧标题作为设计历史保留，当前模型、制作记录和 UE 元数据均使用新名。

## 已制作并保存

- 可编辑源：`SourceAssets/LegendaryStock20261006/Model/TacticalStock_Editable.blend`，内嵌贴图，按托架／接座／贴腮／肩垫／控制件分组。
- 通用交换件：同目录 `TacticalStock_Assembly.glb`。
- FBX：`SourceAssets/LegendaryStock20261006/Exports/` 内完整后托及五个分件，共六个文件。
- 表面：深灰涂层、聚合物、橡胶、香槟金、钢件和暗红饰片六种材质；三组原创 1024×1024 法线／ORM 贴图，共六张。微观表面由程序制作，未复制品牌素材或现成后托网格。
- UE 目标：`/Game/Weapons/LegendaryStock20261006/Models`、`Materials`、`Textures`；本轮通过已运行编辑器的互斥桥执行导入并保存，共六个网格、六种材质、六张贴图。
- 保存回执：`SourceAssets/LegendaryStock20261006/import-receipt.json`，最终状态为 `six_meshes_six_materials_six_textures_saved`。

保留认可图的连续贴腮、三角镂空、窄金属收边和宽橡胶肩垫。镂空由实体拓扑形成；前端接座封闭，肩垫有实体厚度和横向防滑纹。参考图未展示的背面与底面由本次建模补充，不称为已有多视图的精确还原。

## 作者及后续装配约定

Blender 使用米，UE 导入为厘米；前向为 +X，后托沿 -X 延伸。原点位于前端接座的接触面；所有 FBX 使用相同局部坐标，分件重组时不需要再次加偏移。模型含 Mount／Forward／CheekRest／ShoulderContact 作者标记；后两者为后续装配参考点，不代替具体枪械与手臂接触标定。

V3 整体作者网格为 98,454 个三角形；分件为 Body 21,934、Mount 1,976、CheekRest 25,544、ButtPad 41,556、Controls 7,444。新增截面用于肩垫、背板和相邻托架共用的纵向凹弧，避免长直边跨过曲面。V2 为 75,160 个三角形，V1 为 40,020 个三角形。完整件与分件是两种装配选择，不能同时显示造成重复。此为近景模型制作统计，不是性能测量；未自动减面或进行性能测试。

法线源为 OpenGL 方向，UE 导入开启绿色通道翻转；ORM 为线性纹理。材质保留 WeaponWetness 参数，默认干燥。全部实体使用单面不透明材质。

已完成模型、数值及下述九把枪的专用适配、原厂后托替换逻辑和运行时目录接入。贴腮与长度控制件保留几何结构，尚未制作玩家可操作的调节功能或调节动作。

## 数值定义（2026-10-06）

用户授权设置数值，定位为偏重开镜射击的通用传说后托：

| 属性 | 变化 | stats |
| --- | --- | --- |
| 后坐力指数 | 降低 35% | `recoil_mult: 0.65` |
| 枪械稳定性 | 提高 30% | `stability_mult: 1.3` |
| 开镜耗时 | 减少 10% | `ads_percent: -0.1` |
| 腰射散布系数 | 增加 15% | `hip_spread_mult: 1.15` |

原有高性能后托为后坐力降低 20%、稳定性提高 15%、腰射散布减少 30%；本款提高开镜射击的收益，以腰射表现作为取舍。数值按当前 `GunsmithSystem.cpp::Calculate` 口径记录：开镜为耗时百分比，不是固定毫秒；稳定性为倍率，不是额外 30 点，最终仍受现有评分范围限制。伤害、射速、容量、换弹和射程不增加新修正。

唯一作者数值定义为 `SourceAssets/LegendaryStock20261006/attachment-definition.json`，`option` 使用现有枪匠的 id／name／description／effects／stats 结构，由 `install_catalog.py` 写入活动目录 `Content/ColdSteelData/gunsmith.json`。说明只描述造型和结构，增减由 stats 与对应 effects 表达；后续建模重生成会读取此定义，避免丢失已设数值。

当前运行时的 `common_options` 会无条件为全部武器开放对应槽位；本款只写入九把已适配武器的 stock 选项，没有修改公共 stock。手枪及 ASH12 等一体式后托宿主不开放此改造。

## 枪械接入（2026-10-06）

稳定 ID 为 `legendary_adjustable_tactical_stock`；九把枪共用名称、传说红卡身份、属性及图标，各自加载专用网格：

| 枪械 | 武器定义 | Fitted 网格 |
| --- | --- | --- |
| M4A1 | `ue_m4a1` | `SM_TacticalStock_M4` |
| AKM | `ue_akm` | `SM_TacticalStock_AKM` |
| QBZ191 | `ue_qbz191` | `SM_TacticalStock_QBZ191` |
| M16 | `ue_m16a2` | `SM_TacticalStock_M16` |
| A762 | `ue_a762` | `SM_TacticalStock_A762` |
| SVD | `ue_svd` | `SM_TacticalStock_SVD` |
| PKM | `ue_pkm_lowpoly` | `SM_TacticalStock_PKM` |
| LMG201 | `ue_lmg201` | `SM_TacticalStock_LMG201` |
| HK416 | `ue_hk416` | `SM_TacticalStock_HK416` |

九个网格已保存至 `/Game/Weapons/LegendaryStock20261006/Fitted`。从各枪现有可用后托提取前端实际接触接口，保留约 15–20 mm 接口段，截面封口后以约 10 mm 实体过渡接座连接新后托。旧后托后部不保留，新后托主体不按枪械任意缩放；可编辑源及 FBX 在 `SourceAssets/LegendaryStock20261006/Integration/Editable` 和 `Integration/Exports`，具体文件以 `fitted-models.json` 为准。

适配网格使用各枪 `WPN_root` 的物理厘米坐标，运行时挂接根骨并以 0.01 倍抵消这些宿主的 FBX 根骨百倍缩放；HK416 在制作阶段转换其原有参考坐标。选择时隐藏原厂后托材质段，切换其他后托继续使用既有恢复路径。

`SkeletonStockVisual.cpp::SetGunsmithStock` 接入共用装配入口，覆盖持枪、枪匠预览、背包武器图及掉落武器的现有调用链。`LegendaryTacticalStock.h` 集中维护武器与网格映射，`ColdSteelIconResources.cpp` 提前加载对应网格。传说识别加入 `GunsmithModificationTier.h`，沿用现有红卡样式；存档沿用现有部件 ID 数据，不新增存档格式。`DefaultGame.ini` 已加入资产目录的烘焙引用。

配件图标根据实际模型轮廓制作，使用现有灰阶金属方框标准。运行时 PNG 为 `Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/stock_legendary_adjustable_tactical_stock.png`，UE 图标为 `/Game/Weapons/LegendaryStock20261006/Icons/T_TacticalStockIcon`。图标制作源、提示词及回执保存于 Integration。

后台导入已保存九个适配网格和图标，`FPSGAMEEditor` 与 `FPSGAME` Win64 Development 均构建成功。未启动交互编辑器或游戏，未进行游戏测试、验收截图或验收渲染；仅制作配件交付图标。实际持枪、装卸、存档与各视图表现由用户测试，不把构建及导入成功视为游戏验收通过。

交付回执位于 `SourceAssets/LegendaryStock20261006/Integration/`：`fitted-import-receipt.json`、`icon-import-receipt.json`、`catalog-install-receipt.json`、`native-build-receipt.json`。

## V2：按设定图细化线条与橡胶（2026-10-06）

用户指出整体线条和缓冲垫材质与设定图差距明显。本次继续使用 `Design/concept-02.png`，重制贴腮垫前高后收、下缘下沉的楔形截面；承托壳和香槟金收边沿同一条曲线衔接。托架轮廓与三角孔改为收拢的斜向线条，孔口使用实体圆角；后端改为三角饰片，缩小前端调节件，减少侧面的突起。

肩部缓冲垫改成连续的凸面厚胶体，端部前缘嵌入背板，背面横向防滑沟槽和内圈边界直接写入同一个封闭网格。贴腮垫增加沿下缘的模压接缝。橡胶 UV 改用截面周长与轴向距离展开，保持约 35 mm 的平铺尺度，避免旧逐面主轴投影在曲面转折处切换方向。

橡胶贴图使用原创不规则模压颗粒：约 0.55 mm 单元、细窄沟谷与较宽颗粒表面。法线、粗糙度与少量底色变化共用相同纹理；ORM 的 B 通道在此私有材质中承载底色颗粒系数，金属度由单独参数控制。橡胶为金属度 0、基础粗糙度 0.65、Specular 0.28，保留天气淋湿入口。托架完整涂层保持非金属，香槟金及裸钢饰件为金属度 1；微纹不改为低频脏污。

六个母版网格、六种材质、六张贴图及九个运行时适配网格沿现有资产路径更新；枪型接口、部件 ID、属性、装卸逻辑与存档格式保持原样。无需原生代码构建。共用改造图标以新版实际模型为轮廓，通过内置 imagegen 合成现有灰阶金属方框；制作源、成图和提示词位于 `RefinementV2/`，活动 PNG 键和 Texture2D 路径沿用上文。

V1 的源脚本、可编辑母版、导入记录及 UE 资产备份保存在 `SourceAssets/LegendaryStock20261006/RefinementV2/Before`。本轮模型／材质保存回执为 `RefinementV2/asset-install-receipt.json`，图标回执为 `RefinementV2/icon-import-receipt.json`。未运行游戏测试或验收渲染，视觉效果交由用户体验；图标制作画面不作为实机效果证明。

## V3：肩部接触面的纵向凹弧（2026-10-06）

用户在游戏截图圈出尾部缓冲垫，指出靠肩面应有内凹弧度。V2 的横截面虽已圆润，沿高度的接触线仍近直线；本版重做纵向弧线，中段向枪身方向内收，上下端保留圆润的包肩轮廓。设定图仍为 `Design/concept-02.png`，用户圈注存于 `RefinementV3/user-shoulder-curve-reference.png`。

橡胶肩垫、结构背板、香槟金包边、后端托架和三角饰片使用同一个局部曲率场，前端安装面保持原位。长直边补充沿高度的截面后再形成凹弧，避免弯曲橡胶而让硬背板仍跨成直线。横向防滑沟槽随整片肩垫变形，曲面 UV 的纵向距离重新按弧长展开，肩部接触作者标记同步移动。数值、材质配方、部件 ID 及九把枪的装配坐标不变。

本版继续更新六个母版及九个实装网格，并以新版实际模型更新一张共用灰阶改造图标。V2 源文件及 UE 资产备份在 `RefinementV3/Before`；模型保存与图标保存分别记录于 `RefinementV3/asset-install-receipt.json` 和 `RefinementV3/icon-import-receipt.json`，具体状态以回执为准。图标提示词为 `RefinementV3/icon-prompt.txt`，成图为 `RefinementV3/tactical-stock-framed-icon.png`，使用内置 imagegen 合成既有金属框。

未启动游戏、运行测试或制作验收渲染；图标源图属于交付图标的生产素材，不作为实机观感通过的证据。

## 重建入口

- 建模与导出：`Tools/Weapons/LegendaryStock20261006/author_model.py`，用 Blender 后台执行。
- 导入及保存：`Tools/Weapons/LegendaryStock20261006/import_background.ps1`。已有编辑器时使用现有桥；关闭时使用无界面 commandlet。两条路径共用批次互斥，不启动交互编辑器。
- UE 资产作者脚本：`Tools/Weapons/LegendaryStock20261006/import_model.py`。
- 逐枪适配：先通过 `run_asset_stage.ps1 -ScriptName export_fitting_sources.py` 导出已安装接口，再用 Blender 后台执行 `fit_models.py`，最后运行 `run_asset_stage.ps1 -ScriptName import_fitted.py` 保存新网格。
- 图标：`render_icon_source.py` 制作实际模型图标源，结合已保存提示词与框架参考生成成品；运行 `run_asset_stage.ps1 -ScriptName import_icon.py` 导入现有成品。
- 原生构建：`build_native.ps1` 依次构建 Editor 与 Game，不主动关闭或打开编辑器。
- 活动目录：构建与适配资产保存后执行 `install_catalog.py`，仅修改九个宿主的目标选项；安装前目录备份位于 `Integration/Before/gunsmith.json`。
- 当前 V3 材质与网格更新：依次后台执行 `author_model.py`、`fit_models.py`，再运行 `run_asset_stage.ps1 -ScriptName import_refinement.py`，一次保存母版表面和九套运行网格；不必重新安装数值目录。

模型源、导出、材质和资产身份记录在 `SourceAssets/LegendaryStock20261006/authoring.json`；逐枪适配记录在 `Integration/fitted-models.json`。既有枪械网格和其他后托资产保持原样，新后托使用独立资产路径。
