# 储物箱表面材质改善提升计划（2026-09-24，规划稿）

范围：五档互动储物箱（`SK_WarehouseCrate_T1..T5`）与共用的一族材质 `M_Crate_*`
（静态 `SM_*_v2` 同用这一族，一并受益）。源宝箱（`MI_Ritual_*`/`MI_Chest_Ziarat_4K`）
只作**质量基准**，不在本计划改动范围内。计划确认后按阶段另行授权执行。

## 1. 现状盘点（证据）

- 材质组织：8 个**互相独立**的 master Material，无父/实例体系
  （`probes/material_inventory.json`；对比源宝箱＝`M_Ritual_Metal` 母材质 + 6 个 MIC 实例）。
  每档箱子最多同时重编 3~4 套完整 shader。
- 图结构（`fix_crate_materials.py` L75-116）：
  - Albedo：无独立基色贴图，用 `T_Crate_*_Surface`（MASKS 自定义打包：R=粗纹、G=细纹、B=粗糙）
    的 R/G 通道加权去 Lerp **两个常量色** → 颜色单调、无斑块/磨损/色相变化；
  - Metallic / Specular：**纯常量** → 金属不会在棱边"破漆露铁"，只有整体明暗；
  - Roughness：B 通道 Lerp 区间（唯一有变化的通道）；
  - Normal：直连，无强度标量、无 cavity 细节；
  - **完全没有** AO、边缘磨损、自发光通道。
- `M_Crate_Gem`：无贴图、三个常量（0.012 底色/金属 0/粗糙 0.05/高光 0.8），单面——宝石无光泽层次、不会发光。
- 贴图：5 组 2K（Surface=TC_MASKS、Normal=TC_NORMALMAP，`make_crate_maps_v2.py` SIZE=2048；
  第四轮木色已换游戏体素木纹，获认可）。`never_stream=False`、World 组——流送合规。
- 基准差距（为什么"观感糙"）：源宝箱是 Ziarat 大理石 **4K 五通道全套**（BaseColor/Cavity/Normal/
  Roughness/Specular）+ DirtyMetal 4K MR，材质语言=实例化+全通道分离；储物箱是"常量 tint + 打包噪声"。
- 已知遗留：骨骼 usage 标志已补齐并落盘（`probes/usage_readback.json` 8/8 skeletal:true；
  第七轮修复节）；`M_Crate_Gem` 单面为 authored 原状。

## 2. 总原则

- 表现目标：向源宝箱的"完成度"看齐（通道分离、实例化、细节层次），**风格仍走游戏体素语言**
  （第四轮已认可，不回退成写实大理石）。
- 性能边界（`skills/ue5-performance-packaging/references/fpsgame-performance-development.md` §3/§4）：
  贴图保持 2K 预算、World 流送组、不开 `never_stream`；材质从 8 套独立变 1 母 + N 实例，
  减 shader 变体而不是加。不引入材质函数依赖环。
- 制作纪律：一切改动后台 commandlet/桥完成；**每步保存后全新进程读回**；usage 标志清单
  （static+skeletal+two-sided）作为每次材质重建的收尾检查（第七轮教训，已入清单）；
  退役贴图入 `trash/` 记哈希；不碰几何/骨架/动画/碰撞/JSON/关卡。

## 3. 分阶段计划

### P0 基线复核（前置，用户动作）
重开一次 PIE 确认 usage 修复生效（木/石/铁/鎏金/银华五色 + 拱顶在位）。
生效后的截图即为本计划基线；若仍有问题先修它，不在糙基线上谈提升。

### P1 结构收敛：母材质 + 实例（半天，后台）
1. 新建 `M_Crate_Master`：Default Lit、Opaque、双标志（static+skeletal）、two-sided 开关参数化；
   输入契约：`T_Albedo`(sRGB) + `T_ORM`(Masks：R=AO, G=Roughness, B=Metallic) + `T_Normal`，
   加 `Tiling`、`NormalStrength`、`EdgeWear`、`EmissiveColor/Intensity` 等命名参数。
2. 8 个 `M_Crate_*` 改为挂在母材质下的 **MaterialInstanceConstant**（名称路径不变，
   5 个 SK 与 5 个 SM 的槽位引用零改动——对象替换、路径兼容）。
3. Gem 单独保留简单母材质（clearcoat 可选），补 two-sided。
- 产物：`Material/M_Crate_Master.uasset` + 8 个 MIC + 重编译回执；
- 验收：commandlet `recompile_material` 零错误；新进程读回每个实例的父/参数；
  PIE 日志无 "missing usage flag"。

### P2 贴图升级（1 天，后台，Blender/Python 程序化管线）
按族（wood/woodDark/stone/iron/ironDark/gold/silver/gem）产出三件套 2K：
1. **Albedo**（新增，sRGB）：从"常量双色 Lerp"升级为贴图直接基色——木纹保留体素语言；
   石材加斑驳与灰缝；铁/鎏金/银加氧化晕色与镀层色斑。
2. **ORM**（替换现 Surface 自定义打包，改标准通道）：
   - AO：板缝/铆钉脚/捆带压痕暗部（现完全缺失，立体感的主要损失点）；
   - Roughness：在现有变化基础上加指纹/磨损/漆面不均；
   - Metallic：常数改掩码——**棱边与铆钉磨损处露金属底**（T3/T4/T5 观感关键）。
3. **Normal**：现法线并入 cavity 微细节，强度参数化（默认 0.8，可调）。
- 预算：8 族 × 3 张 2K ≈ 24 张（含 mips 约 +33%），与现状 10 张相比增量受控；
  共用一张 2048 图集可作 P2 备选（省 draw，UV 需重排——默认**不做**，仅在显存告警时启用）。
- 验收：新图导入读回尺寸/压缩/sRGB 组；`read_image` 出差异清单（不做像素级验收）。

### P3 档位识别与点睛（半天，参数化，不再动贴图）
每档一组 MIC 参数（数值表执行时定稿，方向如下）：
- T1 木质：哑光清漆（rough 高带窄）、无金属露底；
- T2 石木：石面 AO 加重、木框旧化；
- T3 铁质：捆带金属掩码最强、铆钉 AO、冷灰高光；
- T4 鎏金：金面 rough 压低 + 雕花带**极低自发光**（暗处可辨"鎏"）；
- T5 银华：银面 + 宝石 `Emissive` 微光（Sapphire 色调，暗光下箱体第一识别点）。
- 验收：五箱同框并排截图（用户侧）一眼可分档。

### P4 验证与交付（半天）
- 离线：全家族重编译 + 新进程读回（父/参数/标志/贴图组）；
- 对照：同机位 `read_image` 基线 vs 提升后差异清单；
- 游戏内：**用户自行测试验收**（规则）；
- 文档：README 新增第八轮节；旧 `T_Crate_*_Surface/Normal` 退役入 `trash/crate-mat-p2/` 记哈希；
  git 精确暂存（素材目录 + README + 计划状态更新），是否提交听用户指令。

## 4. 风险与回滚

| 风险 | 对策 |
|---|---|
| MIC 替换 master 时槽引用丢失 | 路径不变原则 + 替换后 5 SK×11 槽读回 |
| 两-sided/usage 又漏 | P1 收尾清单强制检查（第七轮教训入 checklist） |
| 体素风格被"写实化"带偏 | Albedo 以第四轮认可图为新图底稿，只做增强不做换血 |
| 显存/预算超 | 2K 固定、图集备选、不开 never_stream，出现告警再议 |
| 编辑器开着改资产冲突 | 一律走 MCP 桥批次互斥；落盘以 mtime+新进程读回双证据 |

## 5. 明确不做

- 不动源宝箱材质、`warehouse_assets.json`、骨架/动画/碰撞/储存逻辑与关卡摆放；
- 不做 Nanite 化（骨骼网格不适用）；不动静态建造面板的构件数据；
- 不主动 PIE/截图/验收（用户规则）。
