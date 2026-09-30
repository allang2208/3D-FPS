# 201 主体接口与涂层整理：FitFinish37

2026-09-29，接续 [主体/盖体审计](../../../Docs/Weapons/lmg201-body-cover-audit-20260929.md) 后获用户授权制作。已后台导入、编译和保存；未运行游戏、开盖动作测试或视觉验收。详见 [制作记录](../../../Docs/Weapons/lmg201-fit-finish-20260929.md)。

## 当前产物

- 可编辑源：`LMG201_FitFinish37_Editable.blend`，保留独立枪身零件和原生骨架。
- 局部替换源：`Exports/SK_LMG201_F37_BodyParts.fbx`。
- 已保存完整装配导出：`Exports/SK_LMG201_F37_Installed.fbx`，含当前原生手臂、供弹分件与本轮枪身。
- 运行主体仍为 `/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10`，另有完整候选副本 `/Game/Weapons/LMG201/FitFinish37/SK_LMG201_F37_Installed`。
- 9 类主体材质：`/Game/Weapons/LMG201/FitFinish37/Materials/`；38 个旧件/配件材质接口的私有适配：`FitFinish37/Adapted/`。
- 天气表仍为 `/Game/Weapons/LMG201/Accessories22/DA_LMG201_AttachmentWetMaterials`。
- 当前绑定：本目录 `bindings.json` 及上级 `Material21/bindings.json`。

## 作者入口与依赖

1. `model.py` 用 Blender 后台制作盖壳、机匣上肩/开口、护木后安装端与导气接头，烘焙盖体自己的 Normal/AO，保存 Blend/FBX。依赖 Surface32 可编辑源、Detail35 局部顶点、Repair36 盖内细节；不使用首轮废案枪壳。
2. `materials.py` 创建本枪私有主体材质，适配旧件/配件涂层并保留源分区和实例覆盖。新主体细纹复用 `Material21/FineRoughness.hlsl` 及本枪纹理，不改结构 Normal。
3. `install.py` 备份后按原槽身份替换枪身几何，保留当前原生骨架、手臂、动作、弹匣、布袋与机关件，保存到当前路径；同步静态分件、材质绑定表和天气表，导出完整装配。
4. `run_background.ps1` 是互斥后台入口，默认运行 `integrate.py`；有 UE 进程时保留现场而不覆盖。`finish_surface.py` 只补充/保存主体细纹配方，不重导几何。

入口带制作回执续跑逻辑，已保存几何不再次覆盖，已适配材质不重复套层。再次修改源几何/历史材质时，需要显式开启对应的制作修订；不能只重跑旧入口就声称新内容已重导。

## 恢复与完成边界

`delivery.json` 记录实际保存的 31 个网格、天气表、保存后散列、修改前私有副本及原始字节路径。UE 备份在 `FitFinish37/Previous/`，原始字节在 `Before/`；恢复应针对清单中的具体资产完成，不批量清理现用资源。

`model.json` 记录源制作；`materials.json` 记录完整材质图编译/保存；`production_console.log` 与 `finish_surface_console.log` 是后台制作日志。完整图调用 `recompile_material` 后无返回编译错误并保存。重建现有图期间的临时断线即时重编译提示，与最终完整图结果分别对待。

本轮未改动画轨道、未替换原生骨架，未启动 UE GUI、游戏或验收渲染。外观、实际开盖帧及干湿表现由用户测试。全部坐标和配方只属于此游戏模型，不作为其他枪型标准。
# 用户否决状态（2026-09-29）

此版机匣/盖体存在横向尖刺、错误外形和镂空，已被用户否决。不要重新运行本目录的几何制作或安装脚本覆盖当前枪体。源码保留用于追溯；后续修正见 `../ReferenceRepair38/README.md`。现有涂层资产仍被后续版本引用，不能整目录删除。
