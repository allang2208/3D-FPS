# M4 / AKM 改造件与枪身材质统一

2026-09-13，按用户要求逐槽检查当前其他枪械的改造件，补齐材质统一并写入标准工作流。

## 检查结论与修改

当前枪匠支持 M4、AKM、QBZ191。本轮重点为 M4 的 16 个配件网格及 AKM 的 19 个配件网格（含 LPVO 活动环与三个专用瞄具座）；同时读取新后握把的材质身份。QBZ191 前轮独立涂层保留。

| 枪型 | 原有情况 | 本轮处理 |
|---|---|---|
| M4 | 普通前握把、枪口、枪托金属已使用本枪原有材料；瞄具外壳、阻手器金属座与弹鼓紧固件另有材料 | 为四种瞄具、LPVO 环、阻手器金属座、弹鼓紧固件制作对应机匣的独立材质，共 7 个网格版本 |
| AKM | 专用瞄具/桥座、两种枪托和精修三角握把已匹配本枪；直握把、侧倾握把、枪口件和部分弹鼓/阻手器金属仍使用 M4 或早期通用材料 | 补齐直握把、侧倾握把、三种枪口、弹鼓紧固件及阻手器金属座/安装件，共 7 个网格版本 |
| 非金属及功能区域 | 聚合物、橡胶、镜片、分划、刻字、枪口内腔和钛色饰件具有独立用途；新后握把贴图为非金属 | 保留原有材质身份。弹鼓外壳沿用聚合物，本轮修改其金属紧固件；没有将整个配件强制金属化 |

### 材质基准

- **M4**：实际运行机匣 `/Game/Weapons/M4InfimaV3/Body_001`。从当前 `Body_BaseColor`、`Body_Roughness` 取无铭文的机匣区域；使用与原枪相同的 `MF_PhongToMetalRoughness` 转换及实际参数，保持原枪当前反射响应。当前原枪历史导入把粗糙度文件作为 sRGB Shininess 输入，本轮仅匹配该现状，没有修改枪身母材质；不能将这个历史约定写成通用 PBR 标准。
- **AKM**：实际运行 `/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR`。复用已经从同一 Soviet 机匣提取的 `T_AKM_Mount_Base_color/Metallic/Roughness`，与现有 AKM 桥座及专用瞄具一致。
- 涂层使用追加的独立物理投射 UV；既有 UV0/UV1、几何、安装原点、法线、AO、透明及发光输入保留。瞄具金属遮罩与镜筒内壁角点色遮罩共同限制涂层范围。
- M4 机匣区域及颜色空间约定见 `SourceAssets/WeaponAttachmentFinish20260913/profiles.json`；AKM 原始许可与取样来源沿用 `SourceAssets/AKMArmSupport20260911/Metal/provenance.json`。

## 接入路径

部分旧 M4 网格被正在运行的编辑器占用，旧资源覆盖保存失败后改用独立网格版本，避免影响打开的资源。

- 正式变体：`/Game/Weapons/AttachmentFinish20260913/{M4,AKM}/Meshes`，保留原资产短名和材质槽顺序。
- 专用材质及 M4 区域贴图位于同目录的 `Materials` / `Textures`。
- 实际加载入口已更新：`AKMAttachmentVisual.h`、`M4GunsmithVisual.cpp`、`M4DrumVisual.cpp`、`M4HandstopVisual.cpp`。
- 枪匠预览和掉落继续复制同一角色装配入口的网格与材质；倍率环使用 M4 专用版本，AKM 原专用版本保留。`DefaultGame.ini` 已登记新目录用于打包。
- 已打开的编辑器需要重启以加载新的原生模块。未在旧进程中强行替换模块，也未结束用户或其他任务的进程。

## 作者入口与本轮检查范围

`SourceAssets/WeaponAttachmentFinish20260913/` 保留本轮来源读取、原件备份、区域贴图、投射 UV 的可编辑 Blend/FBX、独立材质制作脚本及导入记录：

`inspect_materials.py → export_parts.py → prepare_profiles.py → author_uv.py → import_finish.py`

Blend 保存配件几何与新增 UV，UE 专用材质图由 `import_finish.py` 编辑；Blender 材质不作为 UE Phong 转换的精确渲染替代。

按用户本轮明确检查要求，`check_saved_assets.py` 在新命令行进程读取 14 个已保存变体：230 项资源检查无失败，涵盖槽名/顺序、三角面数、目标材料绑定、引用枪型、涂层 UV 及原法线/AO/透明/发光路径。记录为 `asset_readback.json`。必要 Editor 原生构建成功，记录为 `build.log`。

导入与读回 commandlet 的退出码为 1，日志包含项目原有 GameFeatureData 设置错误；本轮 Python 材质导入和资源读回完成。没有运行游戏、渲染对比、ADS、换弹、射击或存档回归；这些不在本轮完成声明内。

标准已同步到个人技能和工程镜像的 [枪身与配件材质统一](../../skills/ue5-weapon-workflow/references/weapon-finish.md)，并从枪械入口、配件标准、跨枪复用标准及 `WEAPON-WORKFLOW.md` 引用。
