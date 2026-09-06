# 枪械改造与 ADS 可复用经验

2026-09-06，来源为 AKM / HK416 / P9 改造、护木换弹跟随、独立枪托和材质统一的实际实现及验证。以下规则用于游戏资产；型号名、数值和骨骼名是案例，不能当作所有新枪的默认值。

## 目录

1. 改造合同与部件建模
2. 通用瞄具、安装变换与 ADS
3. 镜片透明与瞄准验收
4. 活动骨骼与原件替换
5. 材质、UV 和实际预览
6. 草稿、实例保存与弹药
7. 枪口和音效
8. 验收、清理与推送

## 1. 改造合同与部件建模

- 开始前读取源模型网格、材质槽、Skin、骨骼和动作，实际查看当前外观。独立文件不等于独立改造：旧 stock_sleeve_01 是贴合原表面的包覆，原托仍在里面，因此不能显示镂空。
- 原网格可复用的握持区域先保留；增加防滑包覆与真正替换部件是不同方案。镂空托、异形托须独立建模并移除原托几何，否则新旧形状重叠。
- 保留可编辑 TSCN / GLB / 生成脚本、稳定挂点与语义节点名。通用几何只保留一份；不同接口/长度的部件分别适配，不能把整体非均匀缩放当成精修。
- 当前枪托 skeleton / compact / precision 分别为三角镂空、轻量伸缩外形、带贴腮件的精确射击外形；两把枪各有适配模型。伸缩/折叠外观不代表已实现对应操作动画。
- 现实商品仅作轮廓参考，记录来源，不直接复制商标、商业模型或工程尺寸。示例外观参考：[Midwest Alpha](https://midwestindustriesinc.com/alpha-series-folding-stock/)、[Magpul CTR](https://magpul.com/media/wysiwyg/GIS/MAG310_CTR_Carbine_Stock_Mil-Spec_GIS_01.pdf)、[Magpul PRS Lite](https://magpul.com/firearm-accessories/stocks/prs-lite-stock.html)。

## 2. 通用瞄具、安装变换与 ADS

### 2.1 一个红点模型，多把枪适配

- 红点模型保留 `Mount`、`SightRear`、`SightFront`、`Lens`、`ReticleDot`。双标记位于实际光学中心线；装饰护圈、导轨表面不能替代瞄准点。
- AKM、HK416、P9 复用同一个 reflex_01；适配器只决定正确骨骼、导轨位置、姿态和眼距。镜体不因换枪而重复建模，不能为对轴随意拉长/放大镜体。
- 当前适配器入口为 `akm_attachment_mounts.gd`、`hk416_attachment_mounts.gd`、`p9_attachment_mounts.gd`。AKM 有 SOCKET_Scope；HK416 使用 ARMA 上的导轨位；P9 镜体随 slide。必须重新确认新资产骨骼名，不能取“第一个 Skeleton”。

### 2.2 固定安装变换与活动世界点

若 `B` 为安装时骨骼世界变换、`W` 为配件期望世界变换，则保存局部挂点：

```gdscript
var bone_world := rig.global_transform * rig.get_bone_global_pose(bone_idx)
part.transform = bone_world.affine_inverse() * desired_world
```

之后标记的世界位置按当前骨骼求解：

```gdscript
var point_world := rig.global_transform \
    * rig.get_bone_global_pose(bone_idx) \
    * part.transform * marker.position
```

此式要求 marker 是 part 的直接子节点；嵌套节点须先组合中间变换。不要把某帧的世界坐标直接保存为 rest/local 坐标。已有骨骼空间 `bone_mount` 一旦由源姿态建立，重装配件继续用它，不能在换弹中途重新测一次并写回。

### 2.3 ADS 求解

1. 把当前有效照门/准星或红点的 SightRear / SightFront 转到 Gun 的同一局部空间。
2. 将 `front - rear` 旋转到相机 -Z，再平移使 rear 位于 `(0, 0, -eye_distance)`。本项目动画视模的求解形式：

```gdscript
var alignment := Basis.looking_at(front - rear, Vector3.UP).inverse()
var ads_position := Vector3(0, 0, -eye_distance) - alignment * rear
```

3. 眼距根据实际镜体大小、FOV、近平面及后托遮挡检查。0.30 m 是现有动画视模案例，不是所有瞄具的强制尺寸；不得只复制欧拉角。
4. 原厂/红点切换后重新校准；子弹方向仍走当前 `_aim_dir` 与近墙遮挡合同，不再另建一条“红点伤害射线”。
5. ADS 开火可以有受控偏移，停火应回正。不要锁死模型或每帧追踪套筒，再通过反向整枪位移抵消机械运动。

### 2.4 P9：可见镜体随套筒，ADS 用闭锁基准

P9 的镜体真实跟随 slide，但 ADS 校准使用“父骨骼当前姿态 × slide 局部 rest”，保持闭锁基准。这样既保留射击机械动作，又不会拖动整双手追着套筒补偿。

```gdscript
var parent_idx := rig.get_bone_parent(slide_idx)
var closed := rig.get_bone_global_pose(parent_idx) * rig.get_bone_rest(slide_idx)
var stable_point := rig.global_transform * closed * part.transform * marker.position
```

当前 `infima_viewmodel.gd::ads_sight_position` 与 `_part_point` 分别提供稳定校准点和可见活动点。不要交换用途；新枪若有更深的机械层级，应明确组合整条闭锁链。

## 3. 镜片透明与瞄准验收

- 当前红点镜片是单个光学平面，不是有前后壁的实体盒；Alpha 混合、不写深度、不投影，红点单独不受光照。材质统一不得把 Lens、红点或发光/透明材质转换成枪体涂层。
- 当前玻璃 Alpha 0.005、红点半径 0.00065 m 是已验证案例。对更换镜体/FOV不要盲目复制数值；重点是敌人与高对比目标仍清晰可辨。
- 数值检查：相机局部 rear/front 的 Z < 0，横向 `Vector2(x,y).length() < 0.0001 m` 为当前尺度阈值。还需检查屏幕中心投影和真实镜框遮挡。
- 显示黑白高对比靶，分别渲染有/无 Lens，比较红点外的对应像素。本案例最大 RGB 通道差 < 0.05；不能用“材质写了透明”或静音 GIF 代替实际画面。
- 覆盖原厂/红点、腰射→ADS、ADS→换弹、开火回正、切枪、重新应用配件，以及 30/60/144 FPS。实际渲染中验证近平面不裁镜、后托不挡视线。

## 4. 活动骨骼与原件替换

- 导入器可能合并并重命名骨骼。AKM 的 root 是手臂，枪体 root 被重命名为 root_2；曾因使用 `find_bone("root")` 导致护木换弹时滞留。按源 MeshInstance3D.skeleton 与 Skin bind 找真实枪体骨骼，HK416 当前为 ARMA。
- 枪口、瞄具、弹匣和枪托按语义挂点区分。弹匣跟随弹匣骨骼（HK416 CARGADOR），不能与整枪刚性共用。
- 可独立隐藏的原件直接隐藏；合并网格按已验证三角形掩码过滤索引，保留顶点、UV、权重、材质槽及源网格恢复引用。不能只删除网格顶点后留下损坏索引。
- 新旧枪托切换、恢复原厂、枪托+加长弹匣、再次材质刷新都须验证。HK416 材质入口以前按索引数重载整枪网格，会把原托带回；必须识别已替换状态。
- 动作检查至少装备/拉栓、普通换弹、空仓换弹。比较实际 BoneAttachment3D 世界平移与旋转，不能只检查 transform 有限；贴合包覆件额外比较源蒙皮接触点距离（本案例法向外扩约 1.2 mm）。

## 5. 材质、UV 和实际预览

- 顺序固定：轮廓与接口→倒角/硬边法线→UV→材质→实际渲染。原枪托梁的平滑法线让方梁像圆管，必须先修建模，不能靠压暗灯光掩盖。
- 六款枪托使用独立贴腮板、倒角轮廓、锁扣、垫圈/六角紧固件和壳体分缝，细节密度与原枪体保持一致。
- 游戏与面板统一通过 `WeaponSurfaceMaterials.prepare_attachment`，共用 `weapon_finish.gdshader` 和已选 HK416 `coating_albedo.png`；金属涂层、聚合物、橡胶分别处理粗糙度/金属度/反光，不另造偏白高光材质。
- 覆盖顶层 material_override 和 surface override 的实际消费路径。各面使用有效 UV，避免所有侧面 UV 压成直线；检查顶点/UV 数量与实际纹理方向。
- 原 GLB 若无多材质区域，可离线生成区域掩码；改法线保留硬边与权重，不能破坏蒙皮或以变更主光掩盖 PBR 失真。
- 保留编辑源的 StandardMaterial3D；运行时 ShaderMaterial 不保证原样导出到 GLB。记录两者职责，不能把未烘焙 Shader 纹理称为已嵌入 GLB。
- 面板冻结当前蒙皮姿态后保留 active material；切换预览先隐藏旧几何，图形模式在 frame_post_draw 后释放源资源，headless 不等待永远不会发生的渲染帧。
- 同尺寸、同灯光记录整枪和配件近景。效果与旧 GIF 不符时查真实加载路径、材质覆盖顺序和可见节点，不凭截图推测已接入。

## 6. 草稿、实例保存与弹药

- `gunsmith_parts` 属于装备实例，不修改共享 WeaponData。选择配件只改草稿；“应用改造”才写当前 instance_id，并触发当前持枪更新与保存。关闭或换枪放弃未应用草稿；装备/换弹繁忙时按已有策略阻止应用。
- stock 从布尔升级为 `skeleton/compact/precision` 后，UI、Gun、适配器、保存读回全链保留 ID。旧 true 映射为 compact；任何中间步骤把值归一成 true 都会丢失型号。
- Godot 中 `bool(String)` 与 String/bool 直接比较曾报运行错误。按明确类型解析、规范化后比较；多型号变更摘要不能只比较“是否已安装”。
- 弹药对应 AKM 7.62、HK416 5.56、P9 9 mm；初始赠送记录只处理首次成功加入，不因正常消耗为零反复补满。配置脚本导出属性在 .tres 的 script 赋值后设置。
- 换弹完成从当前背包实际扣取，再加入弹匣；卸掉增容件返还溢出弹药，满包时按现有守恒策略保留，不能消失。切枪保留每把实例已装弹量，备用弹来自共享对应口径库存。
- 开发测试、截图、import 都设置独立 INVENTORY_SAVE_PATH。不能为了画面方便覆盖真实背包；显式恢复才备份后操作并读回。库存消失时区分存档覆盖、初始标记、场景结算等路径，有证据才归因。

## 7. 枪口和音效

- 消音器延长枪口后，弹丸出生位置、火光、烟雾统一取新 Muzzle；方向取 Mount→Muzzle。保留相机瞄准与贴墙命中逻辑。
- 音频以用户指定素材和实际资源引用为准。声音变了先查播放器、随机 pitch、叠加机械声、湿混响和总线；未引用旧文件的存在本身不会改变枪声。
- 当前开火使用指定录音直接播放、pitch=1，取消额外开火金属撞击/混响；保留已授权消音器音量衰减。不因下次“优化手感”擅自加回这些层。
- HK416 fire/reload/equip 保持用户选定用途；UI click/confirm 共用原 game-dev button_click.mp3。删除旧音频时同时处理确认无引用的 import 与生成配置，避免生成器复活废案。

## 8. 验收、清理与推送

| 改动 | 本地案例入口 | 观察结果 |
|---|---|---|
| 瞄具与镜片 | tests/test_akm_attachment_ads.gd，GUNSMITH_TEST_WEAPON=akm/hk416/p9 | 双标记居中、有无镜片靶差异 |
| 家具与动作 | tests/test_gunsmith_furniture.gd、tests/probe_attachment_motion.gd | ADS 多帧率、真实骨骼变换、护木接触 |
| 多款枪托 | tests/test_stock_variants.gd | 草稿/应用/存档、型号恢复、材质/UV、组合安装 |
| 枪口 | tests/test_gunsmith_muzzle.gd | 改造前后枪口与弹丸/特效位置 |
| 弹药与实例 | tests/test_caliber_ammunition.gd、tests/test_weapon_inventory_persistence.gd | 口径、数量守恒、实例已装弹与保存 |
| 原始枪声 | tests/test_selected_fire_audio.gd | 真实开火路径、录音、pitch、消音器音量 |

先检查对应文件在当前检出存在及测试前置条件；表中路径是本地实现案例，不保证本次文档发布已包含运行时依赖。静态检查、无头检查、实际渲染、听感分别报告，不互相替代。

清理只限本次归属明确、确认无引用的废案；旧 sleeve 仍被新枪托生成器用作比例/坐标参考，不能当“游戏已不用”就删除。原始生成图、最终贴图的来源记录、可复现脚本、必要失败对照保留。扫描代码、场景、工具、来源记录后，精确删除及配套 UID/import。

提交前检查仓库 WORKFLOW.md §8、remote、上游、暂存区与每个待推提交；禁止 git clean/reset --hard/广泛暂存。混合共享分支必要时从远端基线建立独立发布工作区，只发布当前明确范围。普通非强推，推送后 ls-remote 回读 SHA。记录未发布运行时代码、已有故障和验证边界。
