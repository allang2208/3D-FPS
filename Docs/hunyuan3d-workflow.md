# 混元 3D 候选资产工作流

当前宿主：D:/FPS3D/FPSGAME。入口：Tools/AssetPipeline/hunyuan3d.ps1。

## 已接通范围（2026-09-10）

TokenHub 文生/图生 3D → 本地任务记录 → 续查 → 下载候选资产并记录 SHA-256。

后续实测：2026-09-10 棱镜阻手器任务 `1489624951358898176` 已完成图生 3D 和 ZIP/GLB 下载。入口与处理记录见 `SourceAssets/PrismHandstop20260910/README.md`。本次验证发现：将三视图拼图作为单张输入，会生成三个并排物体；不能把该路径称为多视图融合。此次保留其中一个完整重建体并整理后接入；后续单物体生成宜先使用单独的清晰视角图。减面前先焊接服务网格的重复顶点，避免 UV 拆点独立坍缩产生裂缝。
默认模型 hy-3d-3.1，生成和下载目录为 Saved/Hunyuan3D/Candidates/<name>，已由仓库 Saved 忽略规则排除。
本次真实查询通过 TokenHub 鉴权，返回 FailedOperation.JobNotFound；旧平台返回 401 invalid_api_key。
这证明平台与密钥匹配，不证明剩余额度、生成质量或完整资产交付。此次没有提交计费生成任务。

## 凭证

现有密钥用 Windows 当前用户 DPAPI 加密保存在 %LOCALAPPDATA%/FPSGAME/Credentials/hunyuan3d.dpapi。
不在项目、命令参数、任务清单中记录密钥。也支持 HUNYUAN3D_API_KEY 环境变量覆盖。
更新密钥在 PowerShell 7 中执行下列交互命令，输入不会回显：

```powershell
$newCredential = Read-Host 'TokenHub API Key' -AsSecureString
$privateDirectory = Join-Path $env:LOCALAPPDATA 'FPSGAME/Credentials'
New-Item -ItemType Directory -Force -Path $privateDirectory | Out-Null
$newCredential | ConvertFrom-SecureString | Set-Content (Join-Path $privateDirectory 'hunyuan3d.dpapi')
```

本机使用入口 ps1 指向真实 Python 3.11，避免 WindowsApps 的文件系统重定向导致读取不到凭证。直接执行 py 时也应使用真实解释器。DPAPI 解密依赖 PowerShell 7（pwsh）和原 Windows 用户。

## 使用

在 D:/FPS3D/FPSGAME 执行：

```powershell
# 仅查询不存在的任务，不提交生成；检查响应业务码，不把 HTTP 200 等同于任务成功。
./Tools/AssetPipeline/hunyuan3d.ps1 probe --provider tokenhub

# 生成新候选；图片与文字二选一。此命令调用收费生成服务，按账户额度计费。
./Tools/AssetPipeline/hunyuan3d.ps1 submit --name zombie_candidate_v01 --image D:/References/zombie_a_pose.png --pbr
# 或文生模型
./Tools/AssetPipeline/hunyuan3d.ps1 submit --name zombie_candidate_v02 --prompt '写实感染者，全身，A姿势，四肢清晰分离'

# 查询一次；完成后下载。未完成时可以再次执行同一条命令。
./Tools/AssetPipeline/hunyuan3d.ps1 resume --manifest Saved/Hunyuan3D/Candidates/zombie_candidate_v01/manifest.json
# 自动每 10 秒续查，默认最多 20 分钟。
./Tools/AssetPipeline/hunyuan3d.ps1 resume --manifest Saved/Hunyuan3D/Candidates/zombie_candidate_v01/manifest.json --wait
```

提交不自动重试。网络中断且 manifest 为 submission_pending 时，先在控制台查任务，避免重复收费。已取得 job_id 的任务总是 resume，不重新 submit。官方任务 ID 有效期 24 小时，及时下载。
下载失败退出非零，重新 resume 重试下载。输出保留为独立候选，不替换 Content 正式资源。

## 拓扑、绑骨与 UE 后续阶段

TokenHub 此接口返回生成模型。FBX 格式或生成成功不等于已绑骨。
腾讯云另有智能拓扑、UV、绑骨蒙皮和文生动作接口，使用 ai3d.tencentcloudapi.com 与腾讯云 SecretId/SecretKey 签名方式；当前单个 TokenHub Key 没有验证这些接口权限，客户端不假造串接。
后续接入该组凭证后才能继续实现服务端拓扑与绑定。现阶段 manifest 明确保留 rigging_verified=false、ue_runtime_verified=false。
候选进入 UE 前检查模型轮廓、关节拓扑、权重、基础变形；动作制作先实际查看源视频/动作表并记录时长、循环、接触帧。完成实际 UE 预览后再更新正式资产引用。

## 验证

```powershell
& "$env:LOCALAPPDATA/Programs/Python/Python311/python.exe" -m unittest discover -s Tools/AssetPipeline -p test_hunyuan3d.py -v
```

覆盖业务失败、凭证脱敏、不同平台查询协议、提交超时不重试、下载失败、生成失败停止。

## 官方接口依据

- [TokenHub HY-3D](https://cloud.tencent.cn/document/product/1823/137181)
- [腾讯云 3D API 概览](https://cloud.tencent.cn/document/product/1804/120838)
- [腾讯云签名凭证与调用](https://cloud.tencent.cn/document/product/1804/120757)

旧 Godot 客户端仅作历史参考，本入口独立维护于 D 盘，不恢复 E 盘开发线。
