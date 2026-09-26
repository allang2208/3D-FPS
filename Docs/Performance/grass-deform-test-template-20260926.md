# 草地交互 GPU（GrassDeform）用户验收记录模板（2026-09-26）

> 状态：**模板，未测试**。制作方不主动运行 PIE／不截图／不做验收；本文写给用户自测填写。
> 计划与阈值出处：[草地交互 GPU 升级计划](../WorldGeneration/grass-interaction-gpu-20260925.md)
> （性能预算见其 §7，验收清单见 §9，契约 v2 见 §10.5）。填完后本文可作为发布前的验收凭据。
>
> 用法：复制本文件为 `grass-deform-test-<你的日期>.md`，逐节填写。留空的单元格＝未测，
> 不要用推测值填充。不确定的地方写「未验证」比写数字更有价值。

填写人：________　日期：________　构建：编辑器 / 打包（圈选）　提交 SHA：________

---

## 0. 结论摘要（先填末尾，回填这里）

| 项 | 结果 | 备注 |
|---|---|---|
| CPU 增量（§2） | 通过 / 超预算 / 未测 | |
| GPU 增量（§2） | 通过 / 超预算 / 未测 | |
| 视觉验收（§4–§7） | 通过 / 有伪影 / 未测 | |
| Nanite 对照（§8） | 无差异 / 有差异 / 未测 | |
| WP 跨 cell（§9） | 连续 / 有缝 / 未测 | |
| 低画质自动关（§10） | 通过 / 未通过 / 未测 | |
| 已知边界是否可接受（§11） | 可接受 / 需返工 | |

遗留问题清单：

1.
2.

---

## 1. 硬件与设置（§7 预算只在这些设置下成立）

| 项 | 填写 |
|---|---|
| CPU | |
| GPU | |
| 显存 | |
| 分辨率 / 窗口模式 | 1920×1080 / |
| 画质档 | Epic（`sg.*` 全 3） |
| 是否开光追 / Lumen | |
| `r.Nanite` | 1 |
| `r.Nanite.Foliage` | 1 |
| 场景与位置（哪个区域、是否村落） | |
| 天气 / 时间 | |

在游戏内先执行：`GrassDeform.Status`，把整行输出粘到这里：

```
（粘贴 GrassDeform.Status 输出）
```

期望形如：`enabled=1 assets=1 rt=1024 center=(x,y) flattenAlive=0 dirty=0 cvar=1 foliageQuality=3 (0 forces off) user=1`。
若 `assets=0`：M1 资产未创建，先跑 `Tools/GrassDeform/run_asset_setup_m1.ps1`，
或资产在但 `MA_Grass` 未接线（见计划文末「M1 手工接线」）。**`assets=0` 时本表其余测试无意义。**

---

## 2. 性能：`r.GrassDeform` 0 / 1 对照（计划 §7 阈值）

方法（每档都做）：

1. 站在同一位置、朝向同一方向（用同一个存档／同一个出生点），画面里要有大片草。
2. 控制台 `r.GrassDeform 0`，静置 10 s 让 `stat unit` 平滑，记录 3 次读数；
3. `r.GrassDeform 1`，在同一位置走动或原地踩踏产生持续变形，静置 10 s，记录 3 次读数；
4. 两轮之间除该 cvar 外不要改任何设置。

| 指标（`stat unit`） | `r.GrassDeform 0` | `r.GrassDeform 1` | Δ | 阈值 | 判定 |
|---|---|---|---|---|---|
| Frame (ms) | | | | — | 参考 |
| Game (ms) | | | | **≤ 0.1 ms** | |
| Draw (ms) | | | | 参考 | |
| GPU (ms) | | | | **≤ 0.3 ms @1080p Epic** | |

`stat unit` 三次读数（0 / 1 各三行，原始值不要只写平均）：

```
r.GrassDeform 0：Frame=      Game=      Draw=      GPU=
r.GrassDeform 0：Frame=      Game=      Draw=      GPU=
r.GrassDeform 0：Frame=      Game=      Draw=      GPU=
r.GrassDeform 1：Frame=      Game=      Draw=      GPU=
r.GrassDeform 1：Frame=      Game=      Draw=      GPU=
r.GrassDeform 1：Frame=      Game=      Draw=      GPU=
```

注意事项：

- GPU 一行在 RHI 未报告时显示「由 RHI 未报告」，此时改用 `stat gpu` 或下面 §3 的 `ProfileGPU`。
- 场景本身 GPU 已跑满（GPU 时间接近帧时间）时，Δ 会被掩盖；换一个 GPU 有余量的场景再测一次并注明。
- 阈值是按「一整片草的 WPO 采样增量」定的；若这里超预算，先看 §3 是否 WPO 本身很贵。

对照参考（同类系统可达水平，非本工程实测）：`D:\FPS3D\_dgs_demo\perf_*.png` 记录交互 CPU Δ<0.1 ms。

---

## 3. `ProfileGPU` 检查点（计划 §7）

命令行输入 `ProfileGPU`，在输出里找下面几项。**需要截图或粘贴文本**，不要只写"正常"。

| 检查点 | 期望 | 实测 | 判定 |
|---|---|---|---|
| `MA_Grass` 的 WPO 增量 | 相对 `r.GrassDeform 0` 有可见增量，但不是数量级增长（1 次 RT 采样 + ~10 ALU/顶点） | | |
| `M_GrassDeformStamp` | 只在 stamp 事件当帧出现，事件量级 = 一次爆炸（1 次 DrawMaterial） | | |
| `M_GrassDeformFade` | ≤ 8 Hz（默认 6 Hz）且只在 dirty 时出现；静止不动 + 草已回弹后应完全消失 | | |
| `M_GrassDeformRecenter` | 只在跨 4 m snap 格时出现，且是 2 次 draw（双面搬移） | | |
| decal 相关 pass（M3 脚步 decal） | 存在但受池上限约束 | | |

粘贴 `ProfileGPU` 里与上面相关的行：

```
（粘贴）
```

若看不到三个 pass 的名字：确认 `r.GrassDeform 1`，并在有事件时（走路 / 放个爆炸）再抓一次。
静置无事件时三个 pass 都**不应**出现——出现了说明 dirty 判定失效，按缺陷记录。

---

## 4. `GrassDeform.DumpRT` / `GrassDeform.Status` 操作流程

1. 进游戏，`GrassDeform.Status` 确认 `enabled=1 assets=1`（记下 `rt=` 的边长）。
2. 在草地上走一段路（踩踏源，10 Hz）。
3. 执行 `GrassDeform.DumpRT`：把 RT 导出到 `Saved/GrassDeform/GrassDeformRT_<时间戳>.png`。
4. 打开该 PNG 肉眼检查：
   - 应看到玩家附近的亮斑（R 通道＝压平强度），形状是走过的轨迹；
   - 不应是**整张全亮**（全局色变）或**完全纯黑**（没写进去）。
5. 站住不动，等 `RegrowthSeconds`（默认 18 s）之后**再 dump 一次**：亮斑应明显衰减消失。
6. 每次 dump 同时记一行 `GrassDeform.Status`：

| # | 操作 | Status 输出 | PNG 观察 | 判定 |
|---|---|---|---|---|
| 1 | 走动后 | | | |
| 2 | 等待回弹后 | | | |

补充命令：

- `GrassDeform.Stamp X Y Z Radius [Strength]`：手工在指定世界坐标打一个踩踏点；
- `GrassDeform.Impulse X Y Z Radius [Strength] [WaveSpeed]`：手工打一个带波前的冲击。

用这两个命令做 §7（爆炸）的定点复现最省事：站在目标点附近，`GrassDeform.Impulse <火球坐标> 600 1 1800`。

---

## 5. M1 踩踏走路检查

1. `r.GrassDeform 1`，`GrassDeform.Status` 记一次。
2. 在草地上**走**（不是跑）一段直线，再**跑**一段。
3. 期望：身后留下倒伏痕迹；痕迹跟随玩家；跑比走的压平更强（强度随速度 0.3..0.7）。
4. 停下：按默认 `RegrowthSeconds=18 s` 回弹到直立。
5. 转身绕圈走：痕迹应跟着窗口移动，**不应**在地图某处留下固定的压平环（那是 RT 边缘 clamp 的典型症状）。
6. 关 `r.GrassDeform 0`，重复走路：应**完全无**倒伏。

| 检查 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 走路留痕 | 有 | | |
| 跑动更强 | 是 | | |
| 停止后回弹（~18 s） | 是 | | |
| 长时间走动后无固定残留环 | 无 | | |
| `r.GrassDeform 0` 后无任何变化 | 无 | | |

---

## 6. M2 四处爆炸点检查（火球 / 陨石 / 巫妖瓶 / 弹坑）

**重要限制（M2 实测发现）**：RT 窗口是玩家周围 **48 m**（±24 m）。**距离玩家超过约 24 m 的爆炸
不会在草地上留下可见压平**——不是 bug，是当前契约的已知边界（见计划 §10.5）。所以本节每一处
都**必须先站到爆炸点 20 m 以内**再触发，否则测的是窗口边界而不是功能。

同时注意（计划 §10.5 通道语义边界）：同一时刻只能有一个波前环，快速连打两次爆炸时第二发会
覆盖第一发的环——这是已知且 M4 决定接受的，记录时注明即可。

逐点流程（每点重复）：站到 20 m 内 → 触发 → 看草 → 等回弹 → 看回弹。

| 爆炸点 | 触发方式 | 站距 (m) | 环扫压平可见 | 与效果范围同心 | 回弹正常 | 备注 |
|---|---|---|---|---|---|---|
| 火球 | 左手火球命中地面 | | | | | |
| 陨石 | 陨石技能 | | | | | |
| 巫妖瓶 | 巫妖投掷瓶落点 | | | | | |
| 弹坑 | 铲子/爆炸制造弹坑 | | | | | |

「同心」判定要点：草的压平区应与火球伤害圈／陨石冲击圈／毒池足迹／弹坑碗口**大致同心**，
不应明显偏移到一侧或大出一圈。发现偏移时记录：爆炸点世界坐标、玩家坐标、偏移方向与大致距离。

补充对照：

- 每处都要在 `r.GrassDeform 0` 下复测一次：草应**完全无**变化（确认不是别的系统在做这件事）。
- 关 cvar 后仍有压平 → 说明该处爆炸调用未走 GrassDeform，按缺陷记录。

窗口边界实测（可选，用来确认 §11 的已知边界）：

| 爆炸距玩家 | 草反应 | 说明 |
|---|---|---|
| ~10 m | | 应正常 |
| ~20 m | | 应正常 |
| ~30 m | | 预期无反应（>24 m） |
| ~50 m | | 预期无反应 |

---

## 7. M3 脚步检查（粒子 + decal + 白名单，decal 池 ≤12）

1. 确认 M3 资产已创建（`NS_GrassFootstepPuff`、`M_GrassTrampleDecal`）且
   `UGrassFootstepFeedbackComponent` 已挂在玩家上（编排者已接线）。
2. 在**草地**表面走动，期望三件事同时发生：
   - 草屑／尘粒子（`NS_GrassFootstepPuff`，≤64 活粒子）；
   - 地表 decal 脚印轨迹；
   - 比移动源更强的单脚 stamp（脚印比普通走路更深）。
3. 换成**非白名单**表面（石头／金属／木板等）：应**不触发**上述反馈（Niagara/decal/stamp 都不应出现）。
4. 长时间跑（建议 ≥5 分钟连续行走 + 多次爆炸，制造大量脚步）后检查 decal 数量不泄漏。

| 检查 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 草地脚步 → 粒子 | 有，≤64 活粒子 | | |
| 草地脚步 → decal 脚印 | 有 | | |
| 草地脚步 → 更强 stamp | 有 | | |
| 非白名单表面不触发 | 不触发 | | |
| 长跑后 decal 数 | **≤ 12** | | |
| 长跑后粒子数 | 回到 0（池 AutoRelease） | | |

decal 数量观察方法（任选其一并注明用的是哪个）：

- `stat decals` / `stat scenedecals`（若有）；
- 开发者面板的性能页 decal 计数；
- `r.Decal.Debug` 类调试视图；
- 长时间跑后目视：不应看到几十上百个脚印堆在地上。

注意（计划 §10 风险 3）：若 decal 在 DynamicMesh 地表**完全不生效**，那是已知降级路径，
应记录为「decal 无效，仅 RT + 粒子」，并注明是否可接受，而不是当作粒子或 stamp 失败。

---

## 8. Nanite 开关对照（伪影检查）

同一位置、同一朝向，切换 `r.Nanite.Foliage`（必要时连 `r.Nanite`）对比：

| 设置 | 压平形态 | 波前环 | 闪烁/抖动 | 草穿透/撕裂 | 截图编号 |
|---|---|---|---|---|---|
| `r.Nanite.Foliage 1`（默认） | | | | | |
| `r.Nanite.Foliage 0` | | | | | |

已知风险（计划 §10 风险 1）：Nanite 聚类误差会让 WPO 出现细微裂缝或草尖分离，尤其在偏移幅度
接近草高时。若只在 Nanite 开启时出现，记录为「Nanite WPO 伪影」，回退方案＝交互草网格单独关 Nanite
（FoliageType / 实例级），不要改全局 `r.Nanite`。

---

## 9. World Partition 跨 cell 连续性

1. 选一条**跨越 cell 边界**的草地路线（用 World Partition 可视化或已知 cell 尺寸确定边界位置）。
2. 以正常速度走过边界，观察草地上刚留下的压平痕迹在跨 cell 前后：
   - 不应出现一条**突然截断的直线**；
   - 不应出现痕迹**整体跳位**或翻转；
   - 越界瞬间不应闪一下（recenter 搬移缝，计划 §10 风险 2）。
3. 反复来回走 5 次以上，记录是否偶发。

| 检查 | 期望 | 实测 | 判定 |
|---|---|---|---|
| 跨 cell 痕迹连续 | 连续 | | |
| 跨 cell 无跳位 | 无 | | |
| 跨 4 m snap 格无可见缝 | 无 | | |
| 远端 cell 未加载处 | 无残留、无报错 | | |

同时记录 Output Log 里是否有 `LogGrassDeform` 的 warning（尤其资产缺失或 RT 重建）。

---

## 10. Scalability 低画质自动关（§9 的 M4 项）

1. `GrassDeform.Status` 记一次基线（应 `enabled=1`，`foliageQuality=3`）。
2. 执行 `sg.FoliageQuality 0`（或 `scalability 0` 整体低画质）。
3. 期望：
   - `GrassDeform.Status` → `enabled=0 foliageQuality=0`；
   - 走动／爆炸**完全无**草的倒伏与波前；
   - 与 `r.GrassDeform 0` 的效果一致（这是契约：低画质 = 关）。
4. 恢复 `sg.FoliageQuality 2` 或 `3`：应**自动恢复**到 cvar 驱动状态（`enabled=1`，草再次响应）。
5. 恢复后确认 `r.GrassDeform` 的值没有被系统改写（`r.GrassDeform` 仍是 1）。

| 步骤 | 期望 Status | 实测 Status | 视觉 | 判定 |
|---|---|---|---|---|
| 基线 | `enabled=1 foliageQuality=3` | | | |
| `sg.FoliageQuality 0` | `enabled=0 foliageQuality=0` | | 无反应 | |
| 恢复 `sg.FoliageQuality 3` | `enabled=1` | | 恢复反应 | |
| 恢复后 `r.GrassDeform` | 仍为 1 | | | |

也请顺带核对 `sg.FoliageQuality 1`（Medium）：按契约 level ≥1 时 deform **仍然开启**，
由 `r.GrassDeform` 决定。若在 level 1 就被关掉，说明门槛判定错了。

---

## 11. 已知边界确认（记录用，不需要"修好"）

| 边界 | 出处 | 实测是否命中 | 是否可接受 |
|---|---|---|---|
| 48 m 窗口：>24 m 的爆炸无草压平 | 计划 §10.5（M2 发现） | | |
| 同时刻只能有一个波前环（第二发覆盖第一发） | 计划 §10.5 | | |
| decal 若在 DynamicMesh 地表不生效 → 降级为仅 RT + 粒子 | 计划 §10 风险 3 | | |
| Nanite WPO 细微伪影（若出现）→ 交互草网格单独关 Nanite | 计划 §10 风险 1 | | |

---

## 12. 缺陷记录

| # | 现象 | 复现步骤 | 期望 | 实际 | 严重度 | 截图/日志 |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |

附：Output Log 里 `LogGrassDeform` 的全部输出（可用 `log LogGrassDeform` 提高详细度）：

```
（粘贴）
```

---

## 13. 未测项声明

填完后列出本次**没有**覆盖的部分（例如：未测打包构建、未测 WP 流送压力场景、未测低配 GPU、
未测多人）：

-

> 本模板由 M4 收尾单创建；制作方未运行本表任何一项。表内期望值全部来自计划文档
> [grass-interaction-gpu-20260925.md](../WorldGeneration/grass-interaction-gpu-20260925.md)，
> 阈值改动请同步改计划 §7。