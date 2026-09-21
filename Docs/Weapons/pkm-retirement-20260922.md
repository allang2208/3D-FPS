# PKM 全系列废案归档（2026-09-22）

用户已明确否定本轮 PKM 建模与开发，整轮退役，无保留的已接受 PKM 替代版本。该结论覆盖生成、初次接入及后续各次优化，最后导入的 VideoAdaptation10 也在其中；不得以文件名、版本号或导入成功恢复为正式枪械。

## 本机归档

归档根为 `trash/pkm-rejected-20260922`。共移出 **903 份文件**，另保存 **18 份共享文件修改前快照**，合计 7,219,927,706 字节。原路径、目标、大小、SHA-256、理由及保留替代物见 [完整归档清单](pkm-retirement-20260922-manifest.json)。复制/移动前限定目标根，归档后逐文件读回散列；这属于用户要求的仓库整理，不是游戏测试。

- `SourceAssets/PKM20260921`：795 份参考、Meshy 原始结果、贴图、Blend、FBX、动作数据、脚本与历史回执，整目录归档。
- `Content/Weapons/PKM`：106 个包，包含 Integrated20260921、Refined20260921、SourcePreserve20260921、SightGrip20260921 四套导入目录及其动作、骨架、材质和贴图。通过现有互斥桥在 UE 内先保存、归档，再移除；移除前未发现该目录外的包依赖。
- `Source/FPSGAME/Weapons/PKMWeaponAssets.h` 和本轮专用 `Saved/Logs/PKM10Import.log` 一并归档。
- `SharedFileSnapshots` 保存本轮清理前的共享文件；它们含并行内容，只能用来提取 PKM 历史片段，不能整文件覆盖恢复当前工程。

本机绝对归档位置：`D:/FPS3D/FPSGAME/trash/pkm-rejected-20260922`。操作回执与本次源码移除补丁保存在 `Saved/PKMRetirement20260922`。

## 有效入口移除

移除 `ue_pkm`、专用 `ammo_762x54r` 的新目录定义和初始仓库发放，移除 PKM 的网格/动画选择、换弹声音时点、弹链显示、冲刺、检视、抛壳、图标/掉落支持、预加载和 cook 入口。保持 A762、AKM、M4 与其他武器的内容和并行改动。

`source-combat-items.json` 中原有 PKM 历史数值资料不属于本次 UE 接入，保留。历史文档中的 PKM 分析/精确暂存案例也保留，不代表当前武器目录。未清空用户存档、弹药袋或仓库保存文件；已有存档的旧条目不因本次文件归档被主动删除。

## 可复用经验

经验写入枪械技能的 [生成枪体精修](../../skills/ue5-weapon-workflow/references/generated-rifle-refinement.md)、手臂技能的 [整臂适配](../../skills/ue5-fps-arms-animation/references/grip-arm-refinement.md)，并在通用模型、枪械、手臂三个 SKILL 入口增加路由。新增内容同步到个人技能和工程镜像；已有其他章节差异未借此覆盖。

记录失败边界：空间切分不等于机械分件；材质调整不能修复碎面/硬边；成熟手指姿态不等于正确肩肘腕支撑；视频遮挡内部仍需承认不确定。此次没有独立对照证明失败必然来自 Meshy 或 UE 导入器，不作此归因；09/10 版的方法也没有被转写成成功模板。

## 构建与发布边界

源码移除已写入本机工作树。通过互斥桥尝试必要的 Live Coding 构建，失败于现有 `FrostRuneVisualDiagnosis.cpp` 的未声明 `Weapon` 和 `RuneGoldMaterialCommandlet.cpp` 的 `FindPropertyByText` 等错误。未修改这些并行文件，也未强制关闭编辑器；本轮没有成功生成或应用新的原生模块，当前进程仍可能带有旧的已编译分支。修复这些构建错误并完成常规构建后才能更新基础 DLL/EXE。

公开 HEAD 原本未包含本次 PKM 运行接入及其专用头文件；它们均来自本机未提交工作。清除这些新增项不会为了显示“代码改动”而一并提交共享文件里的其他功能。本次公开提交为归档散列/范围说明和对应 SKILL 教训。

Git 不包含 `trash`、参考视频/图片、Meshy 模型/PBR、Manny 或其他第三方源、Blend/FBX/uasset、密集动作数据、运行日志或凭据。允许商用不等于允许公开再分发；此次没有通过归档改变任何素材许可。只普通推送到已授权 `origin` 的 `main`，推送前审查待推提交、完整暂存差异、大小和敏感信息，完成后回读远端 SHA。

没有启动游戏测试、截图或验收渲染。归档完成、发布完成和原生构建受阻分别报告。
