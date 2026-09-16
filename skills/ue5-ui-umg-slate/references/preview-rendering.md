# 物品与枪械预览：贴图、色彩和透明合成

用于 UE 的 UMG／Slate 实时模型预览。资料读取和制作照常进行；仅在用户要求排查、预览或测试时执行对应检查，不因本参考追加实机验收。

## 将加载与显示质量分开

- 材质对象已赋值，不代表高清贴图 mip 已驻留，也不代表该材质使用的 shader 已就绪。分别定位资产引用、材质同步、贴图流送、网格 LOD、捕获与 UI 合成；不要只凭画面粗糙重做模型。
- `FPreviewScene::ConstructionValues::SetForceMipsResident(false)` 不保证最高贴图精度。离屏预览需要自己的可见资源请求；全局流送池大小不是“正在超预算”的证据，不能因此直接扩大整个游戏预算。
- 在当前网格和覆盖材质确定后收集纹理，装配／材质变化时更新，只为展示集合发起高清请求。使用限时续期或明确的所有权管理；关闭后释放本预览资源，避免永久锁住已卸下配件或清除其他使用者的强制驻留状态。
- UI 等待采用异步刷新，不在 Tick 中 `FlushRenderingCommands` 或阻塞等待全部流送。`HasPendingInitOrStreaming()` 可识别实际初始化／流送；`IsFullyStreamedIn()` 对未挂载的 optional mips 可能一直为 false，不能据此无限保持加载状态。

## 色彩和透明度是不同通道

- UE 5.8 的 `SCS_SceneColorHDR` 输出原始场景色，捕获路径会禁用后处理。只打开抗锯齿 ShowFlag，不能让这条路径自动获得最终色调映射或时序抗锯齿。
- 需要最终显示色时选择对应的 FinalColor／`SCS_FinalToneCurveHDR`，让 RT 格式、线性／sRGB 采样和 Slate 输出保持一致，避免重复 gamma 或直接截断高光。
- FinalColor 的 alpha 受全局后处理设置影响。若 UI 需要透明背景，可独立捕获覆盖率，使用相同几何、投影和分辨率进行合成；不要为一个面板擅自改变全项目 alpha 配置。
- 原始 SceneColorHDR 的 alpha 是反向覆盖率；合成时明确 `1 - A`。保留真实镂空与半透明镜片，不能用按黑色去底代替覆盖率。
- 间歇捕获可以选择空间抗锯齿与受限超采样，避免时序历史不连续。若选择 TAA／TSR，则同时管理持久渲染状态、连续预热以及切枪／投影变化后的历史重置；这些方法按目标质量和预算选用。

## 资源生命周期与不同枪型

- 显示尺寸使用 DPI 后的真实像素，避免以 Slate 逻辑尺寸生成过小 RT；颜色和覆盖率一起调整，设合理最长边和像素预算。
- 近景展示副本可使用 LOD0；不要为预览修改玩法网格的全局 LOD。仍需保留源骨架姿态、部件可见性、安装变换和各枪型实际材质。
- 复用组件切换网格时清理过期 OverrideMaterials，再同步来源材质；材质没变不反复 SetMaterial。动态材质实例参数变化仍需刷新其纹理集合。
- 打开、旋转、换件和资源流送期间提高刷新率，稳定后降频；失效来源及时从预览世界移除。关闭时释放所有捕获组件、RT、画刷及资源引用。

## FPSGAME 当前入口与证据边界

相对工程根 `D:/FPS3D/FPSGAME`：`Source/FPSGAME/UI/M4GunsmithPreview.cpp`、`M4GunsmithPreviewResources.cpp` 和 `M4GunsmithWidget.h`。强化／附魔的 `M4StandalonePreview.cpp` 共用实现；背包图标子系统是另一条捕获路径，不自动视为一起修改。

2026-09-13 实现采用 FinalToneCurveHDR 颜色、无光照覆盖率、至多 2 倍采样／2048 最长边、展示纹理短期续载和活动／静止分档刷新。这些是本机案例参数，不是所有预览的固定标准。Editor／Game 必要构建已完成，未做实际画面与游戏验收，不能写成已验证的视觉范例。

合成材质由 `Tools/AssetPipeline/build_gunsmith_preview_resolved.py` 恢复，依赖既有工作台的 `RT_PreviewDefault`；资产位于已有 cook 目录 `Content/UI/GunsmithWorkbench`。旧背景／环境恢复器不等于新版合成材质恢复器。案例说明见工程 `Docs/UI/gunsmith-preview-quality-20260913.md`。

2026-09-14 剑的展示接入：加工面板经 `M4MeleePreview.cpp` 创建独立静态模型，共用 `world_mesh` 资产、枪械双通道合成及流送；`ColdSteelMeleeIcon.cpp` 在现有图标队列中生成竖向剑图，`ColdSteelMeleePreview.h` 共用轴向与几何居中。枪械／剑的共享表面支持拖动旋转、滚轮缩放和双击复位；剑隐藏瞄准按钮，同一物品普通刷新保留角度。缓存键包含剑模型路径，OnReady 沿用现有背包、装备、仓库和浮窗订阅；面板观察角度不影响固定图标构图。`ColdSteelWeaponIconCatalog` 的 `-Definition=ue_rune_sword` 可仅制作剑目录图，命令行读取物品目录但不初始化玩家存档。制作与构建记录见 `Docs/UI/sword-preview-icons-plan-20260914.md`，不代表实机测试。

## 背包改装图与材质编译（2026-09-16）

- 枪械图标按实例已保存的配件组合实时生成；编辑器下任一参与材质编译失败，整张改装图会静默退回基础目录图，面板本身不报错。用户侧表现就是“只有部分枪的贴图反映改造”。
- 定位顺序：日志 `WeaponIcon: material compile failed …` 与 `WeaponIcon: render failed …; using catalog image` → 对应材质资产 → 修资产本身，不要先改图标管线或复制主题。该放弃任务的分支在 `#if WITH_EDITOR` 内；打包运行不会放弃，坏部件改用默认材质渲染。
- 已知缺陷类：材质里 clamp 已接 `MP_ROUGHNESS`，但 clamp 的输入引脚为空（作者脚本丢线）。这类材质往往同时用于游戏内视图模型，属于资产修复。
- 审计与修复入口：`Tools/UI/scan_weapon_material_clamps.py`、`Tools/UI/repair_weapon_roughness_clamps.py`；资产被运行中的编辑器独占时，用编辑器内最小脚本（仅 `get_material_expressions`／`connect_material_expressions`／`recompile_material`／`save_loaded_asset`）恢复接线，并用 Restart Manager 确认持有进程。
- 不要在交互编辑器的远程执行里调用 `unreal.MaterialEditingLibrary.get_material_property_input_node`：2026-09-16 实测会令 `UnrealEditor-MaterialEditor.dll` 访问违例崩溃编辑器。属性接线查询放到无界面 `UnrealEditor-Cmd -ExecutePythonScript` 进程中。
- 案例与备份：`Docs/UI/backpack-icon-gunsmith-mods-20260916.md`、`Saved/BackpackIconModFix20260916/`。
