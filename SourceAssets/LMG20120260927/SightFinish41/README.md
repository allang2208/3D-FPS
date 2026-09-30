# 201 SightFinish41

2026-09-29，根据用户的 ADS 遮挡和扳机脱接截图继续修订，并以项目当前 QBZ191 材质为参考调整 201。

- 编辑源：`LMG201_SightFinish41.blend`；作者脚本：`model.py`。
- 制作输入：`capture.json`、`pose_inputs.json`、`interfaces.json`、`finish_targets.json`、`material_inputs.json`。
- 材质：`materials.py`、`materials.json`。以 191 当前机匣材质及其本地源贴图有效金属区域取样，只使用数值和分层方法，不把 191 枪身图集套到 201。
- 后台接入：`run_background.ps1 -taskScript materials.py -taskLog materials`，随后 `run_background.ps1 -taskScript install.py -taskLog install`。脚本取得同一 MCP 互斥，存在 UE 进程时保留该进程并停止启动 commandlet。
- 实际保存：`delivery.json`、`bindings.json`、`Exports/After_Body.fbx`、`Exports/After_RearSight.fbx`。修改前文件保留在 `Before`；运行入口仍是 Cover10 枪体及 Production20260927 后照门。
- 用户所要求的接合/视线排查：`read_interfaces.py`，输出 `saved_interfaces.json`；只读保存导出几何，不启动游戏或生成验收渲染。

几何依赖 Assembly40 的可编辑源和 helper、ReferenceRepair38 helper；源 UV0、骨架、动画、弹匣接口、盖壳轮廓沿用。触发器的源槽 `M_LMG201_Trigger_S41` 在导入时仍映射回运行槽 `M_LMG201_Trigger`。

已后台导入保存，不代表实机 ADS、换弹及材质外观验收。详见 `Docs/Weapons/lmg201-sight-finish-20260929.md`。
