# 腾讯混元生3D（专业版）OpenAI 兼容接口接入

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
