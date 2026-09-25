# DW715 单发装填音效升级：计划与实施

2026-09-25。需求：左轮**未装快速装弹器**时的单发装填目前是一套独立音效，要求把快速装填（装弹器）那套录制音效合理应用过来。

## 一、现状：不是"另一套音效"，而是借用了 AKM 的弹匣音

`FPSGAMECharacter.cpp:1127-1145`，`bUseDanWesson715 && bRevolverSingleReload` 分支：

| 动画节点 | 采样点(源秒) | 现在用的声音 | 实际来源 |
| --- | --- | --- | --- |
| 转轮甩开 | 0.48 | `MagOutSound` | `S_AKM_MagOut` |
| 抛壳（仅空仓） | 1.28（`EmptyCaseClear`） | `ChargePullSound` | `S_AKM_ChargePull` |
| 第 1–6 发压入 | 1.74 + 1.10×i | `MagSeatSound` | `S_AKM_MagSeat` |
| 转轮闭合 | `SingleLoopBegin + 1.10×Count + 0.37` | `ChargeReleaseSound` | `S_AKM_ChargeRelease` |

这五个通用音在 `LoadAKMSound` 里统一加载（`FPSGAMECharacter.cpp:615-619`），是 AKM 弹匣/拉机柄的录音。AK 的弹匣插入和左轮转轮闭合完全是两种机械，所以听起来是"另一套"。

## 二、时间轴本身是对的，不用动

单发动画实测时长（编辑器内读取 `A_DW715_single_*`）：

| 起始/装填数 | 0_1 | 0_2 | 0_3 | 0_4 | 0_5 | 0_6 | 1_1 | 1_2 | 1_3 | 1_4 | 1_5 | 2_2 | 2_3 | 2_4 | 3_3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 时长(s) | 3.3 | 4.4 | 5.5 | 6.6 | 7.7 | 8.8 | 2.4 | 3.5 | 4.6 | 5.7 | 6.8 | 3.5 | 4.6 | 5.7 | 4.6 |

两类片段各有自己的规律（`s_n` = 转轮里已有 s 发、本次装 n 发，播放的片段名就是 `A_DW715_single_<s>_<n>`）：

- **`0_n` 族（全空转轮）**：`时长 = 0.60 + 1.10×n + 1.60`，n=1…6 全部吻合（3.3 / 4.4 / 5.5 / 6.6 / 7.7 / 8.8）。
- **`s_n` 族（残留 s 发）**：用已测的 1_1…1_5 拟合出 `时长 = 0.4×(n−s) + 1.10×n + 2.0`，对 1_1…1_5 与 2_2/2_3/2_4/3_3 **九条全部命中**（误差 ≤0.1 s）：2.4 / 3.5 / 4.6 / 5.7 / 6.8 与 3.5 / 4.6 / 5.7 / 4.6。

关键含义：**两族的每发增量都是 1.10 s，等于 `SingleStep`**；且时长只随**本次实际装填的 n** 增长，与残留 s 无关（1_1 与 2_2 都是 2.4 s，1_2 与 2_3 都是 3.5 s）——也就是说引擎在装不满 6 发时会播放 `n = 实际装填数` 的片段，每发一步，与 `SingleSeatTime(Index) = SingleLoopBegin + 1.10×Index + 0.64` 的步进一致。

**结论：采样点不用改。**（附带发现：`SingleDuration()` 只在 `bEmpty=false` 时对 `0_n` 族成立；`s_n` 族另有常数项，但代码里 `SingleDuration` 的实际使用未查到依赖该常数项的地方，本轮不动它。）

## 三、可以直接复用的录制音

`SpeedloaderSoundCues`（7 条）里，有 3 条的动作在单发装填中**物理上是同一个动作**，因此录音直接通用：

| 录制音 | 录音内撞击位置(锚点) | 前置余量 lead | 单发装填对应动作 | 理由 |
| --- | --- | --- | --- | --- |
| `Open` | 0.1075 s | 0.1075 | 转轮甩开 0.48 | 甩开转轮与装弹器无关，机械完全相同 |
| `Eject` | 0.2575 s | 0.2575 | 抛壳 1.28（仅空仓） | 退壳杆动作相同 |
| `Close` | 0.0675 s | 0.0675 | 转轮闭合 | 合拢转轮动作相同 |

不能复用的 4 条：`Retrieve`/`Insert`/`Release`/`Withdraw` 都是**装弹器本体**的动作（取装弹器、把装弹器推入、释放弹托、抽出装弹器），单发装填没有这些步骤，硬套会变成"手里没有装弹器却在响装弹器"。

## 四、关键：录制音必须按 lead 提前触发

录制音不是"按下即响"，切片起点在撞击之前。管线里装弹器路径已经处理了这件事：

```cpp
Cues.Add({Cue.Contact * CueScale - Cue.LeadSeconds * SourcePerSecond, Sound});
```

单发路径**没有**这个补偿，直接写死 `MechanicalCueTimes = {0.48}`。直接把录制音塞进去，撞击会比动作晚 67–258 ms。

所以单发路径按同一规则重排：

| 声音 | 撞击应对齐 | 减去 lead | 实际触发(源秒) |
| --- | --- | --- | --- |
| `Open` | 0.48 | 0.1075 | **0.3725** |
| `Eject` | 1.28 | 0.2575 | **1.0225** |
| `Close` | `SingleLoopBegin + 1.10×Count + 0.37` | 0.0675 | **… + 0.3025** |

第 1–6 发压入保留 `MagSeatSound`：录制素材里**没有**单发压弹的采样（`Release` 是弹托一次性释放 6 发，用它递归 6 次会更假），而且它对应的采样点 1.74+1.10×i 就是动画里撞击发生的时刻，按撞击对齐本身就是对的。这一条属于"素材缺口"，如实标注。

## 五、实施步骤

1. `DanWesson715WeaponAssets.h`：把单发抖轮闭合采样点 `+0.37f` 提为具名常量 `SingleCloseContact`，避免同一魔数散落在代码与动画对齐逻辑里。
2. `FPSGAMECharacter.cpp` 单发分支：按名字从 `RevolverSpeedloaderSounds` 取 `Open`/`Eject`/`Close` 三件录制音，按上表提前触发。
3. 编译。
4. 如实交付：未测试项、回退方式。

## 六、边界与未决

- **`+0.37` 未被独立验证，本轮不动。** 它的语义不清：按 `SingleCloseTail=0.70` 推断，若闭合撞击发生在"片段结束前 0.70 s"，则闭合应在 `SingleLoopBegin + 1.10×Count`，与代码的 `+0.37` 差 0.37 s。用实测时长反推：`0_6` 片段结束时闭合采样点在 `0.60 + 6.6 + 0.37 = 7.57`，距片段尾 1.23 s；`0_1` 则是 `2.07`，距尾同为 1.23 s——即代码把闭合放在**片段结束前 1.23 s**，而不是 `SingleCloseTail` 暗示的 0.70 s。两种解释都自洽，我无法从代码独立判定真实闭合帧。
  因此本轮**保留 0.37 原值**：改它等于在不明真相时挪动一个已经在跑的对齐点。这也保证了本次改动的语义是干净的——**只换音源，不动时间轴**。若用户实测发现闭合声偏早/偏晚，这里才是要查的地方。
- 单发压弹的通用 `MagSeatSound` 保留，属于素材缺口。
- 我无法试听，以上均为代码与素材实测；听感判定归用户。
- 不改动：装弹器路径、其余 5 个 cue、单发动画本身、任何 uasset。

## 七、实施记录

### 改动文件

| 文件 | 改动 |
| --- | --- |
| `Source/FPSGAME/Weapons/DanWesson715WeaponAssets.h` | 新增具名常量 `SingleCloseContact = .37f`（原为散落魔数） |
| `Source/FPSGAME/FPSGAMECharacter.cpp` | 单发分支 `bUseDanWesson715 && bRevolverSingleLoad`：音源与触发点重排 |
| `Source/FPSGAME/Weapons/WeaponReloadStages.cpp` | `Tail + .37f` → `Tail + SingleCloseContact`（与音频 cue 共用同一常量，防止两处漂移；数值不变） |

### 改动后的单发 cue 表

| # | 动作 | 声音 | 触发(源秒) |
| --- | --- | --- | --- |
| 0 | 转轮甩开 | `S_DW715_Loader_Open` | 0.3725 |
| 1 | 抛壳（仅空仓） | `S_DW715_Loader_Eject` | 1.0225 |
| 2…2+n-1 | 第 i 发压入 | `S_AKM_MagSeat`（保留） | 1.74 + 1.10×i（空仓 2.64 + 1.10×i） |
| 末 | 转轮闭合 | `S_DW715_Loader_Close` | `0.60 + 1.10×Count + 0.3025` |

触发点 = 撞击采样点 − 录制音 lead，撞击与动作对齐；与装弹器路径 `Contact*Scale − Lead*SourcePerSecond` 同一规则。

### 失效保护

录制音缺失、或时长不足以容纳 lead 时，回退为原来的通用音 + 撞击时刻（行为与改动前一致），不会出现负触发或空白。

### 编译

Live Coding（用户在编辑器内触发）第一次**失败**，诊断从 per-file SARIF 取出（`Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/FPSGAMECharacter.cpp.sarif`）：

```
C3487 [error] FPSGAMECharacter.cpp:1148
  "USoundBase *": 所有返回表达式必须推导为相同类型: 以前为"TObjectPtr<USoundBase>"
```

原因：`RevolverSpeedloaderSounds` 是 `TArray<TObjectPtr<USoundBase>>`，我的 lambda 用 `auto` 推导返回类型，`return Recorded;`（`TObjectPtr`）与 `return MagOutSound;`（裸指针）冲突。**是我的写法错误**，与其他人未提交的改动无关。

修法（第一次尝试，**仍然报错**）：显式声明返回类型 `-> USoundBase*`。第二次编译仍报 C3487 的变体：

```
条件表达式的 result 类型有歧义: 类型"TObjectPtr<USoundBase>"和"USoundBase *"可转换为多个常见类型
```

原因：即使指定了返回类型，**三元表达式本身**的两个分支（`MagOutSound` 是 `TObjectPtr`，`Recorded` 是裸指针）已经先一步产生歧义，指定的返回类型无法消解。

修法（第二次，已落盘）：不再用三元表达式，改为语句式并把数组元素显式取为 `TObjectPtr<USoundBase>`：

```cpp
TObjectPtr<USoundBase> Recorded = RevolverSpeedloaderSounds.IsValidIndex(CueIndex)
    ? RevolverSpeedloaderSounds[CueIndex] : nullptr;
if (!Recorded || Recorded->GetDuration() <= Lead) return MagOutSound;
return Recorded.Get();
```

### 最终编译：通过（完整 Build）

用户关闭编辑器后，后台跑完整 Build：

```
Build.bat FPSGAMEEditor Win64 Development -Project=FPSGAME.uproject -WaitMutex -FromMsBuild
[4/16] Compile [x64] FPSGAMECharacter.cpp      <- 无错误
[15/16] Link [x64] UnrealEditor-FPSGAME.dll
Result: Succeeded        (Total execution time: 94.89 seconds)
```

- `FPSGAMECharacter.cpp.sarif` 17:15:49 → **CLEAN（无 error）**。
- 仅剩两条与本次无关的既有警告：`ColdSteelWeaponIconAudit.cpp:53` C4996（`FImageUtils::CompressImageArray` 弃用）、`FrostSwordSurfaceCaptureCommandlet.cpp:37/45` C4305（double→float 截断）。
- 产物：`Binaries/Win64/UnrealEditor-FPSGAME.dll`（13729792 B，17:17:12）。

### 编译时间线（如实记录）

| 时刻 | 事件 |
| --- | --- |
| 16:44:03 | 第 1 次 Live Coding 开始 |
| 16:44:19 | `FPSGAMECharacter.cpp.sarif` 写入 → C3487（返回类型推导冲突） |
| 16:50:10 | 第 1 次失败 |
| 16:51 前后 | 第 1 次修法落盘（显式返回类型） |
| 17:03:48 | 第 2 次 Live Coding 开始 |
| 17:04:09 | SARIF 写入 → 报三元表达式歧义（**读的是 17:05:00 之前的旧文件**） |
| 17:05:00 | 第 2 次修法落盘（改为语句式） |
| 17:07:31 | 第 2 次失败 |
| 17:15:32 | 用户关闭编辑器 |
| 17:15:49 | 完整 Build 编译 `FPSGAMECharacter.cpp` → **无错误** |
| 17:17:12 | 链接产出 `UnrealEditor-FPSGAME.dll`；**Result: Succeeded** |
| 17:37:09 | 追加 `WeaponReloadStages.cpp` 魔数替换（`Tail + .37f` → `Tail + SingleCloseContact`，数值不变） |
| 17:37:32 | 增量重编 `[1/4] Compile WeaponReloadStages.cpp` → `Result: Succeeded`（19.60 s），DLL 更新 |

最终状态：三个改动文件均已落盘；`FPSGAMECharacter.cpp.sarif` 17:15:49 CLEAN、`WeaponReloadStages.cpp.sarif` 17:37:28 CLEAN；`UnrealEditor-FPSGAME.dll` 17:37:32 为含全部改动的最新产物。

第 2 次失败对应的仍是修改前的源码（源文件 17:05:00 才写入，编译器 17:04:09 已读完），**不是新问题**。第 2 次修法已由完整 Build 验证通过。

### 实际 cue 表（Count = 装填发数）

空仓（`bPendingEmptyReload`，`SingleLoopBegin = 1.50`）：

| 动作 | 声音 | 触发(源秒) |
| --- | --- | --- |
| 转轮甩开 | `S_DW715_Loader_Open` | 0.3725 |
| 抛壳 | `S_DW715_Loader_Eject` | 1.0225 |
| 第 1 发 | `S_AKM_MagSeat` | 2.14 |
| 第 i 发 | `S_AKM_MagSeat` | 2.14 + 1.10×(i−1) |
| 转轮闭合 | `S_DW715_Loader_Close` | 1.8025 + 1.10×Count |

非空（补装，`SingleLoopBegin = 0.60`）：无抛壳；第 1 发 1.74；闭合 `0.9025 + 1.10×Count`。

### 未测试项

- 编译通过后仅代表可构建；**未运行 PIE、未做游戏内验收**，音画对时与听感由用户判定。
- `SingleCloseContact`（0.37）未独立验证，见第六节。
- 单发压弹仍是 `S_AKM_MagSeat`（录制素材缺口）。
- **潜在次序风险（当前数据不触发）**：闭合 cue 触发点 = `0.60/1.50 + 1.10×Count + 0.3025`，只有在 `CloseLead > 0.3025` 时才会早于最后一发压入（即早于 `+0.64`）。实测 `Close` 的 lead 是 0.0675，因此当前恒晚于压弹。若日后重切录制音、lead 变大，需要在这里补一次排序或夹取。

---

## 八、修正记录（2026-09-25 晚）：改用左轮自带机械音，撤销录制音长尾

### 用户反馈

接入后实测：单发装填换成机械音后**不合格**，要求换一个机械音。

### 我犯的错，以及一个必须作废的结论

**1. 上一轮我把三个干净撞击换成了录制音的长噪声尾巴。**

实测"能量在 60 ms 之后的比例"（原 `_diag_seat_vs_loader.py`，已退役到
`trash/dw715-single-load-seat-probe-20260925/`；该结论由本文表格保留）：

| 声音 | 时长 | 峰值 | 质心 | **60 ms 后剩余能量** |
| --- | --- | --- | --- | --- |
| 左轮自带 `ChargeRelease`（原 Close） | 180 ms | −6.4 | 3335 Hz | **0.2 %** |
| 左轮自带 `MagOut`（原 Open） | 160 ms | −8.0 | 2670 Hz | **0.5 %** |
| 左轮自带 `MagSeat`（压弹，未动） | 170 ms | −8.4 | 3429 Hz | **0.7 %** |
| 录制 `S_DW715_Loader_Close`（我换的） | 480 ms | −5.3 | 4392 Hz | **99.8 %** |
| 录制 `S_DW715_Loader_Open`（我换的） | 250 ms | −6.8 | 5007 Hz | **86.7 %** |
| 录制 `S_DW715_Loader_Eject`（我换的） | 430 ms | −8.3 | 1587 Hz | **83.0 %** |

录制音是长素材，83–99.8 % 的能量在 60 ms 之后；而**它们的尾巴正是上一轮花大力气剔除的风声**。单发装填要连响 6 次压弹，中间夹着长噪声尾巴 —— 这是退化。

**2. 一个结论作废：「单发路径从来不加载 715 自带音，用的是 AKM 的」。**

这是**错的**。`LoadAKMSound`（`FPSGAMECharacter.cpp:2780-2784`）本来就有 715 分支：

```cpp
if (bUseDanWesson715 && FCString::Strcmp(AssetName, TEXT("S_AKM_CriticalHit")) != 0)
{
    FString Cue(AssetName); Cue.RemoveFromStart(TEXT("S_AKM_"));
    return LoadObject<USoundBase>(nullptr, *DanWesson715WeaponAssets::SoundPath(Cue));
}
```

`S_AKM_MagSeat` 等**早就被路由到 `S_DW715_MagSeat`**。我据此做的"AKM MagSeat 又轻又闷（−32.7 dBFS、677 Hz、峰值在 162.7 ms）"分析，测的是 `AKMVideoAudio20260921` 里**引擎根本没在用的文件**。那份分析**全部作废**，不得再引用。

### 采用方案

单发路径全部改用**左轮自带的紧促机械音**，与双持路径 `SingleOpen/SingleEject/SingleClose` 的映射一致：

| 动作 | 声音 | 触发(源秒) |
| --- | --- | --- |
| 转轮甩开 | `S_DW715_MagOut`（`MagOutSound`） | 0.48 |
| 抛壳（仅空仓） | `S_DW715_ChargePull`（`ChargePullSound`） | 1.28（`EmptyCaseClear`） |
| 第 i 发压入 | `S_DW715_MagSeat`（`MagSeatSound`） | `SingleLoopBegin + 1.10×i + 0.64` |
| 转轮闭合 | `S_DW715_ChargeRelease`（`ChargeReleaseSound`） | `SingleLoopBegin + 1.10×Count + 0.37` |

这些音实测 **onset 全为 0.0 ms**，因此**不需要 lead 提前触发**；上一轮加的 `− Lead` 补偿全部撤销。

### 撤销的改动

- 撤销 `RevolverMechanicalSounds` 数组成员与加载循环 —— `LoadAKMSound` 已在做同一件事。
- 撤销 `DanWesson715WeaponAssets.h` 中新增的 `MechanicalSoundCues` / `MechanicalSoundPath` —— 同上。
- 保留 `SingleCloseContact` 具名常量与 `WeaponReloadStages.cpp` 的共用（数值不变，防两处漂移）。

### 编译

| 时刻 | 事件 |
| --- | --- |
| 19:16:31 | 用户关闭编辑器 |
| 19:17:44 | `FPSGAMECharacter.cpp` 编译 **CLEAN** |
| 19:22:40 | `WeaponReloadStages.cpp` 编译 **CLEAN** |
| 19:23:0x | 整体 Build 失败：`RuneSwordComponent.cpp` 报 `ScheduleWalkInspect 找不到标识符` |
| 19:23:34 | 查明原因：**他人并行**在 19:18–19:20 改 `RuneSword*` 与 `FPSGAMECharacterActionPriority.cpp`；`RuneSwordComponent.h`（19:18:28）在我的编译读取之后才写入 —— **构建期竞态，非真实缺陷**（现头文件 193-197 行声明齐全） |
| 19:29:45 | 文件静默后重试：`[5/12] Compile FPSGAMECharacter.cpp` `[7/12] Compile RuneSwordComponent.cpp` → **Result: Succeeded**（107.70 s），DLL 19:29:45 更新 |

**我的文件全程 CLEAN；那次失败是并行编辑导致的构建竞态。**

### 未测试项（本轮）

- 编译通过仅代表可构建；**未运行 PIE、未做游戏内验收**，听感由用户判定。
- `SingleCloseContact`（0.37）仍未独立验证 —— 若闭合声偏早/偏晚，这里是要查的地方。
- 若左轮自带音仍被认为不合格，下一步应考虑**重新剪辑录制音、只保留撞击并去掉长尾**，而不是整段套用（录制音的机械质感更真实，问题只在尾巴）。

---

## 九、再次修正（2026-09-25 晚）：恢复录制音，只换压弹音

### 用户澄清

> 上一版声音才是对的，只要你改进单发装填的音效，你又全部改回原来错误的了，上一版的甩开弹仓是对的

即：**第八节把三个音全退回左轮自带音是过度修正。** 录制音版本（`S_DW715_Loader_*` 按 lead 提前触发）才是对的方向，其中**甩开弹仓（Open）已被明确确认为正确**。真正要改的只有**每发压弹的音**。

### 恢复的内容

`Open` / `Eject` / `Close` 恢复为录制音 + lead 提前触发，与 17:37 版一致：

| 动作 | 声音 | 触发(源秒) |
| --- | --- | --- |
| 转轮甩开 | `S_DW715_Loader_Open` | 0.3725 |
| 抛壳（仅空仓） | `S_DW715_Loader_Eject` | 1.0225 |
| 转轮闭合 | `S_DW715_Loader_Close` | `SingleLoopBegin + 1.10×Count + 0.3025` |

### 压弹音：换成 `S_DW715_DryClick`

被换掉的 `MagSeat` 实测偏软偏中频（前 30 ms 占 79.2 %，1.5 kHz 以上仅 27.0 %），六发连响显得糊。

左轮自带候选实测：

| 声音 | 时长 | 起音 | 前 30 ms 能量 | HF>1.5k | 峰值 |
| --- | --- | --- | --- | --- | --- |
| **DryClick（采用）** | 100 ms | **0.33 ms** | **98.9 %** | **81.1 %** | −12.0 dBFS |
| ChargeRelease（闭合，在用） | 180 ms | 0.54 ms | 89.7 % | 37.4 % | −6.4 |
| MagSeat（原压弹） | 170 ms | 0.33 ms | 79.2 % | 27.0 % | −8.4 |
| MagOut（甩开，在用） | 160 ms | 0.21 ms | 66.1 % | 29.1 % | −8.0 |
| MagInsert | 200 ms | **24.44 ms** | 52.8 % | 64.0 % | −9.1 |

`MagInsert` 起音 24.44 ms（是"推入"不是"咔哒"）被排除；`DryClick` 是左轮自有素材里最紧最脆的咔哒，故采用。回退只需把该行改回 `MagSeatSound`（代码注释已标出）。

### 编译

Live Coding（用户触发）：19:58:53 开始 → **20:04:30 Live coding succeeded**，`FPSGAMECharacter.cpp.sarif` 20:04:11 **CLEAN**。

### 未测试项

- **未运行 PIE、未做游戏内验收**；DryClick 是否合适由用户判定。
- 若 DryClick 听感太干、太亮（毕竟是击锤/击针素材），退路依次为：MagSeat（原样）→ MagSeat 与 DryClick 交替。
- `SingleCloseContact`（0.37）仍未独立验证。

---

## 十、目录整理（2026-09-25）

保留在本目录：

| 文件 | 作用 |
| --- | --- |
| `SINGLE_LOAD_PLAN.md` | 本文（含全部结论与两次修正） |
| `_probe_single_anim.py` | 单发装填动画时长探针（`0_n` / `s_n` 两族的拟合依据） |
| `_diag_seat_replacement.py` | 压弹音候选实测（起音/前 30 ms 能量/HF 占比） |
| `seat_onsets.json`、`seat_candidates.json`、`seat_replacement.json` | 对应实测输出（JSON 保持本机，见 `.gitignore` 第 168 行） |

已退役到 `trash/dw715-single-load-seat-probe-20260925/`（4 条，含 SHA-256 manifest）：
`_diag_seat_onsets.py`、`_diag_seat_candidates.py`（被 `_diag_seat_replacement.py` 的更严口径取代），
`_diag_seat_vs_loader.py`（测的是一个**作废假设**——它量的 AKM 文件引擎从不播放，结论已由本文第八节作废），
`_retire_dead_ends.py`（本次一次性退役脚本，manifest 即持久记录）。