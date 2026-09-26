# 材质中间量探针：Emissive 门控法（2026-09-26，Clearwater 水面案）

材质**编译通过但画面不对**时（"平滑渐变/全黑/无结构"），改参数再截图是每轮 60 秒的盲猜。
正确工具：**一个探针只回答一个问题**——把某个中间量接到 Emissive，无头实拍一帧。
案例正本（含 21 个探针的完整判决矩阵）：`Docs/Fluids/clearwater-water-migration-20260926.md` §7。
框架可直接复用：`Tools/Fluids/clearwater_probe_surface.py` + `run_clearwater_probes.ps1`。

## 1. 门控编码：自动曝光下唯一可信的写法

**常量颜色不可判读**——自动曝光会把任何均匀色归一成中灰，0 和 1 分不清。
必须把"量的存活"编码成**空间图案 × 门控**：

```hlsl
float px = frac(P.x * 0.001);              // 世界坐标条带（对照组）
float alive = step(0.5, abs(SomePin.z));   // 引脚非零 → 1
return float3(px, px * alive, px);         // R=对照组 B=P自身 G=待测量
```

- R 有条带 → P 活着；G 有条带 → 待测引脚非零；G 黑 → 引脚读零。
- 门控值取 0/1 阈值可分级（如 0.5="任何非零"、1.5="只有覆写值能过"），一次区分**默认值/覆写值/零**三态。
- 用 step() 乘进图案而不是当独立通道返回——纯常量通道被曝光归一后毫无信息。

## 2. 注入通道：re-parent MI（对付运行时生成的 Actor）

水面等 Actor 由 C++ 按硬路径 `LoadObject` 材质实例（如 `/Game/Clearwater/MI_ClearwaterWater`），
改组件改不了。注入流程：

1. **duplicate 生产 master** → 在副本上给目标 Custom 节点做字符串替换（用节点体最后的
   `return ...;` 精确串当锚点，替换前 assert 命中且唯一）。
2. 需要看"非输出节点"（如法线节点）时，把 `MP_EMISSIVE` 重连到该节点。
3. `MEL.set_material_instance_parent(生产MI, 探针master)` + 保存——**MI 的参数覆写按名保留**，
   C++ 的 MID 链照常继承。
4. 跑完 `restore`：父项设回真 master，**读回父项路径断言**，再保存。

三个必须知道的 MI 事实（全部实测）：

- **`save_loaded_asset` 对"包不脏"返回 False**——不是失败。判断标准用读回，不用返回值；
  需要强制落盘时先 `mi.modify()`。
- **re-parent 前写在 MI 上的覆写，换父后运行时不生效**（按表达式 GUID 匹配，新 master 的表达式是新
  GUID）→ 回退到新 master 的**默认值**。做"默认值 vs 覆写值"实验时要意识到测到的是默认值。
- **restore 只还原父项，不清除实验注入的覆写**——探针若写过参数值，收尾必须显式写回正确值再保存
  （本案 Wave01 曾被污染，靠 `get_material_instance_vector_parameter_value` 读出生效值才发现）。

## 3. 环境坑（Git Bash + 本机编辑器，全部踩过）

| 坑 | 症状 | 解 |
|---|---|---|
| `tasklist //FI "IMAGENAME eq X"` | **假阴性**——进程明明在却报没有，导致误判"编辑器已关" | 用裸 `tasklist \| grep -i UnrealEditor`，双探针确认 |
| Git Bash 传 `/Game/...` 地图参数 | 被 MSYS 改写成 `E:/Git/Game/...`，引擎加载错地图且不报错 | 走 PowerShell 驱动，或 `MSYS_NO_PATHCONV=1` |
| 编辑器开着时写资产 | `Error saving xxx.uasset`，根因 `MoveFile Error 32`（瞬时占用） | 保存加 6×4s 重试；批量重建仍应等编辑器关闭 |
| heredoc 里的 `\\n`/`\\\"` | 反斜杠被吃，写出的 .py 语法错误 | 避免：用 chr(10)/chr(34) 或 Write 工具写文件 |

## 4. DDC 与着色器级取证

- **DDC 按内容哈希**：同内容重建的材质直接命中缓存不编译。要强制真编译（如为 dump），给节点体加
  唯一时间戳注释。
- `r.DumpShaderDebugInfo 1` 经 `-ExecCmds` 传入时**在地图加载之后才生效**——水材质的编译任务已提交完。
  要拿到着色器转储，把 cvar 写进 `DefaultEngine.ini [ConsoleVariables]`（跑完务必删除），且该次运行
  必须是内容变更后的第一个编译者。
- `MEL.recompile_material` 在 NullRHI commandlet 里**不做 GPU 着色器编译**（工程既有结论），别用它
  当"已编译"的证据；真编译看 -game 运行。

## 5. 排查纪律

- **资产侧先穷尽再怀疑引擎**：默认值、覆写值、`get_material_instance_*_parameter_value` 生效值、
  Custom 节点引脚连线（`get_inputs_for_material_expression`——注意直接读 `inputs[i].input` 永远像断连，
  是错的读法）全部回读过了，才允许说"引擎侧"。
- **逐特征二分**：把可疑结构（参数数量/共享表达式/WPO 双频/纹理链/include/nanite 标志）在**最小底盘**
  上逐个复刻。本案 8 项全部单独健康——说明病灶在"已保存资产的组合状态"，这时下一步是**从零重建
  同构资产**对比，而不是继续拆特征。
- 每个探针的判决（活/死）当场量化记录（行内 std / 条带强度），不要凭肉眼记忆比较。
