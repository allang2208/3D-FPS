# 双持冲刺攻击：双手向下劈（2026-11-04）

用户：双持冲刺攻击的左手动作，弯刀和斧头都做成双手向下劈砍，参考双斧三连击的最后一击。

单持冲刺攻击（`SprintAttack`，40/30 s）是双手跳劈：0.10 s 两只手合握同一把刀柄。双持时每只手各拿一把武器，这个合握不存在。原来左手的武器会被带到右手的刀柄上。

做法同双斧第三段（`HatchetDualAttack3`）：
- **右手**：单持跳劈原样。
- **左手**：右手的镜像，同一时刻落下（`dual_rig`：左骨 = `ROT_X180 @` 右骨世界旋转，位置用左骨自己的局部）。
- **两拳的位置**：
  - 劈砍全程各向外 9 cm（`SPREAD`，同双斧劈），两把武器并排落下，打击时相距约 12 cm，屏幕上在准星两侧 ±0.1；
  - 劈过中线时左拳近 2.5 cm。
- **进出双持待机**：
  - 从双持待机第 0 帧起手（0–0.10 s 淡入）；离开交叉握姿时左手在前（`UNCROSS` 4 cm）；
  - 1.02–1.30 s 收回双持待机；从下方回来时右手在前、左手在后且低 4 cm（双斧劈的回位顺序）。
- **共用**：弯刀对、斧头对、混搭都用这一段；冲刺攻击本来就是弯刀族共用的招式。
- **时钟**：与单持完全相同（命中窗 0.367–0.467、剑气 0.345–0.410、1.333 s），`KukriDualDashRhythm.h` 用 `static_assert` 钉住。玩法、伤害与服务端回执不变。

## 读数

- 两把武器的最近距离（只算画面里看得到的帧；武器真实采样点，斧头取头部、弯刀取刃线）：
  - 弯刀/弯刀 3.91 cm
  - 斧头/弯刀 2.08 cm
  - 弯刀/斧头 1.90 cm
  - 斧头/斧头 1.85 cm
  - 最近处都在 1.11–1.24 s 回到交叉握姿的途中。作为参照，双持待机本身 3.53 cm，双斧劈 2.87 cm。
- 手臂伸展最大 0.96 / 1.00，出现在 0.95 s：单持动作在画面下方伸直的那一刻，看不到。

## 运行接入

- `KukriDashAttack.cpp`：双持（`IsDual()`）且 clip 已加载时播 `DualSprintAttack`（`bDualDash`，起手时确定）；否则仍是单持跳劈。
- 镜头：保留跳起的俯仰和视场，去掉单手劈带的偏航与滚转。两手对称，做法同双斧劈的镜头。
- 剑气：两道，每把武器一道（`KukriDualDashRhythm::RibbonRight/Left`），展开窗口同单持。
- `IsDualClip` 认这段：进出双持握姿时左臂不另做淡化，握持锁保持。
- 第三人称：动作名仍报 `SprintAttack`，身体照旧按副手匹配选自己的双持冲刺版本（`Kukri.FullBody.Dual.Dash`），观察者不受影响。

## 资产与构建

- `A_Kukri_DualSprintAttack`（1.333 s，161 帧）后台导入，0 错误（`import_receipt.json`）。
- `FPSGAMEEditor Win64 Development` Succeeded：`Saved/BuildEditor/build-dual-sprint-attack-20261104.log`。
  第一次构建因头文件里时长写成小数、与单持 `40.f/30.f` 不等，`static_assert` 失败；已改为同一表达式。
- 预览（V7 手模、真实网格，未叠加镜头，非实机）：`HatchetPairs20261104/Previews/DualSprintAttackHH_sheet_*.jpg`、`DualSprintAttackKK_sheet_*.jpg`，每 1/30 s 一格。
- 未运行游戏、测试或验收。

## 重建

```
python -I author_dual_sprint_attack.py --header
UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -script=D:/FPS3D/FPSGAME/SourceAssets/DualSprintAttack20261104/import_dual_sprint_attack.py -unattended -nosplash
python -I ../HatchetPairs20261104/preview_pairs.py dash --render
```
