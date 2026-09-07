# 怪物候选整理与发布 — 2026-09-07

## 发布内容
- 原有普通、矿工、奔跑僵尸三款换皮和出生时随机选原皮/新皮；实例材质隔离，模型与动作不变。
- 后倒死亡 V02 的最终模型、编辑源和直接输入；脓液 V03 独立演示、地形拟合及伤害检查。
- 三类僵尸及三款换皮的色彩增强候选：最终贴图、前后对照及可重建 GLB 的脚本。
- 怪物 SKILL 新增材质变体、后倒与地形脓液两份案例；个人技能与项目副本同步补充。

后倒、脓液、增强色彩仍为独立候选，发布归档不等于正式游戏切换。原换皮随机接入已获先前授权。

## 清理
已删除本会话明确否决的融化 V01/V02、马甲短裤发型、毒液与胖子灰化候选，以及保留成果中的可再生成逐帧图与 .blend1。共 26 个明确目标，534828902 字节。最终来源、可编辑源、有效 GLB、许可和预览保留；后倒构建依赖的 motion V01 保留。

四个 E:/3d 临时预览工程删除被自动审批拒绝，未执行：deathcow-melting-preview-20260907、deathcow-melting-preview-v02-20260907、monster-style-unification-preview-20260907、ordinary-zombie-outfit-preview-20260907。不会自动重试或扩展删除范围。详细本地清单：E:/无尽轮回/3d/monster-publication-20260907/cleanup.json。

## 验证
- 从六张增强贴图重建 GLB，通过几何、骨架、动画及原始二进制保留断言。
- 随机换皮测试 52 个 PASS，完成标记 failures=0；固定选择、材质隔离、重复 setup、副本脚本替换均覆盖。
- 脓液 test.gd 完成：生成一次、阵营、出入、高度、低帧率间隔、消退、随机外形。
- 装填测试自动装填与 R 装填均 ok=true。
- 执行完整 editor import、180 帧冒烟和通用战斗测试。基线已有 3 张 ammo 图标缺失，proj_hit_damage=false，导入/通用战斗退出有资源清理告警。移除本次换皮钩子复跑，图标缺失和 proj_hit_damage=false 相同；不记为整体全绿，不修改无关 UI/战斗实现。
- SKILL quick_validate 通过（Windows 使用 Python -X utf8）。

## 发布隔离
从 origin/main 建立独立发布工作区 E:/3d/publish-monster-materials-20260907。共享 master 含其他未发布历史和大量未提交内容，不整体推送、不重置、不代提交。只暂存本次文件，普通非强制推送 main，远端回读提交号。
- 发布工作区复跑六地形默认 D3D12 渲染：最大间隙 0.0100–0.0138 米，穿地 0，missed_contacts 0；terrain-error.log 为空。
