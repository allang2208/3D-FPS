# 登山包背带当前入口

范围：Jason 的 ue_mountain_backpack，六种身体／服装配置。当前版本 `UEFrontFaceR6_20261022`，说明与剩余项见 `Docs/Characters/backpack-harness-rebuild-20261020.md`。

R6 修正此前遗漏的导出约定：作者 JSON 使用 NumPy／Blender 的 `cross(e1,e2)`，UE 使用 `cross(e2,e1)`。所有包体、背带和扣具经 `winding.py` 重排三角形及对应 UV／法线面角后才能交给 UE，不能直接把作者面序写入引擎。法线向量及坐标不取反。保存器还修正减面后局部反向的法线。用户要求排查时，由 `read_facing_reference.py` 读取 UE 内置 Cube 的 RenderData 作为基准，`check_front_faces.py` 核对真实绘制正面及侧向首命中；`validate.py` 只是作者空间检查，不证明 UE 可见性。R6 证据在 `FacingRepair20261022/`。

以下为历史：R5 处理了接缝开裂，但未解决正反面剔除；R4 关于原始面序朝内的判断错误。其 NumPy 正体积判定不适用于 UE 的朝外判断，已由 R6 的引擎基准替换。

R5 处理接缝开裂：保存器在刚性包体内部连接唯一匹配的重合边，保留 UV／法线覆盖层，再禁止接缝坍缩、分裂与平滑后制作 LOD1。包体与封口作为一个闭合拓扑参与减面；不能再把接缝两侧拆开独立减面。封口三角化禁止使用已有内部边，消除三处重复面。本次按用户排查要求使用 `inspect_render_mesh.py` 读取实际 `RenderData`，由 `check_side_shell.py` 对六套 × 两级 LOD 检查闭合性。记录在 `SideRepair20261022/`；普通制作不因此自动触发检查。

R4 恢复包体误裁；其朝内绕向判断已撤回。`bag_shell.py` 按完整源岛清除旧肩带残片，恢复上壁与翻盖，并跨 UV 接缝追踪六处拆带边界、封口。`repair_shell_sources.py` 只替换六份现有源的包体部分，保留 R3 背带位置、蒙皮和服装偏移；普通完整重做仍由 `author.py` 调用同一包体配方。R4 制作、输入及保存回执放在 `ShellRepair20261022/`。旧检查与预览仅代表 R3，不作为 R4 的通过依据。

作者源与回执在 `SourceAssets/BackpackHarnessRebuild20261020/`；Inputs 是本次从 UE 读取的源快照。更新服装后需要明确重新读取和重做，不能把旧快照当成当前数据。

R3 已修正胸前腹部 U 形，毛衣槽输入已更新为 FieldRangerTop。需要定向刷新衣物时，`inspect_job.json` 使用 `{"phase":"refresh","keys":["ue_field_sweater"]}`；读取衣物和原生绑定后重做受影响变体，再更新源检查与保存回执。`phase=after` 只负责已保存背包的读回。

1. `author.py` 生成六套 JSON，`textures.py` 生成织物贴图。
2. 仅用户要求检查时运行 `validate.py` 与 `pose_checks.py`。保存器按作者 manifest 中的源散列导入，不强制触发检查。仅改变外部文件不等于 UE 已接入。
3. 用项目共享后台 `run_ue.ps1 -Script .../save.py` 保存资产；现有编辑器存在时沿用互斥桥。
4. `publish.py` 按字段写共享配置；不提交 Git，不启动游戏。
5. 用户要求资源核对时设置 `inspect_job.json` 为 `{"phase":"after"}`，后台运行 `inspect_ue.py`，再运行 `check_readback.py`。

旧制作器、共享脚本修改前副本和本轮失败试验均已移入 `trash/backpack-rejected-20261020-full-audit/`，仅用于恢复与问题追溯。旧肩罩、侧带、模板优化报告均被用户否定。旧 `Before/Content` 回退包现位于 `trash/backpack-retired-20261023/` 的对应原路径；当前作者输入和有效检查证据仍保留。
