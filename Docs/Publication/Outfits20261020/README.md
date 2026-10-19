# ST6、法师套装与钢盔源码发布（2026-10-20）

本次直接在 FPSGAME 主仓库提交本对话的服装工作。共享文件只抽取衣物／头部装备所需的改动；其他会话的武器、技能、天气、背包和数值调整留在工作区。公开仓库为源码与制作配方，不能替代完整本机工程。

## 当前版本与制作入口

| 范围 | 当前入口 | 本机依赖／结果 |
| --- | --- | --- |
| ST6 领口与布面 | SourceAssets/ST6Reset20261017/recipe.py → ST6Refine20261018，含 NeckClosure | 保留原生身体、材料、领口源和保存资产；不能只回放旧袖身发布 |
| ST6 袖子 | Tools/ST6SleeveRepair/capture.py、author.py、save_assets.py、publish.py | 正式 23 个第一人称 profile；Body 与 Jason 沿用领口修复 |
| 其他上衣袖子 | Tools/GarmentSleeveRepair | 按原生 profile 派生；保留 ShortSleeveAuthoring 与当前材质输入 |
| ST6 裤靴／七分裤／其他裤腰 | Tools/ST6LowerSet、Tools/TrouserFit、Tools/SmokeGreyCapri/waist_fit.py | 普通与长靴收口变体，不替换原生骨架 |
| 法师上衣与裙摆 | Tools/BlueMageRobe | 身体 FacingFix20261020，内层 HemContinuity20261019，材质 20261020-cross-section-v3 |
| 法师帽／手套／裤子／靴子 | Tools/BlueMageHat、BlueMageGloves、BlueMagePants、BlueMageBoots | 各自 SourceAssets 同名日期目录；原生绑定与 fitted 变体 |
| 套装图标 | Tools/BlueMageSetIcons；法袍 export_facing.py、save_hem_refinement.py | 规范 PNG、家族 PNG、UI Texture、独立展示网格 |
| 钢盔 | Tools/SteelArmet/author_reference_match.py、author_reference_visor.py、bake_reference_surfaces.py、package_reference_blend.py、save_reference_assets.py、publish_reference_match.py | ReferenceMatchV5；run_asset.ps1 默认已指向当前保存入口 |

## 恢复顺序

1. 使用已许可的本机原生角色和各武器网格／骨架，恢复既有 GarmentFoundation、V7 裸臂、共享身体、Witch 布料作者类以及对应历史衣物母版。公开仓库不包含这些资产的再分发副本。
2. 从本机备份恢复本表各 SourceAssets 的 Read、Authored、纹理、导出、配方回执与生产输入；本次仅将明确退出的候选移到 trash，不能从当前模型再导出替代作者源。
3. 必要时在后台构建 FPSGAMEEditor，再用对应 run_asset.ps1 与现有批次互斥执行保存。每次指定唯一回执名；已有编辑器时沿现有桥执行，不另启覆盖其未保存资产。
4. 法袍身体从 FacingFix20261020/Before 的原生数据经 repair_facing.py 生成，export_facing.py 保存可编辑源，save_facing.py 保存 UE 包，再 publish_facing.py 更新对应键。LegFit20261019、HipFit20261019、FacingFix20261020/Before 与 HemContinuity20261019/Read 是有效重建输入，保留在本机。
5. 连续内层使用 capture_hem_sources.py → author_hem_layers.py → save_hem_layers.py → publish_hem_layers.py。材料最终修订使用 hem_conform.hlsl、hem_materials.py、save_hem_refinement.py、publish_hem_refinement.py；不要重新执行旧 StairVisibility 整段隐藏小腿发布。
6. 头部装备由 player_body.json/head_equipment 选择静态／动态网格与逐头型拟合；法师帽和钢盔共享生命周期入口，视野层只在本地拥有者显示。SteelArmet 根目录 fit.json 与 BlueMageHat/native_head_jason.json 仍是当前钢盔制作依赖。
7. 各 save 脚本完成并保存后才执行其 publish；最终按源哈希对应保存回执。脚本存在、配置引用存在和资产已保存是不同状态。

## 归档与保留

[archive-manifest.json](archive-manifest.json) 逐文件记录原路径、trash 目标、大小、SHA-256、原因和替代物。本次归档 199 个文件，共 2,128,534,766 字节；移动前确认所有路径位于本仓库授权范围，移动后核对内容哈希。

退出方案：MovementFit 放大碰撞与相关发布／回滚工具；StairVisibility 整段隐藏小腿与踝帽；未接入的活动褶候选；ST6 早期 Draft；钢盔初稿／Refined 及旧视野框；一次性停止 PIE／退出编辑器助手。内容位于 `trash/Outfits20261020/<原相对路径>`，不进入公开 Git。

保留：仍被读取的 Before、Read、原生身体和权重、当前保存资产、有效几何输入、历史诊断和本轮最终回执。StairRepair 历史诊断请求仅用于解释旧问题，其未接入候选已归档；不得直接视为当前运行参数。Content 中旧 UE 包未作无依据删除，以保留本机回滚与依赖。

## 证据边界

本轮执行的是仓库整理与推送前审查，没有启动 UE、游戏或新回归。前一轮的 hem-refine 构建与材质／图标保存回执在 SourceAssets/BlueMageRobe20261018/HemRefine20261020；当前源引用的已保存内层为 31 个派生网格、32 条映射。离线 2,352 个截面案例的历史结果只说明算法比对，不是运行画面验收。

2026-10-19 的 BlueMageSetAudit 曾完成真实 UDP 主机／客机与同档重连 14/14 阶段，证据保留在 SourceAssets/BlueMageSetAudit20261019/Wire。其后已更改法袍身体、连续内层、材料和布料时序；该早期结果不覆盖当前版本。最新楼梯、空手转身、各武器运动以及联机视觉仍由用户体验，不声明本次已通过。

## 发布边界

只提交原创建模／材料工具、配方、C++、文档与技能；不提交 PNG、贴图、FBX、Blend、UE 包、密集几何／姿态 JSON、日志、缓存或 trash。共享 items.json 仅更新本轮裤靴图标与新 ST6 下装条目；防御数值及其他物品改动不夹带。头饰仅提交法师帽／钢盔配方，其他帽子保留给其任务。modular_outfits 保留本轮衣物数据和已有 Super90 profile 的独立手套标记；其他任务新增的枪械别名不随本次发布，导入它们时继续复用对应 rig_profile。

[publication-manifest.json](publication-manifest.json) 记录提交文件范围、发布前基线、共享文件提取方式和保留依赖。历史设计文档保留过程记录，以本页的当前入口为准。
