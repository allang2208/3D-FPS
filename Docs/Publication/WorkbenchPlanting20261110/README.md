# 强化台、工作台材质与四格种植：恢复材料

本批整理本会话 2026-11-07 至 11-10 的源码、作者配方、修复说明和历史验证结果。正式开发位置仍为工程根目录。**这是精确范围的源码恢复资料，不是完整可编译游戏提交，也不宣称运行时集成全部已进入公开仓库。** 当前共享角色、UI、网络和建筑宿主包含其他并行任务，不能整文件夹带。

## 恢复方式与缺口

- `source-manifest.json` 映射每个副本到正式路径并记录原件 SHA-256 及发布文本 UTF-8/LF 散列（published_sha256_lf）；发布副本清理了无效末尾空行，未修改原作者文件。Source、Authors、History、Config 前缀仅用于分类，恢复时按 source 字段对齐。副本不是第二份生产源码。
- `Integration/prerequisites.json` 列出直接共享头依赖及当前散列；另需角色 Profile/StatusModel 的 EnhancementItem 持久化、网络请求/回执序列化、PlayerState 的服务器工作站路由、主 UI 场景输入和背包拖拽消费者、BuildWorld 工作台登记与种植保存入口。它们包含其他任务，不可用本批材料覆盖整份文件。
- `Integration/scoped-changes.json` 是合法中性共享采集角色壳修复的窄补丁及旋转尺寸消毒片段。片段散列不是完整文件前置散列，须定位原函数人工合并。世界展示的冻结最终 component-space pose、拾取装配与异步 readiness 仍在共享 ColdSteelPickup/ColdSteelPickupWeapon 宿主，应按 History/Docs/UI/enhancement-display-model-audit-20261109.md 核对接入，不声称已包含整份共享宿主。
- 源码涵盖本地台面/仪式、强化 UI 与暂存、四格种植布局/选择/快照和审计工具；完整运行还需原工程依赖与内容资产。Tools 快照也应按清单恢复后使用，不在发布目录直接运行。
- 强化台 V6 的 FBX、贴图和 UE 资产，材质统一的 11 材质、24 网格/51 槽、2 Palette 绑定及其他授权素材留在本机，不上传原始付费/许可素材。材质重导入后须按作者目录 README 的 Reapply 恢复绑定。未发现缺失材质，本轮未从 Fab/Quixel 下载新素材。
- 四格种植 UI 对应四个物理位置，存储16格兼容保留，旧植物不得删除。配置快照并不替代旧存档迁移与生产资产。

## 验证与未覆盖

Evidence/historical-results.json 保留历史 JSON 回执及原件散列。最近正式 Editor 构建为 153/153 action 成功；隔离权威 write 33/33、独立进程 reload 3/3；本机实际 UDP host 13/13，首连和重连成功，含5个种植快照乱序检查。全装备结构审计为默认69件及 Viper25个单槽选项与恢复默认，共95项。它们不是本次重新执行的验收。

NullRHI 不验证视觉、金蓝粒子、魔法阵、鼠标拖拽或最终布局；未覆盖专用服务器、网络丢包并发、种植/收获动作 RPC 与附魔卷轴独立矩阵。源码可能随后有并行变动，历史通过不代表当前完整工程复验。本次仅做出版范围、文本语法、哈希及 Git 推送检查，没有启动 UE。

## 归档

仅将两个已被当前源码取代的 Work/Enhancement* 修改前副本移入 trash/WorkbenchPlanting20261110/Work。archive-summary.json 和本地 manifest 记录原位置、目标、字节、SHA-256、替代路径，移动后逐项核验。历史计划中的旧 Work 路径应按此映射查找。保留材质 Before 回退包、结构审计 Before、当前生产资产和全部存档；不按日期清理旧目录。
