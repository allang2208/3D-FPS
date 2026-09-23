# SVD 战术冲刺与快速近战（2026-09-23）

按用户要求读取枪械与第一人称手臂 Skill 后，替换此前仅整体搬运枪和双臂的四段占位动作。复用项目已留存的步枪战术冲刺方法、M4 N 枪托挥击节奏，以及 QBZ191 O 的本枪握点锁定／腕臂支撑方法；没有引入新的外部素材。

## 动作

- `sprint_enter`：0.4 秒，左手先松开护木并向外下方撤离，右手保持 SVD 后握把接触、抬枪至接近直立。
- `sprint_loop`：1 秒相位周期，右手持枪，左臂放松摆动；运行时仍由现有脚步相位驱动。
- `sprint_exit`：0.4 秒，沿进入路径反向回握。运行组件沿同一进入曲线反向采样，可中途取消；武器动作打断仍采用既有 0.16 秒退出表现与冲刺转开火约束。
- `quick_melee`：0.9 秒，接触时刻 1/6 秒。按 SVD 的待机握点与枪托锚点重新拟合挥击路径，解算肩、肘、腕及扭转骨，保留双手与枪的接触关系；在恢复段交还本枪待机。

四段均为 120 Hz。共享 Manny 骨架、枪械网格、UV 修复、材质及其余八段动作保留。本轮没有更改移动速度、伤害、技能冷却、修炼、音效或输入绑定。

## 源与运行接入

- `../tactical_actions.py`：动作制作模块，供整枪制作和本轮局部重制共用。
- `author.py`：从当前已修复 UV 的 `../SVD_Complete_Editable.blend` 仅更新这四段动作，输出到 `../Exports/A_SVD_*.fbx` 并保存同一可编辑 Blend。
- `../author_svd.py`：整枪重制入口已改为调用新动作模块，避免重做时退回占位动作。
- `authoring.json`：本次作者参数、源时长、握点约束、枪托锚点与解算记录，属于制作记录，非验收报告。
- `import_actions.py` / `import_background.ps1`：只导入这四个动画包；后台入口使用项目现有批次互斥，已有编辑器运行时拒绝另开资产写入进程。
- `Before/`：本轮修改前的局部备份；不得整目录覆盖并行工作区。

实际保存目录保持 `/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations`，四个资源名仍为 `A_SVD_sprint_enter`、`A_SVD_sprint_loop`、`A_SVD_sprint_exit`、`A_SVD_quick_melee`。现有 `SVDWeaponAssets`、`M4TacticalSprintComponent` 和 `RifleQuickCombatClip` 已加载这些路径，因此无需改 C++ 或额外构建。

制作命令：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python 'D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/TacticalActions/author.py'
& 'D:/FPS3D/FPSGAME/SourceAssets/SVDCompletion20260923/TacticalActions/import_background.ps1'
```

## 已完成与边界

Blender 已导出四个 FBX 并保存可编辑源；UE 后台导入返回退出码 0，四段均导入并保存，日志包含 `SVD_TACTICAL_IMPORT_COMPLETE 4`。逐项保存回执见 `import.json`，制作日志见 `author.log`，导入日志见 `import.log`。

按用户规则未打开交互编辑器、未启动游戏、未运行预览／截图／动作或战斗测试。实际手感、屏幕遮挡、接触和过渡由用户测试；保存成功不等于实机验收通过。
