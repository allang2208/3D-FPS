# 腾讯混元生3D（专业版）OpenAI 兼容接口接入

## 平台说明（2026-08 实测）

腾讯混元正从旧平台迁移到 **TokenHub**，两者 key 不通用：

| 平台 | 端点 | Key | 状态 |
|---|---|---|---|
| 旧平台（混元生3D） | `api.ai3d.cloud.tencent.com` | 旧控制台 `sk-` key | 鉴权可通过，但新账号额度常报 `ResourceInsufficient`，新购已停 |
| TokenHub（新） | `tokenhub.tencentmaas.com` | TokenHub 控制台 key | 新账号有免费体验额度，推荐使用 |

旧平台 key 打 TokenHub 会报 401：`API Key 不存在或签名校验失败`。

## TokenHub（推荐）

- Key 创建：`https://console.cloud.tencent.com/tokenhub/apikey`
- 新人免费额度：TokenHub 控制台 → 模型广场 → 新用户福利免费体验 → 领取（含 3D 模型）

```powershell
$env:HUNYUAN3D_API_KEY='TokenHub的key'
python tools/ai-gen/hunyuan3d_api.py tokenhub-submit --image assets/models/ak/ak_ref.png --model hy-3d-3.1
# 记录返回的 JOB_ID
python tools/ai-gen/hunyuan3d_api.py tokenhub-poll --job-id <id> --model hy-3d-3.1
python tools/ai-gen/hunyuan3d_api.py tokenhub-download --job-id <id> --model hy-3d-3.1 --out assets/models/ak/hunyuan/
```

参数（snake_case，与旧版 SubmitHunyuanTo3DProJob 一致）：`model`（hy-3d-3.0 / hy-3d-3.1 / hy-3d-express）、`prompt`、`image_base64`（纯 base64）、`image_url`、`generate_type`、`enable_pbr`、`face_count`、`result_format`。

状态：`queued` → `in_progress` → `completed`（data 内含 obj/glb 下载 URL）。

## 旧平台（备用）

- base_url：`https://api.ai3d.cloud.tencent.com`

## 端点

- base_url：`https://api.ai3d.cloud.tencent.com`
- 提交任务：`POST /v1/ai3d/submit`
- 查询任务：`POST /v1/ai3d/query`
- 鉴权：请求头 `Authorization: sk-xxxx`（控制台创建，勿入库）

## 实测要点（2026-08-09）

- `ImageUrl` 必须传**纯字符串**：
  `"ImageUrl": "data:image/png;base64,xxxx"`。
  官方文档示例写的 `{"Url": "..."}` 对象格式实测返回 400 `Invalid param`。
- `Prompt` 与 `ImageUrl` 二选一，不能同时传（同时传 400）。
- `Model`：`3.0` / `3.1`（3.1 不支持 LowPoly/Sketch）。
- 任务状态：`WAIT` / `RUN` / `DONE` / `FAIL`；成功后从 `ResultFile3Ds` 取 3D 文件。
- 公共错误：`ResourceInsufficient` = 账号未开通服务 / 免费积分未领取 / 资源包耗尽且未开通后付费。

## 客户端

```powershell
$env:HUNYUAN3D_API_KEY='sk-xxxx'
python tools/ai-gen/hunyuan3d_api.py submit-image --image assets/models/ak/ak_ref.png --model 3.1
# 返回 Response.JobId
python tools/ai-gen/hunyuan3d_api.py poll --job-id <JobId>
python tools/ai-gen/hunyuan3d_api.py download --job-id <JobId> --out assets/models/ak/hunyuan/
```

## 开通与额度（账号侧，报 ResourceInsufficient 时检查）

1. 控制台开通混元大模型/混元生3D 服务：
   `https://console.cloud.tencent.com/hunyuan/start`
2. 领取首次开通的 100 免费积分（一年有效）。
3. 免费额度用尽后需购买预付费资源包，或开通后付费：
   `https://buy.tencentcloud.com/pricing/hunyuan/overview`
4. API Key 管理页创建 `sk-` Key。

## 计费参考

- TokenHub 积分制：1 积分 ≈ 0.12 元；新开主账号一次性 100 积分。
- 混元生3D（专业版）默认 3 并发。
