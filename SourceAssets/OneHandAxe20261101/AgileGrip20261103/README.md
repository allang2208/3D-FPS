# 破阵握柄与长柄特殊分类

**当前外观为中段镂空 V2。** 用户于 2026-11-03 要求参考新图改为中空框架，已制作长圆贯穿孔、银灰孔缘和连续双侧框架；名称、数值、长度、端面及柄尾/挂坠位置沿用既定配置。当前入口见 `HollowV2/README.md` 与保存后生成的 `active_model.json`；本页下方的 V1 Blend/纹理是新版的固定制作源，历史回执不代表新版接入状态。

斧头专属握柄，槽 `grip`，改造 ID `hatchet_grip_agile`。与既有 `hatchet_grip_long` 一起由 `GunsmithModificationTier.h` 的武器、槽位和 ID 组合归入特殊改造。原长柄 ID、属性和存档保持。

| 改造 | 造型 | 直接属性 |
| --- | --- | --- |
| 长柄握把 | 27.25 cm 加长柄、黑色棱纹握片、双窄金属带 | 攻击距离+25%、物理攻击+10%、体力消耗+10%、攻击速度-5% |
| 破阵握柄 | 19.25 cm 原长度、中段长圆镂空、连续侧框、碳纤维握片与银灰孔缘 | 体力消耗-25%、攻击速度+15%、重击蓄力速度+15%、武技冷却时间-20% |

两者都只列在战斧目录。破阵握柄原名轻捷握柄，保留旧 ID、特殊改造分类、模型及图标路径以兼容现有装备。2026-11-03 按用户最新指定属性改为上表四项，替换此前的穿甲、削韧与增耗属性；长柄原倍率不变。数值及名称以 `design.json` 为制作真源，当前版本为 `user_tempo_20261103`，游戏目录和两个当前模型清单同步更新。

结算复用现有属性：`stamina_mult=0.75`、`attack_speed_mult=1.15`、`heavy_charge_speed_bonus=0.15`、`martial_cooldown_mult=0.8`。仅该握柄生效时蓄力耗时除以 1.15；武技冷却乘 0.8，作用于上挑、风车等独立冷却，不缩短快速近战动作占用或冲刺就绪时长。双持沿用逐武器计算与组合动作合并规则。无需 C++ 修改、重新编译或模型重导入；本轮未运行测试或游戏。

## 制作入口

- `author_agile_grip.py`：转到 `HollowV2/author_hollow.py`，保留原装端面和外侧接触轮廓，制作中段贯穿孔、内壁和倒角，导出 FBX 与 2K BaseColor/Normal/ORM。
- `HollowV2/TacticalHatchet_GripAgile_HollowV2_Editable.blend`：当前可编辑源；父目录的 V1 Blend 和旧纹理保留为固定制作输入。
- `render_icon_input.py`：实际新模型的改造图标素材制作，灰阶，水平安装端朝左。
- `HollowV2/icon_prompt.txt` / `HollowV2/icon_manifest.json`：当前内置 imagegen 金属框图生成输入与来源。
- `import_agile_grip.py` / `run_import.ps1`：后台串行导入并保存新网格、材质、三张贴图和 UI 图标，仅操作新增命名包。
- `register_agile_grip.py`：保存完成后合并目录，仅更新本选项及模型配方。

破阵握柄 `pommel_offset_cm=[0,0,0]`，复用原装柄尾位置与已接入的穿孔挂坠配方。切换至长柄时仍由其原有 `-8 cm` 偏移带动柄尾和挂坠。

初版分类构建与资产保存见原构建日志和导入回执。此前破甲／削韧方案的检查、修订与构建记录保存在 `BalanceV2/`；其中数值以及 `HollowV2/delivery.json` 的数值是当时快照，当前属性以 `design.json` 和游戏目录为准，不覆盖历史回执。
