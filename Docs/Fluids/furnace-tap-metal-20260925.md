# 高炉出铁口熔融金属流与凝固锭（2026-09-25 设计，SKILL 任务记录）

> 任务：完成冶炼后，从高炉下方出铁口流出金色熔融金属，一小段时间后凝固为对应金属锭。
> 设计依据 skills/ue5-fluid-vfx-workflow/SKILL.md（任务记录/路线选择/分层/预算/交付）；
> 派发目标按 [WORKFLOW.md §11](../../WORKFLOW.md)：`qwen-token-plan-individual / deepseek-v4.1-flash`。
> 姊妹案：黑烟 v1–v5（furnace-black-smoke-20260924.md）、v5 优化计划（furnace-smoke-optimization-plan-20260925.md）。

## 0. 任务记录（SKILL 必备字段）

- **事件与接触面**：冶炼**完成上升沿**（`LiveProgress≥JobTotalSeconds` 且任务仍在炉、未取出）触发一次。
  射流起点＝manifest 实测 `TapHole (17.5,0,63.5)`（SM_BlastFurnace 网格局部，朝局部 +X，README 原文"出铁口，铁水／火花流挂点"）。
  落点＝解析固定偏移（局部约 `(58,0,炉基面)`)，**无碰撞检测**（炉前地面即炉基面，体素构件落位保证）。
- **观察距离**：与黑烟同口径——≤85 m 可见，主观察 2–30 m；细流/火花仅 <35 m 且画质≥中。
- **主体与装饰分层**：
  - **L0 金流（主体）**：Niagara 粒子细流，局部 +X 抛物线下落，金色自发光（白热芯→金→橙边），
    存续 ≈2.2 s，存活 ≤30 粒；运动全解析（初速+重力+微噪声），不烘培。
  - **L1 熔池（主体）**：落点贴地卡，扩张→冷却变暗（亮金→暗红→熄）2.5 s，凝固后收缩消失；1 张卡。
  - **L2 凝固锭（交付主体）**：t≈1.6 s 出现 `SM_Ingot`＋按配方 `MI_{iron,copper,silver,gold}Ingot`
    （四配方对应四金属色），叠一层余晖 glow 卡 3 s 衰减模拟退温（**不改 MI**，母版无 emissive 参数保证）。
    **展示持续到任务被取出**（IsDone 状态存续；取出/拆炉/超 85 m 即隐）——与 UI「冶炼高炉 · 取出矿锭」呼应，是可否决的设计决策。
  - **L3 飞溅火花（装饰）**：落点稀疏火星 ≤12 粒，一次性，仅 <35 m 高画质；受共享 `WindAt` 微量偏转。
- **风向与坐标空间**：流/池/锭全部在炉体局部空间（随构件 Yaw 转，SpawnSystemAttached 到 Body）；仅 L3 火花接风。
- **生命周期与池**：事件型非持续。并发上限 **≤4 座炉同时出铁**；TapFX 与锭组件走有界池复用（ColdPool 同款，异步加载，无同步 Load）。
- **保护玩法**：完成判定＝表示侧只读谓词（子系统 5Hz 循环内比较），**不写** SettleFurnace/Collect/存档/背包/掉落；零玩法合同改动。
- **修改源与资产**：
  - 新 NS：`/Game/Fluids/FurnaceTapMetal20260925/NS_FurnaceMoltenTap`（L0+L1+L3+L2 glow 四发射器同 NS）。
    原定名 `NS_FurnaceTapMetal` **弃用**：资产名恰为发射器名 `FurnaceTapMetalFlow` 的前缀时，Niagara 编译可复现失败
    （幻影 SystemUpdateScript Custom Hlsl 报 `User.DetailReduction 尚未遭遇`，valid=0；逐字节相同内容改名即过；
    无文件/注册表/DDC 残留，内容扰动亦无效）。复现探针 `Tools/Fluids/probe_tap_name_cache.py`。
  - 新作者脚本：`Tools/Fluids/author_furnace_tap_metal.py`（幂等；稳定 tag `FurnaceTapMetal20260925.*`；重跑前无条件退役上一轮 tag；
    禁 `Engine.Environment.DeltaTime`、无 `smoothstep` 内建（手写 smooth）；保存回执 `FURNACE_TAP_SAVED`）。
  - 材质：程序化金色流材质（unlit emissive＋滚动噪声，噪声复用既有 Mantaflow R 通道图集或纯程序，**不新增位图**）。
  - C++ 仅 `FluidPresentationSubsystem.{h,cpp}`（触发＋池＋锭展示；`FFurnaceSmoke` 增 bWasDone/TapAt/TapFX/Ingot 字段）。
  - 复用：`SM_Ingot`、`MI_*Ingot`（Items/Smelting/Ingot）。

## 1. 路线选择（SKILL §2）

层流细口出铁是**确定性解析运动**：初速+重力+微噪声即可读作熔融金属，无湍流相互作用需求
→ **Niagara 解析粒子＋程序化材质**，不做 Mantaflow 烘培、不上 Niagara Fluids/GeomCache/SVT。
P2 备选（用户嫌流不够"稠"再启动）：离线烘一小段 Mantaflow 高粘度流 flipbook 换 L0 主体。

## 2. 运行时预算（SKILL §5）

- 峰值（4 炉同时出铁的极端并发）：≤120 粒 + 4 张池卡 + ≤48 火星 + ≤4 锭静态网格（无 tick、无物理）。
- 常态单炉一次事件：≤30 粒、2–3 张卡、<1.5 s GPU 占用窗口；锭展示期近零成本（静态网格＋距离门隐藏）。
- 透明过画：流+池卡均小屏占（<2% 屏），远低于烟雾案 8% 上限；无新纹理常驻（程序化材质或复用图集）。
- 加载：NS/SM/MI 全部 `RequestAsyncLoad` 批量预载（首触发前就绪），无同步 Load、无新灯、无投影、无碰撞、无导航影响。
- 调度：全部逻辑并进既有 `UpdateFurnaceSmoke` 5Hz 单入口（无新 tick、无新遍历）；上升沿判定 O(1)/炉/拍。

## 3. 恒等与零回归锚点

- 未触发时（bDone=false）：不产生任何组件写入——与 v5 黑烟行为逐位一致；黑烟 v5 的 Heat/Ignition/Puff/L1Gate 不受影响。
- 资产缺失（NS 加载失败）：软引用判空跳过，仅无出铁表现，无日志刷屏、无崩溃。
- 回滚：`TapTemplate` 软引用置空（或触发常量置 0）即热退档；资产回滚＝删除 FurnaceTapMetal20260925 目录；C++ 回滚＝还原两文件。

## 4. 交付与验收（用户规则）

- 后台制作：作者脚本＋headless commandlet（编辑器空窗），构建走 `Tools/Build/Build-Editor.ps1`；占用则如实记阻塞，不强杀、不跨对话协调。
- **不自动测试/截图/PIE/性能采样**。待用户实机确认：完成瞬间出铁、流色（金→橙）、凝固时序、四种锭颜色对应、
  取出即消失、85 m/35 m 分级无突变、与 v5 黑烟同屏不打架。

## 5. 编码任务包（交子代理执行）

- **T1 作者脚本**：按 §0 建 NS_FurnaceMoltenTap（L0/L1/L3＋L2 glow 卡）；程序化金流材质；幂等＋tag 退役＋回执。
- **T2 C++**：`FluidPresentationSubsystem.{h,cpp}`——`FFurnaceSmoke` 增 `bWasDone/TapAt/TapFX/Ingot/IngotDef`；
  5Hz 循环内上升沿触发（复用既有 Job/Smelt/JobTotalSeconds 口径与 Body 变换）；锭池（≤4，异步加载 SM_Ingot＋MI_*，
  展示到取出）；85 m/35 m×画质门；资产判空跳过。
- **T3 构建**：空窗判定→Build-Editor.ps1；占用如实记。
- **T4 资产执行**：空窗 headless 重作 NS（须见 `FURNACE_TAP_SAVED`）。
- **T5 文档**：本案 §5.1 回填执行状态；furnace-black-smoke 案例文档加一行交叉引用。
- **完成定义**：T1–T4 绿（或阻塞有因）＋零玩法合同改动＋锚点在表达式/代码注释内。

### 5.1 执行状态回填（2026-09-26 01:32，本会话收口）

- **T1 作者脚本** ✅ `Tools/Fluids/author_furnace_tap_metal.py`（586 行，四发射器单 NS）。子代理初版后由主会话修复 8 处
  Niagara 作者层 bug：verify_source 自扫描命中禁词字面量（改字符串拼接）、`smooth()` 字符串+浮点混拼、Spawn Count 缺
  Int32 类型参、不存在的 Spawn Probability 输入、f-string 内字面 `smooth()` 未求值（3 处）、VectorVM 无两参 `atan`
  （改 `atan2`）、VEC4 三分量 float4、declare() 漏 `DetailReduction`。
- **T2 C++** ✅ `FluidPresentationSubsystem.{h,cpp}`（子代理执笔＋主会话两处修补：`GetWorld()->GetGameInstance()` 链修
  C3861；TapFX 补 `AllocateDetail`＋`User.DetailReduction` 写入对齐 ConfigureSmoke 口径）。上升沿触发、TapPool ≤4、
  IngotPool 3 固定桶、85 m/35 m×画质门、异步批量预载（NS＋SM_Ingot＋四 MI）全部落位。
- **T3 构建** ✅ 合并点三连绿：build-20260926-004735（首次合并）、-010217（DetailReduction 修补）、-013115（改名
  TapTemplate，Result: Succeeded，0 error，DLL 01:31:27）。日志在 `Saved/BuildEditor/`。
- **T4 资产** ✅ 01:32:19 回执 `FURNACE_TAP_SAVED` ×2：`M_TapMetalFlow`（13,497 B，程序化无新位图）＋
  `NS_FurnaceMoltenTap`（2,765,170 B，compile valid=1）；`FURNACE_TAP_COMPLETE`；`SourceAssets/FurnaceTapMetal20260925/assets.json`
  含锚点/预算/参数契约。**改名缘由**：`NS_FurnaceTapMetal`（发射器 `FurnaceTapMetalFlow` 的前缀）名下同一代码可复现
  valid=0，幻影 SystemUpdateScript Custom Hlsl 报 `User.DetailReduction 尚未遭遇`；无文件/注册表/内存幽灵（探针证实），
  内容扰动无效，`NS_FurnaceTapMetal2`/`NS_ProbeTap*` 名下逐字节相同内容全部 valid=1 → 结论：**资产名不得为任何发射器名
  的前缀**（机理未明，绕行为准）。探针七件归档 `SourceAssets/FurnaceTapMetal20260925/Probes/`，复现件
  `Tools/Fluids/probe_tap_name_cache.py`。
- **T5 文档** ✅ 本节；黑烟案例文档交叉引用见 furnace-black-smoke-20260924.md v5 状态行。
- **验收状态**：authored_compiled_saved；**未做实机/PIE/截图/性能验证**（用户规则，待用户自测：出铁时序、金→橙流色、
  四锭对应、取出即隐、85/35 m 分级、与 v5 黑烟同屏）。

### 5.2 用户实测「无任何特效」排查修复（2026-09-26 上午）

用户实机测试报告几乎看不到任何新特效。排查（用户测试会话日志 `Saved/Logs/FPSGAME-backup-2026.09.26-01.36.04.log`）
定位出 1 个资产致命伤 + 4 个 C++ 缺陷，全部修复：

1. **材质运行时平台编译失败（不可见的直接根因）**：`M_TapMetalFlow` 用 `ParticleSubUV` 节点取每粒子变化但无 SubUV
   纹理 → NullRHI commandlet 编译通过、真机 SM6 编译失败「(Node ParticleSubUV) Missing ParticleSubUV input texture」→
   游戏内 Default Material，四个发射器共用此材质＝全部不可见。修复：改用 `DynamicParameter`＋ComponentMask(R)
   （NS 四发射器本就写 `Particles.DynamicMaterialParameter=float4(seed,var,u2,layer)`，与材质 docstring 契约一致）。
   **教训：NullRHI 下材质"编译通过"不代表真机平台能过；程序化材质不得引用需要纹理绑定的采样节点。**
2. **锭永不显示**：`bShownBefore=Ingot.IsValid()||IngotDef.IsEmpty()` 把 IsEmpty 写反——全新 Entry 恒判"已展示"。改 `!IsEmpty()`。
3. **双重坐标偏移**：NS 粒子坐标本就是 SM_BlastFurnace 网格局部系（assets.json anchor_cm），C++ 又把组件挂到
   Body 相对 (17.5,0,63.5) → 全线错位悬空。改恒等变换挂 Body。
4. **锭落在世界原点**：锭池组件父级是 WorldSettings 根，展示时未重挂炉体 → SetRelativeLocation(58,0,·) 成了世界坐标。
   改 AttachToComponent(Body)＋落点对齐锭模弧 X=45（与 L2 余晖卡同轴）。
5. **金流永不关窗＋池枯竭**：Flow 只在任务取出时归零（设计=「一小段时间后凝固」）；且池组件从不 Deactivate，
   4 次出铁后 TapPool 全部 IsActive 被跳过。改每拍写 3.6s Flow 窗口／4.0s IngotGlow 窗口，Elapsed>7s 或取出即
   Deactivate 归还池位；上升沿不再被 bNear 锁死（远处完成也记 TapAt，走近锭照常展示），资产未载不再 early-return
   跳过整段锭逻辑。

复核链：build-20260926-094941.log Result: Succeeded；author 重跑 09:50:39 回执 `FURNACE_TAP_SAVED` ×2
（材质重建＋NS valid=1 重存）。仍**未做实机验证**——修复依据是日志实锤与静态代码审查，待用户复测：
完成瞬间出铁口金流 → 3.6s 断流凝固 → 1.6s 起锭模处出锭（带余晖）→ 取出即隐。

**二轮复测（12:2x）**：粒子已出现（C++ 修复生效）但呈白色马赛克＝仍是默认材质。新日志实锤：
`M_TapMetalFlow missing usage flag NiagaraSprites! Default Material will be used in game.`——
`MaterialFactoryNew` 空白材质不带任何 usage flag，真机不为 Niagara sprite 编译变体（SubUV 报错已消失，
第一轮材质修复有效）。修复：material() 增 `used_with_niagara_sprites=True` 后重存（编辑器空窗哨兵执行，
回执见 `Saved/furnace_tap_author.log`）。黑烟材质无此问题＝它复制自 Fireball MI，母材自带标记。

**三轮复测（12:45–12:50 会话）＝不成功，用户裁定挂起（"先这样吧"）**。该次日志证据：本任务两资产
**零告警**（SubUV 报错与 usage flag 告警均已消失，无 LogNiagara 错误；同日志中的材质告警全部属他案：
炉体 M_BlastFurnace_* 缺 Nanite flag、MF_GrassDeform SM6 失败）。即编译层问题已清，剩余为观感/时序/
可见性层问题，用户未详述现象，未再排查。**挂起状态**：代码与资产保留在树内原样生效（完成冶炼仍会触发）；
热退档路径见 §3（TapTemplate 置空）。后续接手：先请用户描述现象或提供截图，再按
「透明与可见性问题」参考篇排查（坐标/尺寸/alpha 门/User 参数写入时序），勿再盲改材质编译层。
