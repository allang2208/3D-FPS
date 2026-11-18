# 进村路线自然衔接丘陵

2026-11-17，用户反馈进村路出现单独高起的斜坡／路堤，要求沿丘陵自然衔接，并继续排查优化。承接河曲、湖泊及白崖采石场制作；保留村庄位置、世界种子和道路走向。

## 原因与修改

`FTemperateVillageSite::Grade` 原先在村庄宽缓整形之外，又沿 `FeederLength` 将村口高度插值到 `JunctionZ`。该高度覆盖在中心 4 m、两侧各 3.5 m 过渡的窄走廊中。较长进村路与原丘陵起伏不一致时，两侧就会形成明显路堤。

- 山顶村庄的最终地形只保留现有村庄平地及外围宽缓过渡；外围之外直接返回原丘陵高度，不再另造进村路坡。
- `Approach`、道路净空、黄色草甸走廊、河湖保护范围均保留原路线。没有将 `FeederLength` 清零，也没有改动村庄、入口或世界存档。
- 原坡面计算同时参与 V3 的选址评分，直接删除会改变相同种子的村庄位置。完整旧计算保留为 `GradeForSiteSurvey`，V3 选址显式调用它；运行时地形改用新的 `Grade`。旧版非山顶村庄沿用原规则。
- 排查了共享高度的地形网格／法线／碰撞、世界高度查询、植被落点、生境边界及远景入口，均沿 `Grade` 读取最终地形。生境边界会依据实际丘陵坡脚衔接；未增加第二套道路网格或材质补丁。

## 文件与状态

本批源码仅修改：

- `Source/FPSGAME/WorldGeneration/TemperateVillageSite.h`
- `Source/FPSGAME/WorldGeneration/TemperateVillageHilltop.inl`

制作记录与修改前副本：`SourceAssets/HillsNaturalApproach20261117`。使用现有 `Build-HilltopVillage.ps1 -Batch HillsNaturalApproach20261117` 后台构建，构建结果以该目录回执为准。

实际构建结果：`FPSGAMEEditor` 于 2026-11-17 18:26、`FPSGAME` 于 18:36 完成，返回码均为 0。回执分别为 `FPSGAMEEditor-build.json`、`FPSGAME-build.json`。构建期间将本任务自身的低优先级编译子进程调为普通优先级以缓解 CPU 争用；没有结束其他进程，也没有启动或重启编辑器。

用户问题截图保留在同批 `Reference/user-approach-embankment.png`。未启动游戏、拍摄或运行验收；该图是修改前的问题依据，实际衔接效果交由用户测试。


2026-11-18 整理：本页历史截图、旧宿主和过期备份已移入 trash；当前路径与散列见 [归档发布记录](../Publication/HillsScenery20261118/README.md)。后续状态以 [待办](hills-scenery-todo-20261118.md) 和 [最新完成记录](hills-closure-20261118.md) 为准，不将历史缺口重复记为当前通过。
