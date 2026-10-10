# 缚群 V20：重力垂布与巫婆织物适配

**后续反馈：** 用户于同日提供游戏截图，认为衣物仍像悬浮、效果不佳；V20 不合格。后续修订见 [V21](bound-congregate-garment-v21-20261009.md)，下文保留 V20 的实际制作和历史保存状态。

2026-10-09 用户确认继续制作。依据 [恢复方案](bound-congregate-cloth-resume-plan-20261009.md)，从 V19 混合母版保留身体、触手、骨架与铭牌，在独立场景重做衣物；V18/V19 的衣物不作为合格模板。

## 制作内容

- 主披布仅在肩背连接带采样实际身体，其余布面按裁片长度悬挂。离线重力、拉伸／剪切／弯曲约束及肉体接触用于制作静止垂布，结果保存为模型几何。该制作过程不是游戏布料测试。
- 固定带采用实际局部蒙皮，自由布面沿长度逐渐转为共同躯干支撑；避免袖口、脚、触手攻击骨拉着整片衣摆走。主披布肩部局部仍含其真实 donor 上段权重，以保持与原身体表面的连接。
- 褶皱采用不等距宽缓起伏后重力落定，显示表面平滑；宽裂口通过自由边轮廓形成，不删除零散三角面挖洞。仅自由边薄翻折，不对整个布面重复 Solidify。
- 两件残袖从实际同侧肢体截面制作。右侧骨轴偏离肉体中心，先按截面重新居中，再拟合袖管；保留腕掌空间。
- 主披布代理 1,170 点；左右残袖各 420 点，总计 2,010 个作者点。显示衣物分别为 4,740、1,703、1,680 顶点。此数量不包含身体、固定皮带和铭牌，也不是游戏帧率测量。
- 最大活动范围按新裁片定义：主披布约 20 cm、残袖 4.5 cm，固定区为零；不是直接采用巫婆长袍的 45 cm。

## 材质

复制当前巫婆 `M_WitchRebuilt_Fabric09` 为缚群独立母材质，沿用同一织纹法线／粗糙度资源、UV0 切线和两次织纹采样。保留灰绿主布、两件残袖的原身份色差，用原 G/B 通道补轻微磨损和衣摆污渍。

按实际显示网格面积／UV 面积制作约 4 cm 的纹理重复尺度：主披布约 27.0687、左袖约 26.4692、右袖约 26.8275。它们是平均密度校准，不声称各三角形密度完全一致。

巫婆 Alpha 原为两种织纹倍率的混合，而缚群 Alpha 是布料回拉遮罩。每个新实例把 `WeaveTiling` 与 `RepairWeaveTiling` 设为同一值，保留 Alpha 的布料用途，不影响原巫婆资产。法线强度 0.32、基础粗糙度 0.86，叠加小幅粗糙度变化。Blender 作者着色对既有 DirectX 法线翻绿，UE 继续使用原纹理约定。

## 布料与接入

- 继续使用 `UWitchRebuiltClothingAsset` 的显示／法线／切线稳定绑定和既有距离管理，无新增角色 Tick 或运行时逐顶点修形。
- V20 的衣内胶囊来自作者阶段空间解剖分区和肢体截面；不再以全身最大权重骨的顶点集合自动拟合这版衣内碰撞。配方为 `collision_recipe.json`，坐标为 UE 网格厘米；原生作者函数转换中心、长度和半径到各骨局部单位。
- 保留 4 次目标迭代、6 次上限、1 子步及非 CCD 预算；随新静止褶皱降低弯曲刚度并释放自由下摆的回拉。配置只影响名称为 `GarmentDrapeV20` 的新资产。
- 使用既有 V18 参数化导入器：prepare 保存独立网格、布料及死亡表面；外部重做连续软体嵌入；finish 保存死亡资产后切换原蓝图 VisualMesh。
- 蓝图其他属性不写回，保留用户当前移动、转向、CD、缠绕脱离及 V17 攻击合同。
- 本轮原生修改限于现有编辑器作者函数，新增碰撞配方只在制作期间读取。保存后的运行布料／碰撞不依赖 `SourceAssets` 中的 JSON。

## 文件与实际状态

- 作者：`Tools/BoundCongregate/author_garment_v20.py`。
- 模型及配方：`SourceAssets/BoundCongregateMeshy20261006/GarmentDrapeV20/`。
- 材质：`Tools/BoundCongregate/materials_garment_v20.py`。
- 接入：`import_garment_v20.py`、`prepare_garment_v20_editor.py`、`finish_garment_v20_editor.py`。
- 软体制作：`author_soft_corpse.py --garment-v20`。
- 编译：首次尝试现有编辑器互斥桥时，原编辑器已经退出，未发现节点，也未执行本次 Live Coding。之后由 `finish_garment_v20.ps1` 等待当前后台导入释放二进制，执行普通 Editor/Game 构建并通过 commandlet 接入；没有启动交互编辑器。
- 目标：`/Game/Monsters/BoundCongregate/GarmentDrapeV20/SK_BoundCongregate_GarmentDrapeV20`；角色入口仍为原缚群。

## 最终落盘状态

模型源与 FBX 已制作。Editor 和 Game 的 Development 构建均返回成功，本次增量构建判定产物已是最新；没有 Clean/Rebuild。

后台 `UnrealEditor-Cmd` 已完成新骨架、网格、三件布料、独立材质、匹配连续软体死亡网格／数据及原蓝图 VisualMesh 的保存，进程退出码为 0。`delivery.json` 的 `saved`、`prepared` 均为 true；原蓝图现在引用 V20 网格。`material-delivery.json` 记录新母材质和三个实例全部保存。

导入时 FBX 报旧母版的绑定姿态相对矩阵警告，随后记录重新创建绑定姿态成功。巫婆捕获器对主披布 4,740 条映射进行了 239 条修正，其中 23 条采用局部原蒙皮回退；两件残袖没有局部回退。这里是导入／绑定的制作回执，不代表实际动作和布料表现通过验收。

记录：`authoring.json`、`author-delivery.log`、`collision_recipe.json`、`build-FPSGAMEEditor-console.log`、`build-FPSGAME-console.log`、`import-final.log`、`delivery.json`、`material-delivery.json`，均在本版 SourceAssets 目录。第一次桥接的失败记录保留为 `compile-editor-01.txt`，不作为编译成功证据。

未启动游戏、PIE、预览渲染、静态检查或测试；新衣物效果由用户从 F6 的原缚群入口重新生成后体验。旧 V19 身体输入与完整资产保留可恢复，未提交或推送。
