# ST6 配套裤靴与七分裤腰围调整

按已确认的 ST6 战术长裤／战术靴设计图制作，配套 `ue_hardknuckle_gloves` 与 `ue_st6_sleeves`。采用本地精确建模、物理尺寸的表面高度场及 PBR 制作，沿 Jason 原生骨架复用现有身体动作。没有增加套装加成、动画系统或布料模拟。

## 模型与材质

- ST6 长裤：连续焊接的腰臀、裆部与裤腿；按身体不对称腰背截面贴合腰围，收窄小腿与裤口。实体腰带、扣具、腰袢、斜插袋、低轮廓腿袋、卡其护膝框、黑色圆弧硬壳护膝、后膝伸缩裁片、裤口调节片及缝线。普通裤身与短靴、高筒靴、ST6 靴专属收口版共四份，完整截面一起变形，包边和装饰保持层间距离。
- ST6 靴：复用项目作者脚楦的原生尺寸，重新制作中高筒结构、黑色护趾／后跟／踝片、卡其鞋面框、织物区、鞋舌、鞋带、鞋眼、后跟活动褶、软靴口和实体齿纹鞋底。沿 calf／foot／ball 原生骨骼衔接，不新增骨骼或刚体。
- 四套原创 1024² 平铺表面：灰色织物、卡其皮革、黑色橡胶／硬壳、黑色弹力织物。颜色、Normal、ORM 使用同源实际高度场；OpenGL 法线导入 UE 时翻绿。保留 mip 和纹理流送。隐藏的 `BAKE_ONLY_SurfaceFields` 集合保留实际位移表面源，不进入运行导出。
- 穿戴使用原身体蒙皮和 Leader Pose。靴筒上方补回被鞋靴遮挡区段连带隐藏的原生小腿，使用原 UV、法线和权重；图标和掉落模型不带皮肤。

原始衣服／手套、基础身体、动作、相机与其他裤型不更改。新装备防御与价格沿普通工装裤／系带靴的基础档位，未额外赋予速度加成或减速。

## 七分裤修订

旧裤腰使用以 Y=0.8 cm 为中心的对称椭圆，顶部半宽 17.1 cm、前后半径 12.7 cm；同高度实际腰部左右半宽约 14.3 cm，后腰轮廓明显更浅。新腰口按原生身体水平截面拟合，布料主面保留约 5.5 mm 余量，85–96 cm 高度区间渐变衔接旧臀围。

腰带、腰袢、袋边与缝线共用同一连续变形，法线按变形雅可比变换。普通版和高筒靴版同时更新；之前的原生腰部皮肤补片、小腿补片、已焊接裆缝与骨权重保留。皮肤不随裤腰缩放。未改裤长或七分裤原布料。

新版穿戴、掉落和图标使用 ST6 制作目录下的独立 `CapriTailored` 包，原物品 ID `ue_smoke_grey_capri` 不变。旧资产保留。原 `author_geometry.py`、`save_assets.py` 入口与可编辑 Construction／穿戴 Blend 同步，使后续重制保留拟合腰口。

## 接入矩阵

| 物品／搭配 | 穿戴源 |
| --- | --- |
| `ue_st6_tactical_pants`，裸足／运动鞋 | `SK_Jason_ST6Trousers` |
| ST6 长裤＋系带皮靴 | `SK_Jason_ST6Trousers_ShortBootsFit` |
| ST6 长裤＋铠甲靴／棕色皮靴 | `SK_Jason_ST6Trousers_HighBootsFit` |
| ST6 长裤＋ST6 战术靴 | `SK_Jason_ST6Trousers_ST6BootsFit` |
| `ue_st6_tactical_boots` | `SK_Jason_ST6Boots`，含靴口以上必要原生皮肤 |
| 七分裤普通版 | `SK_Jason_CapriTailored` |
| 七分裤＋高筒靴／ST6 靴 | `SK_Jason_CapriTailored_HighBootsFit` |

活动 rig 为 `Jason`，本机身体和世界身体共用；不恢复已退役的 `JasonFirstPersonLegs`。裤装槽 15、鞋靴槽 13，均使用现有装备、背包、仓库、拾取和存档流程。新增物品 2×3 格，通过开发物品目录可取得；不写入用户库存，不追加掉落或商店规则。

## 文件与重制

- 概念参考：`SourceAssets/ST6LowerSetDesign20261018/`。
- 制作目录：`SourceAssets/ST6LowerSet20261018/`；`ST6_LowerSet_Editable.blend` 为带原生骨架、打包材质、搭配版本和表面高模的编辑源，`Exports/` 为 FBX。
- UE 资产根：`/Game/Characters/ModularOutfit20260924/ST6LowerSet20261018`。
- 正式图标：`Content/ColdSteelData/Icons/ST6LowerSet20261018/`。
- 制作入口：`Tools/ST6LowerSet/prepare.py` → `build_pants_script.py`／Blender `author_pants.py` 和 `author_boots.py` → `bake_surfaces.py` → `prepare_runtime.py` → Blender `save_editable.py` → `save_assets.py` → `publish.py`。
- 七分裤：`repair_capri.py` 使用已保留的制作源和原生腰部表面字段，`update_capri_construction.py` 同步构件母版；`Tools/SmokeGreyCapri/waist_fit.py` 是两套裤子的共同腰围方法，生产输入 `waist_fit.npz` 必须保留。
- 原生来源：项目已有 Jason 身体、原生 Jeans 绑定供体、作者脚楦／几何助手。密集网格、骨权重和许可素材仅留本地，未公开分发。

## 交付状态边界

实际资产保存以 `saved_assets.json` 的 `completed` 为准，目录接入以 `published.json` 为准；仅脚本或生成源不作为导入完成的凭据。生产图标来自实际模型，不以概念图代替。

本次不主动启动交互编辑器、PIE、游戏，也不追加静态测试、动作测试、穿插检查或验收截图。必要材质编译、网格／LOD 构建和保存属于制作。没有实测性能、视觉或联机验收结论；实际穿戴效果由用户测试。
