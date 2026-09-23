# 怪物动作选源、迁移与废案整理

适用：把已有 Godot 或第三方人形动作迁移到 UE 怪物，替换某几个动作，并整理被替代的制作文件。2026-09-15 的 Godot 跑步是历史方案，已被 Khaimera 狂奔路线替代；现行案例与用户认可边界见 [狂奔人形与飞扑](feral-humanoid-pounce.md)。默认由用户测试，不因本参考启动游戏或渲染。

## 从实际运行引用找动作

- 沿场景模型、继承脚本、AnimationPlayer/AnimationTree 别名和播放时钟找实际片段。通用脚本里同名的僵尸动作可能只是备用实现，不能代替该实例的真实引用。
- 记录周期、循环、参考速度、实际移动速度、左右差异、重心与支撑/腾空。按用户指定范围查看源动作；不凭 Run、Hit、Zombie 等名称判断姿态适用。
- 突变体案例：旧 Godot `runner_zombie.tscn` → `runner_zombie_v02.glb`，控制器继承 humanoid_variant_zombie → modern_zombie → ordinary_zombie。正式 `Walk` 是 Denys Almaral 的 `running_58f`，不是备用 `zombie_anim.gd` 的 Quaternius `Run_Arms`。原周期 58/30 s，速度时钟参考 2.357897 m/s；旧宿主现位于 `E:/3d/trash/repository-ue5-root-20260910`。

## 源动作身份与许可

- 普通 Jog 加一点僵尸上身不等于发狂丧尸狂奔。本例这条适配已被用户否定，后续必须更换符合意图的源动作，不能只加速或反复微调同一个失败方案。
- 站立受击读取反应峰值、保持点及恢复段。Hit_Knockback 在本例会双脚离地、躺倒，已改用 Hit_Chest；倒地动作不能仅裁剪时长就声称适合站立硬直。
- GitHub 托管不自动代表免费可用。记录动作原作者、原许可、源文件/版本、改动及模型独立授权；免费样包是否含目标片段需按实际文件判断。Hyper Chase 商业产品名不能被解释为已下载样包含 Hyper Chase；未采用候选不能称已接入。
- 历史 Running / RunFast 来源是 Denys Almaral，CC BY 4.0，交付/发行保留作者、链接、许可及改动说明；Mesh2Motion CC0 只覆盖对应动作，不覆盖 Denys 动作或用户 Meshy 模型。署名入口见本仓库 `SourceAssets/Mutant3Meshy20260915/godot_runner/README.md`。

## 迁移与局部替换

- 每副源骨架建立匹配的 IK Rig / Retargeter，明确参考姿态、父链与骨名归一化；不把 M2M 的源骨链直接套到 Godot 导出骨架。保留目标原蒙皮与物理。
- 原地动画由角色移动系统负责世界位移；播放时钟按角色实际速度和片段参考速度对应。源速度、目标腿长与烘焙时长一起换算；不能靠提高最大追击速度补救跑姿。
- 保留原有腾空，仅修正实际穿地；循环接缝不应把整段强行锁在地面。突变体参考腿长比 0.987144，Running 1.875 s / 240 cm/s、RunFast 1.25 s / 360 cm/s，120 FPS；这些是案例参数，不是所有怪物通用值。
- 只替换用户选定的角色动作。此次 Running / RunFast 更新保留 Hit_Chest、其他动画与玩法；受击 0.9 s、攻击接触、弹反倒放和死亡转物理仍由原合同决定。导入记录、用户认可和游戏测试分别记录。

## 混合制作包的整理

1. 先列出当前编辑源、脚本输入、已安装动画与保留动作。旧分支同时含废案和有效动作时，先提取有效输入；不要把目录日期、revision 或 candidate 字样直接当成废弃依据。
2. 当前脚本不应依赖 trash。突变体将当前完整 Blend 同目录复制为固定 `Mutant3_Meshy_CombatBase.blend`，跑步脚本改读该文件；将有效 Hit_Chest 源/重定向/最终 FBX 保留在 `godot_runner/combat_base/`，再归档整个旧 revision2。
3. 被替代的成品、旧包备份和未选用研究素材移到 `trash/<task>/`，保留原路径、目标、字节数、SHA-256、原因和替代入口。移前校验范围，移后读回散列。原始授权素材、有效编辑源和独立物理/材质输入仍是重建依赖。
4. 同步当前 README、合同/恢复入口和个人技能镜像。历史记录不伪改成当前结果；Git 发布文本与移除清单，二进制、缓存及 trash 按仓库规则保留本机。完整恢复需要资产备份，Git 克隆不等于恢复 UE 内容。

本例归档与发布入口：`Docs/mutant3-animation-publication-20260919.md`、`Docs/AssetArchives/mutant3-animation-20260919.json`。只做用户授权的仓库归档/推送检查，未追加游戏测试。
