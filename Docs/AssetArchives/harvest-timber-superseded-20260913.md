# 采集木材废案归档与技能整理

范围仅包含本轮原木、树桩和切口倾倒的已替代文件；保留其他任务的工作区与暂存内容。

已将 **49 个文件、302,979,601 字节（约 289 MiB）** 移入本机 `trash/harvest-timber-superseded-20260913`。归档保留原项目相对路径；[清单](harvest-timber-superseded-20260913.json) 逐项记录原路径、目标、大小、SHA-256、淘汰原因和替代物。移动前限制绝对路径范围并拒绝链接路径，移动后逐文件散列一致。

主要归档内容：

- 初版三款碎面原木、自制树桩和单独封口圆片的 FBX/UE 网格。
- 上一版 `OriginalStumps` 源导出、树桩/圆片、记录及三份旧制作脚本。
- 仅被上述旧模型使用的 UE 树皮材质、三张旧 UE 纹理，以及旧烘焙法线 PNG。
- 已被当前作者文件替代的 `MatchedTreeSections.blend1` 和基础导入器旧版本快照。

UE Asset Registry 检查覆盖拟归档的 17 个包：13 个旧网格没有包引用者，其余四个旧材质/纹理只有本归档集合内部引用。同步读取源码、制作脚本与配置，移除无调用的 `ProductionHarvestAssets::CutCap` 入口；新基本导入脚本不再创建废案网格。原始引用结果保存在本机归档目录 `asset-referencers-before-move.json`。

保留冻结生成母版、纹理母版、参考/生成记录、当前实心原木 Blend/FBX/PBR、切口源文件/上下段以及正式 UE 资源。作者链仍使用的旧命名材质、中间静态上半段及母版贴图也保留。新的 `prepare_timber_mother.py` 从冻结纹理母版恢复作者源，代替夹带初版失败低模的旧制作器；此次整理没有重新烘焙或生成模型。当前恢复顺序见 [制作入口](../../SourceAssets/HarvestTimber20260913/README.md)。

复用经验分别写入 `ue5-world-interaction/references/tree-harvest-cut-and-fall.md` 和 `ue5-item-asset-workflow/references/solid-timber-and-cut-surfaces.md`，并从对应 `SKILL.md` 路由。个人技能与项目镜像同步；没有修改记忆库。

已完成仓库整理相关的引用、路径和散列检查，以及删除旧 C++ 入口所需的 Editor 构建，记录为 `Saved/Logs/TimberArchive-Build-console.log`。首次引用读取 commandlet 因 AutoFootstep 模块加载失败未执行，完成三个相关模块的一致构建后重新读取成功；这不属于游戏功能验收。

按本次授权检查发布范围、暂存差异和技能/脚本格式后普通推送 `origin/main`。不公开 trash、UE 二进制、生成图或未经允许再分发的树木源素材。此次未运行游戏、模型渲染、玩法回归或性能测试，游戏效果仍交由用户测试。
