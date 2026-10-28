# 山鸣弓弦

高地长弓 `bow_woodsteel` 专属传说弓弦，选项 `highland_mountain_echo`，槽位 `string`。
用户在设计图与效果提案后要求继续接入游戏；数值沿用 V12 提案。

## 数值与机制

- 拉弓速度 +15%，箭矢速度 +20%。单次射击体力消耗和持续拉弓耗体各 +25%。普通拉弓和穿心箭共用拉弓速度。
- 满弓箭命中活着的敌人，最多增加一层弦鸣；上限三层，持续十秒，再次获得时刷新。
- 三层时下一次满弓发射消耗全部层数；该箭不积攒层数。半弓不消耗、不积攒。
- 消耗层数的箭在原发射位置与方向延迟 0.18 秒补出弦影。弹速、重力、距离取原箭快照，仍有真实碰撞、遮挡和防御结算。
- 弦影只复制原箭出手物理伤害的 80%，保留原箭首次敌人命中的暴击结果及物理倍率。原箭尚未产生命中结果时，弦影不额外判定暴击。
- 不消耗额外箭矢或体力；不贯穿、不复制元素、照明、火甲、弹药附效、技能修炼，也不叠层或产生可拾取箭支。
- 服务器持有与当前装备实例绑定的临时层数，复制给客户端显示；卸下、切换和死亡清空，层数不写入存档。改造安装仍复用枪匠原有实例存档。

## 制作与引用

- `MountainEcho_String.blend` / `Export/SK_Highland_MountainEchoString.fbx`：厘米制可编辑源及正式四骨骼导出。三只驱动骨分别位于原生上弓梢、弦结点、下弓梢。
- `author_model.py`：交编银灰与石墨绳股、细金丝、柔性端环、短银套、护弦与三道山纹。
- `authoring.json`：几何数量、材质、接口坐标、来源。
- `import_assets.py`：在本任务独立 UE 目录生成并保存材质、骨骼、网格及距离 LOD；继承现有弓的金属和织物 PBR 纹理。图标通过标准 UI 纹理导入。
- `/Game/Weapons/WoodSteelLongbow20261026/MountainEchoV13`：正式资产目录。既有高地长弓 AlwaysCook 目录覆盖它。
- `bow_woodsteel_string_highland_mountain_echo.png`：imagegen 使用实际弓弦模型素材和认可金属框母版生成的正式图标；提示词和来源见 `icon-source.json`。实战材质保留金色细节，图标纹理饱和度归零。
- `apply_catalog.py` / `catalog-entry.json`：只更新这一个专属弦选项，不覆盖其他武器或改造数值。

## 状态

源模型、导出文件、正式图标、目录条目及 C++ 已落盘。最终 Game 和 Editor 目标均构建成功，结果分别在 `build-FPSGAME.json`、`build-FPSGAMEEditor.json`。
七份材质、一份骨架、一份包含距离 LOD 的弓弦骨骼网格及正式 UI 图标均已保存，`import-receipt.json` 已记录 `complete: true`；最终无界面导入进程退出码为 0。
用户确认保存并关闭当前 UE 后完成最后的 Editor DLL 链接；完成后没有重新打开编辑器。
未启动游戏，未进行运行、视觉或联机测试。模型与机制实际效果由用户测试。

## 后台入口

```powershell
# 在 D:/FPS3D/FPSGAME 下执行，两个入口均使用现有 UE 批次互斥。
& SourceAssets/WoodSteelLongbow20261026/run_stage.ps1 -Stage MountainEchoV13/import_assets -QueueWaitSeconds 3600
& SourceAssets/WoodSteelLongbow20261026/MountainEchoV13/build.ps1 -Targets FPSGAMEEditor
```

构建成功后保持编辑器关闭，不自动启动或运行游戏。
