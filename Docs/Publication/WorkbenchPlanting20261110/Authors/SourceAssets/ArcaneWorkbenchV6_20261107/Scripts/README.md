# V6 强化附魔工作台：已接入

2026-11-07 17:37 UTC 后台 commandlet 完成资产保存和构件注册。未运行游戏、视觉或多人验收。完整状态见 `Docs/UI/arcane-world-workbench-status-20261107.md`。

## 运行资产
- 构件 `arcane_workbench`，显示名「强化附魔台」，建造菜单「其他」。
- `/Game/Building/ArcaneWorkbenchV6_20261107/Meshes/SM_ArcaneWorkbench_V6`。
- 28 个材质、30 张贴图、2 个作者 UCX 凸包。网格完整保留 143,134 三角面。
- 调色板 `/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette`。占格 10×5×10，Z 偏移 -2.703209 cm。
- `ArcaneItem=(0,5.2,96.85)`；`ArcaneCamera=(0,330.2,386.85)`，位置单位 cm。源几何到 UE 为 `(x,-y,z)`，已按导入顶点求解。

## 源身份与作者修订
- 下载包：`C:/Users/allan/Downloads/Enchantment_Workbench_V6_UE_Import.zip`。
- 包 SHA-256：`fd7563e3ed5587b368f4f6b822b7c03585eaf3378e6b6f79282f0fa70ad4d657`。
- 原始 FBX SHA-256：`f227603a89885c7208bc7e44b2e0c290dc23472702af17a26e6f40e1f9d75a86`。
- 原件在 `Input/`，35 个清单文件的字节数与 SHA-256 已核对。
- 实际导入 `Authored/Enchantment_Workbench_V6_TangentFix.fbx`，SHA-256 `c0795266c6bf2d94626bfa18c3e6882783e5c7bb7336b69dc4473329110b5d18`。
- 只为 47 个包含零向量的角点切线基补正交回退（原始零切线 42、零副法线 47），没有修改几何、UV、法线、材质或碰撞。
- RemoveDegenerates=False 必须保留；默认 True 会删掉 10,611 个有效细小面。不得无理由重开此项或重新用原 FBX 覆盖已修订源。

## 后续入口
1. `read_source_fbx.py` 读取原始 FBX 元数据，`fill_source_tangents.py` 生成局部切线修订源。
2. `import_mesh_v6.py` 只用于目标不存在时的初次导入，包含最终正确设置。
3. `author_materials_v6.py` 创建配方材质和贴图并按名称绑定，要求目标目录没有未保存改动。
4. `finish_integration_v6.py` 按实际导入坐标生成 sockets，先备份调色板，再调用 `register_v6.py` 定向注册。
5. `reimport_fine_detail_and_register.py` 为本轮修正批次，已执行；不要盲目重放或覆盖 Before 回退包。

运行中的编辑器资产操作必须经项目 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥；编辑器关闭时使用后台 commandlet。不得另起进程覆盖活编辑器已加载资产，不保存归属不明的 dirty packages。未经用户明确要求，不启动游戏、测试、截图、预览或改正式存档。

## 回执与限制
`Receipts/source.json`、`tangent-authoring.json`、`mesh-import-final.json`、`materials.json`、`sockets.json`、`registration.json` 和 `final-cmdlet-01.log`。

玻璃/晶体采用 UE 透明材质与 IOR 折射，Blender 透射映射为 UE opacity 是跨渲染器近似。相机、透明排序、实际碰撞手感、强化附魔操作和网络行为未做实机验收。本轮不启用混合透明槽网格的 Nanite，不新增 LOD，不宣称性能通过。原素材仅供项目内部使用，不公开再分发。
