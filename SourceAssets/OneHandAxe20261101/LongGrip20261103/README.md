# 战术单手斧专属：长柄握把

选项 ID：`hatchet_grip_long`；槽位：`grip`；宿主：`ue_tactical_hatchet`。作为本斧的本地专属选项加入握柄栏，保留公共握柄库。

| 属性 | 乘数 |
| --- | --- |
| 攻击距离 +25% | `range_mult: 1.25` |
| 物理攻击 +10% | `physical_damage_mult: 1.10` |
| 体力消耗 +10% | `stamina_mult: 1.10` |
| 攻击速度 -5% | `attack_speed_mult: 0.95` |

## 模型

深灰碳钢芯骨、黑色防滑握面，下段增加两道窄金属带和浅槽。基于已接受的斧头原装握柄制作，握柄从 19.25 cm 加长为 27.25 cm；连原装斧头和柄尾的整体长度约为 50 cm。

握柄安装原点仍为武器空间 Z=+11.5 cm。局部 Z≥-16.5 cm 的原有握持区及上接面不变，延长下段 8 cm，末端 5 mm 保持原截面和轮廓斜率，仅整体下移。采用原装面角 UV 和作者法线，形变法线按逆转置雅可比更新；重新展开 UV0 并烘焙 2048×2048 BaseColor、Normal、ORM。

`pommel_offset_cm=[0,0,-8]` 使用现有模块装配逻辑，将所选柄尾下移 8 cm。挂坠继续跟随 `parent_slot=pommel`，沿用上一轮修正过的穿孔结构。原有单手动作和手部握姿继续复用。攻击距离由既有属性系统计算，不更改基础武器条目或攻击公式。

## 文件与接入

- 可编辑模型：`TacticalHatchet_LongGrip_Editable.blend`，包括原装斧头、新握柄及下移后的原装柄尾装配。
- 引擎导出：`Export/SM_TacticalHatchet_GripLong.fbx`。
- PBR：`Textures/T_TacticalHatchet_GripLong_{BaseColor,Normal,ORM}.png`。
- 实际模型图标素材：`IconInputs/hatchet_grip_long.png`；最终专属图标见 `Icons/`，保留标准灰阶金属方框与内圆环。
- 生产入口：`author_long_grip.py`、`render_icon_input.py`、`run_import.ps1`、`register_long_grip.py`。
- `import_receipt.json` 记录实际保存结果；`registration_receipt.json` 记录模型配方与数值发布结果。导入脚本复用原装斧头材质与法线整理器，只写本次新增资产。

没有新增运行时代码，无需本轮原生编译。未运行游戏、自测、检查或验收渲染；图标渲染仅用于制作改造栏资产。由用户测试模型表现和动作配合。
