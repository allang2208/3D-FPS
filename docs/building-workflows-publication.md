# 体素与建筑标准发布记录

2026-09-06。本批只发布VOXEL-WORKFLOW、BUILDING-WORKFLOW、两套SKILL及AGENTS入口。初始基线c1dbe758b9d73f74f4cbdc6c7961e08cdf0361ff；发布时已移至最新天气提交8f445daecc21ad798fc7ef196fd7472601185c8a之上，保留其AGENTS入口。共享master另有25个未发布提交及大量其他会话改动，本批不携带它们，也不宣称主神空间/体素运行代码已经发布。

两套技能同步安装到本机C:/Users/allan/.codex/skills，对应仓库skills中的同名目录。通过skill-creator quick_validate（Windows使用python -X utf8）。本地案例明确标记路径可用性，不依赖未发布脚本来阅读和执行标准。

## 本地废案清理

已解除render_wood_edges对旧木材工厂和着色器的引用，默认渲染当前v3橡木；运行代码、场景与工具中无淘汰路径引用。下列7个源/派生文件及各自.uid或.import共14项已从共享工作区清理，均未在远端跟踪，因此本提交没有对应删除记录：

- assets/environment/sky_base/build_wood.gdshader
- scripts/building/wood_material.gd
- assets/environment/sky_base/wood_worn_v2/wood_worn.gdshader
- docs/sky-base/wood-rounded-steps.png
- docs/sky-base/wood-worn-steps.png
- docs/sky-base/wood-panel-2560.png
- docs/sky-base/wood-stone-panel-2560.png

保留v2原始照片贴图、来源许可、当前木/石/大理石材质、可复现工具及最终预览。历史文档追加淘汰说明。工具与历史文档清理改动保留在本地未发布功能包中，不将其单独加入缺少依赖的远端。

## 验证边界

本地清理后：导入、180帧启动及木石大理石建造回归通过；combat测试断言通过但有既有WarehousePanel绑定报错；reload断言通过，退出有资源清理告警。因此不宣称全项目无报错。

独立发布工作区首次资源导入因E盘空间耗尽失败，随后运行测试受缺失导入资源影响，不计通过。本批没有运行代码修改，发布验证以技能结构、链接与完整暂存差异为准。仅本次新建的未完成导入缓存移至C:/Users/allan/.codex/workflow-publish-cache-20260906保留，未改玩家工作区缓存、存档或他人文件。
