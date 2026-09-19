# 5080 部署记录 — 2026-09-13

状态：节点、五套候选工作流、Pixal3D 单图权重及 MoGe 配套权重均已部署；已通过 WMI 发起 ComfyUI 后台重启以激活节点。未运行生成、节点加载自测、效果或显存测试。

- 宿主：192.168.3.142；ComfyUI：D:/开发文件/ComfyUI。
- 保留既有 Python 3.11.9 / Torch 2.9.1+cu128 与 TRELLIS 包装器。
- MultiViewRefiner：固定源码 f8c676ae94280f164e58a1179ce127efea6f81e1，安装到 custom_nodes/ComfyUI-Trellis2-MultiViewRefiner。
- 五份工作流：user/default/workflows/Mechanical3D。
- Pixal 单图权重：官方 TencentARC/Pixal3D → models/TencentARC/Pixal3D-T（现有节点的名称）。
- MoGe：Ruicheng/moge-2-vitl → models/Ruicheng/moge-2-vitl。
- 直接网络连接及镜像大文件传输受阻，使用临时 SSH 反向通道连接本机现有代理，下载官方权重。仅下载进程使用该代理，不修改系统全局配置。
- 下载完成回执：Pixal3D 19/19 文件、MoGe 3/3 文件，安装脚本正常完成。临时下载通道已关闭。
- 激活入口：activate_remote.ps1，远端执行策略要求本次 PowerShell 进程使用 ExecutionPolicy Bypass，没有更改系统永久策略。后台启动由 launch_comfy.py 完成，以免 SSH 断开结束服务。
- 原始安装回执：本机 Saved/PipelineSetup20260913/remote_installation.json；远端 D:/Mechanical3DSetup/installation.json。启动日志在远端 D:/Mechanical3DSetup/comfy-activation.*.log。
- NATTEN 的前期安装在元数据阶段失败，没有安装成功；现有包装器不导入它，继续复用自身 Torch 投影注意力，不升级 Torch 来安装无关 CUDA 包。

参考图尚未提供。结构 64/128、Refiner 效果与 Pixal 的 16GB 显存表现均未测试，也未宣称优于既有结果。

## 2026-09-13 first user-requested Pixal generation

PhantomRearGripPixal_20260913 generated GLBs and requested Blender previews (prompt 65d39e4a-cd21-48b0-b3fd-d7e9727b1c05). No UE integration or regression tests were run.

First-run repairs: install MoGe 2 utils3d pinned source; enable MoGe native SDPA; adapt Pixal DINO layer lookup to current Transformers; enable existing NAF 2x2 tiling in low_vram mode. Reapply wrapper changes with patch_pixal_compat.py when needed.

Correction to initial deployment note: NAF is an indirect NATTEN dependency. The current cp311/Torch 2.9.1 environment uses original NAF weights with the scoped PyTorch operator in naf_torch_neighborhood.py, deployed inside the cached NAF repository. This is not the native NATTEN kernel. The upstream tiled NAF projection is near-equivalent rather than bit-identical; no numerical-equivalence testing was requested or performed. Candidate source directory README records deployment paths and limitations.
