# 女神石像接入：Diana 扫描件（2026-09-22）

用户在三份 [Sketchfab 备选](goddess-statue-candidates-20260922.md) 中选定 **Diana（noe-3d.at）**，本轮完成下载、归一化、UE 导入与地牢摆放。案例目录：[`SourceAssets/DungeonGoddessStatue20260922`](../../SourceAssets/DungeonGoddessStatue20260922/README.md)。

## 1. 选定与来源

| 项 | 值 |
| --- | --- |
| 模型 | Diana（狩猎女神狄安娜，持弓、背箭袋、脚边猎犬） |
| 作者 | noe-3d.at（奥地利文保扫描团队） |
| 许可 | **CC BY 4.0**（可商用，需署名）→ [第三方声明](../../ThirdPartyNotices/GODDESS_STATUE.md) |
| 原件 | 摄影测量母版：250,349 顶点 / **500,726 三角面**，单张 **8192²** 漫反射图集；**没有法线／粗糙度贴图** |
| 原件散列 | `source_diana.zip` `581A6255…61D2`、`glb_diana.glb` `F98ACF2D…725D` |

选它的原因：真扫描件、授权可商用，且形象本身就是神庙式女神像（含一体式基座与猎犬），与「遗迹侧穴发现女神像」的事件构图一致。

## 2. 下载通道（两个坑）

1. **鉴权头格式**：Sketchfab Data API v3 只认 `Authorization: Token <裸 token>`；带 `api:` 前缀或改 `Bearer` 都返回 401。`/v3/models/{uid}/download` 返回 `source/glb/gltf/usdz` 的预签名 S3 链接，**300 秒有效**。
2. **必须显式走系统代理**：本机 WinINET 代理为 `127.0.0.1:7897`，但 `curl` 不读 WinINET 设置。实测**直连 20–36 KB/s、走代理 1.5–10.2 MB/s（约 22–300 倍）**；185 MB 的 source 包走代理 19 秒完成。下载脚本 `D:\FPS3D\_sketchfab_goddess\fetch_diana.ps1`（`-x http://127.0.0.1:7897`）。

导入用的是 source 包里的原始 OBJ 与 8192² 原图，不是 glb 内嵌的 1.32 MB 压缩贴图。

## 3. 加工

| 步骤 | 结果 |
| --- | --- |
| 轴与朝向 | 源 OBJ 是 Z-up 世界坐标、底面在 Z=24.166；四视图渲染判定**正面朝 -Y**，按项目 FBX 约定（`axis_forward='-Y'`）到 UE 即 +X 正向，无需额外旋转 |
| 归一化 | 等比缩放 ×0.10466432 → 总高 **2.05 m**（对照米洛的维纳斯 2.02 m），底面中心为 pivot、底面 Z=0 |
| 贴图 | 8192² → **4096²** PNG 作为游戏贴图（8192 母版留在 `Source/`） |
| 导出复核 | FBX 回读：三角面 500,726、顶点 250,349 与源一致；**同一顶点 loop 法线最大夹角 0.0°**（未平面化，项目曾因导出顺序丢失硬边，故列为必检项） |
| 可编辑源 | `Authored/Diana_Editable.blend`（贴图已打包） |

## 4. UE 接入结果

导入与装配均在离线 commandlet 内完成（`-run=pythonscript -nullrhi`），回执 `Receipts/import.json`、`Receipts/install.json`：

| 项 | 值 |
| --- | --- |
| 网格 | `/Game/Dungeons/GoddessStatue20260922/Meshes/SM_GoddessStatue_Diana`，bounds 93.46 × 71.36 × **205 cm**，1 个材质槽 |
| 材质 | `M_GoddessStatueDiana`（BaseColorTex / Tint / Roughness 0.72 / Metallic 0 / Specular 0.35，双面）+ `MI_GoddessStatueDiana`；扫描件只有漫反射，其余参数为项目设定值，调参只改 MI |
| 贴图 | `T_GoddessStatueDiana_BaseColor`（4096²，sRGB） |
| 着色／碰撞 | **Nanite 关闭**（按项目导入惯例）；无简单碰撞 + `CTF_USE_COMPLEX_AS_SIMPLE` |
| 摆放 | `L_Dungeon_AuthoredExpansion` · 破损支护室 4×5 m 石质空腔 · 锚点 `side_discovery`（第 8 个）· 世界 `(4710, -4200, 94)` cm · yaw **153°** |
| Actor | `DGN_Prop_GoddessStatue_01`，文件夹 `Dungeons/GoddessStatue`，标签 `DungeonGoddessStatue20260922 / GoddessStatue / RuinEvent`，`BlockAll`，STATIC |

**朝向的算法**：雕像在空腔中心 `(14.1, 4)`，破口中心 `(12, 2.95)`，房间本地朝向 206.57°；房间本地 Y 在世界中取反，故 UE yaw = **153°** —— 玩家钻过破口即正对女神正面，而不是让雕像沿轴摆放。

**落盘证据**：地图与外部 Actor 包在 13:38:15 保存；外部 Actor 包 `…/4/JF/7B8CQ02AJ8AN5B9GM69FDQ.uasset` 字节扫描命中 `DGN_Prop_GoddessStatue_01`、`/Game/Dungeons/GoddessStatue20260922/Meshes/SM_GoddessStatue_Diana`、`Dungeons/GoddessStatue` 与标签。

**独立进程读回**（`Scripts/verify_install.py`，另起 `UnrealEditor-Cmd` 从磁盘打开地图）：

| 项 | 读回值 |
| --- | --- |
| 命中 Actor | 1 个，`DGN_Prop_GoddessStatue_01`，`StaticMeshActor` |
| 变换 | 位置 `(4710, -4200, 94)` cm，旋转 `(0, 153, 0)`°，`STATIC`，`BlockAll` |
| 网格 / 材质 | `SM_GoddessStatue_Diana` · 槽 0 = `MI_GoddessStatueDiana` · 1 槽 |
| 资产尺寸 | 93.46 × 71.37 × **205.0** cm，原点 `(0, 0, 102.5)` |
| 三角面 LOD0 | **500,696**（源 500,726，差 30 = 0.006%，OBJ→FBX 往返丢掉的退化三角形） |
| Nanite | false |
| 碰撞 | `CTF_USE_COMPLEX_AS_SIMPLE`；简单碰撞探测（`Scripts/probe_collision.py`）：**1 个凸包，0 盒体／0 球体／0 胶囊**——不是本项目踩过的"生成球体从地面垂到顶棚堵死内部"那一类，且实际碰撞按三角面走 |

标签刻意使用 `DGN_Prop_` 前缀：`install_rooms.py` 重装房间时会删除 `DGN_RS_`／`DGN_B_` 前缀的 Actor，用别的前缀可避免雕像被后续房间重装清掉。

## 5. 本轮踩到的 API 坑（写脚本时已固化处理）

- `unreal.Vector` 在本版绑定里**既不支持下标也不可迭代**，`Rotator` 同理：用 `.x/.y/.z`、`.pitch/.yaw/.roll` 取分量。
- `mesh.get_bounds()` 返回 `BoxSphereBounds`（`origin` / `box_extent`），不是带 `min/max` 的 `Box`。
- `unreal.EditorStaticMeshLibrary` 在 `-run=pythonscript` 下没有 `get_number_triangles/get_number_vertices`，三角面数改用 Blender 侧回执与 FBX 回读交叉核对。
- `actor.get_folder_path()` 返回 `unreal.Name`，写 JSON 前要 `str()`；回执统一加 `default=str` 兜底，避免"地图已保存但回执写不出来"。
- 材质重建保护：重跑导入时素材已存在且被网格槽引用，**重建被引用材质的表达式表会断言 `!IsRooted()` 直接杀进程**；脚本改为"已存在且表达式数符合预期 → 复核并复用"。
- 交互编辑器的远程执行里**不要**用 `MaterialEditingLibrary.get_material_property_input_node`（会让 MaterialEditor 模块访问违例崩编辑器），接线只做写入与 `recompile_material` 返回检查。

## 6. 编辑器占用与运行方式

本轮期间另一个会话两次短暂打开 FPSGAME 编辑器（`Saved/pkm-rest-fix-editor*.log`）。处理方式：

- 需要 UE 时**不与运行中的编辑器抢进程**：有编辑器在跑就走 `Scripts/run_in_editor.ps1` 远程执行，没有才走 `Scripts/run_headless.ps1` 的 `UnrealEditor-Cmd`；
- 两个运行器都先用 `Get-CimInstance` 检查 `UnrealEditor.exe` / `UnrealEditor-Cmd.exe`（命令行含 FPSGAME），并取与 MCP 桥同名的批次互斥 `Local\CodexUeMcp-Port-8000`；
- 未向其他会话发送任何协调消息，未结束他人编辑器；
- 装配脚本额外加了"地图脏包属于别人就拒绝切关卡"的守卫，避免保存或丢弃他人的未存地图改动。

## 7. 未完成／边界

- **玩法未接线**：空腔锚点只负责摆放；事件①增益／治疗的祈求、祝福、结算没有实现（当前房间生成也只有锚点，没有运行时事件系统）。
- **未做**游戏内运行、PIE、截图、碰撞手感与性能验收。
- 只在破损支护室空腔放了一处；原样板 A 段遗迹侧穴（旧女神像原位置）未放第二件。
- **后续补充（同日）**：同作者另外 5 件可商用神像已下载并导入为资产池（**只导入、未摆放**），见 [女神石像套件导入](statue-set-import-20260922.md)。该轮发现的 OBJ 导入 −180° 朝向坑与本案例导出约定有关，已记入该文档。
- 扫描件没有法线贴图，石面起伏全靠漫反射；需要更强质感要另做法线（本轮未做）。
- `Receipts/verify.json` 的独立进程读回已完成（见第 4 节）；`run_headless.ps1 -WaitForFreeEditorSeconds` 可在编辑器被占用时排队等待，不打断其他会话。
