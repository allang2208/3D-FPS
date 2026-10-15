# 锻钢战锤：原装六件与改造槽

当前改造栏已按后续要求将「锤颈套箍」替换为「符文」，套箍实体保留为固定连接结构，见 [符文槽调整](warhammer-rune-slot-20261014.md)。本轮再移除「金属长柄」改造栏，长柄保持固定实体；当前五栏为双侧锤头、中央锤座、符文、握持包覆、柄尾配重。锤头与中央锤座已有通用改件及数值；握持包覆三款方案见 [通用包覆设计](common-hammer-grips-design-20261014.md)。下文保留初次拆分记录。

用户确定本轮只拆原装六件并接入改造槽；新外形、新属性留待后续确定。武器 ID 仍为 `ue_steel_warhammer`，当前 V7 裸手、三连击、重击、冲刺动作及伤害、距离、体力等数值沿用现有实现。

| 改造槽 | ID | 实体范围 |
| --- | --- | --- |
| 双侧锤头 | `hammer_heads` | 左右击打头及收颈连臂作为一个成对模块 |
| 中央锤座 | `head_mount` | 中央方形座、正背饰板和顶部固定帽；装配根组件 |
| 锤颈套箍 | `neck` | 中央锤座下方铆接套箍 |
| 金属长柄 | `shaft` | 套箍至握持包覆之间的金属杆 |
| 握持包覆 | `grip` | 下段螺旋缠裹与上下收口，保留当前握持外轮廓 |
| 柄尾配重 | `pommel` | 柄尾金属收束与圆钝配重 |

每栏目前只有原装件。沿用 `false`／空选择表示原厂、模型目录 `factory` 表示原厂网格的现有合同；没有增加虚构的拆除项或数值改件。原装六件已装配时没有待应用差异，应用按钮沿用原有禁用状态。

## 制作源与接口

源模型来自 `SourceAssets/SteelWarhammer20261014/SprintDragV1/RigSource/SteelWarhammer_Editable.blend`，只读取战锤对象，不重导手臂与动画。拆分源、FBX、接口边界、图标源及脚本保存在 `SourceAssets/SteelWarhammer20261014/ModulesV1/`。

统一作者坐标为米，长柄轴 +Z，锤头横向 X；沿原三角面切割并插值面角 UV 和法线，仅封新增安装切口。柄尾接口 Z=-0.085，包覆上端 Z=0.405，长柄上端 Z=0.820，套箍上端 Z=0.865；中央座与双侧件接口 X=±0.040。全部接口是本战锤的尺寸，不是通用武器常量。`interfaces.json` 保存实际边界线段及各件原点，后续新件应复制这些安装端。

`head_mount` 保留整把武器的规范原点，其余件相对各自安装原点导出，在目录中只补一次位移。双侧锤头是一个包含两端的静态网格。包覆模块保留原握持段外表面，不新增整根可见长柄与之重叠。

## 接入路径

- `Content/ColdSteelData/warhammer-gunsmith.json`：六栏名称、原装件与说明；由 `WarhammerGunsmith.cpp` 注册为独立双手钝器改造目录，不继承剑的护手、符文或采集工具强化选项。
- `Content/ColdSteelData/warhammer-modules.json`：六件装配、实际 UE 网格、接口版本和从原始已导入模型推导的 `WPN_root` 安装变换。
- `ModularSwordVisual` 共用装配入口追加可声明的 `module_slots`／`root_slot`，既有剑仍默认原四个实体槽。战锤按定义 ID 解析目录，因此旧物品实例无需换新；改造仍存入 `gunsmith_parts`。
- `ProductionToolComponent` 异步预加载六件，挂到当前活动视模的 `WPN_root`，仅隐藏原整锤材质分区。手臂网格及已修正掌面保持原资产；切武器清理模块，显示状态向模块传递。
- 改造台草稿、物品图标及掉落物沿用同一装配函数；第三人称装备捕获沿用子件和骨骼挂点，并同步隐藏原整锤分区。
- 战锤总览读取现有钝器执行器数据，只列直接属性，不套用剑的格挡、突刺或采集数据。
- 六个图标由实际模块制作，灰阶 PBR、倒角钢框、四角铆钉和银色内环；分类和原装选项共用图，PNG 与 UE 纹理一并落盘。

`author_modules.py` 制作六件与可编辑源；`author_icons.py` 制作 UI 图标；`import_modules.py` 导入并保存资产，再由参数化 `FrostSwordModuleAuthoring` 作者 commandlet 从原始静态／骨骼网格的同源 UV 顶点推导安装变换并输出正式目录。重做原装模块时只更新 `factory`，保留后续目录中已有的新件条目。

本轮不执行游戏、截图、回归或验收。资产保存与必要构建结果见同目录回执；运行效果由用户测试。

## 本轮落盘结果

- 六个静态网格、六组分类／原装图标的 12 个纹理资产已保存，导入 commandlet 返回 0，`import_receipt.json` 为 `complete=true`。
- 独立作者工程 `ModulesV1/AuthorHost/WarhammerModuleAuthor.uproject` 构建成功。`prepare_author_host.py` 从共用作者 commandlet 生成最小宿主，避免链接正在开发的其他玩法源码；只读取正式模型并写入明确指定的目录文件。
- 挂载制作 commandlet 返回 0，使用 77,824 个同源 UV 顶点对生成 `warhammer-modules.json`；挂载比例为 0.01，用于抵消现有骨架的 100 倍尺度，不改变武器尺寸。详见 `mount_receipt.json`、`mount_authoring.txt`。
- 完整 FPSGAME 构建本轮未通过：第一次 Game 构建遇到并行更新中的战锤动作／树冠代码；随后 Editor 构建仍受 `RootCrownRootField.cpp` 的 `Instigator` 重名与 `SpellbookBookSampling.h` 访问受保护 `UAnimSequence::IsCompiling()` 阻塞。保留这些并行文件。本轮作者命令的编译问题已修正，并由独立作者工程成功构建。
- 因此当前交付是已保存六件资产、正式装配数据和改造系统源码；不能把独立作者工程的成功称为正式 Editor／Game 二进制已经更新。完整工程完成编译后再由用户运行体验。
