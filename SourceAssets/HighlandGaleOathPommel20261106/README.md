# 风誓轻量配重锤

当前接入版本为 **SurfaceR2**；被替换的 V1 母版与初次检查图已按清单归档到 `trash/HighlandSword20261106`。

- 高地双手剑专属，配重锤槽，ID `highland_gale_oath`，类别为特殊改造。
- 持用该剑时奔跑体力消耗 ×0.85；切换武器或使用采集工具时不生效。原唐刀护手通道独立保留，避免重复乘算。
- 重击蓄力速度加成 +0.20，使用现有统一蓄力公式。无其他加成时，2 秒基础蓄力变为约 1.667 秒。蓄力速度加成不改变出手阶段速度。
- 不改变其他伤害、攻速、重量或耐久属性。

## 模型与截图

`SurfaceR2/Highland_GaleOath_Editable.blend` 保留可编辑分件、设计图与隐藏的真实握柄参考；`SurfaceR2/Highland_GaleOath_GameModel.blend` 为带贴图导出母版，FBX/GLB 在同级 `Export`。纹理为 4096px BaseColor、OpenGL Normal 与 ORM（R AO、G Roughness、B Metallic）。

R2 将原三角面驱动的内沿坡面改为固定物理圆角，并提供连续侧壁法线；在烘焙前固定三角化。接口保持原厂局部 Z=0、+Z 朝剑尖，挂载 Z=-22.7cm。

`SurfaceR2/Review20261106` 内含正面、斜侧、背面、真实握柄衔接四张模型截图，已逐张查看。这些是 Blender 实际游戏导出母版渲染，不是 UE 游戏截图。V1 检查时发现的内沿碎面与侧壁高光断裂已在 R2 修订；后续 2026-11-06 完成 38 项隔离检查与 7 阶段真实 UDP 检查（装备、属性、重击 RPC、重连），未做实际渲染的双人战斗验收。结果见 `Tools/HighlandNetworkAudit20261106`。

UE 网格：`/Game/Weapons/HighlandClaymore20260922/GaleOath20261106/SurfaceR2/Meshes/SM_Highland_Pommel_GaleOath_R2`。

## 接入与重制

- `SurfaceR2/author.py`、`finish.py`：模型、UV、PBR 与导出。
- `SurfaceR2/publish.py`、`install.ps1`：后台模型导入与保存；`import_receipt.json` 为实际保存回执。
- `Integration/install_catalog.py`：只合并本配重选项与真实接口，保留其他目录项。
- `Integration/build.ps1`：必要原生 Editor 构建，已成功；输出位于 `Integration/Logs`。
- `Integration/render_icon_source.py`：实际模型灰阶横向素材。
- `Integration/icon_prompt.txt`：内置 imagegen 的完整提示词；以认可金属框及实际模型为参考，生成一张灰阶图标。
- `Integration/publish_icon.py`、`install_icon.ps1`：已保存正式 PNG 与 UI Texture2D，回执为 `icon_receipt.json`。

导入收据用于续接同版初次导入。后续重新制作需使用新修订目标，不能用旧完成回执跳过新资产导入。
