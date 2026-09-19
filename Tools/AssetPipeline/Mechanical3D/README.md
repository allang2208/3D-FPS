# Mechanical3D 候选管线（2026-09-13）

用户授权准备三项优化，参考图稍后提供；本次不提交生成、不测试、不启动或重启应用。

## 当前状态

5080 已于本轮恢复连接。使用既有 `D:/开发文件/ComfyUI`、`.venv/Scripts/python.exe`（Python 3.11.9、Torch 2.9.1+cu128）与已安装的 ComfyUI-Trellis2。五份 API 工作流按远端节点输入定义重新生成，多视角细化节点已安装，Pixal3D 与 MoGe 权重已下载完成，并已发起后台重启以激活节点。详细记录见 DEPLOYMENT.md。未提交生成或测试任务。

| 文件 | 用途 |
| --- | --- |
| workflows/trellis_ss32.api.json | 结构分辨率 32 对照候选 |
| workflows/trellis_ss64.api.json | 结构分辨率 64 候选 |
| workflows/trellis_ss128.api.json | 结构分辨率 128 实验候选 |
| workflows/trellis_multiview_refiner.api.json | 既有几何母版的多视角细化 |
| workflows/pixal_singleview.api.json | Pixal3D 单图独立生成 |

三档 TRELLIS 保持 1024_cascade、16/32/24 步、相同 seed、4K 纹理、50 万面母版导出目标，保留原始几何；关闭填洞与 only-shell，以保留机械空隙和内部结构。32 档也是新的对照配置，不冒充旧枪托原样复现。128 未证明可在 16GB 上运行。游戏低模减面不包含在本轮。

输入占位为 ComfyUI input 下的 mechanical3d/front.png、right.png、back.png。须提供同物体、相同尺度、对应空间方向的分离图片，不能将拼图直接放到 front.png。

Refiner 另需 mechanical3d/base_raw.glb，网格坐标必须与图像方向一致；旧导出可能旋转过坐标，不能直接假定一致。该扩展没有 DINO-lock；细化可能改变几何，原母版须保留。

Pixal3D 通过 Trellis2MeshWithVoxelAdvancedGenerator 使用单图投影条件。远端旧版包装器识别名称 `TencentARC/Pixal3D-T`，该目录接收官方 `TencentARC/Pixal3D` 的单图权重；不传它不支持的 pixal3d_multiview 输入，不接普通 TRELLIS 的多视图采样器。采用 Pixal 官方配置的引导强度、区间和时间重映射值，步数仍为候选 16/32/24。多视图 Pixal 需要其专用权重和相机参数，不在本轮三项中额外扩展。

## 部署

`install_remote.py` 在已知的 5080 Python 中执行。源节点由本机下载后通过 SCP 传递，远端从 staging 复制；权重使用 huggingface_hub 下载，直连不可用时本次使用 HF_ENDPOINT=https://hf-mirror.com。安装没有更换 Torch、CUDA 或原有 TRELLIS 包装器。现有包装器源代码不导入 NATTEN，投影注意力复用已有 Torch 模块，因此不额外安装 NATTEN；前期 NATTEN 元数据构建失败，没有成功安装该包。

源包暂存：远端 `D:/Mechanical3DSetup/refiner_source`；工作流目录：`D:/开发文件/ComfyUI/user/default/workflows/Mechanical3D`。API JSON 可以通过 ComfyUI 导入，参考图占位需要之后替换。

本机 Saved/PipelineSetup20260913 保存本轮下载的上游节点源码，build_workflows.py 只提取输入定义并生成 JSON，不连接服务，不提交任务。尚未进行运行兼容性或效果测试。

## 来源

- https://github.com/visualbruno/ComfyUI-Trellis2
- https://github.com/cuzelac/ComfyUI-Trellis2-MultiViewRefiner
- https://github.com/TencentARC/Pixal3D

后续需要参考图时再进行用户授权的测试，当前文件不能作为效果提升证明。

## 后续标准入口（2026-09-13）

本文部署状态属于初始准备阶段。后续 Pixal 单图运行、TRELLIS 三视图选中候选及接口修订已整理到 [通用模型生成技能](../../../skills/asset-model-workflow/SKILL.md) 与其案例引用；以后生成按该标准执行，不将本文件的早期“未运行”记录视为最终状态。
