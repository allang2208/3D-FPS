# 主场景祭坛：已生成，保存受阻

2026-09-22，用户要求移除 O 快捷键，通过主场景方形祭坛打开出征面板。

- 目标关卡 `/Game/GameMaps/DayNight_Lighting`。
- 编辑器中生成的对象标签 `Expedition_SquareAltar`，文件夹 `Main Hub/Expedition`，Actor 标签 `ColdSteel.ExpeditionAltar`。
- 使用现有 `/Game/Props/SquareAltar20260922/SM_SquareAltar`，保持原比例、四材质及三角面碰撞；相对 PlayerStart 前方 650 cm、左侧 400 cm，底部贴 Floor。
- `place_hub_altar.py` 已完成 Actor 创建、标记和碰撞设置；最后 `save_current_level()` 失败。日志 2026-09-22 09:27:32 UTC 报告 `DayNight_Lighting.umap` 无法移动，Windows Error Code 32（共享占用），随后 `Error saving`。
- 该对象当时留在编辑器未保存的主场景中。没有宣称已持久化；不要关闭这份未保存场景。文件占用解除后，可在当前场景保存，或重新执行此脚本复用已有标记，不重复生成。
- 提示与 E 交互源码已改，O 快捷键源码已移除；本轮相关编译单元完成编译，全工程链接被 `AAuthoredDungeonGenerator::EndPlay` 未定义符号阻塞。没有修改该地牢类，也没有结束任何 UE 进程。
- 没有启动 PIE、截图或运行测试。保存及原生链接完成前，本轮接入属于未完成状态。
