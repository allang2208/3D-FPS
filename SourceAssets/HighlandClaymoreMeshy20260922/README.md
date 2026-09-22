# 高地双手剑 Meshy 候选生成

用户于 2026-09-22 重新附图并选定弧形护手、叶形端部的版本，以本目录 `References/user-selected.png` 为唯一造型依据。此前圆环版不作为生成输入。

范围：按 Meshy 管线生成一份带 PBR 纹理的模型候选并本地保存；后续游戏接入另行开展。使用原图单图输入，不生成额外变体，不重新设计护手。背面与厚度由图生模型推断。

计划参数：Meshy 7.1，2K 几何，8K 基础色，PBR，保留原始高细节网格，关闭输入风格增强。输出 GLB、FBX、OBJ 和服务返回的材质贴图。只提交一个候选；API 官方价格为 40 积分（2026-09-22 查询）。网页端可用档位与积分以提交界面为准。

官方接口：https://docs.meshy.ai/en/api/image-to-3d

官方价格：https://docs.meshy.ai/en/api/pricing

生产入口：Python 3.11 运行 `meshy_session.py`，隐藏输入密钥后执行 `submit`，随后 `watch` 跟踪并自动下载，最后 `exit`。密钥仅保存在本次生产进程环境中，不写入脚本、设置或交付文件。请求与任务回执位于 `Meshy/candidate01`，已有任务时复用任务编号。

任务：`01a0c80e-6d05-74ae-b285-d84a9eaae8d5`，单图 `/v1/image-to-3d`，服务返回 `SUCCEEDED`，实际消耗 40 积分。9 个服务输出文件已全部下载。

交付位于 `Meshy/candidate01/downloads`：

- `model.glb`、`model.fbx`、`model.obj`、`model.mtl`：原始生成模型。
- `texture_0.png`：基础色；`texture_0_metallic.png`、`texture_0_roughness.png`、`texture_0_normal.png`：PBR 贴图。
- `preview.png`：服务自带缩略图，不是本地验收渲染。

下载文件保留服务原始文件名，使 OBJ/MTL 中的相对纹理引用可用。请求参数、输入哈希、任务状态和下载来源记录随候选保存。生成进程已结束，未保存密钥。

原始生成阶段已完成并保留上述文件。用户随后要求游戏接入，当前入口见 [Integration/README.md](Integration/README.md)：已完成分件、尺寸适配、改造模块、UI 图标、UE 导入、物品目录与常规构建。符文微光在 UE 材质中处理，Meshy 7.1 原输出没有独立发光贴图。未运行游戏测试或视觉验收，由用户体验。
