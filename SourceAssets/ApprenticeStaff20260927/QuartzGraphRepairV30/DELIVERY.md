# 杖头水晶棋盘格修复

2026-09-28。用户反馈 V29 透明度恢复后，游戏中的水晶呈现马赛克。

原因：当前 UE 的 `UMaterialEditingLibrary::DeleteAllMaterialExpressions` 遍历表达式数组时调用删除函数，删除同时改变数组，导致旧节点残留。V22 重建脚本调用此接口后，世界材质中出现两个 `Thin Translucent Material Output`。编辑器日志明确报错：`The material can contain only one Thin Translucent Material node`，PCD3D_SM6 编译失败并改用默认材质。

修复：`QuartzAimV22/ue_quartz_material.py` 改为先取得节点列表快照，再逐个删除，随后重建完整材质图。保留 V29 恢复的透明度 `0.24–0.42` 和透光色 `(0.78, 0.84, 0.82)`；预览材质继续使用 Default Lit / Before DOF。

通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 的共享批次互斥，在已经运行的编辑器中执行 `repair_materials.py`，完成材质编译并保存两个现用包：

- 世界材质 `M_Staff_QuartzDenseV22`：20 个节点、2 个薄透明输出 → 14 个节点、1 个薄透明输出。
- 工作台材质 `M_StaffQuartzPreviewV23`：17 个节点 → 12 个节点，薄透明输出保持 0 个。

两次 `recompile_material` 均返回空错误列表，保存成功。实际执行记录见 `editor-install-output.txt` 和 `install-receipt.json`；修复前原包保存在 `Before/`。

未启动或重启编辑器，未运行游戏、截图、渲染或追加测试。游戏内观感由用户测试。本次无需 C++ 编译或 Blender 重导出。
