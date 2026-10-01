# G18 镭射与手电挂位前移

用户反馈镭射靠近扳机，要求同步调整镭射和手电。两件配件均已通过后台 commandlet 重导入、保存到原有 G18 资源路径，未打开交互编辑器或启动游戏测试。

原配件尾部在枪根制作坐标 Y=-54 mm，扳机护圈下段前缘约为 Y=-63.117 mm，二者沿枪身方向重叠约 9.1 mm。本次保持原尺寸与高度，将两件配件沿枪口方向统一前移 25 mm，尾部改为 Y=-79 mm，与护圈前缘沿枪身方向相距约 15.9 mm。这些数值来自制作几何，不是实机验收结论。

原夹座来自 M1911。前移后，使用 G18 实际导轨底面重新取形，只修整夹座上接触面及邻近倒角，底部与配件壳体的原接触位置随主体平移。接触面嵌入导轨 0.15 mm；主体、镜片、UV0 和材质绑定保留，夹座 UV1 按现有物理尺寸重投影。

`Emitter` 和 `AimGuide` 与主体同步前移。导入时显式写回 UE 的插座位置，避免重导入保留旧插座坐标。运行时继续通过既有配件装配入口与这些插座获取镭射／手电起点，本次未增加 C++ 挂位补偿或重新编译。

## 落盘内容

- 网格：`/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_laser`、`SM_G18_flashlight`。
- 两张选项图标：`ue_g18_tactical_laser`、`ue_g18_tactical_flashlight`，同时更新目录 PNG 和 UE 纹理。
- 制作目录：`SourceAssets/G18TacticalFit20260930`；`author_fit.py`、`author_icons.py`、`import_fit.py` 可按顺序重建本次输出。
- 可编辑源与 FBX：同目录 `Exports/`；替换前 UE 网格包保存在 `BeforePackages/`。
- 完成记录：`import_receipt.json`，状态 `tactical_fit_imported_and_saved`；后台导入进程退出码 0。
- 原接入目录的配件清单与图标几何只更新 laser／flashlight 两项，保留先前扩容弹匣与瞄具修复源指向。

导入日志仍提示两个源网格部分切线／副法线近零，未将资产保存结果表述为视觉验收通过。未进行自测、截图或验收渲染，由用户在游戏中测试。
