# ST6 酒红贝雷帽：模型、材质与游戏接入

用户于 2026-10-23 要求将 ST6 头盔占位物改成贝雷帽，先做精细建模，随后提升材质与细节并接入游戏；明确选择酒红帽体、黑皮帽箍、暗银帽徽。

## 造型与结构

- 帽冠向佩戴者右侧自然偏垂，左前侧形成帽徽支撑区；局部斜褶、收拢褶与顶部偏心形体由几何生成。
- 羊毛毡壳体厚约 1.8 mm，独立内衬厚约 0.55 mm；黑皮帽箍约 1.2 mm 厚，带卷边、内侧回折和双道实体针脚。
- 后部两条调节绳与绳结；侧面两处真实布尔通气孔及暗银孔圈，布尔工具保存在独立集合内。
- ST6 原创盾形帽徽由贴合帽面的皮革底托、倒角金属盾、氧化凹面、翼形浮雕、中央矛形纹与立体 ST6 字样组成。各件可独立修改。
- 酒红毛毡、黑皮、内衬各有原创 BaseColor、OpenGL Normal、ORM、16 位 Height，共 12 张贴图。毛毡 2K、皮革与内衬 1K；真实物理重复尺度随制作配方保存。

## 文件与后续接续

- 可编辑源：`SourceAssets/ST6Beret20261023/SurfaceV2/Exports/ST6_Beret_Burgundy_Editable.blend`
- 带材质模型：`SourceAssets/ST6Beret20261023/SurfaceV2/Exports/ST6_Beret_Burgundy.glb`
- 独立 HatRoot 绑定导出：`SourceAssets/ST6Beret20261023/SurfaceV2/Exports/SK_ST6_Beret_Burgundy.fbx`
- 重制入口：先运行 `Tools/ST6Beret/make_textures.py`，再以 Blender 后台执行 `Tools/ST6Beret/author.py`。
- `authored.json` 为本轮导出回执，`fit_candidate.json` 保存头部参照、尺寸、坐标约定与候选挂接变换。

Blender 中分为可编辑部件、独立 HIGH 毛毡细节层、Jason 头部参考和通气孔工具四个集合。高模包含细分及实际高度位移；参考头、高模与布尔工具均排除在 FBX／GLB 导出之外。字体在母版中保持可编辑，导出中转换为网格。

第一版详细导出含 20 个部件、127,878 个三角形。该数量是模型导出统计，不是实测渲染性能；升级版的游戏 LOD、材质与挂接见下文。

帽口使用现有 Jason 原生头部作者数据制作，椭圆半径约 8.80 × 9.44 cm；帽箍原点对应参考身体 Z=168.75 cm。佩戴效果及头发适配尚未进行实机验证。

## SurfaceV2 材质与细节升级

第一版作者源已归档至 `trash/Equipment20261025/SourceAssets/ST6Beret20261023`，不再用于生产。当前制作目录为 `SourceAssets/ST6Beret20261023/SurfaceV2`，升级内容如下：

- 酒红毛毡增加交错短纤维、细颗粒和多尺度粗糙度；游戏材质使用 Cloth 着色的绒面响应。
- 黑皮帽箍使用细皮纹、压痕与微表面遮蔽；保留卷边、双道针脚和独立内衬。
- 暗银帽徽增加方向性细拉丝、氧化与粗糙度变化；保留立体翼纹、矛形纹和 ST6 字样。
- 新增后部调节绳端套、内侧织标与内标文字，共 23 个可编辑部件。完整近景源为 145,790 三角形、8 个材质槽。
- 毛毡、皮革、内衬、暗银四组原创贴图，各含 BaseColor、Normal、ORM 和 16 位 Height，共 16 张。UE 使用前三类，Height 保留用于离线高模制作。

`SurfaceV2/Exports` 中保存更新后的 `.blend`、`.fbx`、`.glb`；`Authored/hat.json` 是游戏静态网格制作源，`materials.json` 保存材质槽对应关系。另已制作正式 320×320 库存图标；该渲染用于物品资源制作，未追加效果预览或验收截图。

## 游戏接入方式

- 继续使用 `ue_st6_tactical_helmet`，显示名更新为“ST6 酒红贝雷帽”。原防御、强化系数、价格、格子占用和 ST6 套装加成沿用既有定义。
- 佩戴网格通过现有 `head_equipment` 静态网格分支挂接 `head` 骨骼，使用原生头部的独立适配变换。2026-10-24 已将男女角色的 `covers_scalp_hair` 改为 false，保留帽外发型；原先 true 会隐藏整束女性长发，详见[头饰与发型可见性](headwear-hair-workflow.md)。没有新增逐帧逻辑或物理模拟。
- 独立提供佩戴、居中掉落、库存展示网格，以及正式库存图标。静态网格保存三个 LOD；远处 LOD 采用既有资源制作流程的 55%／30% 简化比例。
- 资源目录为 `/Game/Characters/ModularOutfit20260924/ST6Beret20261023/SurfaceV2`，已处于项目既有 Cook 目录内。
- `ColdSteelProfileRuntime.cpp` 为这件物品补齐旧实例的图标和世界模型引用刷新，使旧存档中的占位装备可以读取当前外观；不重建物品实例或修改强化数据。
- `publish.py` 使用共享配置事务，只拥有 `head_equipment/ue_st6_tactical_helmet`；物品目录只更新该条目的外观字段，并保留写入前副本。

## 制作入口与落盘回执

制作脚本现默认写入 SurfaceV2；也可在项目根目录显式设置 `ST6_BERET_ROOT` 为 `D:/FPS3D/FPSGAME/SourceAssets/ST6Beret20261023/SurfaceV2`，依次运行：

1. Python 执行 `Tools/ST6Beret/make_textures.py`。
2. Blender 后台执行 `Tools/ST6Beret/author.py` 与 `Tools/ST6Beret/prepare_delivery.py`。
3. PowerShell 执行 `Tools/ST6Beret/run_asset.ps1 -Script save_assets.py`，通过共享 UE 批次锁保存资源。
4. PowerShell 执行 `Tools/ST6Beret/build.ps1`，后台构建 Editor 与 Game。
5. Python 执行 `Tools/ST6Beret/publish.py`，发布物品外观与头部挂接配置。

`authored.json` 记录作者源和图标制作阶段；`saved_assets.json` 记录实际 UE 资产保存阶段；两个 `build-*.json` 记录构建结果；`published.json` 记录配置发布阶段。作者源回执中的 `unreal_imported: false` 仅表示该制作步骤没有执行导入，后续保存状态以独立回执为准。

首次 Editor 构建被 `ProductionRuneboundPassive.cpp` 的 const 材质指针调用非 const `GetBaseMaterial()` 阻断（C2662）。为完成项目构建，仅将该局部材质指针由 `const auto*` 改为 `auto*`，不修改符文行为；首次失败回执单独保留为 `build-FPSGAMEEditor-attempt01.json`。

作者源、库存图标、UE 资产保存与配置发布均已完成：`saved_assets.json` 和 `published.json` 均为 `completed: true`。首次资源保存批次 `beret-surface-v2-save-01` 正常退出；必要的 Editor／Game 构建均已成功，两个 `build-*.json` 的 `exit_code` 均为 0。没有主动打开 UE 编辑器或游戏，也未进行佩戴、动作、联机或性能测试。游戏中的最终效果由用户自行测试。
