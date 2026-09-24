**用户规则（2026-09-20）：禁止主动向其他对话/任务发送协调消息。** 不调用 send_message_to_thread 或跨任务消息工具询问占用、请求让位、通知释放、协商编译/重启；不通过轮询其他对话或共享留言板变相协调。接入等待交由桥的批次互斥处理，期间继续独立制作。真实文件/资产归属冲突或无法安全执行的编译/重启，保留现场，仅在当前对话向用户简要说明阻塞；不联系其他对话。此规则覆盖旧文中的“定向协调/集中协调”等要求；只有用户明确另行要求发送指定消息时才执行。

**全局用户规则（2026-09-12）：所有工作默认不主动进行检查、测试或验收，由用户自行测试；仅用户明确要求时执行。此规则覆盖本项目文档、SKILL 及引用文档中的默认验证要求。必要的开发、构建与接入照常完成，交付时如实说明未测试。**

**默认后台制作、编译与落盘（用户确定，2026-09-23）。** 不主动启动 UE 编辑器。源码、配置、文档、外部模型/贴图/动画，以及可在后台完成的构建、导入和保存，优先通过文件、命令行或适用的 commandlet 完成。只有用户明确要求打开，或必要操作确实无法在后台完成、只能在编辑器中进行时，才打开 UE；仅剩必要编辑器操作时使用短批次接入。 后台构建成功后直接交付，不自动打开或重启编辑器；已经运行的编辑器不因本规则主动关闭。必要编辑器接入统一使用 Tools/AssetPipeline/mcp_call_codex.ps1 的批次互斥；不另起进程覆盖已加载资产，不强制结束他人编辑器。详细条件见 [后台开发与编辑器使用条件](skills/ue5-auto-assistant/references/editor-open-development.md)。

# 当前开发方向

当前工程为根目录 `FPSGAME.uproject`（UE 5.8.2）。用户已指定后续全面转向 UE5；Godot 只作为归档参考。完整本机宿主为 `D:/FPS3D/FPSGAME`，Git main 的当前源码直接位于根目录，不再仅发布 `unreal/<topic>` 摘录。

- 开发和发布先读 [WORKFLOW.md](WORKFLOW.md)，仓库整理、归档与推送遵守第 8 节。
- 枪械读 [ue5-weapon-workflow](skills/ue5-weapon-workflow/SKILL.md)，手臂和 MAT 读 [ue5-fps-arms-animation](skills/ue5-fps-arms-animation/SKILL.md)。先参考现有动作，核对实际运行加载，再修改。
- 天气读 [ue5-weather-workflow](skills/ue5-weather-workflow/SKILL.md)，调试读 [ue5-debug-validation](skills/ue5-debug-validation/SKILL.md)。
- 流体特效（枪口烟、火焰／爆燃烟、水花／涟漪、毒液／毒池、血液及冷雾）的新增、优化与针对性修复，先读 [流体特效工作流](skills/ue5-fluid-vfx-workflow/SKILL.md)。后续同类任务按此标准制作，复用离线流体源、共享调度与有界池，保留已认可的水花方块修复；技能数值、枪械动作和怪物 AI 仍走对应领域技能。执行后台制作／必要编译／资产保存，不自动测试或验收。
- 新建或改造面板、页签、栏目、卡片与弹窗，先读 [面板与栏目工作流](UI-WORKFLOW.md) 和 [UE UI 技能](skills/ue5-ui-umg-slate/SKILL.md)，按 [规划模板](Docs/UI/panel-column-plan-template.md) 明确结构、响应布局、数据范围、状态和交互，再按授权阶段制作／接入。
- 冷钢 UI 以 [正式设计规则](Docs/UI/ui-cold-steel-design-system.md) 为准：黑灰低透明度玻璃、Noto Sans SC／JetBrains Mono、统一按钮；冲突的旧字体、配色和抽屉条款由该文替换。共享 `ColdSteelUIStyle`，不再复制近似主题。
- 非枪械物品（药水、材料、弹药包装、卷轴）的图标、三视图、按精度分流的模型制作、材质与稀有度光效读 [ue5-item-asset-workflow](skills/ue5-item-asset-workflow/SKILL.md)。
- 怪物制作、混元管线、专用绑骨、动画、布娃娃、战斗和村庄刷怪读 [ue5-monster-workflow](skills/ue5-monster-workflow/SKILL.md)。手脑案例中的未通过项不作为已完成标准。
- 20 cm 体素建造（材质、放置构件、承重与倒塌数值）读 [体素建造工作流](Docs/Building/voxel-build-workflow.md)：任何材质的净跨 2 m 必须成立，改承重数值必须跑 `Tools/Building/run_voxel_stress_probe.ps1` 离线探针；带资产的 USTRUCT 不要用热补丁改。
- 地貌破坏（丘陵高度场弹坑、铲子挖／填、下沉与抬升上限、性能开关）读 [地貌破坏：高度场方案](Docs/WorldGeneration/terrain-destruction-20260916.md)；体素地形已退役（归档在 `trash/voxel-terrain-retired-20260916/`），不要再叠加第二套地形。它与 20 cm 建造体素是两套语义，不要混用。
- 丘陵地表材质（分层家族、按高度图混合、近景视差凹凸、顶点色与 `Wetness` 契约、材质 HLSL 离线校验）读 [丘陵地表材质：分层与凹凸](Docs/WorldGeneration/ground-material-layered-20260918.md)；运行时地形用 DynamicMesh，没有 Landscape，Landscape 节点一概不可用。重建一律走 `Tools/WorldGeneration/build_hills_ground_v2.py`，不要重跑已作废的三层／河岸旧脚本。
- C++ 玩法实现（Actor/Component/DataAsset、UPROPERTY/UFUNCTION、GameplayTags）读 [ue5-cpp-gameplay](skills/ue5-cpp-gameplay/SKILL.md)；世界交互（拾取、生成器、overlap/trace、反馈）读 [ue5-world-interaction](skills/ue5-world-interaction/SKILL.md)；PCG 生成、模块化建筑与运行时高度场地表读 [ue5-pcg-building](skills/ue5-pcg-building/SKILL.md)；PIE 性能、打包前检查与发布就绪读 [ue5-performance-packaging](skills/ue5-performance-packaging/SKILL.md)。
- UE 模块名（`RenderCore`、`AIModule` 等）到领域的对照表在 [UE 模块索引](skills/ue5-module-router/references/ue5-module-routing-table-final.csv)，**技能分流以本文件上面的清单为准**；该表约 76% 的行指向已不存在的技能（`ue5-architecture`、`ue5-save-load-replication`），只当模块清单查，不要按它的 `TargetSkill` 跳转。
- 保留动画时序、UI、库存、存档和并行修改。源码编译与真实运行验收分别报告。
- FPSGAME 后续开发把性能约束纳入制作：触及 HUD／属性／技能读取、场景灯光与几何、纹理或图标加载时，读取 [性能开发约束](skills/ue5-performance-packaging/references/fpsgame-performance-development.md)，复用有界缓存和已有调度，避免重新引入重复刷新、同步等待与无预算资源。保留已恢复的光追／Lumen；本规则不自动授权采样或测试。
- 截图、渲染与候选图的判读：**交互读图直接用会话内挂载的 `read_image` 工具**（能看图、可追问、不需要 key）；需要批量、headless 调用或刻意不让图片字节进会话历史时才走 [读图脚本](Tools/deepseek-vision.ps1)。用法与边界见 [DeepSeek Flash 读图](Docs/deepseek-vision.md)。读图只做定性确认和差异列表；定量几何用像素测量，最终视觉验收仍由用户拍板。
- 技能与魔法开发、迁移及左手施法读 [技能／魔法标准工作流](skills/ue5-skill-magic-workflow/SKILL.md)。当前火球左手 V3 已获用户认可，后续复用动作占用、数据接入与完整骨段方法，数值按具体技能调整。
- 唯一日常开发及 Git 工作目录为 `D:/FPS3D/FPSGAME`，直接从这里提交并推送 `origin/main`。本目录已有独立 `.git`，不依赖 E 盘仓库。E 盘旧仓库/发布副本已退出工作流；不要再建立常驻同步副本。并行修改精确暂存，保留未提交工作。
- 退役文件放 `trash/<task>/` 并记录散列。二进制资源及恢复边界见 [AssetSetup](Docs/AssetSetup.md)，未审核再分发许可的原始资源不公开提交。

## 通用模型生成入口（2026-09-13）

用户指定新的配件、枪械、怪物、道具和建材模型生成采用 [asset-model-workflow](skills/asset-model-workflow/SKILL.md)。先按形态与精度分流：5080 优先用于冰锥、矿石、树干等不规则粗糙主体；精细小件、工具、灯具和规则构件优先 Blender／Vibe3D 精确建模，再转对应领域技能。保留明确指定的模型路线与已认可资产；不得将后握把参数直接套到所有类别。继续遵守默认不主动测试、预览或验收的用户规则。

## Vibe3D 建模入口（2026-09-19）

规则几何与模型后处理使用 [Vibe3D 制作与后处理](skills/asset-model-workflow/references/vibe3d-workflow.md)，由通用模型技能分流；PCG、动画、玩法接入继续走各自技能。按需使用现有 UE MCP 桥，不自动运行插件测试、截图或建模验收，不批量替换已认可资产。
