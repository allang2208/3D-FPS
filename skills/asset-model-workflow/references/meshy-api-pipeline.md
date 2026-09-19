# Meshy API 管线（模型与动作备选，2026-09-19 登记）

用户于 2026-09-19 确认将 Meshy API 作为模型管线的备选生成路线之一，与 5080/TRELLIS.2 本地路线和 Vibe3D 编辑器路线并列。本文只登记通道、计费、接口与已核实约束；实际采用仍由用户在具体任务中指定，默认不自动触发。2026-09-13 的胖子僵尸与 Mutant3 来自**网页端**手工产出；本文是 API 直调通道，2026-09-19 已用 `GET /v1/balance` 实测通过（与会员积分同池，不另计费）。

## 分流（何时选 Meshy）

- 用户指定 Meshy、或需要**成品带 PBR 纹理的有机/角色造型**且本地 5080 路线反复出不了合格候选时：用 Meshy 图生 3D。
- 需要**给已绑骨怪物套用现成动作**：先走本文的动画库搜索（678 个预设、有 GIF 预览），比外部翻 CC0 源快；无合适预设再回 Mesh2Motion/GitHub 源或本地手工修。
- 机械件、精确接口件、建材模块仍以 Vibe3D/本地 Blender 为准（Meshy 网格不保证孔洞与安装面精度，同 5080 的教训）。
- 商用许可：付费档私有资产授权；Free 档输出 CC BY 4.0。发布/再分发前按 WORKFLOW 第 5 节单独核可。

## 调用方式（已核实 2026-09-19）

- 认证：`Authorization: Bearer msy_…`；key 在 meshy.ai/settings/api 创建、只显示一次。**key 只存环境变量 `MESHY_API_KEY`，绝不写入仓库、脚本、提交与日志**。
- 本机直连 `api.meshy.ai` 超时，须走系统代理 `127.0.0.1:7897`（curl `-x` / requests `proxies`）。
- Base：`https://api.meshy.ai/openapi/`；机器可读文档 `https://docs.meshy.ai/llms.txt`、`llms-full.txt`、OpenAPI 规范 `docs.meshy.ai/openapi.yaml`。官方另有 MCP server：`npx -y @meshy-ai/meshy-mcp-server`（env `MESHY_API_KEY`），见 docs.meshy.ai/api/ai。
- 异步任务三步：`POST /v{1,2}/<task>` 拿 id → `GET /v…/<task>/<id>` 轮询（或 `/:id/stream` SSE）到 `SUCCEEDED`/`FAILED` → 下载 `model_urls.glb|fbx|obj`。状态流 `PENDING→IN_PROGRESS→SUCCEEDED|FAILED|CANCELED`。
- 常用端点：`v2/text-to-3d`、`v1/image-to-3d`（`image_url` 或 base64）、`v1/multi-image-to-3d`（走三视图时用）、`v1/rigging`、`v1/animation`、`v1/remesh`、`v1/uv-unwrap`、`v1/retexture`、`v1/text-to-motion`、`v1/balance`、`v1/animations/library`。
- 请求 `enable_pbr: true` 才有金属度/粗糙度/法线图；浏览器端不能直调（CORS 封），一律本地脚本。

## 计费（积分；docs.meshy.ai/api/pricing.md 为准，下表节选）

| 任务 | 积分 |
| --- | --- |
| 图生 3D（Meshy-6/7/7.1）| 无纹理 20；带纹理 30；8K 纹理 35；`geometry_resolution` 2k/4k 再 +5 |
| 图生 3D（Smart Topology T2 / 其他档）| 无纹理 5/15 一带，T2 带纹理 15 |
| 文生 3D 预览 / 精修 | 20(+5) / 10（8K 15） |
| 自动绑骨 | 5 |
| 动作套用 | 3/个（一次最多 10 个） |
| 文生动作 | swift 3；prime 10 |
| UV 展开 / Remesh | 5 / 5 |
| 格式转换 / 缩放 | 1 / 1 |
| 重贴图 Retexture | 10（8K 15） |

- 会员套餐积分（Free 100、Pro 1,000/月起，Pro 即含 API access）与 API **同池扣减**、月初清零不结转。
- **IN_PROGRESS 的任务不可取消不退分**（`DELETE` 只对 PENDING 有效）；试错先用低档低参数。
- `v6-lite`/低模/T2 档 5 积分适合廉价试探。

## 硬约束与坑（已核实/官方明示）

1. **结果只保留 3 天（非 Enterprise）**：任务 SUCCEEDED 后脚本立即把 GLB/FBX/贴图下载到 `SourceAssets/<任务>20MMDD/`，与 5080 案例同样落 authoring/回执 JSON；不能只记 URL。
2. 回执里若出现对象存储预签名 URL（`q-ak=AKID…`/`X-Amz-Signature`/SAS 等），**入库前剥离查询串**（GitHub push protection 会拦，见 2026-09-19 混元教训）；提交前 `grep -l 'q-ak=AKID'` 扫一遍。
3. 时间戳为 Unix 毫秒。输出格式不保证齐全，下载前检查 `model_urls` 对应键存在。
4. 429=超速率（Pro 20 req/s、队列 10 任务）；轮询间隔 ≥5 s，不重复提交同一在跑任务。
5. 蒙皮/拓扑按 [[meshy-humanoid]] 的既有人形处理链继续：Meshy 骨名不保证解剖序，UE 侧 IK 重定向与体型修正不变。

## 动画库搜索（怪物动作接入前置步骤）

```
GET https://api.meshy.ai/openapi/v1/animations/library[?search=…&category=…&sub_category=…]
→ [{action_id, name, key, category, sub_category, preview_url(GIF)}]
```

- 2026-09-19 实测全库 678：WalkAndRun 176 / BodyMovements 158 / DailyActions 157 / **Fighting 154**（含 GettingHit 受击族、Dying 11 个死亡类、武器挥砍如 Heavy_Hammer_Swing/Charged_Axe_Chop/Charged_Slash）/ Dancing 33；多数有 `_inplace` 原地版（适合 UE 根运动分离）。
- **验收分工**：候选 GIF 是公开 CDN 直链，只列给用户挑（用户拍板 = 零 token）；不要自己批量读图判断。
- 选定后 `POST /v1/animation`（3 积分/个）套到 rigging 任务或已绑骨模型上；产物同受 3 天保留限制，立即落盘。
- `action_id` 语义、参数以 `docs.meshy.ai/api/animation.md` 与 `openapi.yaml` 现场为准，不凭本文记忆传参。

## 记录与交付

沿用第 2 节通用记录要求：保存输入图/prompt、模型档位（meshy-7.1/latest）、任务 id、请求参数、积分消耗前后 balance、下载文件散列与许可来源。与 5080 路线共用"候选→用户选定→冻结母版→本地适配接入"的节奏，不因为 API 快就跳过用户选型步骤。
