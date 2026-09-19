**全局用户规则（2026-09-12）：所有工作默认不主动进行检查、测试或验收，由用户自行测试；仅用户明确要求时执行。此规则覆盖本项目文档、SKILL 及引用文档中的默认验证要求。必要的开发、构建与接入照常完成，交付时如实说明未测试。**

# 当前开发方向

当前工程为根目录 `FPSGAME.uproject`（UE 5.8.2）。用户已指定后续全面转向 UE5；Godot 只作为归档参考。完整本机宿主为 `D:/FPS3D/FPSGAME`，Git main 的当前源码直接位于根目录，不再仅发布 `unreal/<topic>` 摘录。

- 开发和发布先读 [WORKFLOW.md](WORKFLOW.md)，仓库整理、归档与推送遵守第 8 节。
- 枪械读 [ue5-weapon-workflow](skills/ue5-weapon-workflow/SKILL.md)，手臂和 MAT 读 [ue5-fps-arms-animation](skills/ue5-fps-arms-animation/SKILL.md)。先参考现有动作，核对实际运行加载，再修改。
- 天气读 [ue5-weather-workflow](skills/ue5-weather-workflow/SKILL.md)，调试读 [ue5-debug-validation](skills/ue5-debug-validation/SKILL.md)。
- 新建或改造面板、页签、栏目、卡片与弹窗，先读 [面板与栏目工作流](UI-WORKFLOW.md) 和 [UE UI 技能](skills/ue5-ui-umg-slate/SKILL.md)，按 [规划模板](Docs/UI/panel-column-plan-template.md) 明确结构、响应布局、数据范围、状态和交互，再按授权阶段制作／接入。
- 冷钢 UI 以 [正式设计规则](Docs/UI/ui-cold-steel-design-system.md) 为准：黑灰低透明度玻璃、Noto Sans SC／JetBrains Mono、统一按钮；冲突的旧字体、配色和抽屉条款由该文替换。共享 `ColdSteelUIStyle`，不再复制近似主题。
- 非枪械物品（药水、材料、弹药包装、卷轴）的图标、三视图、5080 模型、材质与稀有度光效读 [ue5-item-asset-workflow](skills/ue5-item-asset-workflow/SKILL.md)。
- 怪物制作、混元管线、专用绑骨、动画、布娃娃、战斗和村庄刷怪读 [ue5-monster-workflow](skills/ue5-monster-workflow/SKILL.md)。手脑案例中的未通过项不作为已完成标准。
- 20 cm 体素建造（材质、放置构件、承重与倒塌数值）读 [体素建造工作流](Docs/Building/voxel-build-workflow.md)：任何材质的净跨 2 m 必须成立，改承重数值必须跑 `Tools/Building/run_voxel_stress_probe.ps1` 离线探针；带资产的 USTRUCT 不要用热补丁改。
- 地貌破坏（丘陵高度场弹坑、铲子挖／填、下沉与抬升上限、性能开关）读 [地貌破坏：高度场方案](Docs/WorldGeneration/terrain-destruction-20260916.md)；体素地形已退役（归档在 `trash/voxel-terrain-retired-20260916/`），不要再叠加第二套地形。它与 20 cm 建造体素是两套语义，不要混用。
- 丘陵地表材质（分层家族、按高度图混合、近景视差凹凸、顶点色与 `Wetness` 契约、材质 HLSL 离线校验）读 [丘陵地表材质：分层与凹凸](Docs/WorldGeneration/ground-material-layered-20260918.md)；运行时地形用 DynamicMesh，没有 Landscape，Landscape 节点一概不可用。重建一律走 `Tools/WorldGeneration/build_hills_ground_v2.py`，不要重跑已作废的三层／河岸旧脚本。
- 保留动画时序、UI、库存、存档和并行修改。源码编译与真实运行验收分别报告。
- 截图、渲染与候选图的判读走 [读图工具](Tools/deepseek-vision.ps1)，用法与边界见 [DeepSeek Flash 读图](Docs/deepseek-vision.md)。读图只做定性确认和差异列表；定量几何用像素测量，最终视觉验收仍由用户拍板。
- 技能与魔法开发、迁移及左手施法读 [技能／魔法标准工作流](skills/ue5-skill-magic-workflow/SKILL.md)。当前火球左手 V3 已获用户认可，后续复用动作占用、数据接入与完整骨段方法，数值按具体技能调整。
- 唯一日常开发及 Git 工作目录为 `D:/FPS3D/FPSGAME`，直接从这里提交并推送 `origin/main`。本目录已有独立 `.git`，不依赖 E 盘仓库。E 盘旧仓库/发布副本已退出工作流；不要再建立常驻同步副本。并行修改精确暂存，保留未提交工作。
- 退役文件放 `trash/<task>/` 并记录散列。二进制资源及恢复边界见 [AssetSetup](Docs/AssetSetup.md)，未审核再分发许可的原始资源不公开提交。

## 通用模型生成入口（2026-09-13）

用户指定新的配件、枪械、怪物、道具和建材模型生成采用 [asset-model-workflow](skills/asset-model-workflow/SKILL.md)。先按同一对象三视图与 5080 候选流程制作，再转对应领域技能。保留明确指定的模型路线与已认可资产；不得将后握把参数直接套到所有类别。继续遵守默认不主动测试、预览或验收的用户规则。

## Vibe3D 建模入口（2026-09-19）

规则几何与模型后处理使用 [Vibe3D 制作与后处理](skills/asset-model-workflow/references/vibe3d-workflow.md)，由通用模型技能分流；PCG、动画、玩法接入继续走各自技能。按需使用现有 UE MCP 桥，不自动运行插件测试、截图或建模验收，不批量替换已认可资产。