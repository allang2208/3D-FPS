# 地图系统发布与归档 · 2026-11-17

本次发布保存 M 键地图、实景正交底图接入、丘陵材质与等高线、个人分层迷雾、标记/标签/彩色光柱、本人/全队可见及地图打开时的 HUD 避让。共享标记不会揭开个人迷雾；每人两种可见性合计最多 10 个，队友记录只读。

## 发布范围与集成

25 个地图专属 C++ 文件直接发布在 Source/FPSGAME，3 个可复用脚本保留在 Tools/MapMarkers。公共控制器、菜单、HUD、PlayerState 和 Cook 配置中混有其他任务修改，因此只发布本次 15 份地图补丁：[集成清单](integration-manifest.json)。补丁基于 07b45d69e33f08739c442cbf8bd09edc40d0eceb 的各文件 blob，先核对基线并执行 git apply --check，再按清单合入；当前本地完整工程已含这些改动，不应重复应用。

PlayerSkillPreparation.cpp 的 Editor-only MapMarkerWire 夹具分支已在基线提交中，未重复发布。ColdSteelMapMarkerSharing.cpp 的 OutLifetimeProps 命名修正及 ColdSteelHillsMap.cpp 的 Ecology 参数已经包含在本次完整文件中；此前 HillsMultiplayer20261115、HillsVegetation20261115 发布目录中针对这两个文件的旧补丁不要再次叠加。

这是一份按任务范围整理的公开源码交付，不代表 Git 干净克隆即可构建/游玩。完整项目仍依赖既有地牢、丘陵、PlayerState/加载流程和本地 UE/Marketplace 资源；公共宿主必须结合其它已发布的工程接入记录合并。[资产依赖](asset-dependencies.json) 记录本地底图、光柱材质与三个场景文件的哈希；这些已保存资源保留原位，没有推送到公开仓库。引擎 Plane 由对应 UE 安装提供。

外部地图方案的历史选型链接保存在 [地图方案](../../UI/world-map-plan-20261113.md)。最终采用工程原生 Slate 与场景/地牢数据，没有在本发布包中转售、再分发 Fab 插件或引擎二进制。

## 保留的历史结果

[共享记录](../../UI/map-marker-sharing-20261115.md) 和 [精简结果](Evidence/results-summary.json) 对应 2026-11-15，而非本次重新测试：

- 正常真实 UDP 与 60ms/2% 弱网各 21 条观测通过；每组 host、guest、重连 guest 三个进程退出码均为 0，峰值同时两个进程。
- 模拟地牢生命周期 64 项、0 失败、退出 0；它没有 socket，不能称为真实地牢 UDP 验收。旧几何与会话检查见 [审计记录](../../UI/map-conversation-audit-20261115.md)。
- NullRHI 覆盖标记数据、光柱 Actor/拥有者与材质状态，不证明画面、鼠标交互、专用服务器或公网；3 项 Slate 输入用例跳过。首个中断批次单独保留，没有计作整轮通过。
- Evidence 中保留结果、退出回执、版本/启动 PID 与测试源/资产哈希。历史 Editor/Game 构建成功见对应实施记录；不把历史构建等同于本次公开子集的构建验证。

本次仅整理文件、沉淀 SKILL 和执行必要的 Git 发布检查，未启动 UE、编译、运行游戏或复测。

## 归档与保留边界

[cleanup-manifest.json](cleanup-manifest.json) 逐项记录原路径、目标路径、字节数、SHA256；[cleanup-receipt.json](cleanup-receipt.json) 记录移动后的核对结果。

已将 2,034 个既有文件、702.63 MiB，以及 37 个目录链接移至本地 trash/map-system-20261117。包含任务临时宿主、复制 DLL、DDC、日志、隔离测试档案、9 张截图和初步盘点文件；未发现本任务 GIF。目录链接仅移动链接本身，目标 Content/Config/插件目录未遍历或改动。没有永久删除。此次发布生成的候选文件与临时索引直接保存在该目录的 PublicationWork 中，不计入既有文件移动数量。

保留实际运行源码、已保存场景/底图/材质和可复用脚本；其他任务的日志与已有暂存内容保持原样。trash、Saved、Binaries、DDC 等不进 Git；线上只保留精简回执，不上传截图和测试档案。

## 技能沉淀

本机维护源与工程 references 同步新增：

- [地图坐标、输入和冷钢表现](../../../skills/ue5-ui-umg-slate/references/world-map-navigation.md)
- [私有/全队标记与个人迷雾](../../../skills/ue5-save-load-replication/references/map-markers-and-personal-fog.md)
- [真实联机、模拟与归档证据](../../../skills/ue5-debug-validation/references/map-marker-network-evidence.md)

既有 SKILL 入口仅增加本次引用；其他未发布经验保持在工作区，未夹带进本提交。
