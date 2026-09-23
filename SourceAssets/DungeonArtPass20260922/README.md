# 地牢美术资产：候选筛选与散件第一批导入

本目录承担两件事：

1. **候选筛选**（2026-09-22）：盘点新构建的地牢场景，筛出贴合且许可可商用的美术资产 —— 结论见 [地牢美术资产候选](../../Docs/Gameplay/dungeon-art-pass-candidates-20260922.md)、可执行清单 [`Config/shortlist.json`](Config/shortlist.json)。
2. **散件第一批导入**（2026-09-22）：用户点名的 7 件，下载 → 归一化 → 导入 UE，统一存放在 `/Game/Dungeons/ArtPass20260922` —— 记录见 [散件第一批接入](../../Docs/Gameplay/dungeon-art-pass-import-20260922.md)。

## 已导入的 7 件（`/Game/Dungeons/ArtPass20260922`）

```text
Meshes/     9 个：Lantern、Cobweb_1/2/3、StepLadder、Rope、Extinguisher、Bucket、OilBarrel
Materials/  12 母材质 + 12 材质实例（水桶 4 套，其余各 1）
Textures/   37 张，均 ≤2048
```

| 件 | 真实尺寸 | 用途（候选清单里的定位） |
| --- | --- | --- |
| Lantern | 0.32 m 高 | 遗迹侧穴、暗角提灯 |
| Cobweb ×3 | 0.59–0.66 m 卡片 | 顶角／门框／破口，Masked + 双面、无碰撞 |
| StepLadder | 1.10 m 高 | 工作间／维修间 |
| Rope | 0.45 m 盘径 | 管线分配间／维修间 |
| Extinguisher | 0.55 m 高 | 走廊／维修凹室挂墙 |
| Bucket | 0.30 m 高 | 工作间地面 |
| OilBarrel | 0.88 m 高 | 设备区／排水检修室 |

全部为 **CC BY 4.0**：来源、作者、散列与改动记录见 [PROVENANCE.md](PROVENANCE.md)，署名文字见 [ThirdPartyNotices/DUNGEON_ART_PASS.md](../../ThirdPartyNotices/DUNGEON_ART_PASS.md)。

## 脚本

| 脚本 | 用途 |
| --- | --- |
| `Scripts/search_art_candidates.ps1` | 42 词扫 Sketchfab（CC0/CC-BY、可下载），输出 `candidates.csv`（786 条） |
| `Scripts/fetch_candidate_thumbs.ps1` | 拉入围件缩略图与元数据，供人工看图筛选 |
| `Scripts/inventory_map.py` | 地图透视盘点（**未执行成功**，见下） |
| `Scripts/fetch_props.ps1` | 按 `Config/props.json` 下载 7 件的 source + glb（支持 `-Proxy`） |
| `Scripts/extract_props.ps1` | 解包（含内层 zip）并盘点源文件 |
| `Scripts/inspect_props.py` | 逐件读几何／槽名／尺寸／朝向并渲染两视图 |
| `Scripts/prepare_textures.py` | 贴图降采样到 2048 并统一命名（37 张，0 缺失） |
| `Scripts/prepare_props.py` | 归一化几何（真实尺寸／底面中心 pivot）、蛛网拆分、导出 FBX、回读校验 |
| `Scripts/import_props.py` | UE 导入：网格 + 逐槽材质 + 贴图 + 碰撞策略 |
| `Scripts/verify_props.py` | 独立进程读回（尺寸／槽／混合模式／Nanite／碰撞） |
| `Scripts/run_headless.ps1`、`run_in_editor.ps1` | 与 Diana／塑像套件同一套运行器：进程检查 + 批次互斥；编辑器开着自动改走远程执行 |

## 复现顺序

```powershell
$bl = 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe'
$case = 'D:\FPS3D\FPSGAME\SourceAssets\DungeonArtPass20260922'

$env:SKETCHFAB_TOKEN = '<token>'
& "$case\Scripts\fetch_props.ps1"                 # 大文件建议 -Proxy http://127.0.0.1:7897
& "$case\Scripts\extract_props.ps1"
& $bl --background --factory-startup --python "$case\Scripts\inspect_props.py"   -- $case
python "$case\Scripts\prepare_textures.py" $case
& $bl --background --factory-startup --python "$case\Scripts\prepare_props.py"   -- $case
& "$case\Scripts\run_headless.ps1" -Script "$case/Scripts/import_props.py"  -LogName 'import-props.log'
& "$case\Scripts\run_headless.ps1" -Script "$case\Scripts/verify_props.py"  -LogName 'verify-props.log'
```

## 数据源

| 文件 | 内容 |
| --- | --- |
| `Config/shortlist.json` | 22 件候选（uid／许可／面数／分组／用途） |
| `Config/props.json` | 7 件下载清单（uid／许可／目标尺寸／用途） |
| `Config/import_spec.json` | **导入唯一数据源**：归一化模式、材质槽与贴图角色、混合模式、碰撞策略 |
| `Receipts/download.json` | 14 个包的大小与 SHA-256（206.1 MB） |
| `Receipts/source_scan.json` | 逐件源几何／槽名／包围盒 |
| `Receipts/textures.json` | 37 张贴图的原始与输出尺寸 |
| `Receipts/prepare.json` | 归一化结果与 FBX 回读校验 |
| `Receipts/import.json` | UE 导入回执 |
| `Receipts/verify.json` | 独立进程读回 |

## 未完成事项与原因

- **地图透视盘点未跑成**：另一会话的编辑器（巫婆任务 `L_Dungeon_Randomized`）长时间占用，超过 20 分钟等待未释放；按规则不起第二个进程、不结束他人编辑器、不切换对方关卡。缺口结论改用截图 + 房间文档 + 已有 Actor 扫描。编辑器空闲后可补跑：
  ```powershell
  & "$PSScriptRoot\run_headless.ps1" -Script 'D:/FPS3D/FPSGAME/SourceAssets/DungeonArtPass20260922/Scripts/inventory_map.py' `
      -LogName 'inventory-01.log' -WaitForFreeEditorSeconds 1800
  ```
- **7 件尚未摆放**：本轮只导入资产。
- 候选清单里其余 15 件未下载。

## 网络环境记录（2026-09-22 晚）

- 当天早些时候：系统代理 `127.0.0.1:7897` 生效，直连 S3 仅 20–36 KB/s，走代理 1.5–10 MB/s。
- 晚间：**系统代理被关闭**（`ProxyEnable=0`），代理隧道到 `api.sketchfab.com` 的 TLS 握手失败（curl exit 35），而直连 API 正常（200，约 3 s）。
- 实测结论：**API 走直连、S3 大文件走代理**。`fetch_props.ps1` 的 `-Proxy` 默认空，需要时显式传入；下载前先各测一次速度。
- Sketchfab 预签名链接 **300 秒过期**，中断重试会全部 403（表现为 0 字节不动）。
