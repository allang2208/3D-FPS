# 黑色皮革手套：毛面细节与实体腕口 V2

后续材质分区、掌面抛光和柔软腕口见 [V3 制作记录](black-leather-tailored-surface-v3-20260928.md)。本页保留 V2 参数与接入历史。

对应物品 `ue_field_gloves_black`。用户认可前版方向，本轮只继续调整表面毛躁感及手套与腕臂衔接的厚度。保留物品 ID、装备槽、战斗属性、现有动作及其他手套。

## 制作内容

- 复用地牢、主神空间海军蓝地毯的浅层 POM 思路：所有颜色、法线、ORM 和高度/绒面遮罩沿同一个偏移 UV 采样，并沿用未偏移 UV 的梯度选 mip。
- 手套使用自身烘焙图集和当前蒙皮表面的世界位置导数换算 UV/厘米；不套用静态地面的世界平铺坐标。左右手镜像及各原生参考姿态沿原 UV、骨架处理。
- 新增皮革颗粒和断续短纤维高度，法线烘焙与高度图由同一作者材质生成；缝线、织物和腕口采用更明显的绒面反光。高度不是从颜色亮暗猜测，颜色仍是黑色皮革。
- `Relief` 图的 R 为归一化高度，G 为短纤维/织物遮罩，B 为 UV 岛边缘的视差淡出。每组 4 张纹理：BaseColor、ORM、Normal、Relief。第一人称 4K，Body 2K。
- Cloth 着色模型的绒面量由遮罩控制；皮革部分保留较低绒面量，织物、缝线和包边增强。没有增加透明毛发层、壳层、WPO 或模拟。
- 腕口沿实际开口轮廓径向加厚约 3 mm，制作圆润外缘、端面、内侧壁与 5.5 mm 内回折；厚度向手腕方向在约 25 mm 内收薄。Body 沿自身较短的腕口制作，未把第一人称切口直接复制过去。
- 所有新包边顶点继承原边界对应的骨骼权重；掌心、指腹和手指不做整体增厚。掉落模型直接使用已带实体腕口的游戏网格，移除旧版展示用的全手套 Solidify，避免重复壳层。
- 原生 Body 骨架轴包含 1 倍导入尺度，而 FPS 为 100 倍。作者坐标转换按厘米保留平移并归一化轴方向；保存的骨架、参考姿态及原权重不变。

## 预算及边界

- 浅层高度范围 0.8 mm，UV 偏移最多 8 个原始图集 texel；缝外 3–20 texel 渐变。最多 6 次粗步进和 2 次细化，近处最多 13 次纹理读取，禁用步进时 4 次。
- 视差在距离 80–240 cm、掠射角及纹理 mip 变粗时淡出；细纤维反光随 mip 淡出。贴图保留流送和 mip。
- 第一人称双手 LOD0 为 25,166 三角面，单手 12,583，Body 26,824；新增腕口双手 1,740 面、单手 870 面、Body 880 面。UE 导入仍生成三级 LOD。
- 视差只改变表面采样，不改变轮廓或碰撞；腕口轮廓的厚度来自真实几何。
- 没有新增动画、动作速度修改、运行时逐帧逻辑或 C++ 编译需求。

## 作者源与接入

- 作者目录：`SourceAssets/BlackLeatherDetail20260928/ReliefCuffV2/`。上一版源和 UE 资产保留。
- 资产目录：`/Game/Characters/ModularOutfit20260924/BlackLeatherReliefCuffV2/`。
- 图标：`Content/ColdSteelData/Icons/BlackLeatherReliefCuffV2/ue_field_gloves_black.png`，320×320 透明 PNG，背包、装备栏及仓库沿用同一物品图标。
- 高模、游戏网格、烘焙材质和新贴图保存在 M4/Body `.blend`；展示 `.blend`、掉落 FBX 和正式物品图标同步制作。图标制作不属于游戏验收。
- 制作脚本：`black_leather_relief_cuff.py` → `build_black_leather_relief_cuff.py` → `finish_black_leather_relief_maps.py` / `author_black_leather_relief_family.py` → `import_black_leather_relief_cuff.py`，均在 `Tools/ModularOutfit/`。
- 材质定义：`black_leather_relief_material.py` 与 `black_leather_relief.ush`。
- 配方只更新黑色手套的 22 个 `rig_meshes`，统一材质覆盖保持为空，使用网格自身材质；物品说明、掉落网格/材质及图标同步更新。
- 已由后台 commandlet 保存 22 个原生骨骼网格、8 张贴图、2 个材质及 1 个掉落网格，共 33 个 UE 资产；完成同一物品的配方、说明、掉落引用和图标更新。导入退出码为 0，日志记录 `BLACK_LEATHER_DETAIL_PUBLISHED ue_field_gloves_black 22`。
- 作者回执为 `published.json`，导入日志为 `Saved/black-leather-relief-cuff-import-20260928.log`。整个接入未启动交互编辑器或游戏。

参照实现：`SourceAssets/GodSpaceLayout20260927/Integration/carpet_relief.ush`、`build_navy_carpet.py`，以及 `Docs/Gameplay/dungeon-wall-relief-followup-20260924.md`。

未启动游戏、预览或验收测试；实际光照、腕口与上衣搭接、换弹及抓握表现由用户测试。
