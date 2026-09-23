# 女神石像套件（同作者 5 件，仅导入）

同一作者 **noe-3d.at** 的另外 5 尊可商用授权神像，作为地牢遗迹雕像的资产池。与已接入的 Diana（[DungeonGoddessStatue20260922](../DungeonGoddessStatue20260922/README.md)）同一作者、同一管线来源。

**本轮只导入资产，不摆放**（用户指定）。所有网格已统一为正立、底面 Z=0、pivot 在底面中心、正面 +X（UE 中 yaw 0 朝 +X），可直接拖进关卡。

接入记录：[女神石像套件导入](../../Docs/Gameplay/statue-set-import-20260922.md)。来源与许可：[PROVENANCE.md](PROVENANCE.md)。

## 筛选

作者目录共 819 件，其中可商用且可下载 75 件，神像题材 24 件，最终选 5 件单尊女性神祇立像（群像、斯芬克斯与男性纪念像未纳入）：

| key | 作品 | 授权 | 题材 |
| --- | --- | --- | --- |
| venus | Venus | CC0 | 立姿维纳斯，脚边小像 |
| flora | Flora | CC BY 4.0 | 花神，手持花束、带基座 |
| muse | Muse | CC BY 4.0 | 缪斯，持戏剧面具 |
| magnamater | Magna-Mater-Brunnen | CC0 | 大母神，坐姿带两名孩童（增益／治疗语义最贴合） |
| baroque | Barockstatue | CC BY 4.0 | 巴洛克女性立像，动态扭转 |

## 资产

内容根：`/Game/Dungeons/StatueSet20260922`（`Meshes/`、`Materials/`、`Textures/`）

| key | 网格 | 三角面 | 归一化尺寸 (m) | 放置高度 | 源上轴 | 朝向修正 |
| --- | --- | --- | --- | --- | --- | --- |
| venus | `SM_Statue_Venus` | 597,703 | 0.563 × 0.718 × 2.00 | 2.0 m | Z | yaw −90° |
| flora | `SM_Statue_Flora` | 502,658 | 0.954 × 0.606 × 2.00 | 2.0 m | Z | yaw −90° |
| muse | `SM_Statue_Muse` | 477,835 | 0.949 × 0.858 × 2.00 | 2.0 m | **Y** | 绕 X −90° 立起 + yaw 180° |
| magnamater | `SM_Statue_MagnaMater` | 604,948 | 0.981 × 0.718 × 1.80 | 1.8 m | Z | yaw 180° |
| baroque | `SM_Statue_Baroque` | 373,544 | 0.778 × 0.534 × 2.00 | 2.0 m | Z | yaw 180° |

每件都带 `M_Statue_*`（母材质）+ `MI_Statue_*`（材质实例）+ `T_Statue_*_BaseColor`（4096² 扫描漫反射）。统一策略与 Diana 相同：

- 单材质槽，槽 0 指向对应的 `MI_Statue_*`；
- **Nanite 关闭**（项目导入惯例）；
- **无简单碰撞图元** + `CTF_USE_COMPLEX_AS_SIMPLE`（三角面即碰撞体）；独立读回确认 box/convex/sphere/sphyl 计数全为 0；
- 材质参数 `BaseColorTex / Tint / Roughness 0.72 / Metallic 0 / Specular 0.35`，双面；调参只改 MI，不动母材质图。

## 落地证据

`Receipts/import.json`（导入）与 `Receipts/verify.json`（**编辑器内独立读回**，2026-09-22）：

```
venus        found=true size=[56.27, 71.84, 200.0] cm  slot0=MI_Statue_Venus        MI_parent=M_Statue_Venus        srgb=true nanite=false simple=0/0/0/0
flora        found=true size=[95.37, 60.56, 200.0] cm  slot0=MI_Statue_Flora        MI_parent=M_Statue_Flora        srgb=true nanite=false simple=0/0/0/0
muse         found=true size=[94.93, 85.75, 200.0] cm  slot0=MI_Statue_Muse         MI_parent=M_Statue_Muse         srgb=true nanite=false simple=0/0/0/0
magnamater   found=true size=[98.09, 71.78, 180.0] cm  slot0=MI_Statue_MagnaMater   MI_parent=M_Statue_MagnaMater   srgb=true nanite=false simple=0/0/0/0
baroque      found=true size=[77.83, 53.37, 200.0] cm  slot0=MI_Statue_Baroque      MI_parent=M_Statue_Baroque      srgb=true nanite=false simple=0/0/0/0
```

## 目录与复现

| 路径 | 内容 |
| --- | --- |
| `Config/statues.json` | 唯一数据源：来源、授权、目标高度、上轴、朝向修正 |
| `Download/` | 作者原包与 Sketchfab 转换包（本机保留，不入 Git） |
| `Source/` | 解包的原始 OBJ 母版、MTL 与 8192² 原图 |
| `Authored/` | 5 份 `SM_Statue_*.fbx` 与 5 份 `*_Editable.blend`（贴图已打包） |
| `Textures/` | 5 张 4096² 游戏贴图 |
| `Previews/` | 源四视图、归一化后四视图（`*_final`）、朝向对照图 |
| `Receipts/` | `download` / `source_scan` / `prepare` / `verify_fbx` / `import` / `verify` |
| `Logs/` | 每次运行的编辑器日志 |

```powershell
$bl = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$case = 'D:\FPS3D\FPSGAME\SourceAssets\DungeonStatueSet20260922'

$env:SKETCHFAB_TOKEN = '<token>'
& "$case\Scripts\fetch_statues.ps1"            # 走系统代理 127.0.0.1:7897 下载 source+glb
& "$case\Scripts\extract_sources.ps1"          # 解包并解开内层 zip
& $bl --background --factory-startup --python "$case\Scripts\inspect_statues.py"  -- $case
& $bl --background --factory-startup --python "$case\Scripts\prepare_statues.py"  -- $case
& $bl --background --factory-startup --python "$case\Scripts\verify_statues.py"   -- $case

# UE（编辑器关着走 commandlet；开着会自动改走远程执行）
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/import_statues.py" -LogName 'import-set.log'
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/verify_assets.py"  -LogName 'verify-set.log'
```

## 边界

- **未摆放**：本套不写任何地图，地图里目前仍只有 Diana 一件（破损支护室空腔）。
- 未做游戏内运行、PIE、截图、性能或碰撞手感验收。
- 5 件均为扫描件，只有漫反射贴图，没有法线／粗糙度贴图；石面起伏全靠漫反射。Muse 的源网格在同一顶点上存在最大 106° 的法线断层（源件本身如此，非导出造成），近看可能有接缝感。
- 与 Diana 一样，本套模型与贴图是本机素材，按项目规则不入 Git；仓库只保留脚本、配置、文档与回执。
