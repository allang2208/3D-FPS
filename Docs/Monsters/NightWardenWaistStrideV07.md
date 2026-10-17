# 守寝者：短破布围腰与沉稳移动 V07

> 历史制作记录；2026-10-17 当前 V18 移动仍被用户否定并转待办。旧版本源/资产可能已归档，恢复位置与当前状态以 [收尾记录](../Publication/NightWarden20261017/README.md) 为准。

用户要求在恢复的原始身体上只增加一圈遮挡裆部的破布，参考巫婆处理布料与动作的关系，并制作更有气势、无需僵尸风格的移动动画。V06 原始模型保留为恢复基线。

后续实际 AI 移动已接入 V08，见 [守寝者 AI 移动 V08](NightWardenAIMovementV08.md)。V07 的网格、围布与行走继续使用；下文原地预览状态属于 V07 当时的交付记录。

## 造型与布料

身体外形、原 UV 和原 45 根关节位置保持不变。源文件已有的上身腿骨污染按高度连续衰减，并按该顶点原有的非腿部骨链重新分配，共涉及 7,890 个顶点；手臂仍跟随原手臂链，不因高度被拉回脊柱。不重新分配整身权重，不增加手指骨。

围布为连续短围腰：固定卷边腰口、约 33 cm 长的外层布面、小幅破边及纤维，内侧增加不参与物理的搭叠遮挡层。破损只落在下缘，中央遮挡不挖洞。贴图和布面参数复用实际 `WitchRebuilt` 的 Fabric09 母材质。

外层使用 1,040 点的独立连续代理，腰口固定、下摆逐渐释放，最大活动距离 13 cm。原生制作入口复用 `UWitchRebuiltClothingAsset` 的稳定位置／法线／切线捕获和巫婆下袍的已保存 Chaos 配置，按短围布调整碰撞厚度、动画牵引与阻尼。专用碰撞覆盖骨盆、下腹、左右大腿和巨臂前臂；内侧遮挡层保持蒙皮，防止外摆露出敏感部位。

制作代码为 `Source/FPSGAME/Monsters/NightWardenWaistClothAuthoring.cpp`，仅在编辑器构建中注册 `NightWarden.BuildWaistCloth`，只处理本轮 V07 网格路径，不改变巫婆或其他怪物资产。

## 单位与动作

V06 的静态导入保留了 100 倍容器缩放，该容器不适合直接进入当前重定向流程。V07 在导出副本中将网格与骨架数据统一烘焙到厘米、对象缩放为 1，并为原骨架增加中性的地面根 `NW7_Root`。原 45 根关节位置与身体比例不变。

源动作改为项目已有的 `/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd`，经 UE 原生 IK Retargeter 进入原始骨链。先按双方肩部横向注册整个根坐标，再对齐骨链；使用 `AutoAlignBones` 保留根偏移，避免 `AutoAlignAllBones` 清空它。原地化同时移除供体嵌在骨盆上的净水平行程，保留周期内的承重位移。

定制循环为 2.4 秒、60 fps、145 个采样关键帧，使用完整徒手步态、较慢承重／较快摆腿、受控肩宽和巨臂延迟回摆；足底支撑来自原裸脚，围布不参与整身接地判断。最终使用目标 UE 骨架自身的局部四元数轨道写入动画，避免动画 FBX 再次转换坐标。

## 制作与接入状态

2026-10-16，围布源、厘米制模型／代理 FBX、布料绑定、正式动画和原 `BP_NightWarden` 入口均已完成并保存。必要 Editor 构建结果为 Succeeded，`helper-build-stdout.log` 记录退出码 0；最终 Finish 后台导入保存批次退出码 0。`V07WaistStride/Records/ue_delivery.json` 的状态为 `waist_cloth_stride_and_entry_saved`、`complete: true`。

已保存外层 Chaos 代理共 1,040 点，其中 160 点固定；下摆最大活动距离 13 cm，使用 5 个随骨骼移动的碰撞胶囊。内层遮挡和腰口维持蒙皮。F6 原“守寝者（模型与衣物）”入口重新生成的角色将使用 V07 网格与动画，启用布料、关闭整身布娃娃；这是原地循环展示，尚未加入 AI 位移或战斗逻辑。动作名为 `A_NightWarden_CommandingStride_V07`。

制作期间一次重定向后的 `UAKMAnimationAuditLibrary::FinishAnimationCompression` 调用触发了引擎 `CacheTasksByKeyHash` 重复任务断言，导致当时编辑器退出。该通用函数没有被修改；本轮新增限定 V07 路径的 `NightWarden.FinishMotion`，先等待已有压缩结束，再请求／等待缓存，避免重复提交同一 Hash。后续改在后台继续，不主动重启编辑器。该事件不作为已完成保存，也不能用旧源缓存替代重新生成的配准动作。

制作目录：`SourceAssets/NightWarden20261015/V07WaistStride`。

- `Scripts/author_waist_v07.py`：从 V06 制作独立围布、遮挡层、代理与碰撞描述。
- `Scripts/import_waist_v07.py`、`retarget_stride_v07.py`：保存新模型、原始骨链的厘米制骨架和原生动作输入。
- `Scripts/author_stride_v07.py`：节奏、承重和巨臂动作制作；保存 UE 局部关键帧及可编辑 Blender 源。
- `Scripts/install_stride_v07.py`：绑定并保存物理布料和动画；接入阶段调用独立的入口切换脚本。
- `Scripts/activate_stride_v07.py`：在非试玩状态下保存原 `BP_NightWarden` 的网格、动画及布料设置。
- `Scripts/v07_background.ps1`：Prepare／Retarget／Finish／Activate 后台接入；已有编辑器时沿用批次互斥。
- `Scripts/build_waist_helper_v07.ps1`：等待正在进行的引擎构建结束后，再提交本轮必要编译。

本轮不主动进行渲染、游戏运行或验收测试。制作、实际保存和用户后续观感分别记录；不把旧 V01／V02 的局部数据修订当作整体动作认可。
