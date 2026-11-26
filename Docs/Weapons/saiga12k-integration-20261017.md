# Saiga 12K 整枪与通用改造件接入 · 2026-10-17

目标工程：`D:/FPS3D/FPSGAME/FPSGAME.uproject`。物品 ID：`ue_saiga12k`；仓库起始军械发放入口已登记，既有档案按原有一次性领取标记补发。

## 初次导入制作与落盘

| 路径 / 通道 | 本次内容 |
| --- | --- |
| `SourceAssets/Saiga12K20261017/Original` | 官方下载的原始 FBX、GLB；原包另存于同级 ZIP |
| `Authoring/Saiga12K_FittedParts.blend` | 11 个可编辑分件；原轮廓、硬边法线与机械身份保留 |
| `Exports/Saiga12K_FittedParts.fbx` | 枪体子装配导出；运行时原生骨架装配由生产脚本完成 |
| `/Game/Weapons/Saiga12K/Integrated20261017/SK_Saiga12K_Manny` | 当前 AKM 原生骨架与 V9 裸手，替换枪体，重建 LOD 和 21 个手臂矫正形状 |
| 同目录 `Materials/MI_Saiga12K_*` | 11 个语义材质，钢件与聚合物分开，沿用 WS1 母材质 |
| `items.json`、`gunsmith.json`、`combat-weapon-formulas.json` | 独立霰弹枪、八发弹匣、12 号弹药组与整发伤害公式 |
| `modular_outfits.json` | 复用当前 AKM 原生手臂的衣袖／手套适配，基础视模直接为裸手 |
| 装备、掉落、图标资源清单、起始军械 | 新定义加入实际调度；按现有档案协议保存弹量与弹种 |
| 角色开火、准心、服务端命中预算 | 鹿弹／箭型弹按弹丸分摊整发伤害；独头弹使用单弹丸口径 |
| 换弹业务、机械声 | 弹匣式装填和空仓拉栓；复用 AKM 的动作、动作时钟与事务，不走管式逐发装填 |
| 枪口／ADS／抛壳 | 本枪独立的 root-local 标记；使用 12 号空弹壳 |
| `Content/ColdSteelData/Icons/ue_saiga12k.png` | 原生目录图制作器已输出 640×320 透明底图标，与运行装配共用模型和材质 |
| 打包配置、署名 | 新武器 cook 目录；CC BY 4.0 署名随现有 Licenses 目录打包 |

## 动作与声音

同骨架、同轨迹直接引用共享序列：待机、瞄准、开火、瞄准开火、检视来自 `AKMIntegration/SourceMatched`；普通与空仓换弹来自 `AKMIntegration/SovietFab/ReloadPolish/base`；装备来自 `AKMIntegration/EquipCharge`。冲刺与快速近战复用现行 AKM 家族。没有导出重复的整套动作，未额外创建无差异的姿态配置。

枪声引用现有 `Super90/GameDevAudio20261007/S_Super90_Fire`；换匣与拉栓引用 `AKM/VideoAudio20260921`；空击和命中声沿用共享原有入口。此处是本项目内复用，模型的 CC BY 许可不扩展到手臂、动作或声音。

手部握点以当前 AKM 枪的握把位置注册，Saiga 原模型统一缩放 1.25（枪体全长约 90.23 cm），不逐件拉伸。腰射采用共享右腕基准和独立保存的展示偏移，机瞄按本枪后照门／前准星计算完整方向及滚转。制作参数是初始接入配方，尚未经用户实机确认。

## 枪匠范围

当前版本支持按住左键连续射击，松开停止；沿用原有开火、换弹和动作中断状态机。标准射击间隔仍为 0.22 s，原厂弹匣为八发，十二发扩容改造见文末追加记录。`inherit_common_options=true`，共用热成像与赐福激光定义。

| 槽位 | 已接入选项（不含原厂） |
| --- | --- |
| 瞄具 | 全息、EOTH 全息、全景红点、2 倍棱镜、1–6 倍镜、热成像 |
| 枪口 | 霰弹枪喉缩、鸟笼消焰器、消音器、鸭嘴 |
| 前握把 | 垂直、战术垂直、斜握把、棱镜止滑器、倾斜握把 |
| 后握把 | 幻影、防滑、平衡 |
| 枪托 | 骷髅、核心、QR 性能、战术伸缩、传说可调战术枪托 |
| 战术挂件 I / II | 两侧各支持激光、手电、赐福激光 |
| 弹匣 | 仅原厂八发 |

通用件保持现有属性与物品 ID；26 种通用件形成 29 个非原厂安装选项（包含双侧挂件）。适配模型、安装座和材质保存于 `/Game/Weapons/Saiga12K/Common20261017`，共 37 个网格和 4 份握姿配置。瞄具保留源 `Aim`、变倍环与选择器；固定机瞄在抬高的光轴下方。枪托与后握把按独立原厂材质槽隐藏，第三人称同步该隐藏状态。枪口端点、消音音效、消焰倍率和鸭嘴散布按当前安装配方生效。战术发射器正向与双侧模型同时烘焙到本枪 root 坐标。

握姿复用 AKM 共享基础序列和稀疏差量，握把接触位置保持不变；安装座按 Saiga 护木与机匣接面制作。通用改造件图标沿用既有共享图标；组合图按当前配方异步加载新资产。

游戏初始数值：整发基础物攻 80、弹匣 8、间隔 0.22 s、普通换弹 3.333333 s、空仓换弹 4.291667 s、有效射程 25 m（2026-10-19 由 35 m 下调；同日起霰弹枪只在有效射程内造成韧性伤害，见 [枪械默认不造成韧性伤害](../Combat/firearm-toughness-damage-20261019.md)）。它们是游戏调参，非现实性能承诺；弹种倍率与角色成长继续由现有权威数据计算。

## 生产入口与记录

- `Tools/Saiga12K/read_source.py`：读取源几何与机械分件制作输入。
- `Tools/Saiga12K/produce_assets.py`：后台生产与保存骨骼网格、材质、LOD、手臂矫正形状。
- `Tools/Saiga12K/save_editable_source.py`：后台保存分件 Blend 与 FBX，不渲染预览。
- `Tools/Saiga12K/register_data.py`：首次登记本枪目录；遇到已有定义停止，不覆盖后续改动。
- `Tools/Saiga12K/build_catalog_icon.ps1`：只生成本枪目录 PNG，不加载／写入玩家档案。
- `Tools/Saiga12K/build.ps1`：等待本机共享构建和 UE 资产进程结束，再完成 Editor／Game 常规构建。
- `SourceAssets/Saiga12K20261017/Receipts/assets.json`、`data.json`、`build.json`：资产、数据、构建分别记录。
- `Receipts/source_files.json`：本次源码／配置路径；`SourceBefore` 保留写入前现场，仅作差分来源，不能整文件回退共享代码。

模型作者与许可：[TastyTony 的原始模型](https://sketchfab.com/3d-models/low-poly-saiga-12k-e9887136eaf14be396bdbea54f76ff3d)，[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。背景介绍参考 [Saiga-12](https://en.wikipedia.org/wiki/Saiga-12)。

未启动交互编辑器、PIE 或游戏；未做动作、画面、音效、联机或打包验收，由用户测试。资产保存和编译结果不能代替上述验收。
## 本次构建中的接口修复

首次 Editor 构建遇到 `Monsters/NightWardenFootPlantNode.cpp:40` 的两个 `HasCurveData` 调用缺参。UE 5.8 的基类第二参数默认 `false`，但 `UAnimSequence` 重写声明没有默认值；本次只给两个调用补上显式 `false`，使其符合相同运行时语义。首轮错误日志保留为 `Receipts/first-attempt-build-FPSGAMEEditor.log`；最终构建结果以 `Receipts/build.json` 为准。

## 最终落盘状态

- Editor 常规构建目标成功，增量结果为 `Target is up to date`；Game 目标成功并链接 `Binaries/Win64/FPSGAME.exe`。分别见 `Receipts/build-FPSGAMEEditor.log`、`build-FPSGAME.log` 和 `build.json`。
- 原生目录图制作进程退出 0，`WeaponIconCatalog: COMPLETE failures=0`；640×320 PNG 已保存。此项是图标资产制作，不是游戏或画面验收。
- 资产、数据、作者源及本次构建回执汇总在 `Receipts/delivery.json`。未测试，由用户体验。

## 2026-10-17 连射与通用件追加

- 生产脚本：`Tools/Saiga12KCommon/produce_assets.py`、`save_lods.py`。只保存本枪独立的配件资产；整枪骨架与原生手臂不重导入。
- 制作来源与槽位清单：`SourceAssets/Saiga12KCommon20261017/sources.json`、`inputs.json`、`integration.json`。
- 实际资产保存回执：`SourceAssets/Saiga12KCommon20261017/Receipts/assets.json`，后台生产退出码为 0。
- 本次构建及 LOD 保存结果记录在同一追加目录的 `Receipts` 下；上文原厂导入构建记录仅代表原厂版本。
- 未做运行、动作、画面、音效或联机测试，由用户测试。

### 追加版本落盘结果

Editor 与 Game 常规构建成功，均为退出码 0；Game 产物为 `Binaries/Win64/FPSGAME.exe`。25 个改变了安装几何的网格已从 Saiga LOD0 生成 100% / 50% / 25% 三级 LOD，保存进程退出 0；其余保留共同母件的原有 LOD。最终记录为 `SourceAssets/Saiga12KCommon20261017/Receipts/delivery.json`。首次 Game 构建的头文件相对路径错误已经修复；共享天气代码的同名局部变量错误在本次重建前已由当前工作区更新解决，本任务未覆盖该文件。未进行运行测试。

## 机匣盖与 WS1.1 表面修订 · 2026-10-17

当前运行枪体为 `/Game/Weapons/Saiga12K/Refined20261017/SK_Saiga12K_Manny`，通用件为同目录 `Attachments`。原厂和 Common 版本保留作来源；本段取代它们作为当前材质与几何版本的描述。

源机匣盖的开口延伸至顶部，而且原 GLB 材质均声明双面。此次以上盖完整一侧恢复连续顶面，保留原外形曲线，增加 0.7 mm 实体壁厚及 0.18 mm 接口圆角；侧面另开低于顶面与肩部的抛壳口。盖内表面单独使用消光材质。其余原始薄片采用本枪实例的双面覆盖，未修改共享母材质。

枪体共 5,165 个三角形，原有机械骨骼、挂点和动作不变。枪体重新展开唯一 UV0/UV1；只替换枪体区域，手臂原生四套 UV、权重、21 个 V9 矫正形状沿用。2K SurfaceMask 在就位装配中烘焙，RGBA 为凸边／凹腔／AO／暴露度，线性 Masks 压缩；材质读 UV1。钢、聚合物、枪机、弹壳和盖内腔按 WS1.1 分槽建立实例，以 `M_WeaponSurface` 的 Clean 预设为父级，采用厘米尺度细纹和同一湿润层。颜色使用 `FinishColor`，不沿用初版错误的无效 `BaseColor` 覆盖。

37 个静态配件及安装座另存独立修订，保留原 UV、结构法线、安装变换、插座和已生成的 LOD。普通钢件、聚合物、橡胶及凹腔分别绑定本枪实例；玻璃、分划、发光、饰色与混合光学外壳保留原着色分支，混合外壳仅使用自身涂层参数。每个材质与实际槽绑定记录在 `SourceAssets/Saiga12KRefine20261017/Receipts/assets.json`，制作输入包含实际继承纹理、参数和透明模式。

本版生产入口：`Tools/Saiga12KRefine/author_surface.py` → `install_assets.py` → `activate.py` → `build.ps1`。可编辑源为 `SourceAssets/Saiga12KRefine20261017/Authoring/Saiga12K_Refined.blend`，FBX 和引擎装配 JSON 同目录保存。旧 `Tools/Saiga12K` 与 `Tools/Saiga12KCommon` 入口保留用于历史版本，不用于本版重导。

自动连射、原厂八发弹匣、所有改造选项及属性不变；衣袖／手套配置已登记新网格路径。编译及目录图标制作状态以本修订目录 `Receipts` 为准。未启动游戏、截图或验收渲染，视觉效果由用户测试。

### 机匣盖与材质修订最终交付

新枪体、2K 表面遮罩、37 个配件/安装座及其材质已保存；Game 和 Editor 常规构建均退出 0。目录图标已由新版运行装配重新生成，生产进程退出 0。按本次明确授权结束编辑器使用窗口，完成后保持交互编辑器关闭。回执：`SourceAssets/Saiga12KRefine20261017/Receipts/delivery.json`。未做实机、画面、音效或联机验收。

## 圆弧准星与十二发弹匣 · 2026-10-17

`ColdSteelCrosshair.cpp` 的霰弹枪圆弧入口由管式判定改为 `IsShotgunWeapon()`，12K 共用四段开口圆弧、动态散布半径及鸭嘴配件的椭圆显示；开镜时沿用既有隐藏规则。

新增本枪专属 `magazine / saiga12k_ext12`「加长弹匣」。基础八发不变，安装后增加四发，容量为十二发；沿用扩容类代价，装填耗时增加 25%，开镜耗时增加 5%。选项描述仅叙述匣体形态，数值通过属性显示。通用容量计算、装备实例与存档按这个选项 ID 处理。

作者源从当前 Refined 枪体的 `Saiga12K_Magazine` 材质区取件。以原厂壳体成对站点拟合中心曲线，保留插接颈、卡笋及上方抓握区域；在下段插入 7 cm 弧长，将原底板沿同一圆弧移动并旋转约 10.51°。原有外形筋条随截面连续延伸，不整体拉伸原厂件。制作后 LOD0 为 2,112 个三角形，保存 100% / 50% / 25% 三级 LOD。

静态网格保存于 `/Game/Weapons/Saiga12K/ExtendedMagazine20261017/SM_Saiga12K_Ext12`。模型已转换为原生 `WPN_SOCKET_Magazine` 坐标，以 0.01 比例接入继承 100 倍缩放的骨骼；沿用本枪普通与空仓换弹轨迹。安装时隐藏原厂弹匣材质区，卸下时恢复；第三人称与掉落外观继承该隐藏状态及挂载静态件。该专属 ID 走骨骼随动分支，不触发弹鼓抛落动作。

材质实例继承当前原厂弹匣的 WS1.1 聚合物配置，使用新弹匣独立的 UV1 与 1K SurfaceMask；未重用枪体 UV1 遮罩。图标由实际模型以安装姿态的水平侧视渲染，再通过内置 image_gen 合入现有批准的灰阶金属方框。实际 PNG 键为 `FramedFirearms/ue_saiga12k_magazine_saiga12k_ext12.png`，同名 Texture2D 已导入并保存，采用 UI 组、Editor Icon 压缩、sRGB、Never Stream。生成方式、完整提示词和源图映射保存在 `SourceAssets/Saiga12KMagazine20261017/Icons/generation.json`。

本轮作者场景、配方、烘焙、导入和构建脚本分别保存在 `SourceAssets/Saiga12KMagazine20261017` 与 `Tools/Saiga12KMagazine`。资产回执为 `Receipts/assets.json` 和 `icon.json`；本轮构建结果单独记录在 `Receipts/build.json`。本轮没有进行游戏、动作、画面或联机测试，交由用户测试。

本轮 Game 与 Editor 构建均已完成，退出码均为 0（2026-10-18 凌晨收尾），汇总见 `SourceAssets/Saiga12KMagazine20261017/Receipts/delivery.json`。首轮 Game 编译被共享天气代码的旧字段名阻断；仅将 `FPSUDSHillsAtmosphere.cpp` 中一处 `PreviousFog->FogInscatteringColor` 改为 UE 5.8 现有的 `FogInscatteringLuminance`，方向散射字段已由共享工作区同步修正。首轮日志保留，没有覆盖其他天气逻辑。按此前授权正常结束 PIE 并关闭交互编辑器，本任务未重新打开编辑器。未进行游戏或验收测试。

## 全面表面重建与整体检查 · 2026-10-18

当前运行版本切换到 `/Game/Weapons/Saiga12K/SurfaceRebuild20261018`。本轮用户明确要求先出方案和成品目标预览，再重建表面并整体检查；方案保存在 `SourceAssets/Saiga12KSurface20261018/plan.json`，完整图文报告为同目录 `Report.html`。`Preview/12K_TargetPreview.png` 是内置 image_gen 制作的设计目标；`Actual_*` 是实际模型 Cycles 渲染，`SavedUE_Hero.png` 使用独立进程从 UE 保存资产读回的几何。三者的性质分别记录，不将目标图当作游戏截图。

### 几何与表面

| 对象 | 本轮结果 |
| --- | --- |
| 原厂枪体 | 从 5,165 到 88,834 三角形，不含手臂；17 个枪体材质区域 |
| 上盖 | 连续弧形实体壳，0.7 mm 壁厚，保留侧面抛壳口与内壁，补纵向压筋 |
| 枪管／导气组件 | 以原就位坐标重建连续曲面、端环、内孔与过渡，保持枪口和机瞄标记 |
| 机匣与控制件 | 整理平面、边缘和角点法线，重建圆形固定件，保留原机构与独立机械骨骼 |
| 聚合物外壳 | 护木、后握把、枪托按原截面包络重建，恢复凹面装饰，补握把和托垫规则防滑筋 |
| 原厂与十二发弹匣 | 保留插接段、原曲线、底板和换弹骨骼，补纵向筋条；十二发件为 5,104 三角形 |
| 通用配件 | 37 个网格保留几何与 LOD，使用本枪私有表面实例调整对应金属参数；玻璃、分划与发光身份保留 |

沿用 WS1.1 母材质，未修改公共母材质或公共预设。主体关闭 `GrainRoughness`、`MottleRoughness`、`MottleColor`、`Stipple`、随机划痕及统一磨损，通过真实边缘与结构法线提供细节。机匣盖粗糙度 .36、枪机 .31、普通深色金属 .39、聚合物 .50、橡胶 .68、内腔 .75；纯金属和非金属区域分别使用 Metallic=1/0。深色金属配色沿用项目 Clean 外观配方，不作为裸钢实测反射率。

枪体使用 4K 结构法线及 2K SurfaceMask，十二发弹匣使用 2K 法线及 1K 遮罩。源法线为 OpenGL，UE 导入只翻转一次绿色通道，采用 Normalmap 压缩、关闭 sRGB；遮罩线性 Masks，UV1，法线走 UV0。没有新增整面颗粒法线。保留纹理 mip 与流送。扩容件保留 3 级 LOD，第一人称骨骼网格及通用件沿用原 LOD 方案；未测量帧率收益。

### 本轮检查结论

- 枪体及扩容件：坐标／法线／UV 全部有限，零面积面与退化 UV 均为 0；法线向量长度正常，法线贴图有效区域 Z 均值约 .994。
- 已独立读回 39 份网格：材质槽与保存配方一致，没有默认网格材质回退；法线压缩、采样、绿色翻转、遮罩及颗粒参数符合本轮配方。
- 37 个通用件：数值比较的包围盒与 LOD 数保持一致。初版检查脚本的结构体身份比较已改成数值比较，不把不同包装对象误判为几何变化。
- 手臂 37,086 个三角形的坐标、角点法线、全部四套 UV、权重指纹与基线一致；骨架、骨变换和 21 个矫正形状名称一致。枪体有效骨骼权重错绑数为 0；零权重占位项不当成影响骨骼。
- 已查看整体、反侧、机匣近景、顶面、扩容弹匣和 UE 保存几何读回渲染。上盖顶面连续，功能性抛壳口和弹匣开口保留；制作中发现的扩容件全局倒角塌面与退化 UV 已修正。
- 新拆分的 `Saiga12K_StockPad` 随原厂枪托一起隐藏／恢复，第三人称、掉落快照同步该隐藏状态。

Game 与 Editor 构建均成功，完整记录为 `Receipts/build.json`。扩容件图标根据当前实际模型更新，运行 PNG 与独立 Texture2D 已保存；生成提示词及映射见 `Preview/generation.json`。整枪目录图通过当前编译定义的离屏 commandlet 生成，结果另记 `Receipts/catalog.json`。

本轮检查范围是本枪模型、材质、保存资产与离线外观。全自动、圆弧准星、八发／十二发容量、通用配件数值及存档身份保持原有逻辑；没有进行 PIE 动作回归、帧时间采样或联机测试。图文报告和回执明确区分这些范围。


## UE 漏面实修与母材纠正 · 2026-10-18

用户的实机截图推翻了前两轮仅凭离线几何预览作出的外观结论：UE 实际存在背面剔除、结构裂缝与法线重算。此前的 SurfaceRebuild／Detail 离线报告不能作为 UE 外观验收。

本轮修正 Blender→UE 角点绕序，缝合结构开放边界，重建弹匣自交筋条，保留作者法线并重烘结构法线。母材仍使用 WS；混合配件使用私有金属区域涂层，保留光学与湿润分支。枪匠对本枪降低柔光强度，避免发白。

正式网格路径保持 `/Game/Weapons/Saiga12K/Detail20261018`，共 39 份资产已更新；私有材质／纹理为 `Closure20261018`。原资产备份、作者源、脚本与真实 UE 对照保存在 `SourceAssets/Saiga12KClosure20261018` 和 `Tools/Saiga12KClosure`。实际报告为前者的 `Report.html`，完整回执为 `Receipts/delivery.json`。手臂、机械骨骼、全自动、圆弧准星及容量逻辑保持原合同。

已按用户要求检查结构、材质、39 份保存资产与实际 UE 离屏外观；Game／Editor 已构建，目录图标已更新。未进行射击、换弹动作、帧时间或联机测试。
