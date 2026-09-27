# 高炉、铸造台与锻造：整理和源码发布

宿主：`D:/FPS3D/FPSGAME`。目标：`https://github.com/allang2208/3D-FPS.git` 的 `main`。遵守 WORKFLOW 第 8 节，保留当前共享分支和并行修改，以精确路径、片段发布，不重置或切换工作区。

## 当前成果

- 高炉连续液柱、水平模腔、飞溅与凝固锭，修复烟雾预算跳过出铁更新及池对象归还问题：[修复记录](../Fluids/furnace-casting-repair-20260926.md)。这是几何与材质驱动的流动表现，不是真实液体模拟器。
- 独立铸造台承接连续冶炼，成品架有界缓存，满架暂停；玩家领取并自行存箱。铸造台包含已认可铁砧、封闭木桶、水体、工具和挂件，沿用高炉扫描材质与同一风场：[挂件与做旧](casting-wind-weathering-20260927.md)、[当前作者说明](../../SourceAssets/CastingStationRealism20260927/README.md)。
- 第一人称锤／钳握持、缩圈目标、随机停留与回锤间隔、红热剑胚、击打火星与用户提供的打铁录音、入水淬火及蒸汽：[实景动作](../UI/forging-world-action-20260927.md)、[热感](../UI/forging-thermal-presentation-20260927.md)、[火星加强](../Fluids/forge-sparks-boost-20260927.md)、[快速落锤](forge-fast-downstroke-20260927.md)。旧计划中的固定回合时长是历史设计，实际以当前系统和后续随机节奏记录为准。
- 三把剑共用剑胚，配方读现有材料；工艺伤害修正、物品浮窗、领取／废弃折半返料与存档仍走各系统入口：[三剑配方](../UI/forging-sword-recipes-plan-20260927.md)、[浮窗](../UI/forged-weapon-tooltip-20260927.md)。
- 最新材料 UI 为名称银白、持有量与“已满足／缺 N”红绿、所需数量灰色，数字分列右对齐；有工件时读取支付记录并显示中性“已投入”。[审计与实施记录](../UI/forging-cold-steel-audit-plan-20260927.md)中其他优化仍是待办，未借整理发布实施。

## 废案归档

42 份文件，共 38,078,222 字节（约 36.31 MiB），移动至本机 `trash/forging-publication-20260927/`。逐文件路径、大小、SHA-256、原因及保留替代物见 [归档清单](forging-retired-20260927.json)。移动前核对绝对路径边界，移动后回读散列。

归档包括未采用的四张面板背景及制作记录／导入器、弃用的背景 UE 纹理、被用户否定并由 V3 替代的铁砧 V2、工具架／风化／落锤前快照、失败金流作者快照、两个自动 `.blend1` 与已被用户录音替代的合成 WAV。同步移除背景图的强制 cook 项和旧铁砧 V2 安装回退；没有删除原始用户 MP3。

**保留的旧源有实际用途：** 当前 `author_geometry.py` 仍打开 `AnvilReferenceV3/Authored/CastingStation_AnvilReference_Source.blend`，V3 作者继续读取初版总装。因此初版总装、V3、当前 V7 制作源与 FBX、纹理、来源证明、保存回执均保留。旧作者辅助函数仍被当前脚本引用时也保留。`trash` 不公开提交。

## Git 内容与运行接入边界

直接发布材料配方、作者／导入脚本、HLSL、相关制作记录、归档清单与三组 SKILL 更新。脚本的执行环境是 Blender 或 UE Python，不将静态语法检查称作导入成功。

共享工作区的运行实现涉及尚未发布的工作台输入类型、伤害改造倍率、地牢输入恢复等接口，不能将整份共享文件连带提交。本次将 21 份新运行源保存为 [新源交接补丁](ForgingPublication20260927/new-runtime-sources.patch)，将 27 份共享文件的本题改动保存为 [接入交接补丁](ForgingPublication20260927/shared-runtime-hooks.patch)。基础提交、源文件散列、排除项和合并注意事项见 [交接清单](ForgingPublication20260927/runtime-handoff.json)。

补丁是公开源码记录，**未应用到公共 `Source` 树，Git 克隆不能单独重建本机全部锻造行为**。伤害和浮窗混合位置只抽取 Forge 修正，合入完整接口时保留既有近战／工具倍率且避免再次乘 Forge；地牢恢复输入的分支须保留 `!IsWorldForging()` 门控。完整宿主已经包含这些修改，不要重复应用补丁。本机源码、已保存资产与上轮 DLL 保持可继续开发状态。

## 本机资产和恢复顺序

1. 恢复现有高炉石／铁扫描、Normandy 木材、Clearwater 波纹、Mantaflow 图集、Manny 抓握供体及认可 V7 原生手臂；它们沿用原有素材许可。
2. 高炉几何与材质入口：`Tools/Fluids/build_furnace_casting_mesh.py` → `author_furnace_casting.py`，辅助 `furnace_material_graph.py`。旧 `author_furnace_tap_metal.py` 已转向正式作者。
3. 总装作者：`CastingStation20260926/author_station.py` → `AnvilReferenceV3/rebuild_anvil.py` → `CastingStationRealism20260927/author_geometry.py`。恢复相应 manifests／纹理，再由 `install_station.py` 路由当前 `install.py`；做旧与动态挂架入口为 `install_wind_weathering.py`，保持七个材质槽与挂点。
4. 锤钳与动作入口在 `Tools/Forging`。恢复本机 `Content/ColdSteelData/forge-grip.json`、可编辑 Blend、V7 手臂与骨架采样，再按当前落锤参数制作并导入；淬火可编辑源单独保留。录音由 `author_sound.py` 转换，`import_forge_audio.py` 仅导入接触音。
5. 恢复 `/Game/Props/CastingStation20260926`、`/Game/Props/ForgeInteraction20260927`、`/Game/Fluids/FurnaceCasting20260926` 及当前建筑 palette／相关资产依赖。参数 JSON 与脚本并不替代已导入 UE 包。

二进制、骨架／姿态数据、密集采样、FBX／Blend、扫描纹理、音频、运行回执、Saved 和 trash 留本机。`forge-grip.json` 含授权供体姿态，不因是 JSON 就对外分发；用户提供录音也没有自动取得再分发许可。纯材料配方 `forging-recipes.json` 不含这些数据，可公开。

## SKILL 与检查

- 冷钢 UI：数量与状态语义色、已支付快照、数据口径、行复用及动态补行的字体／DPI。
- 第一人称手臂：工具相对握持、腕肘与相机开口区分、落锤接触同步及淬火。
- 流体表现：连续金流、池归还、实际接触火星／蒸汽及挂件共享风场。

个人技能与工程镜像同步对应新增参考页及入口，保留各自其他修改。发布检查限定为用户授权的文件范围、归档散列、暂存差异、脚本语法／JSON、敏感信息、文件大小、许可边界与远端回读；没有重新构建、导入、启动编辑器或运行游戏测试。最近一次材料 UI 常规构建为 `forging-material-columns-20260927-r2.log` 的 `Succeeded`，不将它写成公共交接补丁的构建验证。
