# 废弃焚化处理厅：独立主体 V1

后续反馈修订见 [铭牌与栏杆 V2](dungeon-incinerator-scene-fixes-20260930.md)：铭牌改为单一正面、栏杆补连续碰撞体。随后按用户要求将坑扩大为 4.4 × 5 m，并制作接灰设备及中文提示牌，见 [灰渣接收区 V3](dungeon-incinerator-ash-station-20260930.md)；深度保持 1.2 m，未新增地下二层。

制作日期：2026-09-29 至 2026-09-30。主构造完成后，按用户追加要求完成炉门机构、投料推车、带盖医疗废物料斗及既有配电柜复用，见 [精密设备制作记录](dungeon-incinerator-equipment-20260930.md)。生产随机池保持既有七房，本房尚未入池。

**本批已完成后台构建与实际落盘。** `Saved/BuildEditor/build-20260930-000048.log` 记录 `Result: Succeeded`；`Receipts/install-v1-map.log` 对应命令行退出码 0，`Receipts/install.json` 记录 `stage=sample_map_saved`、23 组网格、独立地图及 12 盏灯。没有运行或视觉测试。

## 主要构造

- 主厅约 28 × 21 m；南侧与东端切斜形成不对称偏楔形平面。高处桁架下缘约 8 m，屋面微升。两端各有 2 m 门斗，总长度约 32 m（未计墙厚）。
- 南侧三联停用炉区：厚砌体、真实凹入炉口、固定投料槽和支架，炉口约 2.2 × 2.6 m。2026-09-30 已将粗门替换为 Blender 精密炉门：六点锁紧、手轮、液压缸、双软管和铰链；另有滚筒推车与带盖料斗各一件。当前均为停用静态布景，无工作火焰、液压动作或环境伤害。
- 中部连续约 7 m 宽的作业带；设备、灰坑和楼梯集中在两侧，炉前可横向通行。
- 西南灰渣坑现为 4.4 × 5 m，深 1.2 m；实际楼板留洞，四周围护，8 级返回楼梯加宽至 1.6 m 并移到一侧。已制作炉侧导灰管、密闭接灰斗、隔离闸门、抽拉式接灰箱和中文用途牌；当前为停用静态布景。
- 北侧观察台约 14 × 4.5 m，高 2.4 m；两端各设 2.6 m 宽楼梯、16 级，踏步高 15 cm / 进深 30 cm；栏杆避开登台开口。
- 三套炉顶集烟罩与高位排烟、墙边检修管、真实吊杆、屋顶桁架及附墙支柱。主要吊杆接到屋面，炉区保留固定管路支撑。
- 外部接口 3 × 2.8 m，平层标高一致；样板封板独立分组，未来入池需排除。主体不会缩放为旧房型或恢复已撤回的尺寸/内装变体系统。

## 作者源与资产

作者目录 `SourceAssets/DungeonIncineratorHall20260929/`；主体尺寸由 `Scripts/prepare_design.py` 输出为 `Config/room.json`，后续精密设备的定位独立维护于 `Equipment20260930/Config/layout.json`。

- `Scripts/geometry.py` / `export_geometry.py`：从已认可车站作者中提取的本批几何和 FBX 制作公共部分；没有调用旧车站安装器。
- `Scripts/author_hall.py`：本房专用结构制作；保存 `Authored/AbandonedIncineratorHall_Subject.blend`、23 组 FBX 和 `manifest.json`。
- `Scripts/install_subject.py`：只导入本房新包、绑定已有材质、构建 Nanite、保存独立地图。已保存目标不被静默替换。生产随机目录、现有地图和其他任务资产不在写入范围内。
- 资源目录 `/Game/Dungeons/IncineratorHall20260929`。
- 独立地图 `/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject`。
- 保存回执 `Receipts/install.json`；只有 `stage=sample_map_saved` 才表示地图已实际落盘。第一次后台进程因整机提交内存不足、页面文件太小而中止；未因此关闭其他进程或改变系统配置。

后台导入改用 `-nullrhi -NoShaderCompile`，并以命令行配置将 Asset/Texture 异步编译并发设为 2，完成网格制作和地图保存；不修改项目常规渲染设置。第一次无渲染导入已保存全部网格，地图装配时修正本机 Python API 的 `generate_overlap_events` 属性写法后续接保存，未重导已完成的同版本网格。最终无渲染过程不是视觉验收。

复用已认可的混凝土、灰浆、金属 PBR、墙裙瓷砖及 UV、工业吊灯与管件/法兰制作函数。没有将第三方原件授权扩展为公开再分发。新外部素材本批只查找，尚未下载或导入；见 [细节素材与免费候选清单](dungeon-incinerator-hall-assets-20260930.md)。

## 样板接入

出征菜单新增“废弃焚化处理厅 · 主体样板”；使用正式 FPS GameMode、PlayerStart、入口返回锚点与既有传送门行为，地图加入 MapsToCook。原生改动限于 `ColdSteelExpeditionController.cpp` 和 `SceneTestPortal.cpp` 的现有函数，无新增反射字段或新玩法类。源码、构建状态及地图保存状态分开记录。

结构主体阶段不增加怪物、掉落、封门战斗和伤害。后续认可主体并授权入池时，再配置真实占位 cells、端口对、可行走/怪物锚点、候选概率与灯调度；同时撤销独立菜单、地图打包项、返回门和样板封板。

## 制作成本与交付边界

23 组结构/装饰网格合并按用途维护；不透明网格启用 Nanite、显式切线及完整回退几何。楼板、楼梯、栏杆、炉体承担阻挡；瓷砖表皮、小管件、细节和桁架不叠加查询碰撞。不能据此推算 FPS。

12 盏局部灯、其中 4 盏投影；明确角色、半径、34 m 最大绘制距离和 6.5 m 渐隐。独立样板采用有界固定照明，不称为已接生产房间调度；入池时沿用现有 AuthoredDungeonLighting。

没有主动打开 UE、启动游戏/PIE、截图、渲染或测试。制作导入和必要编译不等于运行、导航或视觉验收，交由用户测试。
