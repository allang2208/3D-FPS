# Sprint46 — PKM 手掌混合带权重收窄（方案 B1）

## 做了什么

只改 **PKM 自己的** 权重源文件：

```
SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/PKM.json
```

**没有碰**共同表面母版 `M4_original.json`，也没有碰任何其他 profile（`AKM/ASH12/M4/M16/S1911/QBZ191/...`），
符合 [认可的裸手基准](../../../../skills/ue5-fps-arms-animation/references/accepted-bare-hands.md)
第 24 条"不为适配某处改动全局裸手母版"。

## 规则

对每个"以手为主"的顶点（手骨 + 掌骨 + 指骨权重合计 > 0.5）：
把它的三根小臂骨权重（`lowerarm_*` / `lowerarm_twist_01_*` / `lowerarm_twist_02_*`）
**乘以 K = 0.25**，移出的部分给 `hand_<side>`。

选 **线性缩放** 而不是硬性重指派：权重场对小臂权重是连续的，
相邻顶点得到相近处理，**结构上不会产生新的折痕**。

## 为什么是 K=0.25

离线扫描（顶点集合固定取自**原始**权重，逐帧量手掌混合矩阵的非刚性 `‖BᵀB−I‖` p99）：

| K | idle 左掌 | sprint 左掌 | 左掌最大位移 |
|---|---|---|---|
| 1.0（改动前） | 0.4200 | **1.2706** | — |
| 0.75 | 0.3621 | 1.0915 | 5.8 mm |
| 0.5 | 0.2728 | 0.8204 | 11.6 mm |
| 0.35 | 0.2041 | 0.6135 | 15.1 mm |
| **0.25（采用）** | 0.1521 | **0.4569** | 17.4 mm |
| 0.0（完全刚性） | 0.1407 | 0.1407 | 23.2 mm |

**目标：把冲刺进入段的手掌非刚性降到"项目已经接受的 idle 水平"（0.4200）。**
K=0.25 给出 0.4569，最接近且不越过；同时 idle 本身也从 0.4200 改善到 0.1521。

代价是腕部混合带最大位移 17.4 mm（sprint）/ 10.1 mm（idle）。
但 **p50 = 0.00 mm** —— 绝大多数手掌顶点完全不动；改动只落在少数带小臂权重的顶点上
（手掌平均小臂权重只有 0.0427）。且位移是平滑的，不是折痕。

## 实际改动量

| 项目 | 值 |
|---|---|
| 顶点总数 | 18646 |
| 改动顶点数 | **908**（左 454 / 右 454） |
| 涉及的非手/非小臂骨权重 | **0**（刻意做到最小 diff） |
| 手掌小臂权重 均值 / 最大 | 0.0427 / 0.3775 → **0.0147 / 0.1132** |

源文件哈希：

| | SHA-256 |
|---|---|
| 改动前 | `a6d7b7e469087f97ec797a2655eee41d5df012f11926da974ccda39ed88f5315` |
| 改动后 | `831feb0d33012eb1e9f31afd91dce10d906015a91d09b8c78edf5779d30bc17f` |

备份：`Sprint46/Before/PKM.json`。回执：`Sprint46/weights_receipt.json`。

第一版实现无差别地对每个条目做归一化，把无关骨的末位改掉了（float32 噪声约 7e-08，
表现为 2580 处 diff）。已改为**只在总和偏离 1 时才归一化**，现在非手/小臂骨的改动为 0。

## 自检（用落盘后的文件重算）

以 `Authored/PKM.json` 现值作为输入重跑同一套测量（顶点集合因重新分类变为 1347 个）：

| clip | 改动前 | 改动后 |
|---|---|---|
| `sprint_enter` 左掌 | 1.2706 | **0.5370** |
| `idle` 左掌 | 0.4200 | **0.1787** |

（此处前后顶点集合不同，故与上表 K=0.25 的 0.4569 略有差异；上表用固定集合，是权威对照。）

## 全 clip 回归复核（权重是网格属性，影响所有 PKM clip）

用固定的原始顶点集合，对**每一条 PKM clip** 分别用改动前/后的权重跑同一套测量
（`check_all_clips.py`，逐帧取手掌非刚性 p99 的最大值）：

| clip | 改动前 p99 | 改动后 p99 | 最大位移 | 结论 |
|---|---|---|---|---|
| `idle` | 0.4200 | **0.1521** | 15.3 mm | 改善 |
| `equip` | 0.2301 | **0.1407** | 20.3 mm | 改善 |
| `reload` | 0.7638 | **0.2700** | 19.4 mm | 改善 |
| `reload_empty` | 0.7637 | **0.2700** | 19.4 mm | 改善 |
| `sprint_enter` | 1.2706 | **0.4569** | 25.8 mm | 改善 |
| `sprint_loop` | 0.3821 | **0.1387** | 15.0 mm | 改善 |
| `sprint_exit` | 1.2706 | **0.4569** | 25.8 mm | 改善 |

**7 条全部改善，无一条回退。**

附带发现：**`reload` / `reload_empty` 原本就有 0.7638**，比已认可的 idle（0.4200）还差近一倍 ——
也就是说换弹时的手掌扭曲问题本来就存在，本轮一并下降 65% 到 0.2700。
这与用户最初反馈里提到的"换弹状态"吻合。

## 接入完成（2026-09-25 22:15）

UE 关闭后，等指挥闸门出现空窗，通过 `run_bake_when_clear.ps1` 顺序执行两步
（都用 `Tools/ModularOutfit/Run-Authoring.ps1` 的无头 commandlet）：

```
STEP_BEGIN import_bare_palm_v7   → Python script executed successfully
STEP_BEGIN bake_native_bare_defaults_v7 → Python script executed successfully
SPRINT46_PIPELINE_DONE
```

两次都是 **0 error**（导入 9 个 warning、烘焙 9 个 warning，均为引擎既有警告，
如 D3D12 驱动、MikkTSpace 零长度法线）。

### 影响面实测：只有 PKM

烘焙日志里唯一的重建记录是：

```
LogPython: NATIVE_BARE_BEGIN PKM
LogPython: NATIVE_BARE_SKIP Bow no V7 authored mesh      ← 既有跳过，与本轮无关
```

其余 20 个 profile 走第 100 行的哈希一致分支被静默跳过。旁证：
其他武器的视模网格修改时间仍是 `09-25 16:43`，未被本轮触碰。

### 链路凭证

| 环节 | 凭据 |
|---|---|
| 授权源 | `Authored/PKM.json` = `831feb0d33012eb1e9f31afd91dce10d906015a91d09b8c78edf5779d30bc17f` |
| 导入回执 | `BarePalmV7/Saved/PKM.json` → `authored_sha256` = `831feb0d…` **一致** |
| 烘焙回执 | `BarePalmV7/NativeDefaults/PKM.json` → `authored_sha256` = `831feb0d…` **一致** |
| 裸臂资产 | `Content/Characters/ModularOutfit20260924/BarePalmV7/PKM/SK_PKM_BareArmsV7.uasset`（8512 KB, 22:14:56） |
| PKM 视模 | `Content/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular.uasset` 79152 → **79156 KB**，22:15:25，SHA-256 `0ecbde5c951700dc` |
| 烘焙回执字段 | `native_bare_arms: true`、`native_bare_skin` 指向 `BarePalmV7/PKM/SK_PKM_BareArmsV7`、`runtime_tested: false` |

原有手套版本保留完好：`NativeDefaults/Packages/PKM.uasset`（77569 KB，09-23 14:56:51）未被覆盖，
`original_gloved_source` 仍指向 `SK_PKM_GlovedSource`。

### 需要你留意的一点

`bake_native_bare_defaults_v7.py` 会**重写运行时配置** `Content/ColdSteelData/modular_outfits.json`
（对每个 profile 执行 `profile.update(receipt['profile_fields'])`，被跳过的 profile 也一样）。
该文件在本轮 22:15:26 被改写。

它相对 HEAD 的 diff 主要是**整套手套改指向**（`FittedFieldGlovesV1` → `HuntFieldGlovesV1`，全部 profile），
属于另一条手套工作流；本轮没有运行前的快照，因此**无法把这份 diff 逐行归因**。
同目录的 `NativeDefaults/modular_outfits.before.json` 是旧备份（只有 21 个 profile、
PKM 还指向 V6），**不能当作本轮运行前的快照**。

该文件受 git 跟踪，建议接入后复核一次 `git diff -- Content/ColdSteelData/modular_outfits.json`。
PKM 条目本身是正确的：已新增 `native_bare_arms: true`、`native_bare_skin` / `base` /
`bare_arms_candidate` 均指向 `BarePalmV7/PKM/SK_PKM_BareArmsV7`。

按用户规则，**本轮未做运行测试与视觉验收**（回执里 `runtime_tested: false`），请你实测确认。

## 尚未完成的接入（历史记录）

**游戏内 `SK_PKM_Manny_Modular` 目前仍是旧权重，没有任何 UE 资产被改写。**
当前状态是安全的、自洽的：源文件已更新，引擎侧未动。

接入需要两步，都必须**在没有 FPSGAME 编辑器运行时**通过
`Tools/ModularOutfit/Run-Authoring.ps1` 以无头 commandlet 执行：

```
# 1) 把 Authored/PKM.json 导入裸臂资产并刷新 Saved/PKM.json 的 authored_sha256
Tools/ModularOutfit/Run-Authoring.ps1 -Script Tools/ModularOutfit/import_bare_palm_v7.py -Log <log>

# 2) 烘焙进武器原生视模（内容寻址，只会重建 PKM）
Tools/ModularOutfit/Run-Authoring.ps1 -Script Tools/ModularOutfit/bake_native_bare_defaults_v7.py -Log <log>
```

**当前被阻塞**：有一个**其他对话的** FPSGAME commandlet 正在运行
（PID 45028，`-script=...RuneSword202609...`）。`Run-Authoring.ps1` 检测到 FPSGAME
编辑器/commandlet 在跑会直接抛错（它只做互斥、不排队等待）。
按项目规则不结束他人进程、不向其他对话发协调消息，因此等它自然结束后再跑。

**影响面已经确认很窄**：`bake_native_bare_defaults_v7.py` 是内容寻址的 ——
第 97-100 行会比较 receipt 里的 `authored_sha256`，一致就 `continue` 跳过。
只有 PKM 的 `Authored/PKM.json` 变了，所以**只会重建 PKM 一个原生包**，
其余 20 个 profile 原样跳过。

## 文件

- `design_palm_weights.py` — 离线扫描（K 扫描 + 位移/非刚性测量），改 `FACTORS` 可做自检
- `apply_palm_weights.py` — 写入 `Authored/PKM.json`（含备份与回执）
- `weights_receipt.json` — 改动回执
- `reweight_sweep.json` — 扫描原始数据
- `Before/PKM.json` — 改动前的源文件备份

## 顺带确认的事实

- 授权 JSON 的 `positions` 与工程内 V7 网格完全一致（前 18642 点 `max |d| = 0.0000 m`）。
- 该 JSON 是 **UE 空间**：厘米 + Y 翻转（`json = (x, −y, z) × 100`）。
  不换算会让蒙皮计算差 100 倍 —— 第一版扫描因此报出"位移 6973 mm"这种不可能的读数。
- PKM 的视图模型网格是 `SK_PKM_Manny_Modular`，代码以
  `/Game/Weapons/PKMLowpoly20260922/` 前缀做守卫，碰不到其他武器。

按用户规则本轮**未做测试与验收**。