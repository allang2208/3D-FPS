# 技能体系梳理与重组（2026-09-23）

范围：`skills/` 148 个文件、15 个技能入口。本轮只做结构重组与路由修复，**不删任何经验内容**；
唯一删除的是一个已作废的草稿 CSV。

## 结论

**不是"一个大文件"的问题。** 顶层已经是 15 个技能 + `references/` 的分离结构，且没有集中清单，
技能按 name 按需加载，15 个入口不会同时进上下文。12/15 个技能的入口显著小于其 references，
渐进披露本来是生效的。

真正的问题是三类，都与"大小"只有部分关系：

1. 两个高命中入口把**案例笔记写在了入口里**，每次调用都全额加载；
2. 一段政策被**逐字复制到 15 个入口**，形成 15 处可漂移副本；
3. 一个 **83.6k token 的路由技能基本失效**，并让 4 个技能事实上不可达。

## 诊断数据（重组前）

| 项 | 数值 |
| --- | --- |
| `skills/` 总量 | 1,291,653 B / 148 文件（≈40 万 token） |
| 最大单文件 | `ue5-module-router/references/ue5-module-routing-table-final.csv` 149 KB ≈ 46.7k token |
| 死数据 | `…-draft.deprecated.csv` 111,740 B ≈ 35k token，无人引用 |
| `ue5-module-router` 总量 | 267 KB ≈ 83.6k token（全树 20.7%），**AGENTS.md 未点名** |
| 路由表有效率 | 755 行中 572 行（76%）指向**不存在**的技能（`ue5-architecture` 532、`ue5-save-load-replication` 40） |
| `asset-model-workflow/SKILL.md` | 43,906 B ≈ 13.7k token，其中 **81.6% 是带日期案例**；入口/细节比 2.14（全树唯一 >1.1） |
| `ue5-fps-arms-animation/SKILL.md` | 28,046 B ≈ 8.8k token，**64.8% 是带日期案例** |
| 政策副本 | 「默认后台制作」出现在 **20 个文件**（含全部 15 个入口） |
| AGENTS.md 未点名的技能 | `ue5-cpp-gameplay`、`ue5-pcg-building`、`ue5-performance-packaging`、`ue5-world-interaction`、`ue5-module-router` |

## 关键风险判断：不是"会不会缺经验"，而是"经验在哪一层"

对被搬动的条目逐条核对过：`ue5-fps-arms-animation` 里那 14 条带日期的教训，在 `references/` 里
**0 命中**——它们只存在于入口，是独一无二的积累。**因此本轮全部是"搬"而不是"删"**；
若按"入口瘦身=删案例"处理，会真的毁掉经验。

反过来，`asset-model-workflow` 的两个大章节在 `Docs/` 里**早有更完整的正本**
（喷泉 47.2 KB、高炉 7.9 KB + 12.2 KB），而入口副本**没有链回正本**。
所以重组的目标从"变小"改成了**"路由器化"**：判据是**复用面**，不是长度。

- 对**一类**未来任务有效 → `references/`（按需加载）
- 只对**那一次**有效 → `Docs/`（唯一正本）
- **每次都必须知道** → 留在入口

## 四项改动

### 1. 删除死数据

`skills/ue5-module-router/references/ue5-module-routing-table-draft.deprecated.csv`
（111,740 B）——无引用、被 `-final` 取代。**这是本轮唯一删除的文件。**

### 2. 政策收敛到单一真值源

15 个入口里逐字复制的 860 字符政策块（含 2 处重复的 2026-09-12 重述）替换为
一句**操作性摘要 + 指针**（指向仓库根 `AGENTS.md` 与
[后台开发与编辑器使用条件](../../skills/ue5-auto-assistant/references/editor-open-development.md)）。
刻意保留operative 规则在入口可见，不是裸链接。

### 3. 可达性修复

- `AGENTS.md` 补上 4 个未被点名技能的分流条目（C++ 玩法 / 世界交互 / PCG 建造 / 性能打包），
  这 4 个技能的 references 里确有项目专属经验（`fpsgame-voxel-placement`、
  `authored-dungeon-generation`、`ground-surface-material` 等），此前不可达即能力丢失。
- `AGENTS.md` 同时把 `ue5-module-router` **降级为模块清单**，并标注 76% 行失效。
- `ue5-module-router/SKILL.md` 重写：删掉对 `ue5-architecture` 的跳转指示与失效的重生成脚本路径；
  写明 CSV 必须 grep 查、不要整篇读；更正工具口径（原文的 Tool Priority Matrix 描述的是
  **另一套 MCP 工具**，本项目走 `mcp_call_codex.ps1`）。
- `routing-policy.md` 顶部加同样的更正。

### 4. 按复用面拆分两个高命中入口

| 入口 | 前 | 后 | 减少 |
| --- | ---: | ---: | ---: |
| `asset-model-workflow/SKILL.md` | 43,906 B | 14,940 B | **−66%** |
| `ue5-fps-arms-animation/SKILL.md` | 28,046 B | 11,146 B | **−60.3%** |

新拆出的 references（内容逐字搬迁，非重写）：

| 新文件 | 来源 | 触发条件 |
| --- | --- | --- |
| `asset-model-workflow/references/blender-hardsurface-checklist.md` | 硬表面自检 + 必验硬边 + 白模扭曲 | 做 Blender 程序化硬表面 / `from_pydata` 堆实体 / 从零重建 |
| `asset-model-workflow/references/mesh-scaling.md` | 缩放已有网格 | 把现成模型改成工程尺寸、不重做几何 |
| `asset-model-workflow/references/python-material-authoring.md` | Python 造材质踩坑表 | 无头 Python 建改材质/材质实例，或"能编译但没接对" |
| `asset-model-workflow/references/in-editor-asset-authoring.md` | 在运行中的编辑器里做资产 | 必须进编辑器（活物理、视口相关） |
| `ue5-fps-arms-animation/references/measure-before-writing.md` | 14 条"先量后写"教训 | 复刻/迁移参考动作、动手前要测量 |

两个入口都补了**触发表**（`## 触发表` / 扩写既有的 `## 按问题读取`），
每份新 references 都带**正本回链**（喷泉→`Docs/Building/fountain-water-20260918.md`、
高炉→`Docs/Gameplay/blast-furnace-model-20260923.md`）。

## 验证

| 检查 | 结果 |
| --- | --- |
| 内容逐字保全 | 每个搬迁章节在新文件中逐字断言通过（5/5） |
| 只改目标区块 | 对快照逐行 diff：15 个入口**0 处意外改动** |
| 引用未丢失 | 15 个入口的 markdown 链接数全部不变 |
| **路由可解析** | 全树 289 条相对链接，**断链 0** |
| 我引入的断链 | 校验抓到 2 处（搬迁后 `references/xxx` 前缀失效）→ 已修，复查 0 |

> 说明：链接校验时对快照报了 3 处"断链"，是快照放在 `Saved/SkillReorg20260923/` 下
> 导致 `../../../Docs/` 多降两级的**假阳性**；现状树 0 断链。

## 净效果

| 项 | 前 | 后 |
| --- | ---: | ---: |
| `skills/` 总量 | 1,291,653 B / 148 文件 | 1,157,861 B / 152 文件 |
| 净减少 | — | **−133,792 B ≈ −41.8k token** |
| 单次加载 `asset-model-workflow` | ≈13.7k token | ≈4.7k token（−9.0k） |
| 单次加载 `ue5-fps-arms-animation` | ≈8.8k token | ≈3.5k token（−5.3k） |
| 可达技能数 | 10/15 | **15/15** |
| 政策真值源 | 20 处副本 | 1 处（AGENTS.md）+ 摘要指针 |

## 未做

- **未做冷启动可达性抽查**：本轮只证明指针可解析（机械代理），没有证明"从冷启动读入口能否命中
  正确文件"。建议的抽查题（按你的默认不主动测试规则，只列不跑）：
  1. "Python 造材质实例时哪些属性写不进去" → 应命中 `python-material-authoring.md`
  2. "`from_pydata` 堆封闭实体要断言什么" → 应命中 `blender-hardsurface-checklist.md`
  3. "喷泉边缘溢流 V7 的参数在哪" → 应命中 `Docs/Building/fountain-water-20260918.md`（经回链）
  4. "把这把枪的模型改成 40 cm" → 应命中 `mesh-scaling.md`
  5. "复刻参考动作前要先量什么" → 应命中 `measure-before-writing.md`
- **未处理** `ue5-auto-assistant/references/` 下 3 个引用不存在技能的文件
  （`mcp-skill-mapping.md`、`natural-language-triggers.md`、`beginner-smoke-prompts.md`，共约 5.8 KB）。
- **未重生成** 755 行路由表（需按当前 15 个技能重做映射，属独立工作）。
- 未提交 git；工作区原有未提交改动保持原样。

## 回滚

改动前快照：`Saved/SkillReorg20260923/skills-before/`（148 文件，1,291,653 B，与改动前逐字节一致）。
本轮四个脚本与回执在该目录的兄弟路径 `SourceAssets/SkillReorg20260923/`。

## 脚本与回执

| 文件 | 用途 |
| --- | --- |
| `SourceAssets/SkillReorg20260923/consolidate_policy.py` | 删死数据 + 政策收敛 |
| `SourceAssets/SkillReorg20260923/split_asset_model_skill.py` | 按复用面拆分第一个入口 |
| `SourceAssets/SkillReorg20260923/split_fps_arms_skill.py` | 拆分第二个入口 |
| `SourceAssets/SkillReorg20260923/verify_links.py` | 链接解析校验（快照 vs 现状） |
| `SourceAssets/SkillReorg20260923/*.json` | 四步各自的回执 |
