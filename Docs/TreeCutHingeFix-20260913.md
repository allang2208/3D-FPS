# 树桩断面与切口倾倒修复

本次修复对应两个反馈：地面树桩横截面没有正确显示木纹，以及整棵树先倒下、随后才露出树桩。运行时现改为在砍断这一刻显示原树下段树桩，移除站立树，仅让实际切开的上半段绕切口前缘倾倒。

## 断面与模型

- 四种原树主干分别在局部 Z=42 cm 处切成 `SM_CutStump_A/B/C/D` 和上半段，上下段采用同一源模型和切平面。上半段写入 `SK_CutUpper_A/B/C/D`，保留原树骨架及 Nanite 叶片组合数据。根部外形、树皮与叶片 UV、源法线保留；上下断口分别封面。
- 原树桩封面只写入一个 UV 层，其他继承层的断面 UV 退化。现在所有继承 UV 层的封面都写入平面投影坐标，材质明确使用 UV0。地面树桩使用不透明 `M_TreeCutSurface`，上半段断面使用支持消隐的 `M_FallingCutEnd`，共同取用已有年轮纹理 `T_PoplarEndReference`。
- 原树的叶片属于 Nanite 组合子节点，普通主干 FBX 不包含完整树冠。制作时保留原始材质表，运行时资产则复制原树的骨架与组合配置，仅替换截断的主干源几何。树皮、叶片、断面的材质槽分别对应 0、1、2，原叶片子节点的材质映射保持有效。
- 上半段包含真实封闭断口，不再依赖整树材质遮罩裁掉根部，也不再另挂一个圆片补底。

## 倾倒时序与成本

砍断成功的同一次游戏线程操作中，先根据已采集记录刷新树桩，再移除站立树并生成上半段。无需等待原先 0.2 秒的刷新周期或树倒完。

`DA_TreeCut_A/B/C/D` 保存导入后 UE 厘米坐标下的真实切口轮廓。按倾倒方向选取轮廓前缘作为支点，更新旋转时同时修正模型原点，使切口前缘保持原位、背缘抬起。地形接触估计与掉落时序沿用同一倾倒计划。

第一斧开始异步预加载对应树形，砍断提交前要求资源就绪；生成组件持有网格后释放预加载句柄。上半段启用 Nanite，并保留冠部惯性和落地回弹。没有增加运行时切网格或整树刚体模拟。树桩继续使用四组静态实例，附近 64 米内最多显示最近 64 个；本次没有性能实测。

树木资源 ID、采集次数和掉落存档格式沿用原有结构。上一次修复的三款实心可拾取短原木不受本次修改影响。

## 本机资源与交付范围

- 作者脚本：`SourceAssets/HarvestTimber20260913/export_tree_sections.py`、`cut_tree_sections.py`、`import_tree_sections.py`、`build_falling_assemblies.py`。
- 可编辑源：`SourceAssets/HarvestTimber20260913/FellingCut/MatchedTreeSections.blend`。
- 生产 FBX 与元数据：同目录 `Delivery`；引擎导入记录：`FellingCut/import.json`、`FellingCut/assemblies.json`。可编辑 Blend 保存主干切割几何，完整树冠依赖 UE 原树的组合子资产。
- 本机资源路径：`/Game/Items/HarvestTimber/SM_CutStump_*`、`SK_CutUpper_*`、`DA_TreeCut_*`、`M_TreeCutSurface`、`M_FallingCutEnd`、`M_CutUpperMotion`、`MI_CutUpper_*`。`SM_CutUpper_*` 仅作为主干导入中间资源。

原生 Editor 构建已完成，见 `Saved/Logs/TreeCutAssembly-Build-console.log`。主干/树桩导入记录为 `Saved/Logs/MatchedTreeSections-ImportFinal.log`，上半段组合资源制作记录为 `Saved/Logs/CutTreeAssemblies-Import.log`（A）和 `Saved/Logs/CutTreeAssemblies-ImportBCD.log`（B/C/D）。资源导入记录以脚本的完成标记和保存结果为准；项目现有 GameFeatureData 配置错误会使整个 commandlet 返回非零，不应写成整项目检查通过。

按用户规则未启动 PIE、渲染、回归或性能测试；重启 UE 加载新原生模块及资源后由用户测试。上述制作与构建完成不代表游戏效果已经验收。

本次没有购买资产或调用新的模型生成。原树衍生二进制遵守原资产许可，保留在本机；源码发布包含实现、作者脚本与说明。
