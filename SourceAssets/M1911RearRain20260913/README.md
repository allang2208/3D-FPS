# M1911 后部材质与两把新枪的雨滴接入

## 本轮修改

M1911 后部击锤、拇指保险、后方小盖板／销钉及握把螺钉共 18 个零件，原来与枪管共用亮色机加工钢图集。沿用现有 Steel 图集的 UV 岛，仅重新烘焙这些零件的 BaseColor、Roughness 和 Metallic，使用当前套筒的烤蓝涂层。结构法线、AO 和原枪管／膛室／内腔材质保留。

新的 M1911 网格仅复制原 Hero 网格并更换 Steel 材质槽，骨架、蒙皮、形状、材质槽顺序和动画不变。运行网格改为 `/Game/Weapons/M1911/RearFinish20260913/SK_M1911_Manny`，由角色初始化入口同步给枪匠、动态背包展示和掉落组装使用。

原天气库只有 21 项材质映射，没有包括 M1911 Hero 及 QBZ191 当前新材质。新增两把枪本体、机械瞄具和现有改造件的雨滴材质，合并到当前 `RainVisibility` 天气库及其 `NaturalV2` 基线库，保留原映射与天气资源。

雨滴沿用 `WeaponBeads.hlsl` 的 UV 水珠、湿润粗糙度和法线效果。运行时继续使用 `WeatherViewEffectsComponent` 的按武器实例积水、屋檐遮雨衰减、切枪保持湿度和逐渐干燥机制。材质实例保留原有及继承的纹理、标量、颜色和静态开关；玻璃、分划、手模和内腔独立材质不添加这一外表面水珠层。M1911 的钢材图集额外保留暗内腔排除遮罩。

## 制作入口

- `read_current_materials.py` / `sources.json`：本轮实际加载的枪体与改造件材质来源，以及旧天气库映射。
- `bake_rear_finish.py` / `rear_finish.json`：重烘焙指定后部零件，保留其他 UV 岛原贴图。
- `M1911_RearFinish_Editable.blend`、`Textures/`：可编辑源与新图集。
- `install_finish_and_rain.py` / `installed.json`：复制枪体、绑定新材质、生成雨滴材质并合并天气库。
- `/Game/Weapons/M1911/RearFinish20260913`：新的干燥枪体与材质。
- `/Game/Weather/WeaponExpansion20260913`：两把新枪的雨滴材质。

只进行了制作、必要资产保存与原生构建，未启动游戏、自测或渲染验收。需重启 UE 编辑器后由用户查看 ADS 色差和雨天水珠。

本轮保存 53 项雨滴材质映射；两个天气库各从 21 项变为 73 项（其中 1 项更新现有来源）。资产脚本完成并写出 `installed.json`，命令行进程因工程既有 GameFeatureData 配置报错返回 1。原生构建为 `Succeeded`，输出 `UnrealEditor-FPSGAME-913193955.dll`；这些制作／构建结果不代表已完成游戏视觉验收。
