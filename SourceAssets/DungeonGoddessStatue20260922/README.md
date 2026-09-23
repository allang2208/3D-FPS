# 地牢女神石像（Diana 扫描件）

用真实摄影测量扫描的狩猎女神狄安娜石像，替换 [5080 生成物品整批废案](../../Docs/Gameplay/dungeon-5080-retirement-20260922.md) 中退役的 `goddess_statue`，作为 [房间资产清单](../../Docs/Gameplay/dungeon-room-asset-list-20260920.md) F2「女神像」事件道具的实体。

来源、许可与散列见 [PROVENANCE.md](PROVENANCE.md)。接入记录见 [女神石像接入](../../Docs/Gameplay/goddess-statue-integration-20260922.md)。

## 结果

| 项 | 值 |
| --- | --- |
| UE 资产 | `/Game/Dungeons/GoddessStatue20260922/{Meshes/SM_GoddessStatue_Diana, Materials/M_GoddessStatueDiana, Materials/MI_GoddessStatueDiana, Textures/T_GoddessStatueDiana_BaseColor}` |
| 网格 | 500,726 三角面 / 250,349 顶点（UE 读回 500,696，往返丢 30 个退化三角形），单材质槽，**Nanite 关闭**（按项目导入惯例） |
| 尺寸 | 93.5 × 71.4 × **205 cm**（按真人尺度雕像归一），底面 Z=0，pivot 在底面中心，正面为 +X |
| 材质 | 扫描漫反射 + 参数化粗糙度 0.72 / 金属度 0 / 高光 0.35；`MI_GoddessStatueDiana` 供调参；双面（源材质即 `doubleSided`） |
| 碰撞 | 无盒体／球体／胶囊简单碰撞，仅 1 个凸包（实测探测），三角面即碰撞体 `CTF_USE_COMPLEX_AS_SIMPLE`（避免生成体把空腔堵住） |
| 摆放 | `/Game/GameMaps/L_Dungeon_AuthoredExpansion` 破损支护室石质空腔，锚点 `side_discovery`（第 8 个），世界坐标 `(4710, -4200, 94)` cm，yaw **153°**（正对破口） |
| Actor | `DGN_Prop_GoddessStatue_01`，文件夹 `Dungeons/GoddessStatue`，`BlockAll`，STATIC |

## 目录

| 路径 | 内容 |
| --- | --- |
| `Config/diana.json` | 来源、目标高度、内容根、摆放锚点与朝向的唯一数据源 |
| `Download/` | 作者原包与 Sketchfab 转换包（本机保留，不入 Git） |
| `Source/` | 解包后的原始 OBJ 母版、MTL 与 8192² 原图 |
| `Authored/` | `SM_GoddessStatue_Diana.fbx`（导入输入）与 `Diana_Editable.blend`（可编辑源，贴图已打包） |
| `Textures/` | `T_GoddessStatueDiana_BaseColor.png`（8192 母版降采样到 4096） |
| `Scripts/` | 检查、归一化导出、FBX 复核、UE 导入、UE 装配、落盘复核、碰撞探测与两个运行器 |
| `Receipts/` | `prepare.json`、`import.json`、`install.json`、`verify.json`、`collision_probe.json` |
| `Previews/` | 源模型四视图、FBX 回读对比、朝向判定图 |
| `Logs/` | 每次导入／装配／复核的编辑器日志 |

## 复现顺序

```powershell
$bl = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$case = 'D:\FPS3D\FPSGAME\SourceAssets\DungeonGoddessStatue20260922'

# 1) 看源：几何统计 + 四视图（判断朝向与比例）
& $bl --background --factory-startup --python "$case\Scripts\inspect_and_render.py" -- `
    "$case\Source\source\Diana_C\Diana_C.obj" "$case\Previews"

# 2) 归一化并导出 FBX + 4096 贴图 + 可编辑 blend
& $bl --background --factory-startup --python "$case\Scripts\prepare_diana.py" -- `
    "$case\Source\source\Diana_C\Diana_C.obj" $case 2.05 4096

# 3) 复核导出后的法线没有被平面化（本项目有硬边丢失的前例）
& $bl --background --factory-startup --python "$case\Scripts\verify_fbx.py" -- `
    "$case\Authored\SM_GoddessStatue_Diana.fbx" "$case\Previews\fbx_front.png"

# 4) UE：导入 → 装配 → 独立进程复核
#    编辑器关着走 -run=pythonscript；编辑器开着走远程执行，两个运行器都会
#    先检查有没有别的 FPSGAME Unreal 进程，并取 MCP 桥同名的批次互斥。
& "$case\Scripts\run_headless.ps1"  -Script "$case/Scripts/import_diana.py"  -LogName 'import-editor.log'
& "$case\Scripts\run_headless.ps1"  -Script "$case/Scripts/install_diana.py" -LogName 'install-editor.log'
& "$case\Scripts\run_headless.ps1"  -Script "$case/Scripts/verify_install.py" -LogName 'verify-editor.log'
# 编辑器开着时改用：run_in_editor.ps1 -Script <同一个脚本> -LogName <日志名>
```

## 边界

- **没有接线玩法**：空腔锚点只是把雕像摆进去；事件①增益／治疗的祈求、祝福与结算尚未实现，本轮的锚点与 Actor 标签可供后续挂接。
- 未做游戏内运行、PIE、截图或性能验收；观感与碰撞手感由用户测试。
- 雕像只摆在破损支护室空腔一处；原样板 A 段遗迹侧穴（旧女神像原位置）未放第二件。
- 扫描件本身没有法线／粗糙度贴图，表面细节全部来自漫反射；如需更强的石面起伏，需要另外做法线（本轮未做）。
