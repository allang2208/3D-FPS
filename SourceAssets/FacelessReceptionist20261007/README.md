# 当前版本：V04（2026-10-08）

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

当前制作包见 [V04/README.md](V04/README.md)：按用户截图修订攻击穿裙、肩部衣层与织物材质，实际保存 UE 网格、材质和动作修正曲线，并完成本轮要求的离线姿态检查与资产读回。未启动游戏／PIE，由用户继续体验。

[V03](V03/README.md) 及更早源文件保留作追溯。V04 穿衣版剔除衣内重复人体面，完整身体另行完整保留。

以下为 V01 历史记录，不代表当前造型通过验收。

# 无面接待员 V01
制作开始：2026-10-07；落盘：2026-10-08（Asia/Shanghai）。
状态：模型、独立衣物、蒙皮与 32 个 UE 资产已保存；F6 入口已加入，FPSGAMEEditor 后台构建成功。FPSGAME 独立 Game 构建因其他 Building 源码的 Unity 同名常量冲突失败。未测试或视觉验收。

## 使用入口
使用本轮已构建的 Editor 目标运行时，在 F6 → 怪物生成 → 无面接待员 中生成。独立 Game 可执行文件尚未更新本轮入口。
角色包：/Game/Monsters/FacelessReceptionist/BP_FacelessReceptionist。
本轮没有修改地图或自动生成场景实例。

## 文件
- Authoring/FacelessReceptionist_V01.blend：完整 Meshy 身体、29 个独立服装／细节对象、女僵尸骨架、三条源动作。动作保存在 NLA 中并默认静音，打开文件保持绑定姿态。
- Delivery/FacelessReceptionist_V01.glb：完整穿衣角色，含蒙皮与贴图；此 GLB 不包含动画片段。
- Delivery/FacelessReceptionist_Clothing_V01.glb：独立衣物和共同骨架，含贴图。
- Delivery/SK_FacelessReceptionist_V01.fbx：UE 用的合并穿衣骨骼网格。
- Delivery/SK_FacelessReceptionist_Body_V01.fbx：独立完整身体骨骼网格。
- Textures/：原身体 PBR 与本地制作的织物、衬衫、鞋、胸牌、包边 PBR。
- Source/：用户原 GLB 的原样副本。
- authoring_receipt.json、animation_sources.json：制作与动作来源记录。
- ue_delivery.json：每个实际保存 UE 资产的回执；build_receipt.json：本次后台构建退出状态。

## 外观与分件
保留用户已减面的无面女性主体及原始 UV／贴图。原 GLB 没有骨架或动画，共 110326 个导入顶点、199526 个三角面；没有再次减面。
深灰蓝单排扣西装配浅色衬衫、过膝 A 字裙、平底封口鞋和 M / RECEPTION 胸牌。翻领、领尖、袖口、口袋嵌条、纽扣、裙腰与后开衩是独立制作对象，服装具备厚度。
服装共 71504 个三角面；穿衣导出含完整身体，合计 271030 个三角面。29 个作者对象在 UE 导出中合并，使用 6 个材质分区。
完整身体没有因穿衣而删除。原模型的临时打底表面仍存在于身体内部，外层服装覆盖它；本次没有宣称恢复了被原模型衣物遮住的身体细节。
衣物目前是骨骼蒙皮，没有制作 Chaos 布料模拟。

## 骨架与动作
源骨架：/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale。
输入 A 姿通过肩、肘、腕、髋、膝、踝的制作定位，拟合供体表面并进行三角形重心权重转移；然后将身体与衣物转换到女僵尸的原生参考骨架空间。手部沿用供体的独立手指骨。原始模型、制作定位及结果分别保留。
骨架对象的 0.01 单位换算随源保留；FBX 对象 root 是 UE 根骨，不能命名为会被 UE 剥离的 Armature。Blender 有 160 条骨，导入 UE 包含容器根为 161 条骨。
只使用自己的骨架、物理资产、动画副本与蓝图，不修改原女僵尸资产。

正式游戏动作直接复制当前 A_Nurse_idle / A_Nurse_walk / A_Nurse_attack，并通过项目现有 RebindNativeAnimation 将副本关联到相同参考骨架的独立 Skeleton，保留本地骨骼轨迹和现有时序。
Blender 中的三个动作来自项目已导出的原始女僵尸 FBX；行走与攻击去除水平线性根位移趋势。它们是制作源，正式游戏使用上述项目动作副本。
未添加新攻击动作、独立技能或新平衡数值。角色继承现有 NurseZombie 行为、命中时钟、人形物理和反应系统。导航与胶囊沿用已有 Nurse 规格（半径 34 cm、半高 92 cm），F6 占地半径 44 cm。

## 材质制作
身体沿用原 BaseColor / Normal / MetallicRoughness。衣物微织纹由固定数值表面场生成，颜色、粗糙度与切线法线共同使用该表面场；没有把空细分称作高模烘焙。
BaseColor 为 sRGB，Normal / ORM 为线性。作者法线采用 OpenGL，UE 导入翻转绿通道。ORM：R 遮蔽、G 粗糙度、B 金属度。
UE 材质接 Substrate FrontMaterial，启用 SkeletalMesh 用途；纹理保留流送和 mip。
本次不包含浅层视差、高模雕刻或额外透明衣层。

## 后台制作链
脚本位于 Tools/FacelessReceptionist：
1. prepare_inputs.py：保存用户原始 GLB，读取身体和女僵尸参考骨架。
2. author_character.py：完整身体蒙皮、独立裁片、材质贴图、源文件及基础导出。
3. attach_source_actions.py：写入现有女僵尸源动作，不播放或渲染。
4. export_delivery.py：保留源分件，导出单一根骨和合并运行网格。
5. import_assets.py：可从保存回执续接的后台 UE 导入与保存。
6. finish_build.ps1：等待已有构建结束后，精确加入 F6 目录并完成 Editor/Game 后台构建。

finish_data_textures.py 是本轮线性数据贴图修订步骤；author_character.py 已同步该修正，重新制作无需额外重复此步。
import_assets.py 默认按回执跳过已保存内容；重新制作后用 RECEPTIONIST_FORCE_REIMPORT=1 环境变量请求重导本角色资产。不要在打开本角色资产的编辑器之外重导同一包。

## 状态边界
已完成的是作者源、导出与实际保存资产，不代表蒙皮、裙摆、穿模或游戏行为已通过用户验收。
FBX 导入曾报告绑定姿态相对矩阵不一致，随后引擎回执记录重新创建绑定姿态成功；该日志结果不等于动作验收。
全程后台制作与 commandlet 保存；未主动打开 UE 编辑器、游戏、PIE、截图、验收渲染或测试。交由用户体验。
Meshy 模型为用户提供，动作／骨架为项目已有女僵尸资源；不改变源资源权利。本轮未提交 Git 或公开分发。
