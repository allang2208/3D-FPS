# M1911 快速进战·握把砸击（2026-09-19）

按 DanWesson715QuickCombat20260918 的作者管线为 1911 补齐快速进战 clip，让两把手枪
都真正支持砸击（此前 1911 在 `TriggerPistolQuickCombat` 的"没有作者源 clip"门槛被明确拒绝）。

## 2026-09-19 终版：真根因是基准取错 idle 代；修法=以运行时 Contact idle 为基准直接复用 715 动作表

用户第二轮反馈"还是不对，直接复用 715 行不行"后查出**真根因**：可编辑源 blend 里堆着历代
action，前两版基准取的是老一代 `M1911_idle`——那一代装配朝向差 180°（枪口 +Y/右手 +X）且枪收在
胸口（wpn.y=+0.144）。而**运行时 idle 是 `M1911_Contact_idle`**（`M1911WeaponAssets::AnimationPath
("idle")` → Contact20260913），它和 715 的 idle 在臂架空间**逐位一致**（枪口 -Y/右手 -X/枪前伸
wpn.y=-0.390，连握把距离都是 0.133 m）。所以：第一版=镜像（老 idle 翻转系里直搬动作表）；
第二版=方向修对但起点错（从"枪收胸口"起手，与游戏 idle 差 54 cm，起收各一次大跳变）。

**终版做法**（即用户说的"直接复用"）：基准换 `M1911_Contact_idle`，动作表/解算/共轭护栏全部
不动——ALIGN 自动退化为 0°，715 动作表原样直用，右手用 1911 自己 Contact idle 的握把关系。
**验证**：与 715 clip 逐帧增量差全 0.000（枪/左手/肘，8 个关键时）——两枪 clip 数值完全一致；
`|WPN_root−hand_r|`=0.133 恒定、末帧精确回 idle。715 自身抽查：QC 基座（PalmClearance 源）与
运行时（Upgrade 源）两代 DW715_idle 逐位一致（差 0.0000），715 从未中此坑。
资产 10:30 重导入；C++ 未动，旧 PIE 内存需重启。

（下一段 180° 共轭是第二版的中间结论，机制本身成立、护栏保留在脚本里，但它不是主因。）

## 2026-09-19 第二版（中间结论）：装配朝向 180° 镜像的共轭修复

**根因**：1911 的 Manny 装配在它自己的臂架空间里与 715 相差 180°（枪口 +Y、右手 +X；
715 是枪口 -Y、右手 -X，`WPN_root` 欧拉角 (0,4.9,-180) vs (0,0,0)）。动作表里**枪局部系合成
的量**（枪偏移 `gun`、倾角 `tilt`）身体相对方向天然一致；但三个**以臂架空间分量直用的量**——
左手下垂偏移 `left`、肘极 `pole_r`、躯干平移 `gun*.25`——全部左右/前后镜像：左手甩向枪口
方向而非左后出镜、蓄势抬肘方向反、重心前送变后撤。

**修法**（`author_actions.py` "装配朝向对齐"段）：由本枪 idle 的枪口方向推 ALIGN
（正则系→本枪臂架系的纯 Z 旋转，实测 -179.2°），上述三个量经 `ALIGN @` 共轭后使用；
带断言"对齐后右手必须在正则系 -X 侧"防共轭方向搞反。躯干偏航绕 Z 与装配朝向同轴、
身体相对意义不变，不用共轭。

**验证**（`compare_idles.py`，正则系逐帧增量差，idle 框架差已消除）：
左手 0.001–0.003 m、枪本体 ≤0.050 m（残差来自 1911 idle 自带 4.9° 枪口上仰，Z 分量≈0）、
肘 ≤0.096 m（方向已正，位置差为两枪 idle 手臂弯曲度不同的 IK 非线性）。
枪-手不变量 `|WPN_root−hand_r|=0.125 m` 仍全程恒定、末帧精确回 idle。
资产已重导入（10:20 落盘）；C++ 未动，运行时按路径加载即生效（旧 PIE 内存需重启）。

## 文件

- `author_actions.py`：打开 RearFinish 可编辑源 → 以 `M1911_idle` 为基准 → 逐帧 120 Hz 烘焙
  `M1911_quickcombat` → 导出 `Animations/A_M1911_quickcombat.fbx` → 存 `M1911_QuickCombat_Editable.blend`。
- `inspect_rig.py`：装配源检查记录（rig `SK_M1911_Manny` 108 骨、action 清单、WPN/手/手指骨齐全）。
- `animation.json`：动作表（与 715 逐值相同）、接触时间与导出去向。
- `import_assets.py`：骨架**从运行网格 `/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny` 动态解析**
  （实际是 `P9Retarget20260913/SK_M1911_Manny_Skeleton`，同命名骨架有三份，别硬编码），
  压缩设置沿用 `BC_M4Viewmodel`。
- `import.log` / `import.json`：导入记录（`M1911_QUICKCOMBAT_IMPORT_COMPLETE`，读回 `length=0.5500`）。

## 动作

与 715 完全同一张动作表（0.55s，接触 0.26s；节拍改动必须两份源同步并复核
`QuickCombatPistolMotion.h` 的分段比例常量）。枪的运动写在 `WPN_root` 上、右手由握把关系
带动（RIGHT_GRIP 取自 1911 自己的 idle），左手同解算器做松握→下垂出镜→回握。

作者源自检（`author_actions.py` 末尾打印）：

- `|WPN_root − hand_r| = 0.125 m` 全程恒定（1911 自己的握把距离；"枪不跟手"在作者源层面不可能）；
- t=0.55 精确回到 idle 基准位；
- 枪根局部坐标系诊断：枪口在 WPN_root 局部 -Y（0.000, -0.156, 0.023），与 715 同约定，
  动作表可直接沿用（该诊断的 dominant 轴判定首版写错了——Python 元组先比字符串 'z'>'y'，
  按值取下标才对；数值本身一直是对的）。

## 运行时接线（随本轮源码改动）

- `M1911WeaponAssets.h`：新增 `QuickCombatAnimationPath`（本目录 clip）。
- `FPSGAMECharacter.cpp`：`bUseM1911` 分支加载自己的 clip；
  `InitializeWeaponVisuals()` 重置段新增 `QuickCombatAnimation=nullptr`——修复换枪残留指针
  （此前先用过 715 再切 1911，会把 715 的 clip 播在 1911 上）。
- 门槛注释更新：没有 clip 的手枪仍明确拒绝（该原则保留，只是 1911 不再是例子）。

## 未做

未实机测试、渲染或验收，由用户测试（重点：1911 砸击动作观感、接触时刻命中反馈、
与 715 的动作语言一致性）。制作脚本里的关键帧读数只用于作者源自检，不代表视觉/手感合格。
