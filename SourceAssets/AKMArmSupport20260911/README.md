# AKM 分握把腕肘支撑与全息连接座材质 — 2026-09-11

本次参考 M4 `AngledForegrip20260910/WristNatural/build_animation.py` 及棱镜握把 `PrismHandstop20260910/GripAnimation` 的双骨链、肘部弯曲平面和前臂扭转分配。AKM 两种握把分别测量，不照抄 M4 位移。保留已经接受的掌位、握把大小、原厂弹匣隐藏和直接回握时段。

## 整臂

- 短握把原腕轴折角约 6.98°，仅转动肘部弯曲平面，调整后约 0.06°；肩位和骨长不变。
- 斜握把原腕轴折角约 32.01°，调整肩带支撑与肘部平面后约 8.12°，肘弯由约 34.60° 到 69.21°。肩带相对本次旧 AKM 源偏移约 `(-.01189,.08514,-.01148)` 米，为原作者坐标，不是游戏摄像机偏移。
- 以上是骨架轴线指标，不是人体关节角验收值。实际同视角源模型和游戏腕背近景另行查看。
- 两种握把各九条：idle、aim、fire、aim_fire、equip、reload、reload_empty、drum_reload、drum_reload_empty。
- 肩肘支撑跟随既有握持权重；普通源帧270–330、空仓380–440回握，120Hz；取弹、装入、拉栓、右手与机械轨道、弹药和业务时长不变。

## 实际运行资产和作者入口

最终动画：`/Game/Weapons/AKMIntegration/SovietFab/ArmSupportFinalV2/{prism,angled}`。两份 M4 握把运行源码仅替换 AKM 分支路径。

1. `probe.py` 测量现有 AKM 接触/臂链并输出旧姿态图。
2. `build.py -- prism`、`build.py -- angled` 烘焙肩肘修正，输出全模型 `.blend` 和初步 `.fbx`。
3. `import.py` 导入初步 `ArmSupport` 动画及材质；`import_metal.py` 仅重建材质。
4. `preserve_runtime_digits.py` 把原正式资产**压缩完成后的**手指局部轨道合入最终动画。最终可编辑序列是上述 UE 资产；导出为各目录 `*_Runtime.fbx`。
5. `editable_runtime.py` 将最终 UE 导出保存为 `*_Runtime.blend`，是可编辑动画骨架；全模型肩肘作者文件和连接座作者文件分别保留。重新导入初步 FBX 后必须再次执行第4步，不能跳过。

验证中发现旧动画压缩数据的掌骨旋转与 RAW 不同；未完成异步压缩时，标为 COMPRESSED 的求值可能回落到 RAW，导致读回结果依赖加载时间。`AKMAnimationAuditLibrary` 明确完成压缩后再取样。前期未等待压缩的比较报告不作为验收；`verify-settled.log` 和 `ue_validation.json` 是最终18条逐帧比较，手腕、全部指尖、右手、枪根、弹匣最大位置差约0.00056cm。

## 全息镜连接座

旧 `AKM_AdapterSteel` 绑定 `SourceMatched/M_AKM_FabGunsteel`，与现款 SovietFab 枪体材质不同。现只替换全息镜连接座的材质槽和UV，瞄具本体/玻璃仍使用原正式材质。

- 新模型：`/Game/Weapons/AKMIntegration/SovietFab/ArmSupport/SM_AKM_optic`。
- 新材质：同目录 `M_AKM_Soviet_MountSteel`。
- 从已经合法导入的同款 Fab AKM 机匣金属区域提取 BaseColor、Metallic、Roughness、Normal；来源与裁切区域见 `Metal/provenance.json`。
- `prepare_metal.py` 提取金属贴图，`build_metal.py` 按实体尺寸重排连接座UV，保留顶点、面和挂点。OpenGL法线在UE翻转绿色通道。
- 源模型 `AKM_OpticMount_Editable.blend`；`SM_AKM_optic.fbx`；`metal_geometry.json`、`metal_import.json`。
- `mount_material.png` 是连接座与枪体材质的Blender检查图，瞄具本体在该源预览中是材质占位；正式视觉以游戏 `optic_mount_review.png` 为准。

## 运行检查

新进程使用独立 `ForegripAudit` 存档。`run.ps1 -Run akm-arm-prism-final` 和 `run.ps1 -Run akm-arm-angled-final -Angled` 检查18条加载映射、ADS、射击、装备、两种握把各四种换弹、直接回握、弹鼓脱手与原厂弹匣隐藏，并输出掌侧、腕背和全息连接座近景。`Delivery` 的视频来自相应运行画面和同次游戏混音，记录真实采样间隔。

测试入口添加 `-Multiprocess`：引擎会跳过启动时的 SDK 检查子构建，避免与并行项目的 Build.bat 锁排队；不改变动画和换弹时钟。

早期 `akm-support-angled-v1` 遇到数秒长帧，跳过抽出检测窗口，不作为最终验收；原生业务时钟未为审计而放慢。当前已打开的旧编辑器需重启加载新的原生引用。
