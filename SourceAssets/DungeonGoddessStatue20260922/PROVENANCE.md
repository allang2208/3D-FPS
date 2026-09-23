# Diana 女神石像来源与许可

## 模型

| 项 | 内容 |
| --- | --- |
| 名称 | **Diana** |
| 作者 | **noe-3d.at**（<https://sketchfab.com/www.noe-3d.at>），奥地利专业文保扫描团队 |
| 页面 | <https://sketchfab.com/3d-models/diana-ea77e1d0442244aeb3d558a08ccdfc1a> |
| 许可 | **CC BY 4.0**（`CC-BY-4.0 (http://creativecommons.org/licenses/by/4.0/)`，写在 glb 的 `asset.extras.license` 里）：允许商用，**必须署名** |
| 描述 | 奥地利 Waldreichs 城堡入口处的狩猎女神狄安娜石像；女神持弓、背箭袋，脚边有猎犬。年代与作者不详 |
| 获取日期 | 2026-09-22 |
| 获取方式 | Sketchfab Data API v3（用户提供的 API token），`GET /v3/models/{uid}/download` |

## 下载原件（本机保留，不入 Git）

| 文件 | 大小 | SHA-256 |
| --- | --- | --- |
| `Download/source_diana.zip`（作者原包） | 185.3 MB | `581A62554413A19F2B85899CCB3450E4B4F221E3A89F0432A3F1E924030961D2` |
| `Download/glb_diana.glb`（Sketchfab 转换包） | 17.8 MB | `F98ACF2DADC4D3C8E4A8256829D3CF89E3A4D2D797A4227B219D69635F9B725D` |

原包内（`Source/`）：

| 文件 | 内容 |
| --- | --- |
| `source/Diana_C/Diana_C.obj` | 摄影测量母版网格：250,349 顶点 / **500,726 三角面**，含 UV 与法线 |
| `source/Diana_C/Diana_C.mtl` | 单材质 `Diana_O_Material_u1_v1`，仅 `map_Kd` |
| `source/Diana_C/Diana_C_Diana_O_Material_u1_v1.png` | **8192 × 8192** RGB 漫反射图集（66.1 MB） |
| `textures/Diana_C_Diana_O_Material_u1_v1.png` | 同图集的另一份（8192²，60 MB） |

**这是一件只有漫反射贴图的扫描件**：没有法线、粗糙度或金属度贴图。glb 内嵌的贴图只有 1.32 MB（Sketchfab 转换时压缩过），所以导入用的是 source 包里的 8192² 原图，而不是 glb 里的版本。

## 下载通道说明（复现要点）

Sketchfab 的下载接口需要鉴权，匿名调用 `/v3/models/{uid}/download` 返回 401：

```powershell
$dl = Invoke-RestMethod -Uri "https://api.sketchfab.com/v3/models/ea77e1d0442244aeb3d558a08ccdfc1a/download" `
      -Headers @{ Authorization = "Token $env:SKETCHFAB_TOKEN"; Accept = 'application/json' }
# 返回 source / glb / gltf / usdz 的预签名 S3 链接，300 秒内有效
```

- 鉴权头是 `Authorization: Token <裸 token>`；**带 `api:` 前缀或换成 `Bearer` 都会 401**。
- **必须走系统代理**：本机 WinINET 代理为 `127.0.0.1:7897`，但 `curl` 不读 WinINET 设置，默认直连只有 20–36 KB/s；显式加 `-x http://127.0.0.1:7897` 后为 **1.5–10.2 MB/s**（source 包 185 MB / 19 秒）。下载脚本：`D:\FPS3D\_sketchfab_goddess\fetch_diana.ps1`。

## 加工产物

| 文件 | 大小 | SHA-256 |
| --- | --- | --- |
| `Authored/SM_GoddessStatue_Diana.fbx` | 34.98 MB | `D785067D91A0EC2F58C264C01B1E643F705675412C38DD86E5FAD5A1B377AE37` |
| `Authored/Diana_Editable.blend` | 42.98 MB | `ED87F1377D3BF4AD0A71DA94A6BB0C1A91E6E41C342547B41C358F93A02134FB` |
| `Textures/T_GoddessStatueDiana_BaseColor.png`（4096²，8192 母版降采样） | 21.12 MB | `7E5CECBA0FD569870408E7978CC39BA9F6D04A386261F9FBBF2F80F5EB769058` |

加工只做三件事：统一缩放到 2.05 m 高、把底面中心移到原点、把 8192² 图集降采样到 4096²。几何、UV、法线与贴图内容未改。

## 署名（CC BY 要求）

> "Diana" by noe-3d.at, licensed under CC BY 4.0.
> Source: https://sketchfab.com/3d-models/diana-ea77e1d0442244aeb3d558a08ccdfc1a

游戏内公开分发时，这段署名需随项目第三方声明一并发布，见 `FPSGAME/ThirdPartyNotices/GODDESS_STATUE.md`。
