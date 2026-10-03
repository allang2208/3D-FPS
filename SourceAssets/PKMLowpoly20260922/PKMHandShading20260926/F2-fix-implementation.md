# F2 外科式修复实现记录（2026-09-26，合并点执行：父会话）

> ## ⛔ 已回滚（2026-09-26 13:02，用户指示）
>
> 用户实机验收反馈**「没成果」**（条纹未消除），指示先退回修改。回滚证据：
> - 代码：6 处改动全部反向撤销；`Source/FPSGAME/Characters/` 零 F2 标记残留
>   （grep FPWeaponShadow/FPBodyShadow/IsFirstPersonLocalOwner/PKMHandShading20260926 = 0 命中）；
>   `git diff --stat` 逐字回到实现前状态（Actions 6 / Camera 4 / Component.cpp 3 /
>   Equipment.cpp 16，Component.h 恢复零差异），他人未提交改动未触碰。
> - 构建：`Saved/BuildEditor/build-20260926-130232.log` Result: Succeeded（28.22s），
>   DLL 已还原为修复前行为。
> - **在体否定证据**：默认态（世界武器/部件副本第一人称停投影）下条纹未消除 →
>   世界武器副本的直接光阴影至少不是唯一成因。待用户回补：条纹是否有任何变化、
>   是否做过 cvar A/B、`fps.body.WorldBodyShadow 0` / `fps.body.WorldBody 0` 两项检验结果。
> - 注意新变量：2026-09-26 01:35 原版 SkinMicro 真图首次导入 UE（此前案发期为 32×32 占位图、
>   昨夜为被否决各向同性版）——用户今日所见条纹与首报是否同一形态待确认。
>
> 以下为回滚前的实现记录，保留供复用（改动可按本文原样重放）。

用户拍板「直接按 F2 修」后实施。诊断依据见同目录 `README.md`（机制 A：第一人称下隐藏的
世界身体/世界武器副本以 `bCastHiddenShadow` 向 VSM/Lumen 投影，落在正常接收阴影的视模
手臂上；PKM 换弹时世界 PKM 大枪身副本与视模左小臂空间重合＝首要嫌疑与 PKM 特异性解释）。

原定 F2 执行子代理（77e9ca56）运行 11 小时零写入，判定卡死，已中断；实现由父会话直接完成。

## 与原 F2 定义的一处偏差（实测约束）

原定义「只隐藏世界身体**手臂段** section」不可行：`SKM_Manny_PlayerSkin` 只有
**M_Torso / M_HeadLegs 两个材质 section**（uasset 名字表实测），手臂与躯干共用 M_Torso，
段级压制无从下手。因此拆成两个独立开关，默认值按证据与合同取舍：

| cvar | 默认 | 语义（1=投影） | 依据 |
|---|---|---|---|
| `fps.body.FPWeaponShadow` | **0（停投影＝修复生效）** | 本地第一人称世界武器/部件副本是否投影 | 首要嫌疑（PKM 特异性=最大近身投影体）；副本第一人称下 OwnerNoSee 完全不可见，唯一本地输出就是阴影 → 停投影零可见性代价（只失去第一人称下自己枪的地面影，且该影与视模枪错位） |
| `fps.body.FPBodyShadow` | **1（保持投影＝合同不变）** | 本地第一人称世界身体（含跟随其阴影像征的装备壳）是否投影 | 段级不可行，只能整身取舍；置 0＝等效 F1（第一人称失去自身地面影），用户已明确选 F2 弃 F1，故默认不越权。用途＝残余条纹的 A/B 判定开关 |

两开关**仅对本地受控玩家的第一人称状态生效**（`IsFirstPersonLocalOwner()` 闸门）；
远端玩家的副本实例在各客户端本地构建、F6 第三人称视图走 `!IsFirstPersonLocalOwner()`
分支——均完全不受影响。收枪（Stowed）不投影的既有规则保留。

## 改动清单（共 3 文件 6 处，全部叠加在他人未提交改动之上，未回退任何内容）

`Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp`
1. `FPSPlayerBodyDiagnostics` 命名空间内新增两个 cvar（`GFPWeaponShadow=0`、`GFPBodyShadow=1`，
   `FAutoConsoleVariableRef` 注册，帮助文本含 0/1 语义）。生效机制与既有 `fps.body.WorldBodyShadow`
   相同＝使用点读取＋周期重申（既有 OnChanged 回调实为未绑定死代码，未复制该模式）。
2. 新增导出 getter `FPSPlayerBodyFPWeaponShadowEnabled()` / `FPSPlayerBodyFPBodyShadowEnabled()`。
3. 新增私有辅助 `IsFirstPersonLocalOwner()`，并把 `ShouldWorldBodyCastShadow()` 内同式收敛到它
   （语义零变化）。
4. `ApplyWorldBodyShadow()`：身体网格与 OutfitMeshes 的投影闸门叠加 FPBodyShadow 条件。
   装备壳（衬衫/手套世界副本）由 `FPSModularOutfitComponent::FollowVisibility`（:112-126）
   每帧照抄源组件 `CastShadow/bCastHiddenShadow`，随身体闸门自动生效，无需改该文件。

`Source/FPSGAME/Characters/FPSPlayerBodyComponent.h`
5. 私有段声明 `IsFirstPersonLocalOwner()`；文件尾声明两个导出 getter（含语义注释）。

`Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp`
6. `UpdateWorldWeaponPresentation()`（:246，注意本函数定义在 Equipment.cpp 而非 Component.cpp）：
   新增 `WeaponShadow = BodyShadow && (!IsFirstPersonLocalOwner() || FPWeaponShadowEnabled())`，
   `ApplyShadowFlags(Mesh, WeaponShadow && !Stowed)` 替换原 `BodyShadow && !Stowed`。
   该函数**每帧**由 TickComponent 调用 → 控制台切换一帧内生效。

所有改动处均有锚点注释引用 `PKMHandShading20260926` 与日期。

## 刷新链路（为什么不需要新钩子）

- 每帧：`TickComponent` → `UpdateWorldWeaponPresentation`（武器闸门重申）
- 每 0.2s：`UpdateOwnerVisibility` → `ApplyWorldBodyVisibility` → `ApplyWorldBodyShadow`（身体闸门重申）
- F6 视图切换：`FPSPlayerBodyCamera.cpp:57` → `ApplyWorldBodyShadow`
- 副本重建：`RebuildWeapons` 尾部 → `UpdateWorldWeaponPresentation`

## 用户实机验收单（构建完成后）

1. 装备 PKM，换弹，近距看左小臂：**深色斜带/灰褐层应消失**（默认即修复态，无需输命令）。
2. A/B 自证归因：`fps.body.FPWeaponShadow 1` → 条纹应回来；`0` → 消失。
   （这一对开关同时就是原 T1 检验的精细化版本。）
3. 若置 0 后仍有残余压暗：`fps.body.FPBodyShadow 0` → 残余消失＝世界身体臂段是次级投影体；
   此时二选一：接受等效 F1（常开 0，代价＝第一人称无自身地面影），或排期给
   SKM_Manny_PlayerSkin 重分 section（把手臂从 M_Torso 拆出，真·段级 F2，资产活）。
4. 副作用检查：第一人称低头——自身身体地面影仍在（FPBodyShadow 默认 1）、**枪的地面影消失**
   （FPWeaponShadow 默认 0 的预期代价）；F6 第三人称一切影子如旧；远端玩家视角不受影响。
5. 太阳角度检验（原 T3）顺手可做：条纹若原本随光照变化，修复后应无变化源。

## 回滚

- 运行时：`fps.body.FPWeaponShadow 1`（+`fps.body.FPBodyShadow 1`）＝完全旧行为，免重编译。
- 代码级：撤销上述 3 文件 6 处（全部带 PKMHandShading20260926 锚点注释，可 grep 定位）。

## 构建

合并点统一构建一次：`FPSGAMEEditor Win64 Development`。提交时机遵守 WORKFLOW §7 规则 3：
等编辑器（用户 12:20 打开的 PID 17444）关闭、无 UBT/cl/link、Source/ 静默 ≥2 分钟后自动提交
（`build_f2_when_clear.ps1`，日志 `Saved/BuildEditor/build-pkmf2-*.log`）。构建期间他人代码若有
半成品导致失败，如实报告不代修。

**按工程规则：未做任何测试、PIE、截图与验收；以上验收单留给用户实机执行。**
