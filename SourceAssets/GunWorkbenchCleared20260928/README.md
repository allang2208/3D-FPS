# 枪械工作台：移除被否决的小件，恢复原版台灯

后续用户已要求复用库内现成工具，当前活动版本见 `../GunWorkbenchLibraryTools20260928`。本版继续作为保留桌体、原版台灯和工作垫的制作输入。

2026-09-28 用户指出台灯应直接复制已有成品，否决新做桌面小件；随后明确选择“只留桌子、台灯和工作垫”。本版已导入并保存到原 `gun_workbench_table` 建造项。

## 已查明的事实

- 本次排查读取到建造目录实际引用 `GunWorkbenchPolish20260928/SM_GunWorkbench`，各材质也引用已保存的对应资源；并非只写导入脚本而未接入。
- 当时未运行 PIE，也没有可读取的枪械工作台实例。因此没有证明用户此前游戏中的具体实例是否已加载这版资源，不能据此断言不存在其他显示问题。
- 之前的脚本将原台灯及线缆分别减至 55% / 65% 后合并，并非原样复制。更早版本还重新展开了台灯 UV；这不符合直接复用的要求。
- 桌面工具为本次新建的简化几何，用户已否决其质量。提高纹理分辨率或增加表面细节不能替代合格造型；本轮不再重新设计这些小件。

## 当前结果

- 游戏资产：`/Game/Building/GunWorkbenchCleared20260928/SM_GunWorkbench`。
- 只保留原桌体、工作垫（含边线刻度）、原版台灯及其配套线缆。
- 删除工作台上的两只零件盘、三支冲子、螺丝刀、软面锤、六批头座、油瓶等新做小件，同时移除加工过的灯模型。
- 原台灯取自 `DungeonWorkbenchKit20260921` 已有独立对象：灯体原网格 56,222 面，线缆原网格 7,416 面；只做摆放变换，不减面、不重建、不重展 UV。导入直接绑定原 WorkbenchKit 材质实例，不重做灯材质。
- 建造项 ID、占地与交互字段保持原合同。小游戏与双制造页面没有改动。
- `Authored/GunWorkbench_Editable.blend` 保留独立组件；FBX 按既有单网格建造宿主导出。原已否决版本作为制作历史与本轮输入保留，不再是活动建造目录引用。

制作入口：`Tools/GunWorkbench/restore_original_lamp.py -- --remove-clutter`（Blender 后台），`Tools/GunWorkbench/import_cleared_workbench.py`（现有 UE 桥接入）。

排查证据：`../GunWorkbenchLampRestore20260928/source-state.json`。本版保存回执：`import.json`、`import-01.txt`。未启动游戏或进行视觉验收。
