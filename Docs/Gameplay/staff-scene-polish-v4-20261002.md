# 员工区场景修整 V4

按用户七项反馈继续制作，沿用宿舍、更衣淋浴、活动区和原四张样板地图。
资产路径为 `/Game/Dungeons/StaffLiving20261002/ScenePolishV4`。
本次只制作、必要构建、导入和保存，未运行游戏、PIE、截图、渲染或测试；效果由用户体验。

1. **书籍与容器轮廓**：书页块、上下封面、书脊按独立尺寸制作，平放书的封面与书页留出 0.5mm 间隔，叠放间距加大；同步替换书柜、书架本体和书架储物盒内的书籍。轮廓使用整数模板的分数覆盖重建和柔和混合，默认宽度 2.2 像素。只有视线约 18cm 范围、250cm 射线范围内首个可见容器出现高亮；交互仍要求角色距离不超过 240cm。绿色表示未搜寻，黄色表示已搜寻。高亮与 E 提示、E 搜寻共用目标判定，不透墙，不常亮。
2. **床品**：保留四种烘焙褶皱和不同枕头姿态，把被子限制在床垫内；横向边缘最大约 38.8cm，床垫半宽 42cm，梯子与护栏保持在外侧。无需实时布料。
3. **宿舍布局**：每间两张床平行，床头朝外墙、床尾朝入口；床中心距 2.48m，床头柜置于两侧。书桌与椅子移到侧墙，储物柜、书柜与书架沿墙分配安全位置。六间宿舍继续随机选择四套受约束布局，床位固定，容器身份及取物存储键保持一致。
4. **地毯边缘**：宿舍门槛、通道接口与活动区材质交界添加 16cm 宽的实体收边，局部翘起并附包边与缝线，复用原深蓝地毯材质。收边为装饰网格，不增加微小台阶阻挡。
5. **洗漱组合**：原洗手台和镜子朝湿区，而部分位置与门洞重叠，走廊侧看到背面。四组组合改装在更衣区完整北侧隔墙的 x=-5.4/-2.4/2.4/5.4m 位置，整体转向更衣区；盆后承托、排水穿墙点和镜子挂件按内墙面 1.96m 定位。镜面移到框体正面，避免被实心框板遮住。
6. **休息区**：两张台球桌并列，补充分段木质台边、台呢包覆、瞄准菱形镶嵌、六个开口袋沿与网篮、可调脚、球与巧粉。沙发移到平台前部并朝电视，茶几置于两者之间。电视为宽 3.4m 的 16:9 巨幕，窄边框、薄机身、墙架、线槽和独立音箱。
7. **球杆架与饮水机**：三组墙装球杆架各五根球杆，增加下部承托杯、上部开口卡扣、墙面挂板及螺栓；球杆有渐细枫木杆身、握把细纹、接环、尾部护垫、先角和蓝色皮头。饮水机补接水盘、格栅、冷热龙头、状态灯、脚垫与背部通风；19L 倒置水桶使用颈口、圆肩、加强筋、透明蓝色桶壁与内部水体。

容器各自的活动部位和永久开启形态继续沿用原合同，奖励设计仍留待后续。完整瓷砖墙面继续保留，不添加剥落。正式随机地牢池尚未注册。

高亮由现有本地 HUD 统一更新，约每 0.06 秒判断一次；容器仅开启动画期间 Tick，无容器逐帧扫描或空闲 Tick。透明水桶所在网格关闭 Nanite，其余适用网格保留 Nanite 与明确 UCX；镜子保留原反射材质。

源码：`SourceAssets/DungeonStaffLiving20261002/Scripts/author_scene_polish_v4.py`、`dormitory_layout_polish_v4.py`、`import_scene_polish_v4.py`。
完整可编辑源：`SourceAssets/DungeonStaffLiving20261002/ScenePolishV4/Authored/StaffLivingTheme_ScenePolishV4.blend`。
安装回执：`SourceAssets/DungeonStaffLiving20261002/ScenePolishV4/install.json`；原地图及配置备份：`ScenePolishV4/Backups`。
默认作者与导入入口按 `scene_polish_revision=4` 选择当前版本。

```text
open /Game/GameMaps/Design/L_StaffLiving_Theme_Subject
```

对应独立入口仍为 `L_StaffDormitory_Subject`、`L_StaffChangingShowers_Subject`、`L_StaffRecreation_Subject`。
返回主场景：`open /Game/GameMaps/DayNight_Lighting`。

实际落盘：16 份网格、10 款物件材质和 1 款轮廓后处理材质已导入并保存，四张地图已保存，安装阶段为 `samples_saved`。Editor/Game Win64 Development 构建完成，后台导入退出码 0。原生 Editor DLL 于 20:11 落盘，当前编辑器于 20:15 启动，未触发 Live Coding 或重启。制作与构建记录见 `ScenePolishV4/completion.json`；这不表示运行效果已测试。
