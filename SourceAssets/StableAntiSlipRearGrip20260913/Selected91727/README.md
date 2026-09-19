# 稳固防滑后握：选中 seed 91727 接入

2026-09-13 用户选定重抽 seed 91727 并授权替换。冻结上一级 seed_91727 的带纹理母版；旧 seed 91713 与旧导入资产保留。

- 游戏路径：`/Game/Weapons/StableAntiSlipRearGrip/Selected91727/{M4,AKM,QBZ191}/SM_StableAntiSlipRearGrip`。
- 从各枪 `FactoryMountReference` 取得 WPN_root 空间的真实原厂接口。比较上下握持区的后倾方向，按每枪宽度和握持高度适配。保留接口上表面；上端 18mm 区间平滑收进连接轮廓，接头重叠 3mm。模型单位米，FBX 导出厘米，运行沿用 WPN_root 的 .01 骨骼缩放抵消。
- 母版独立保留，游戏主体约 30000 三角面，另加原厂接口过渡。每枪 FBX 与可编辑 Blend 在对应子目录。
- 主体定义为防滑聚合物，保留生成的底色和 UV0 粗糙度变化，金属度 0，粗糙度限制 .55–.95。无新增法线贴图，细节由现有几何与贴图表现。
- 连接头金属使用各枪材质：M4 为当前机匣裁切图和原有 Phong 转换；AKM 为 SovietFab 机匣金属平铺组；QBZ191 从当前枪身程序涂层制作独立贴图，保留其磨损与最终色调处理。UV1 独立物理投射尺度分别为 12x5、12x2.5、10x10 cm；保留 UV0，关闭自动光照 UV 生成。
- ID `stable_antislip_reargrip` 不变，属性仍为开镜速度 -10%、后坐力控制 +20%、稳定性 +15%。当前角色、枪匠、未装备预览、武器图标和掉落沿用共同 SetGunsmithRearGrip 入口。
- 作者脚本 `author_model.py`；QBZ 涂层制作 `bake_qbz_coat.py`；UE 导入 `import_assets.py`。本次没有启动游戏、制作验收渲染或运行测试，方向、动态贴合和实际渲染效果由用户测试。

导入状态：UE Python 脚本成功完成并保存三枪资产（import_results.json）；命令进程退出 1，日志为项目已有 GameFeatureData 配置缺失及本机 8000 端口占用。未因此改动项目插件或服务配置。

必要构建状态：独立模块后缀 913185127 构建失败，首次编译错误在 Source/FPSGAME/Building/VoxelBuildWorld.h:18、:35，C2143/C4430，随后出现对应 UHT 构造函数错误。未修改体素建筑并行代码。资产导入与源码引用切换已完成，新的运行模块尚未生成，因此不能宣称当前游戏进程已使用重抽版本。完整日志 build_stdout.log。
