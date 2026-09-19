# ASH-12 法线、机械分件、材质与雨水 — 2026-09-19

## 完成内容

用户根据上一轮检查报告授权优化。本轮沿用既有 ASH-12 与 Manny 源模型，制作枪型独立的表面修订，并接入当前游戏加载路径。未制作新手臂动作，既有换弹和战术冲刺继续引用原序列及原骨架。

### 网格法线与可见枪机

- 按原始 FBX 与已接受网格的逐机械件仿射关系，使用逆转置法线矩阵重新转换源角点法线；保留原硬边、UV0、九个材质槽及原骨架。
- 同时修正旧 `SourceAssets/ASH1220260917/Scripts/build.py` 的法线转换，防止该作者入口再次原样复制未旋转的法线。
- 原始源模型连通体 79 是机匣窗口内的枪机零件，100 个作者顶点。从 `WPN_root` 刚性转绑至原有 `WPN_bolt`，绑定时保留腰射待机下的原位置。
- 现有空仓换弹在 2.34–2.60 秒驱动拉机柄／枪机，2.65 秒返回；此轮通过真实几何权重让现有枪机轨道生效，未改动动作节拍或手部接触。

### 表面

- 旧 Normal PNG 的 RGB 被源透明通道乘暗。本轮从用户原始 `natga/*_n.tga` 的直通 RGB 重建，丢弃该通道作为透明度的用途，导出不透明 DirectX Normal PNG；UE 使用 Normal 专用压缩、线性采样且不再翻转绿通道。Blender 工作材质单独翻转 Y 以适配其切线约定。
- 七个枪身分区各有一张结构 Normal、一张 ORM。AO 为每个材质区域 7 mm 距离的局部几何烘焙；粗糙度仅有轻微结构／微纹变化，金属度基数沿用既有分区。
- 保留用户选择的纯枪金属外观。新 `SurfaceRegions` 角点颜色区分握把／枪托端垫聚合物、枪机裸钢和枪口内腔消光；UE 与可编辑 Blender 材质均消费该分区。
- Normal 512–2048 像素，ORM 同尺寸。未以整枪加面或统一升到 4K 代替本次修复。

### 水珠与天气

- 七个枪身材质和五个瞄具／倍率环外壳材质各有独立湿润版本，共十二组干湿映射。
- 复用现有 `WeaponBeads.hlsl` 的双尺度附着水珠，叠加于结构法线；水膜和水珠分别影响粗糙度，湿态底色略微变暗。
- 使用现有 `WeaponWetness` 实例数值，接入淋雨、遮雨和逐步干燥；复用现有雨水强度／质量开关。水珠附着使用原 UV，不添加世界空间贴花或第二套天气控制器。
- 枪口内腔排除水珠；瞄具沿用原外壳／镜片／刻字保护遮罩。
- 私有 `DA_ASH12_WetMaterials` 在天气组件初始化时合入现有映射，不覆盖公共天气资产。

### 瞄具

- 全息、全景红点、2×棱镜、LPVO 及独立倍率环制作 ASH-12 专用副本，金属外壳按本枪 Sights 涂层调整。
- 沿用原 UV0 结构法线、AO、白色刻字及光学遮罩，镜片和分划使用原材质。安装变换、眼距和倍率环运动继续使用既有配置。
- 共用装配入口 `M4GunsmithVisual.cpp` 在装备 ASH-12 时选择本枪副本，其他枪型继续使用各自分支。

## 路径

- 作者目录：`SourceAssets/ASH12Surface20260919`。
- 可编辑源：`ASH12_Surface_Editable.blend`；网格导出：`SK_ASH12_Surface.fbx`。
- 制作入口：`author_surface.py`、`working_materials.py`；UE 导入：`import_surface.py`。
- 运行网格：`/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface`。
- 原骨架：`/Game/Weapons/ASH12/Integrated20260917/SK_ASH12_Manny_Skeleton`。
- 材质／贴图／瞄具分别位于新运行目录的 `Materials`、`Textures`、`Optics`。
- 雨水映射：`/Game/Weapons/ASH12/Surface20260919/DA_ASH12_WetMaterials`。
- 接入：`ASH12WeaponAssets.h`、`M4GunsmithVisual.cpp`、`WeatherViewEffectsComponent.cpp`、`Config/DefaultGame.ini`。

## 制作、构建与测试状态

- Blender 制作／贴图烘焙／FBX 导出已完成；编辑源单独补齐了与 UE 一致的材质区域。
- UE 导入进程完成并保存本轮资产：`import2.log`，`ASH12_SURFACE_IMPORT_COMPLETE`，exit 0。首轮因 Python 的编辑器属性 setter 用法退出，已修正后完成导入。
- 必要原生模块构建：等待用户保存并关闭编辑器。
- 按用户全局规则，没有运行额外检查、PIE、渲染、截图、回归或视觉验收；实际反光、枪机运动和雨水观感交由用户测试。本次制作完成不作为实机效果通过的证明。
