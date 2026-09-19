# M4 均衡后握把衔接修整

用户反馈 M4 改造中的均衡后握把与机匣仍有空隙，要求增加衔接件并统一材质。本轮只修改 M4 的 `balanced_reargrip` 外观。

## 制作内容

以 `RearGripFinish20260913/M4/balanced/ForwardFit/Editable.blend` 为作者源，保留上一轮握把主体前移 5 mm 的位置、原厂连接座、已有 UV、角点色和法线。没有改动属性、配件 ID、手部动作及其他枪型。

新增一体式上端过渡座：前段从现有连接座收口，后段沿机匣底部弧形凹面延伸，两侧向握把上沿过渡。上表面按 M4 机匣表面构造，下缘接入握把上部与翘尾；在机匣中预留 0.8 mm、握把中预留约 1.2 mm 的接合重叠，边缘倒角 0.25 mm。局部源坐标范围沿 Y 为 -24 mm 至 +35.5 mm，新增 5,070 三角面。

衔接件复用现有 M4 均衡握把的 Collar 材质，导入时从现用资源读取并继承主体和连接座绑定，不重建或修改共享材质。UV1 使用与现有 M4 涂层一致的 12×5 cm 投射尺度，颜色、粗糙度、金属反射和现有 Phong 转换一致；握持面继续保留聚合物材质。

## 文件与接入

- `M4_BalancedRearGrip_Seam_Editable.blend`：可编辑握把，另保留隐藏的独立衔接件与机匣参考。
- `SM_BalancedRearGrip.fbx`：UE 导入文件。
- `author_bridge.py`：衔接件制作与导出入口。
- `read_authoring_source.py`、`read_seam_profile.py`：为制作读取源坐标和连接面，不生成渲染。
- `import_bridge.py`：独立资源导入及继承当前 M4 材质绑定。
- `authoring.json`、`import_results.json`：作者参数和导入回执。

新网格：`/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914/SM_BalancedRearGrip`。`PhantomRearGripVisual.cpp` 仅将 M4 的均衡后握把切换到此路径；角色、改造展示、库存图标与掉落继续使用共同装配入口。旧资产保留，已有 RearGripFinish20260913 打包目录覆盖此修订。

## 状态

资源已导入并保存，进程退出 0，日志为 0 error(s)、0 warning(s)。复用现有纯资源导入宿主，参数包含 `-multiprocess -ddc=InstalledNoZenLocalFallback`，避免重复 SDK 探测等待其他任务的 UBT 全局锁。两槽材质绑定见 `import_results.json`。

用户保存并关闭编辑器、其他任务的导入与构建自然结束后，已通过 `Tools/Build/Build-Editor.ps1` 完成完整依赖构建，结果 `Succeeded`、退出 0。日志见 `build_editor.log`，引擎构建记录为 `Saved/BuildEditor/build-20260914-104644.log`。本轮未启动游戏、未生成预览或验收渲染、未执行测试，重新打开项目后的贴合外观由用户测试。
