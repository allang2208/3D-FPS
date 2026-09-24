# Meshy 四足绑骨 API 排查记录

> 2026-09-25 整理：下文保留当时制作/诊断记录，旧路径不再表示现役入口。当前模型、动作、归档映射和恢复顺序见 [感染犬发布记录](InfectedDogPublication20260925.md)。

日期：2026-09-24。用户要求排查 API 无法完成四足绑骨的原因；网页端由用户自行操作。排查期间没有再次生成模型，没有导入或替换 UE 资产。

## 结论与边界

已定位失败环节：`POST /openapi/v1/rigging` 在创建异步绑骨任务之前返回 HTTP 422 / `Pose estimation failed`。输入模型、四足模板字段能够到达服务端，但当前犬模型未通过自动姿态识别，尚未产生骨架或蒙皮产物。

实测不能解释为 `animation_type` 字段被完全忽略：错误类型返回了针对 `CreateRiggingRequest.animation_type` 的解析错误，错误枚举返回了明确的 `[biped quadruped]` 允许列表。因此，`quadruped` 是此部署认识的有效参数值。

网页四足与公开 API 的工作流不同：官方公开前端在选择双足时才调用 `estimatePoseV2`；四足进入模型旋转、放置标记点后，携带 `positionJson`、旋转、偏移和尺度提交。公开 OpenAPI 请求定义没有关节点覆盖参数。本次向公开入口追加 `position_json` 的类型探测仍走到相同 422，没有出现字段类型错误或成功跳过估姿的行为。这支持“当前公开入口没有可用的网页手工定位通道”的判断，但不能证明服务器内部所有未公开参数均不存在。

尚无法从 API 返回区分：该犬模型本身不被自动识别、该账户/部署四足分支的限制，还是服务端实现问题。不能将其概括为“Meshy 完全不支持四足”，也不能把仅有参数枚举支持当作已完成四足绑骨。未经服务器侧日志，不能断言其内部实际使用了哪一个姿态识别模型。

## 已完成的资产处理

- 原始生成任务：`01a0d354-0532-73e3-816b-0ba74bfd089d`，原高模 383,356 三角面，完整保留。
- Meshy Remesh 任务：`01a0d363-3cb2-7671-bb86-23d29502718e`，`SUCCEEDED`。
- 请求四边形拓扑、目标 50,000 多边形；下载的 GLB 三角化后为 99,360 三角面、64,184 顶点，低于绑骨接口上限。
- GLB 包含基础色、法线及 PBR 相关嵌入贴图，无节点旋转/缩放。此处仅记录与接口适配有关的结构信息，不作为拓扑变形或视觉验收。
- 重拓扑 GLB：`SourceAssets/InfectedDogMeshy20260924/Meshy/candidate01_quad50k/downloads/model.glb`。
- 重拓扑 FBX：同目录 `model.fbx`；服务预览和贴图也已下载，文件清单见该阶段 `downloads.json`。
- 坐标诊断副本：`SourceAssets/InfectedDogMeshy20260924/Diagnostics/grounded_input/InfectedDog_Grounded_1m.glb`。仅将脚底移到 Y=0、水平居中并均匀缩放到 1 米整体高度；朝向保持 +Z，不改拓扑、UV 或纹理。变换及散列记录在 `preparation.json`。

## 有界对照请求

所有请求均使用同一已有重拓扑资产，不重建模型。诊断脚本对每个 case 只允许一次 POST，若创建了真实任务则禁止后续诊断 POST。

| 请求 | 目的 | 返回 |
| --- | --- | --- |
| 重拓扑 `input_task_id` + `animation_type: quadruped` | 正常四足请求 | 422，姿态识别失败，无任务 ID |
| `animation_type` 改为对象 | 确认字段是否被解析 | 400，Go 字段要求 string |
| 直接使用服务 GLB URL + quadruped | 排查任务 ID 传递路径 | 422，姿态识别失败，无任务 ID |
| 无效 `animation_type` 字符串 | 确认枚举值 | 400，允许值明确为 biped / quadruped |
| 接地并归一高度的 GLB Data URI + quadruped | 排查原点/高度因素 | 422，姿态识别失败，无任务 ID |
| 追加 `position_json: true` 类型探测 | 确认网页定位参数是否暴露 | 422，仍进入姿态识别，未得到定位字段解析错误 |

服务响应头 `X-Api-Version`：`v2026.09.24.post2`。各诊断请求、HTTP 状态、响应体、耗时和余额前后值保存在：

`SourceAssets/InfectedDogMeshy20260924/Diagnostics/rigging_api/<case>/`

首个正常绑骨请求的失败记录：

`SourceAssets/InfectedDogMeshy20260924/Meshy/candidate01_quadruped_rig/submission_error.json`

本轮 Meshy 重拓扑消耗 **5 积分**，余额由 2003 变为 1998；上述未创建任务的绑骨/诊断请求余额均保持 **1998**，未发生额外绑骨消费。凭据临时进程已退出；回执不保存 API 密钥或签名 URL 查询串。

## 官方依据

1. [OpenAPI 定义](https://docs.meshy.ai/openapi.json)：RiggingRequest 列出 `animation_type`、`height_meters`、输入任务/URL等，没有 `position_json` 或手工关节点入口。快照为项目 `meshy_openapi_20260924.yaml`。
2. [Rigging 说明页面](https://docs.meshy.ai/en/api/rigging)：仍以人形输入描述，和枚举定义存在不一致。
3. [官方 CLI 源码](https://github.com/meshy-dev/meshy-cli/blob/main/src/cmd/rigging.ts)：说明人形输入，当前未提供四足参数选项。本次仅下载阅读，未执行；源文件记录在 `Diagnostics/official-cli-rigging.ts.txt`。
4. [官方公开绑骨对话框实现](https://cdn.meshy.ai/webapp-build-assets/production/_next/static/chunks/3ae4w0olsg-wv.js)：步骤为 SelectType / Rotating / PlaceMarkers；双足条件下调用 `estimatePoseV2`；普通四足流程通过手工点位提交 `positionJson`。本地快照为 `Diagnostics/public_web_client/7da84469c2693653.js.txt`。
5. 公开网页代码通过未登录 HTTP GET 获取；没有读取用户浏览器的 Cookie、Token 或认证存储，没有调用网页私有接口提交任务。用户要求改查 API 后，浏览器自动化未继续输入或提交。

## 当前交付状态

Meshy 模型与重拓扑产物已落盘，API 失败原因已定位到自动估姿阶段；**四足绑骨尚未完成**。没有用本地骨架伪装为 Meshy 绑骨结果，也没有将失败候选接入 UE。原感染犬的外观引用、旧动作、六维和感染机制保持当前版本。

后续若用户自行在网页端完成 Quadruped Dog 的关节点定位并导出，可沿用此重拓扑资产继续接入；该网页操作不在本轮 API 排查中代为执行。
