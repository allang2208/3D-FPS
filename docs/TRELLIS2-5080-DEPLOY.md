# TRELLIS.2 部署到 5080 机器（国内镜像清单 + 实测记录）

> 状态：**2026-08-09 已跑通端到端**（红狼王图 → TRELLIS.2 → 9.3MB 带纹理 GLB）。
> 访问方式：SSH 别名 `r5080`（= 192.168.3.142，用户 可爱小鼠，免密，见 `~/.ssh/config`）；
> ComfyUI API：http://192.168.3.142:8188。

## 0. 前置：为什么之前卡住 / 现在解决了

- 之前 5080 上 CuMesh 崩溃，是 Blackwell 兼容问题；`trellis2-blackwell-fix`
  已合入 `visualbruno/ComfyUI-Trellis2` 主线（2026-02-05 起），
  当前 main 分支（2026-07-31 更新）已包含修复，重新拉最新代码即可。
- 模型权重不从 HuggingFace 下载（国内直连被墙），走 ModelScope（魔搭）。
- **5080 现状（2026-08-09 核对）**：ComfyUI 0.30（venv Python 3.11.9 +
  torch 2.9.1+cu128）已装 ComfyUI-Trellis2（含 blackwell_fix.py）；
  TRELLIS.2-4B 全量权重（16.2GB）与 DINOv3（1.2GB）均已就位。
- **本轮修复的两个 Blackwell 崩溃点（已打在 5080 上，备份 .bak_20260809）**：
  1. `trellis2/pipelines/trellis2_image_to_3d.py`：decode 后的 `m.fill_holes()`
     走 CuMesh 会崩（sm_120）→ Blackwell 跳过（黑狼不需要填洞）。
  2. `nodes.py` `Trellis2DecodeLatents`：texture_slat 存在时无条件建 CuMesh BVH
     会崩 → Blackwell 跳过 BVH（本管线文本烘焙不走 BVH 引导）。

## 0.5 端到端实测结论（2026-08-09）

- 命令：`python tools/ai-gen/trellis-gen.py --image x.png --out out.glb --prefix my --faces 20000`
- 单模型耗时：约 195 秒（64 稀疏分辨率 / 12 步采样；含纹理烘焙 2048²）。
- 产物：`ComfyUI\output\<prefix>_00001_.glb`（9.3MB，PBR 纹理内嵌）。
- 客户端下载问题：ComfyUI history 对多 OUTPUT_NODE 不返回 GLB 条目，
  trellis-gen.py 已改为按 `prefix_00001_.glb` 文件名规则直取。
- 参数注意：`sparse_structure_resolution` 用 64（32 网格过小、128 会 OOM）。

## 1. 需要下载的东西（全部已核实源）

| 组件 | 大小 | 国内源 | 命令/链接 |
|---|---|---|---|
| ComfyUI-Trellis2 节点（含全部 wheel） | 180 MB | ghfast.top 代理 | 见 3.1 |
| TRELLIS.2-4B 权重 | 16.2 GB（24 文件） | ModelScope | `modelscope download --model microsoft/TRELLIS.2-4B --local_dir <目标>` |
| DINOv3 特征模型 | 1.2 GB | ModelScope | `modelscope download --model facebook/dinov3-vitl16-pretrain-lvd1689m --local_dir <目标>` |

## 2. 5080 机器环境检查（先做）

1. 确认 ComfyUI 已装、能启动；确认 Python 版本和 torch：
   ```bat
   <ComfyUI>\.venv\Scripts\python.exe -c "import sys, torch; print(sys.version); print(torch.__version__, torch.version.cuda)"
   ```
2. wheel 与 torch 版本对应关系（节点包内自带，`wheels\Windows\<Torch版本>\`）：
   - torch 2.7.0 → `Torch270`（README 官方测试组合）
   - torch 2.8.0 → `Torch280`
   - torch 2.10.0 → `Torch2100`（含 CUDA 13.1 变体，Python 3.13）
   - 若 5080 的 torch 不是这几个版本，优先装 2.7.0/2.8.0 配 cu128；
     不建议在 cu126 环境硬装（ABI 可能不兼容）。
3. 显存：5080 16GB 跑 1024³ 标准档无压力；显存吃紧时节点内开低显存模式。

## 3. 安装步骤

### 3.1 下载节点包（任选一个代理，实测均通）

```bat
curl -L -o ComfyUI-Trellis2.zip "https://ghfast.top/https://github.com/visualbruno/ComfyUI-Trellis2/archive/refs/heads/main.zip"
rem 备用：https://gh-proxy.com/...  /  https://ghproxy.net/...
```

解压到 `ComfyUI\custom_nodes\ComfyUI-Trellis2`。

### 3.2 安装 wheel（进 venv，按上一步确认的 torch 版本选目录）

```bat
cd /d <ComfyUI>\custom_nodes\ComfyUI-Trellis2
<ComfyUI>\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://mirrors.cloud.tencent.com/pypi/simple
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\cumesh-1.0-cp311-cp311-win_amd64.whl
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\nvdiffrast-0.4.0-cp311-cp311-win_amd64.whl
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\nvdiffrec_render-0.0.0-cp311-cp311-win_amd64.whl
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\flex_gemm-0.0.1-cp311-cp311-win_amd64.whl
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\o_voxel-0.0.1-cp311-cp311-win_amd64.whl
<ComfyUI>\.venv\Scripts\python.exe -m pip install wheels\Windows\Torch270\custom_rasterizer-0.1-cp311-cp311-win_amd64.whl
```

（torch 版本不同就换成对应目录，文件清单以实际解压后的 `wheels\Windows\` 为准；
`custom_rasterizer` 不在 README 安装清单里，但 wheel 已内置且为运行时依赖，
缺它导入会报错；cu126 环境若装不进，回退方案见第 6 节。）

### 3.3 下载模型权重（ModelScope 高速，本机实测 76MB/s 级）

先装 modelscope：
```bat
<ComfyUI>\.venv\Scripts\python.exe -m pip install modelscope -i https://mirrors.cloud.tencent.com/pypi/simple
```

放对目录（README 要求）：
```bat
modelscope download --model microsoft/TRELLIS.2-4B --local_dir <ComfyUI>\models\trellis
modelscope download --model facebook/dinov3-vitl16-pretrain-lvd1689m --local_dir <ComfyUI>\models\facebook\dinov3-vitl16-pretrain-lvd1689m
```

> 注意：TRELLIS.2-4B 权重 16.2GB，按 76MB/s 约 3.5 分钟；
> DINOv3 1.2GB 约 20 秒。

### 3.4 重启 ComfyUI 并验证

1. 重启 ComfyUI（节点加载 + 依赖安装）。
2. 打开 http://127.0.0.1:8188，节点列表搜 `TRELLIS`，应看到
   `Trellis2 Image to 3D` 等节点。
3. 跑节点自带 example workflow：`example_workflows\` 下挑一个
   Image-to-3D 的 JSON 拖进画布 → Queue。
4. 输出 GLB 落到 `ComfyUI\output\`。

## 4. 验证标准（跑通才算成功）

- [ ] 节点列表出现 TRELLIS 系列节点，无 import error
- [ ] 1024³ 单模型 ≤ 3 分钟（5080 应远快于此）
- [ ] 导出 GLB 能在 Godot 里直接 import（无粉红材质、法线正常）
- [ ] 没有 CuMesh / o_voxel / nvdiffrast 崩溃（Blackwell 修复生效）

## 5. 5080 机器的访问

本机（3080Ti，192.168.3.153）当前**不知道 5080 的地址和访问方式**
（RDP / Tailscale / 局域网 IP 未记录）。需要：

- 确认 5080 是否在局域网（192.168.3.x）或走远程（RDP / Tailscale / ToDesk 等）；
- 把地址/凭据记到本文件顶部，方便后续直接远程执行部署。

## 6. 回退方案（若 Blackwell 环境仍装不进）

1. **云端 API**：Hunyuan 3D API（~$0.375/个，有免费额度）或 Tripo，
   图生 3D 走云端，本机只负责出图和导入。
2. **老版本路线**：TRELLIS（非 2）在 Blackwell 的兼容问题更少，但质量低于 2。
3. **换网络通道重试**：节点包已实测可通过 ghfast.top 下载；
   若 5080 网络更差，把本机下载好的 zip 直接拷过去（U 盘 / SMB）。

## 7. 之后接入游戏的步骤（本次部署完成后）

1. 生图（本机 FLUX.2 或 5080 出图）→ 图生 3D（5080 TRELLIS.2）→ GLB。
2. GLB 导入 `3-dfps/assets/models/`，Godot 里挂到枪械节点
   （替换 `_build_gun()` 程序化模型，或作为新枪械资产）。
3. 弹匣/枪口等可动部件命名对齐后，现有换弹/开火动画逻辑不用改。
