# 巫婆裙摆、死亡物理与细节修订（2026-09-22）

**历史修订，当前见 [Drape04 / Carry04](witch-drape-grip-20260922.md)。** 用户后续反馈确认本版小腿裙摆权重会造成严重拉伸；该权重策略、死亡禁用布料及右手挂点方向已被替换。本文保留当时排查和制作过程，不能作为当前布料效果已解决的结论。

用户反馈下袍严重穿腿、死亡后腿部散落、模型表面粗糙及握瓶/投瓶动作欠细。当前修订为 **Refinement03**，已写入 `/Game/Monsters/WitchRebuilt` 并完成必要的常规构建。入口仍为 **F6 → 怪物生成 → 巫婆·重建候选**。没有更改 Actor 缩放、骨架单位或整体身高。

## 排查与处理

| 范围 | 发现 | 本次处理 |
| --- | --- | --- |
| 下袍穿腿 | 原下袍仅由 pelvis 支撑；原布料可偏离蒙皮位置 30 cm，腿部碰撞偏细 | 下袍和代理改为连续 pelvis/thigh/calf 权重，局部排开静态腿部包络；脚趾不拉衣摆。代理为 64×33 顶点，腰部固定带 9 cm，最大模拟位移收至 8 cm，加强回归蒙皮驱动，并补足脚部碰撞 |
| 死亡散落 | 继承的 Physics Asset 有 22 刚体、23 约束，含两条 calf→pelvis 额外连接；关节点与当前参考骨架不重合，最大相差 4.597907 cm。活体布料在死亡后仍可能恢复模拟 | 按当前骨架重建 16 刚体、15 关节的连通树，去除跨膝连接，锁定线性位移、禁用约束断裂，重置人体碰撞。死亡开始时布料权重归零并暂停，衣物随死亡动画与布娃娃骨骼变形，不再恢复活体模拟 |
| 粗糙轮廓 | 帽子与头发/头部仅约 3.7k、4k 三角面，暴露手脚轮廓有明显棱角 | 局部焊接、细分和平滑：帽子 22,482、头部/头发 23,922、暴露人体 57,480、内衬 21,660 三角面；原高密度外袍不整体细分 |
| 表面细节 | 原材质缺少独立的近景织纹和皮肤微细层 | 新增四张自制 1024² 无缝法线/粗糙度贴图；布料 4 cm、面部 1.2 cm 尺度的第二 UV。建立 Fabric/Lining/Hat/Head 四个 Detail03 材质，原 UV 和基础颜色保留；手脚继续使用已有护士皮肤材质 |
| 握瓶 | 旧挂点在瓶身较粗的位置，通用握拳与瓶颈不匹配 | 右手挂点移至 13.6 cm 瓶颈高度，掌侧偏移 2.7 cm；按实际瓶身半径拟合每条指骨链。食指、中指和拇指承担主要抓握，无名指、小指保留较松姿态 |
| 投瓶僵硬 | 肩、肘、腕动作衔接及手指打开不足 | 在原短距离前抛意图上重做蓄力、肩躯干带动、肘部轨迹、腕部随动和错峰松指；手骨不平移拉伸前臂。仍为 60 fps / 91 采样 / 1.5 秒，业务释放时刻仍为 0.75 秒 |

上述物理约束及蒙皮问题是已查明的结构问题；未通过实际 Chaos 倒地测试证明其覆盖所有散落/穿插表现。死亡衣物采用蒙皮回退，因此尸体不继续产生独立的裙摆飘动。

待机、步行、举杖、受击、死亡及转身的身体动作键保留，只更新其右手持瓶手指轨道；全部八份可编辑场景同步新网格并重新导入动画。投瓶身体动作单独重做。原 walking/casting 的业务时钟和移动配置保持原值。

## 已执行的范围及边界

- 完成用户要求的源文件、蒙皮/约束排查；查看握瓶近景及待机、死亡交接姿态的 Blender 源模型。Blender 图片不等于 UE 材质效果或实时布料测试。
- 物理资产保存后读回为 16/15，参考关节点最大误差 0；旧、新数据见 `Saved/WitchRebuilt-physics-refinement.txt`。该数字只证明参考连接关系，不代表动态物理验收。
- 六个显示网格的源三角形检查未发现零面积面。投掷右臂骨段长度变化约 0.0000617 cm，首尾手部位置一致；保留原整体尺寸。
- 最终布料为 `WitchRebuilt_WaistDrapeRefinement03`；四种 Detail03 材质均有编译后的 shader types，候选资产无未保存包。UE 导入仍输出 MikkTSpace 零长度法线提示；源网格无零面积三角面，近景实际阴影仍需用户确认，未宣称彻底消除此引擎提示。
- 常规 Editor 构建成功：`Saved/BuildEditor/build-20260922-121815.log`。本轮不使用 Live Coding；构建结果与实时表现分别记录。
- **没有主动启动 PIE、战斗回归或 Chaos 运行测试。** 用户需重新生成候选，观察迈步穿插、投瓶和击杀后尸体。最终外观、动态碰撞与性能尚待用户确认。

## 材质导入中断说明

本轮导入脚本调用 `MaterialEditingLibrary.DeleteAllMaterialExpressions` 时触发 UE `!IsRooted()` 断言，编辑器退出；当时仅四张新细节纹理已保存，原材质尚未覆盖。修订为创建独立 Detail03 材质，不再清空原材质节点。随后修正 CustomInput 构造、常量输入和 Masks 采样类型，并保存重编译后的材质。该问题发生于编辑器制作流程，区别于前轮近战武器 Live Coding 崩溃。

## 交付与重建

- 修改前备份：`SourceAssets/WitchRebuilt20260921/Refinement20260922/Before`，包含作者源、导出与当时 WitchRebuilt UE 资产。
- 作者源：`Authoring/WitchRebuilt_Master.blend` 及八份动作 `.blend`；引擎输入为 `Delivery` 下 FBX。
- 局部重建：Blender 执行 `refine_surface.py` → `refresh_source_meshes.py` → `refine_bottle_grip.py` → `author_throw_polish.py`。`refine_surface.py` 从本次 Before 的 Master 读取，重复执行不会叠加细分。
- 完整重建：`author_body.py` 已调用表面修订，`author_motion.py` 已调用抓握与新投瓶制作；恢复顺序不应再恢复旧的仅骨盆裙摆和通用握拳。
- 自制纹理：`Tools/WitchRebuilt/author_detail_textures.py`；UE 接入通过统一桥运行 `Tools/WitchRebuilt/import_refinement.py`，有 PIE/候选未保存包时保留现场并退出。
- 记录：`Refinement20260922/source_inspection.json`、`surface_result.json`、`bottle_grip.json`、`ue_asset_result.json`、`ue_import_01.txt` 与上级 `ue_delivery.json`。
- 新几何增加近景细节，但没有本轮运行性能测量或新增 LOD 系统。未提交/推送；已有商业人体与动作资产仍仅供本机使用，未取得新的公开再分发许可。
