# 医疗区医生办公室与区域过渡房

用户要求：排水检修退出医疗三房组合，回到普通随机衔接房；医疗第一房替换为较大、较丰富的医生办公室，优先复用现有资产。

新模块 `MedicalDoctorOffice` 的面积约 611 平方米，包含 T 形候诊走廊、两间诊室、四席医生工作室、主任办公室及病例讨论桌、病历室和检查准备室。复用 HospitalCorridor 的长椅、宣传画与信息栏，员工生活区的桌椅、书柜、饮水和咖啡设备，隔离病房的病床、输液架、玻璃门，已有医院可搜索器械车与急救柜，以及此前医生办公室的病历桌面道具。新建房体、隔断、门框、顶面支架及中文导视；墙砖沿用已有破损瓷砖源。

正式医疗顺序：`MedicalDoctorOffice → AbandonedIsolationWard → AbandonedAnatomyTheatre`。每条双主题路线在两组三房之间增加一个随机设施房槽位，候选为 Distribution、Drainage、VentilationLoop；主题内部顺序仍固定。排水检修保留原有几何、道具和交互，解除医疗核心身份及固定朝向限制。过渡房跟随所在支路楼层，避免仅为了经过设施房就额外上下楼。

源文件：

- `author.py` / `Authored/MedicalOfficeWing.blend`：建筑、导视与 FBX。
- `layout.py` / `Config/module.json`：测量过原始资源包围盒后的摆放描述。
- `recipe.py`：只替换医疗首房和过渡规则，合并到最新目录。
- `bake_layouts.py`：离线制作 120 种主题配对的替代布局数据。旧房体的布局不改名套用。
- `scene_assembly.py` / `install.py`：正式目录引用、保留医疗线路图、新办公室独立图的后台保存。
- `Receipts`：实际编译、导入和保存结果。脚本存在不表示已完成落盘，以回执状态为准。

正式地图 `/Game/GameMaps/L_Dungeon_Randomized`，变化用于新生成的地牢；不改写既有玩家存档里的运行布局。保留医疗线路地图 `/Game/GameMaps/Design/L_Hospital_Theme_Subject`，新办公室独立地图 `/Game/GameMaps/Design/L_MedicalDoctorOffice_Subject`。未添加菜单入口或修改默认地图。

制作过程不启动游戏，不进行 PIE、截图、渲染或运行验收。离线布局制作是新目录需要的生产数据生成，不表示已通过游戏体验验收。由用户自行测试。

2026-10-10 用户追加要求逐个检查门口闪动与穿模，按 [门洞修订记录](DoorwayRepair.md) 修复医生办公室及病房门框。实际导入与保存状态见 `Receipts/doorways-install.json`；静态网格排查不等于游戏视觉验收。
