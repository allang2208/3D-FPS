# 唐刀：腾云游龙刀身

按用户提供的“方案一：腾云游龙式刀身”制作本系列第二款刀身，独立选项为 `ue_tang_dao / blade_1 / tengyun_dragon`，改造台显示“腾云游龙刀身”。本轮制作外观与引擎接入，数值保持原装；用户尚未指定本款的战斗改造效果。

当前 SolidV4 刀身从规整、封闭的刀根直接成形，取消旧截面与新刀身之间的周长插值，主体两侧刀面平行，厚度统一为 7 mm。刀根在 z=1.34 cm 起始，插入 z=1.4 cm 的护手安装面 0.6 mm；没有任何原装刀根顶点或材质。刃口与刀背保留正常倒角，龙脊长导槽保留 0.70 mm 实体凹陷，只有刀尖最后 2 mm 做收锋，取消旧版沿长段逐渐减薄的处理。纵向尖端保持 z=88 cm，侧向尖端为 x=9.505 cm。护手、握柄、柄尾和骨骼挂载沿用唐刀当前装配，保留刃口朝前的现有安装方向。

鎏金游龙源纹饰由内置 imagegen 参照用户图中的金纹制作，原图与完整提示记录在 `Textures/Tengyun_GildedDragon_Ornament.png` 和 `ornament_generation.json`。图样已烘焙到双侧钢刃图集，0.13–0.195 mm 浅浮雕及细鳞、云纹继续由既有法线表现，不再使主刀面几何发生起伏；外轮廓和导槽由真实几何承担。参考只给单侧，背面采用同工艺的对应龙纹设计。

新材质使用 4096×4096 BaseColor／ORM／Normal，水波锻钢、细磨削纹、流云蚀刻与金质龙纹由 `surface_math.py` 和 `author_maps.py` 共用物理表面配方。ORM 顺序为 AO／粗糙度／金属度；法线为 OpenGL，在 UE 导入时翻转绿色通道。完整刀身只有 `M_TangDaoTengyunSteel` 一个材质槽，UV 纵向范围为 z=1.4–88 cm，没有原装刀身材质槽。

当前网格直接引用已保存的 `M_TangDaoBladeRuneSurface_CloudTengyunJoint`、其旋风变体及全长三张 PBR，保留共鸣／侵蚀／导魔／祥云的原生遮罩、动态参数、Substrate 自发光输出和曝光处理。本轮只保存独立新网格包，不覆写已加载的纹理或材质。祥云的攻击速度、耐力、韧性及击杀恢复最大体力 15% 数值均不调整。

可编辑源为 `TangDao_TengyunBlade_Editable.blend`；交换件为 `Export/SM_TangDao_Blade_tengyun_dragon.fbx`（3 档 LOD）及 `.glb`（LOD0）。采用普通静态网格路线，完整近景网格与两档显式 LOD 随 FBX 导入。图标制作直接渲染本款真实刀身，按已采用金属方框风格制作灰阶 UI 图标；该渲染属于接入素材制作。

`import_assets.py` 是实际后台导入与保存入口，`catalog_extension.py` 只增量登记本款选项、模块及表面绑定。父级 `install_catalog.py` 与 `SurfaceV2/import_surface.py` 保留两款独立刀身的扩展钩子。保存资产与合并状态分别记录在 `import_receipt.json`、`catalog_receipt.json`；只存在源码不表示已经导入，最终以 `delivery.json` 的实际执行状态为准。

本轮没有新增 C++ 玩法，不自动启动 UE 编辑器或游戏，不进行游戏测试、验收渲染或截图，由用户自行测试。排查范围内仅记录模型接缝、材质区间及必要的导入保存状态。

当前平整度与厚度修复记录见 `PlanarRepair20261002/README.md`。`author_blade.py` 进入该目录的现行作者脚本；`import_assets.py` 根据清单复用已保存表面，仅导入新网格。前一次接缝制作记录见 `JointRepair20261002/README.md`，用户反馈该版本根部扭曲，已由 SolidV4 替代。下方为最初制作与第一次接入的历史记录，不能代表当前修复后的网格和资产数量。

实际交付：三档 LOD 作者三角数为 107036／58868／27828，FBX、GLB、可编辑 Blend 和三张 4K 图集均已保存。正式导入并保存 7 项 UE 资源：3 张 PBR 贴图、2 个原生符文材质（含旋风变体）、1 个三档 LOD 刀身网格和 1 张改造栏 Texture2D。模块目录、唐刀专属选项、表面绑定及旋风映射已合并落盘，最终桥批次返回成功。

接入时编辑器已经运行且处于用户现有游玩状态。首次复制材质被 `EditorAssetLibrary` 的游玩状态限制拒绝，已保存的贴图保留；随后改用 `AssetTools` 复制本款独立材质，借助本轮保存回执保留资产归属，继续完成全部保存和目录登记。没有停止用户游玩或启动、重启编辑器，没有另起 commandlet 覆写已加载资产。执行回执为 `bridge-import-20261002-165340.json`。

## 2026-10-03 源码发布与退役归档

本次唐刀废案和历史备份归档到工程根 `trash/tang-dao-retired-20261003`，其中 `manifest.json` 保存旧路径、新路径、大小、SHA-256 和替代入口。历史回执或文字中的旧日志、Before、ReferenceV2 路径按此清单查找，不再作为当前制作入口。

保留原始 Meshy 输入、当前可编辑 Blend、有效导出、PBR、浮雕高度源和参考图在本机。燕翎配重使用 ConeV3，游龙刀身使用 PlanarRepair/SolidV4，虎首配重使用 ConnectorV4；游龙仍使用 JointRepair 资产目录里的符文材质，不能删除该材质依赖。虎首卡片框样式输入已迁到 `TigerPommel20261002/Icons/frame_style_reference.png`，当前提示词同步记录新路径与原路径。

公开 Git 仅包含源码、小型参数与恢复说明；不包含上述模型、贴图、参考图或 UE 二进制。完整依赖和恢复顺序见工程 `Docs/Weapons/tang-dao-publication-20261003.md`。未为本次发布启动游戏或进行视觉验收。
