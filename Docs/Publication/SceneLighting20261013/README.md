# 场景照明标准与接待大厅整理发布

本次将用户认可的接待大厅配光方法和多轮方向修复经验纳入场景标准，特别禁止向下灯向上直射天花板。保留已认可吊灯；一楼廊下、主入口、楼梯及角落由本层灯具提供最低可读照明。黑色出怪检修门采用持续遮挡加廉价流动纹理，远处保留遮挡。

## 标准与发布范围

- 场景标准入口：`skills/ue5-pcg-building/references/scene-development-standard.md`；详细规则：同目录 `fixture-lighting-standard.md`。`WORKFLOW.md` 和 PCG SKILL 已建立入口，个人 SKILL 同步新增规则。
- 黑色遮蔽经验进入 `ue5-fluid-vfx-workflow/references/transparency-and-visibility.md`，同时提供 SKILL 路由。只归纳本门腔方案，不把不透明贴片当成所有烟雾的通用材质。
- 发布已完成的灯具绑定、范围和廊下配方，以及 `ReceptionSpawnBalance20261012`、`ReceptionDoorVeil20261012` 的原创文字源码。两个灯光配置 JSON 只包含灯具匹配与配光参数，不含第三方网格或贴图数据。
- `AuthoredDungeonGenerator.cpp` 仅取灯型、完整世界姿态、先 Movable 后旋转及删除旧 Yaw 覆盖的方向修复；不夹带共享文件中并行的加载调度、遭遇或实例化改动。共享目录扩展器只取本次照明／黑雾重放钩子；位置表只取接待大厅右门条目。
- 工程 SKILL 正在有另一批本机维护入口整理；工作区保留该批修改。本次索引只增加本任务的路由和规则，不发布或撤销那批结构调整。

## 本机恢复依赖

完整 UE 工程与已导入 `Content` 仍以本机为准。地图、FBX、Blend、噪声 PNG、原场景资产及有效安装回执不随源码发布；原始灯具／材质沿已有资产许可边界保留。共享场景目录包含其他并行工作，不把当前全量 `catalog.json` 和布局库快照作为本批替换提交。

恢复或重建时先具备正式 `L_Dungeon_Randomized` 及现有接待大厅／固定起始区资产；依次使用灯具绑定、对应楼层射程和廊下补光配方，读取最新已保存目录做增量安装。入口分别位于 `ReceptionLighting20261009`、`DungeonFixtureLighting20261009`、`ReceptionCoverage20261009`、`DungeonLightCoverage20261009` 和 `ReceptionGroundLighting20261009`。旧数值是该版本的制作数据，不对不匹配的新灯布局强行套用。

右门移位由 `ReceptionSpawnBalance20261012/install.py` 同步门体、门扇、净空和源 placements。黑雾先用 Blender 后台执行 `ReceptionDoorVeil20261012/author.py` 生成本机 FBX、噪声 PNG 和 `geometry.json`，再通过其 `run_background.ps1 -RenderShaders` 导入材质并保存地图。首次运行前创建对应 `Receipts` 目录。已有编辑器使用现有互斥桥，不启动第二个进程覆盖已加载资源。重放钩子只在本机真实保存回执存在时激活，不能为使脚本运行而伪造回执。

## 废案与保留项

179 份、29,269,136 字节的确认退役文件已移入 `trash/scene-lighting-retired-20261013`，逐文件原路径、目标、SHA-256、原因及替代物见 [归档清单](retired-files.json)。主要为失效 Python 全黑导出器及四份输出、两份失败导入日志、一个空结果文件，以及失败黑雾导入时的重复地图快照。重复快照逐文件确认与成功导入前备份字节一致，迁移后散列读回一致。

保留当前模型作者、真实导入资源、有效原生读回记录、用户认可的场景效果、成功安装回执和最新恢复备份。未凭旧日期将早期母版、共享恢复输入或用户保留的样板判为废案。`trash` 内容及原始二进制不进入提交。

## 发布前检查和测试边界

遵循 `WORKFLOW.md` 第 4、5、7、8 节及并行发布规则：从 `D:/FPS3D/FPSGAME` 精确暂存，核对目标 URL、远端 main、所有待推送提交、完整暂存差异、大小、敏感信息、许可和 `git diff --cached --check`；只普通推送 `HEAD:main` 并回读远端及 Godot 归档标签。

本批为 61 个精确路径，全部是文本；暂存内容约 1.23 MiB，未包含二进制资源或 trash。推送前范围核对、空白格式检查及敏感信息模式筛查完成；灯光配置只含参数和资产路径，不含原始几何／像素。完整暂存差异及文件散列留在本机 `Saved/SceneLightingPublication20261013`。

本次是标准沉淀、废案整理和既有成果源码发布，没有重调场景或运行 UE、游戏、自动回归、画面验收和性能测试，也未为发布重新构建暂存子集。2026-10-09 的运行时方向修复及后续资产落盘证据是历史记录，不能说成本轮重新验证通过。最新黑雾和左右门位置仍由用户体验确认。
