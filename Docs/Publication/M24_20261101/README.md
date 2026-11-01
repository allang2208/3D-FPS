# M24、骨架狙击枪托与实体镜片发布

本批整理 2026-10-26 至 2026-11-01 的 M24 接入、枪匠改造、腕臂动作、独立枪托/握把、金属表面及实体镜内放大工作。目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。本次只做归档、SKILL 沉淀与发布前核对，没有启动 UE 或重跑游戏/联机。

## 提交内容与共享边界

- M24 专用 C++、物品/弹药/攻击公式/枪匠/穿戴配置、作者配方及本批说明进入公开仓库。枪匠新增栓机/枪身槽同时发布 `slots`、`categories`、`defaults`，保留三者的索引关系。SVD/SVCH 只加入共用骨架狙击枪托选项，不提交其他武器的未发布改动。
- `recipe-manifest.json` 列出作者脚本与来源说明。早期版本是恢复链或历史诊断，不应按日期把所有 install 脚本依次执行到当前资产。
- `Integration/` 发布 M24 与共用实体瞄具在共享宿主中的增量，不覆盖完整 Character、枪匠、身体表现和其他武器源码。`integration-manifest.json` 给出目标路径、UTF-8/LF 前置与结果 SHA-256；具名前置是从当前共享宿主精确移除本批修改而得到的私有恢复基线，不是已发布历史版本。
- 先取得同版本私有宿主并核对前置散列，再应用补丁。不要强行应用到 `main` 的不同宿主版本。UDP 夹具依赖既有 Shotgun/S12K/SVCH 诊断基座，本批只发布 M24 分支。其他会话的暂存区和工作文件保留。
- 模型、纹理、密集姿态、UE 包、DLL、下载包与私有宿主不公开分发。V9 手模、M4 握把、SVD/M4 音效和 Meshy 输入各有独立来源；M24 来源许可不覆盖它们。来源记录见 `SourceAssets/M24CustomScope20261026/ATTRIBUTION.md`。

这是含明确恢复边界的源码发布，不是完整资产备份，也不代表干净检出即可构建运行。完整本地工程、许可输入与已保存 Content 仍是恢复条件。公开配方不能替代原始素材。

## 当前装配与数据

- 活动原生枪为 `/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9`。普通/10 发扩容分别使用 `MotionPolish20261027/DA_M24_SupportGrip` 与 `DA_M24_Mag10`；独立后握把使用 `SniperSkeletonStock::M24ProfilePath` 选择的对应握持层。
- `ue_m24` 默认 5 发，可选 `m24_extended_mag_10`。原厂枪托与托腮板合一，稳定 ID 仍为 `m24_cheekrest`。骨架后托为 `stock/sniper_skeleton_stock`，适用 SVD、SVCH、M24；与先进枪机分开装配。
- `body/m24_advanced_action` 解锁后握把改造。退回原厂枪机时归一撤除改造；骨架后托所需默认独立握把仍保留。完整握把替换已取代被否决的原厂托腕部裁片。
- `bolt/m24_carbon_light_bolt` 使用既有动作与加速时钟；M24 的被动暴击伤害增量为 +1.0。具体数值以本次配置键和消费者源码为准，不以旧说明覆盖当前配置。
- 实体镜内捕获保留枪体/镜体和周围场景；M24 上置 1× 与主体 6× 共用过渡时钟，其他高倍镜各自使用准星和刻度风格。相关源为 `PhysicalScopeView`、`PhysicalScopeScene.inl`、`M24ScopeDrawing`、`ScopeOpticalPresentation`，母材质作者入口为 `SharedPhysicalOptics20261030` 与 `M24PhysicalScope20261030`。

## 恢复顺序

1. 恢复有权使用的原始 M24/瞄具、认可 V9 手模、衣袖手套、握把与音效输入。保留 `Original`、`Donor`、作者场景、压缩姿态和仍被脚本读取的 Before/Backups JSON/GZ；这些不会因旧版本号而清理。
2. 初始比例/材质/分件与原生动作链见 `M24CustomScope20261026`、`M24Repair20261027`、`M24Hold20261027`、`M24MotionMagazine20261027`。后续动作在保存资产上局部修订，不从早期 FBX 重新覆盖原生骨架、权重与衣物 Morph。
3. 模型链：`M24AdvancedAction20261029/FullBodyV3` → `M24ReceiverGripRebuild20261031` → `M24ReceiverContinuityV220261031` / `M24StockContinuity20261031`。SVD/SVCH 共用后托入口在 `SkeletonSniperStock20261031`；M24 的后续独立握把与连接座取上述重构结果，不恢复初版裁片。
4. 表面链：`M24StockMetalFinish20261031` → `M24SurfaceRefine20261101/author.py` → `install.py`（含最终切线固化）。保持模型、UV 和材质区域，复用 donor 角点法线，只修新连接面；每个 LOD 的基底固化通过 `M24ChassisAssetTools`。不能重跑早期导入覆盖最终法线。
5. 手部链按普通/扩容、原厂/独立握把分别保留：`M24SprintShoulder20261031`、`M24RightGripFit20261031`、`M24ArmRoot20261031`。装备和空仓换弹的认可拉栓微动来自 `M24BoltMotionReuse20261031`；保留枪栓/手指轨道，以同一个刚体增量携带双臂根部。
6. 图标按 `M24IconsRebuild20261031` 与骨架后托图标作者源生成，沿现有厚金属框、灰阶侧视、实际部件轮廓规则。图标二进制仍保留本机。部署、取消、保存和旧存档继续使用原有稳定配件 ID。

根目录旧 README 是对应日期的交付记录；如与后续明确修订冲突，以这里列出的活动链、当前源码和保存回执为准。精简落盘回执在 `HistoricalReceipts/`。

## 归档与保留

176 个文件、1,032,415,647 字节移入 `trash/m24-retired-20261101/`，保留原相对路径。范围为被替代的 M24 资产/DLL 备份、明确否决的拉栓参考帧和旧图标。源/目标、原因、替代物、大小、SHA-256 见 `archive-manifest.json`；逐项移动与散列读回见 `archive-receipt.json`。脚本为 `Tools/Publication/Archive-M24_20261101.ps1`。`trash` 不进入 Git。

活动 Content、原始 Meshy/Sketchfab 输入、旧动作脚本的有效输入、近期材质前后对比及最终联机回执仍保留。早期有名称为 Before 的压缩姿态仍被后续作者读取，不能整目录删除。

完成使命的发布准备、暂存裁剪副本和私有宿主前置移入 `trash/m24-publication-prep-20261101/`，见 `publication-prep-archive.json` 与 `publication-prep-receipt.json`。恢复补丁前置时，先从该归档的 `SourceAssets/M24Publication20261101/PrivatePreimages/` 取回并核对散列；它们不作为第二份活动源码。提交/推送回执与最终暂存记录留在原发布目录供追溯。

## 已知状态与未覆盖部分

上轮用户要求的复查记录保存在 `HistoricalReceipts/review_result.json`：正式 Editor DLL 构建成功；本机真实 UDP 主机/客机/新建客机重连，每端 60 ms 延迟与 5% 丢包，六阶段两轮共 12 个主机记录；本机与远端 FX 初始化就绪。修复包含稳定部件编号、M24 原生上轴、`WPN_Eject` 解析与新目录 cook 纳入。

两网格各三 LOD 的历史读回确认三角几何/绕序/材质 ID 未变，法线和切线有效；UV 只核对了通道数，未逐坐标比较。构建、保存、无界面联机表现和渲染结果不是同一验收。

**仍需继续处理：骨架后托比黑色机匣偏亮，尚不能称为材质完全统一。** 公网/不同物理机器、打包运行、连续渲染的人体姿态、伤害/弹药权威和枪匠事务完整实战流程也未由这批历史检查覆盖。本次归档与发布没有改变这些结论。
