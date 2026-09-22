# 巫婆重建、毒弹与发布整理（2026-09-23）

用户授权整理废案、更新对应 SKILL，并向 `https://github.com/allang2208/3D-FPS.git` 推送。本次在 `D:/FPS3D/FPSGAME` 原位发布，遵守 `AGENTS.md`、`WORKFLOW.md` 第 8 节和 `Docs/AssetSetup.md`；仅收录巫婆相关文件及共享文件中的巫婆片段。

## 当前保留版本

F6 唯一入口为 `WitchRebuilt` / **巫婆·重建候选**，角色类 `AWitchRebuiltMonster`，公共战斗基类 `AWitchMonster` 为 Abstract。当前修订包括 Seams07 / Drape07 连续衣物及稳定布料绑定、Hands08 双手抓握、Fabric09 统一布面及 Revision11 材质连线修正、FlightDistance12 投瓶交接与远景 LOD，以及 LiquidProjectile13 普通毒弹湿润液团、尾迹和命中飞溅。

用户已认为整体模型基本达标；后续距离与毒弹修订没有游戏内验收。普通毒弹复用已有毒蛆材质和世界效果池，三发散射、伤害及业务释放时钟保持原合同。

## 归档

本次移入 `trash/witch-rebuilt-publication-20260923` 的共 249 个文件，约 1,115.63 MiB：未采用的 MeshLab 代理重采样脚本、专用 Python 依赖和输入输出，18 份被新保存覆盖的自动 `.blend1` 备份，以及已由常规构建替代的旧布料热编译辅助脚本。逐文件原路径、目标、字节数、原因和 SHA-256 见 [清单](../AssetArchives/witch-rebuilt-publication-20260923.json)，移动后散列已核对。

此前两款旧巫婆的 4 份原生文件和 12 个 UE 包已在 `trash/witch-variants-20260922` 中。既有清单为 [原生文件](../AssetArchives/witch-variants-native-20260922.json) 和 [旧包](../AssetArchives/witch-variants-assets-20260922.json)。本次发布对应源码删除与唯一入口接入，不重新执行 UE 资产删除。

保留有效 `Before` 作者输入、当前 `Authoring`/`Delivery`、诊断证据、Meshy 外观/法杖与 Foundation 模板。这些素材仍被现行制作脚本引用，不按文件日期或旧版本名称判废。

## 公开源码与本机素材

公开巫婆 C++、制作/导入工具、技术文档、归档散列、恢复说明，以及 SKILL 的长袍与毒液经验。共享 F6 目录、类重定向和模块依赖仅发布本任务片段；并行的导航提示、韧性数值、武器、UI 与预加载整套改动留在原工作区，不夹带发布。现有预加载表已经在本机刷新；其通用生成器与其他性能工作由对应改动管理。

`.gitignore` 对 `SourceAssets/WitchRebuilt20260921` 使用明确公开入口。Meshy 模型/PBR、Epic Quinn、Zombie Female 人体、完整源动作、密集姿态/几何采样、FBX、Blend、uasset、渲染、日志和本地桥接回执均保留本机；trash 不上传。公开脚本不包含这些原始或派生美术资源的再分发许可，Git 克隆不是完整可运行资源包。

## 恢复与继续制作

优先恢复当前 `Content/Monsters/WitchRebuilt`、`SourceAssets/WitchRebuilt20260921/Authoring` 和 `Delivery`，以及合法来源的 `WitchMeshy20260919`、`WitchFoundation20260920` 必要输入。具体人体、骨架、动作和外观来源见 [源目录说明](../../SourceAssets/WitchRebuilt20260921/README.md)。毒弹还依赖现有 `Content/Monsters/PoisonMaggot/VenomLiquid20260915`。

制作入口在 `Tools/WitchRebuilt`，它同时保留历史分阶段脚本和按需排查工具，不能把整个目录依次运行覆盖最终资产。当前衣物结构见 `author_seams07.py`、持握见 `author_hands08.py`、统一材质见 `author_fabric09.py` / `install_fabric09.py`，远景 LOD 见 `install_distance12.py`；这些脚本依赖对应修订的本机 `Before` 或参数输入。导入通过 `Tools/AssetPipeline/mcp_call_codex.ps1` 批次互斥；不执行已归档的重采样与热编译脚本。

SKILL 更新到 `skills/ue5-monster-workflow` 对应参考，并同步个人技能：稳定显示绑定、左右掌面与拇指局部轴、统一布面连线、手持到抛出交接、布料距离迟滞/LOD，以及跨怪物共用毒液效果池。局部参数作为案例，未把早期失败方案或尚未实测的性能写成通用标准。

## 构建与发布检查边界

最近一次本机完整宿主常规 Editor 构建成功，日志 `Saved/BuildEditor/build-20260923-072738.log`，随后已发起编辑器重开。本次只做用户要求的归档与发布检查，包括精确暂存差异、空白错误、文件大小、敏感信息、再分发边界、远端提交关系与推送回读；不重新编译、启动 PIE、运行回归或渲染。

本机仍有其他模块的并行修改，该构建记录不等同于对本次公开源码快照单独构建或游戏验收。提交及推送只使用普通 `HEAD:main`，不强推，不改写其他历史。
