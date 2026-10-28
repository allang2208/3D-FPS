# Kukri 白膜与改造件源网格修复

用户报告三款刀身显示白膜，其余改造件弹出最小 LOD 警告。

## 故障证据与修复范围

- 用户日志在 `SM_Kukri_GripCheckered`、`SM_Kukri_GripLeather`、`SM_Kukri_PommelSteel` 上先报 `Bad MeshDescription`，随后报最小 LOD 越界。引擎该报错分支对应缺少有效 LOD0 MeshDescription；仅把最小 LOD 改成 0 不足以修复。
- V2 导出将刀身材质槽名改为 `M_Kukri_<kind>_SurfaceV2`，运行配方仍使用 `M_Kukri_<kind>`。实际资产读取确认：三款网格槽名均带 SurfaceV2，材质都是 `/Engine/EngineMaterials/WorldGridMaterial`，原有 PBR 节点和贴图引用仍完整。旧导入取得的槽数组没有保住正确绑定。
- 实际读取还确认同批九款实体配件全部缺少源 MeshDescription，加载后均为 0 个 LOD、0 个三角面。用户截图中的三个配件是其中已触发加载的例子。
- 三份 V2 FBX 已重新导出，恢复稳定材质槽名，保持现有几何、UV、PBR 和安装坐标。
- `repair_assets.py` 负责三款刀身及九款实体配件，使用当前作者 FBX 重建持久源网格，并将所有网格段显式绑定到相应 PBR 材质的 0 号槽；保持非 Nanite 路线和单级 LOD0。
- `kukri_mesh_import.py` 明确使用编辑器 FBX 导入器并禁止在 PIE 中制作。Interchange 的运行/PIE 导入分支不提交源 MeshDescription，不能用于需要落盘并跨进程加载的制作资产。
- 原 `import_blades.py`、`import_components.py`、V2 `import_surface.py` 均已接入同一导入合同，后续不再仅以“包保存成功”代替源网格存在。

## 文件与交付状态

**已完成正式资产替换。** `repair-receipt.json` 记录独立制作宿主内十二个网格保存完成；`publication-receipt.json` 记录十二个正式 Content 网格包已替换，二者均为 `complete: true`。制作回执里的 `published_to_game: false` 表示制作发生在副本中，正式接入状态以 publication 回执为准。

首次接入因互斥占用而等待超时。用户要求继续后，复制本批 60 个网格、材质、贴图包到 `StagingHost/`，不修改 Cook 正在使用的正式资产。独立读取定位上述两类故障；将旧副本网格保留到 `StagingOriginalMeshes/`，从 FBX 新建同路径网格包，避免继承坏的历史构建数据。独立 commandlet 同步完成网格构建，退出码 0；保留六条源 FBX 近零切线/副法线导入警告，未将其描述为无警告验收。

当前制作结果均有 1 个 LOD、有效源 MeshDescription 和 1 个材质段，显式绑定各自 PBR。修复后的渲染三角面数由 UE 导入时去除退化面决定，详见制作回执；没有重新雕刻或改变数值。

工程占用释放后，`publish_when_available.ps1` 取得原有 UE 批次互斥，确认没有工程编辑器或 Cook 进程，并对照副本输入散列保护并行修改，再通过 `publish_staged.py` 原位替换这十二个包。未停止、关闭或重启其他进程，未运行游戏、视觉或联机测试。

- `read_failure.py` / `failure-state.json`：针对本次故障的资产读取，记录源网格、实际材质、纹理与段绑定；不是游戏回归测试。
- `fix_export_slot_names.py`：修正现有三刀身作者母版和 FBX 的槽名，旧源保留在 `Before/`。
- `repair_assets.py` / `repair-receipt.json`：实际保存记录；只有 `complete: true` 表示十二个网格已完成接入。
- `run_background.ps1`：只在没有编辑器运行且取得现有批次互斥后执行无界面制作。编辑器已运行时使用工程原有 Python 桥。
- `prepare_staging.py` / `staging-inputs.json`：独立制作输入与原文件散列；`StagingHost/` 保存本轮实际完成的 UE 包。
- `publish_when_available.ps1` / `publish_staged.py` / `publication-receipt.json`：等待工程空闲并通过同一互斥写回正式资产；只替换本批十二个网格包。

不修改数值、动作、选项 ID、图标、玩家存档或其他武器；不启动 PIE，不追加渲染和游戏测试。最终游戏表现由用户检查。
