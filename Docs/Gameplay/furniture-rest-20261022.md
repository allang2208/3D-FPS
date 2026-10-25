# 家具坐卧交互

本轮为现有 Jason 玩家身体制作坐下、沙发靠坐、床上躺卧动作。动作和家具外观分开：使用已有家具网格，位置按各模型的座面、床面与朝向配置。

## 操作

- 2.5 米内准星命中可用家具时，显示与搜索容器同一材质的轮廓和 E 提示。
- E 进入；坐稳／躺稳后 E、空格或 WASD 起身。坐卧期间可转动视角，收起武器并锁住移动和战斗输入。
- 椅子、沙发、床、低矮下铺各有 Enter／Idle／Exit，共 12 个完整骨架动画。待机包含呼吸，起身使用独立节奏；下铺进入先低身，离开上层床架后再恢复站姿。
- 三座沙发和长椅取最靠近命中位置的座位；实例化家具只绘制命中的单个实例轮廓。
- 翻倒家具不提供坐卧入口。上下铺目前只接下铺；上铺未制作攀爬上床。
- 起身从原进场位置及家具周围候选中寻找有地面且胶囊无阻挡的位置；没有位置时继续保持坐卧，等待再次操作。
- 此功能不修改体力、生命、SAN 或天气时钟，不提供睡眠恢复或跳时。

## 家具范围

实际路径、座位和朝向见 `Content/ColdSteelData/furniture_rest.json`，共 21 个具体网格路径。覆盖生活区椅子／沙发／更衣长凳／四款下铺、接待大厅对应椅子／沙发／长凳、医务室办公椅／会客椅、候诊长椅、正放病床及原始病床、公寓基础及 RefinementV2 的双人床、公寓 RefinementV2/V3 训练凳。

训练凳只接入坐姿。工作台、土壤种植床、床下储物柜、建筑样例的风格化床不按名称自动纳入。双人床当前每张配置一个卧位。病房翻倒床仍保持原布景及碰撞。

家具保持现有 Actor、StaticMeshComponent 或 ISM，不修改地图、生产目录或原模型包。匹配使用完整网格路径；后续换模型需在该配置添加对应座面和方向，不能只改显示名。

## 动作资源调查

- [Fab：Dead Bodies Sitting & Lying Poses](https://www.fab.com/listings/63ed216a-416f-4337-a2a9-0a3ba69aa6f2)：Fab 免费列表列为 Free，内容为 21 个卧姿、9 个坐姿的单帧尸体姿势，不提供本轮所需的完整休息进出动作。免费使用与开源不是同一概念；本轮未下载或接入此包。
- [GitHub：Overte](https://github.com/overte-org/overte/tree/master/interface/resources/avatar/animations)：包含 sitting_idle、sitting_idle02～05、坐姿挪动和交流 FBX；仓库 [版权清单](https://github.com/overte-org/overte/blob/master/debian/copyright) 标记 Apache-2.0。它提供可继续研究的坐姿来源，本轮未抽取或转授权其二进制。
- [Fab：Sitting Animation Pack](https://www.fab.com/listings/e1bc5d46-f0fb-40fb-bff8-4a730816bcd1)：有坐姿动作，但本轮页面不足以确认免费获取，不作为已获得的免费素材。

本轮交付的 12 段动画由本项目在现有 Jason 骨架上制作：双腿／双臂 IK、按阶段的姿态曲线、呼吸与独立起身节奏；没有使用外部包的动作数据。沿用项目已有角色骨架，不意味着该角色资源可单独公开再分发。

## 代码和制作入口

- `Source/FPSGAME/Movement/FPSFurnitureRestComponent.*`：命中解析、单实例轮廓、服务端坐卧状态、占位、动作时钟、站立位置、相机和清理。
- `FPSGAMECharacter.cpp`：为玩家创建并复制家具交互组件。
- `Source/FPSGAME/Characters/FPSBodyFurnitureLayer.inl`：按座面与地面高度差修正脚部支撑。
- `FPSPlayerBodyAnimInstance.*`：在既有动作层之后、死亡层之前应用完整坐卧姿势。
- `FPSGAMEPlayerController.cpp`、`ColdSteelHUDWidget.cpp`：接入现有 E 键、准星提示和输入占用。
- `FPSPlayerBodyCamera.cpp`、`FPSPlayerFirstPersonBody.cpp`、`FPSPlayerBodyComponent.cpp`、`FPSPlayerBodyEquipment.cpp`：坐卧镜头、第一人称身体及手持装备可见性。
- `Tools/FurnitureRest/author.py`：离线作者源，使用本地 Python 3.11 的 NumPy/SciPy；`--profiles-only` 仅重写家具配置，不重做动作。
- `Tools/FurnitureRest/read_support_geometry.py`：读取原家具 FBX 的支撑面，用于病床和候诊椅配置，没有渲染场景。
- `Tools/FurnitureRest/save_assets.py`：保存本任务新动画包，完成压缩后逐包记录；使用共享配置事务只追加本任务的 `Rest.*` 键。

产物位于 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022`，已加入打包目录。作者数据、支撑面数据、保存回执和构建日志位于 `SourceAssets/FurnitureRest20261022`。

## 联机与存档边界

客户端通过所属 Pawn 组件请求操作；服务器重新执行距离／遮挡／家具方向判定并决定座位、退出位置和阶段。相邻玩家占位在进入时排除；复制阶段、锚点和服务端时间供其他端播放。没有信任客户端提交的座位坐标。

坐卧是临时状态，不写人物存档。失去控制器、家具销毁／移动或死亡时释放状态；受伤后在已坐稳状态请求起身。衣服继续跟随原共享身体骨架。本轮没有运行联机或游戏测试，不把源码中的复制路径当作实际联机验收。

## 交付记录

2026-10-23：共 12 个动画已通过后台 commandlet 保存，退出码 0，最终日志含 `FURNITURE_REST_INSTALLED 12`。共享动作键和 21 个家具网格配置已落盘；FPSGAME 与 FPSGAMEEditor 最终常规构建均成功。记录见 `delivery.json`，构建日志为 `build-game-complete.log` 和 `build-editor-complete.log`。

未启动游戏、PIE、预览渲染或运行测试。动作接触、相机舒适度、不同家具的坐卧效果及联机表现由用户在游戏中测试；此记录不宣称已获视觉认可。未提交或推送 Git。

## 2026-10-23 用户要求检查与 GIF 预览

本节是交付后的检查结果。已从保存的 12 个动画包读回姿态，并读取当前身体与椅子、沙发、公寓床、下铺的实际网格。骨架匹配；所有姿态数值有限；各段首尾位置与作者数据的最大差约 0.00000052 cm。此项只证明数据保存和读回一致。

视觉检查结论：**当前版不通过，需要继续修改动作与锚点。**

- 沙发座位太靠后，小腿穿入坐垫与前沿。
- 普通床进入／起身时，身体经过床面，缺少从床边上床、下床的专用路线。
- 手腕／手掌翻转过度，支撑接触和重心转换不自然。
- 下铺仍需从侧面安排进出，避开梯子和床架；仅降低身高不能替代合理路线。

GIF 位于 `SourceAssets/FurnitureRest20261022/Review20261023/sitting_review.gif` 和 `lying_review.gif`，另有四类单独 GIF。它们是保存动画及实际模型的中性材质离线预览，不是游戏录屏；椅子与沙发预览复现了运行代码的座面高度和脚部 IK 修正。头部使用同角色的源几何跟随头骨，省略毛发和面部动画。

本次没有修改生产动作、家具配置或运行代码。尚未在游戏里录制 E 交互、镜头切换或联机流程。详细数据检查见同目录 `review.json`。

## 2026-10-23 RefineV2 当前版本

本节取代上文初版的动作数量、锚点、路线及脚部修正说明。初版及失败预览保留为制作记录。

- 36 个原生 Jason 动画、12 个尺寸／姿态类型；每类包含进入、呼吸保持、起身。共享配置通过 `config_transaction.py` 仅更新本任务的 `Rest.*` 键。
- 覆盖原有 21 个具体网格路径、32 个座位／卧位。候诊长椅按实际四座分配；医务室两把椅子的朝向已修正。
- 椅子、沙发及长凳分别标定坐骨支撑和座面前沿。每帧解算双腿，双脚在地面上；手掌随大腿位置调整，不再使用固定手腕翻转角。
- 床铺从侧边坐下，手掌支撑，先抬腿越过床沿，再转入床面并躺平。下铺从梯子对侧进入，在头部接近上铺之前低头。短病床保留屈膝卧姿，避免脚尖撞脚端栏杆；病床枕头和四款下铺单独检查肩颈与头部支撑。
- 腰背、胸肩、颈部和头部分段转动；躺稳后按实际枕头高度调整颈部。起身保留独立节奏，末尾留站稳时间供正常移动姿势接回。
- 运行时读取类型的座面高度、进场偏移及朝向。移除了初版固定 46 cm 根高度、50 cm 前移与整段下沉；V2 脚部支撑已烘焙，`FootDrop()` 返回零。
- 相机跟随头部位置、俯仰和侧向转身。退出只使用该动作实际到达的侧边位置；位置被占用时保持坐卧。进场胶囊扫掠禁止直接穿过家具或墙面就位。
- 保留搜索容器同款高亮与 E 交互、输入占用和服务端状态复制。适配对象为正常正放、原始尺寸的家具；上铺攀爬和改过尺寸的实例没有新动作。

作者入口为 `Tools/FurnitureRest/refine.py`。旧 `author.py` 是初版记录。新版资产目录为 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2`，Cook 指向新版子目录，旧动作包保留但不再被当前动作键引用。

作者数据、资产保存回执、几何采样、构建日志和核对报告集中在 `SourceAssets/FurnitureRest20261022/RefineV2`。`read_all_geometry.py` 读取全部配置家具；`audit_geometry.py` 对实际蒙皮身体及头部做几何采样，使用 0.7 cm 阈值和三方向射线判断。采样检查有精度与覆盖范围，不等同于所有帧、所有装备的游戏内碰撞证明。

用户本次明确要求自行检查与继续修复，已执行多轮实际网格预览及接触修正。最终 `ReviewSaved` 通过 UE 的 **Compressed** 求值读回已保存动画；另外读取 Source 首尾，用于确认作者数据确实保存。GIF 为实际项目几何、已保存压缩动作的中性材质离线预览，包含进入、保持和起身；不是游戏录屏。

没有启动交互式编辑器、PIE 或联机游戏。E 键实际操作、HUD 实际渲染、联机时延及不同装备外观尚未进行游戏内验收。后台保存、构建、压缩姿态读回和离线动作检查分别记录，不混作游戏内通过。


### RefineV2 保存与检查回执

36 个动画均已保存，后续下铺净空修正的 3 个包保存到 `RefineV2/BunkClearanceV2`，当前动作键已切换。保存及最终读回 commandlet 均正常退出。Editor 与 Game 构建成功。最终检查读取压缩动画，覆盖进入、保持和起身；21 个资源路径、32 个座位的采样标记数为 0，脚部最低点约 0.26 cm 高于地面，进出位置胶囊相对家具网格最小净距约 2.72 cm。头部支撑间距约 0.27～1.52 cm。几何采样阈值 0.7 cm，不宣称每个三角形、任意装备和网络场景均已游戏内验证。

GIF：`RefineV2/ReviewSaved/sitting_review.gif`、`RefineV2/ReviewSaved/lying_review.gif`。数据核对见 `verification.json`，汇总见 `delivery.json`。未提交或推送 Git。


## 2026-10-23 SofaSupportV3 手部支撑修正

按用户反馈重做沙发手部衔接。中间座位双手错时扶住身侧坐垫；左右端座位的外侧手扶扶手，内侧手扶坐垫。手掌接触后固定位置，肩肘配合躯干放松，起身时先支撑再松手。指节减小原始屈曲，使掌根更贴近支撑面；胸背适度后靠，头部回正。原骨盆、腿、脚局部轨道逐帧保留。

Sofa、SofaLeft、SofaRight 各有 Enter/Idle/Exit，共 9 段，接入生活区及接待厅两款沙发的六个座位。资产保存到已 Cook 的 `RefineV2/SofaSupportV3` 子目录。只更新本轮动作键、相机元数据与对应座位类型；其他配置和并行的 `Rest.ApartmentSofa.*` 保留。玩家动作表使用原 scoped transaction；家具表使用专用的读取后比对、备份及原子替换，修改前复核最新内容。

保存 commandlet 最终退出码 0，压缩姿态读回核对通过，阶段边界最大位置差约 0.0033 cm。六个座位的进入、保持、起身几何采样无超过 0.7 cm 阈值的标记。记录：`SourceAssets/FurnitureRest20261022/SofaSupportV3/verification.json`。预览：同目录 `ReviewSaved/sofa_support.gif`，左侧中间座位、右侧扶手座位。预览使用已保存压缩动画及实际网格；未运行游戏内 E 键或联机验收。


## 2026-10-23 SofaNaturalV4 反弓修正

用户指出 V3 腹部前拱、坐姿仍然僵硬。原因是为保持两手低位触碰坐垫，在骨盆姿态不变时给胸椎额外增加 32 度后仰，导致骨盆与胸椎的相对转角约 33.56 度；无穿插不代表姿态自然。V3 的视觉结论已由本节修正。

V4 取消该后仰，胸椎回到骨盆上方，腰背只保留小幅自然曲度与朝支撑手约 3 度的侧倾。靠扶手座位使用外侧手搭扶手、内侧手放腿上；中间座位一手轻搭坐垫边缘、另一手放腿上，不再强迫双掌压到过低的坐垫面。原骨盆与双腿局部轨道未改。

已保存并接入同样九段新动作，目录为 `RefineV2/SofaNaturalV4`，旧 V3 资产保留作对照。后台保存和压缩姿态读回均正常退出。当前坐稳时骨盆与胸椎的相对转角最大约 5.48 度；阶段边界位置差约 0.0033 cm，六个座位的进入、保持、起身几何采样无超过 0.7 cm 的标记。额外使用同机位侧视图检查腹部及腰背轮廓，不能把这些离线检查当作用户的审美认可。

旧新对比 GIF：`SourceAssets/FurnitureRest20261022/SofaNaturalV4/ReviewSaved/sofa_before_after.gif`；侧面对比：同目录 `side_before_after.jpg`；数据：`SofaNaturalV4/verification.json`。本轮没有修改原生 C++ 或重启已打开的编辑器，未做游戏内 E 键与联机实测。


## 2026-10-23 坐卧鼠标转头输入修正

用户报告第一人称坐卧时镜头仍锁定。当前家具相机已有独立 ControlRotation、水平自由转头和上下 85 度范围，但 `AFPSGAMEPlayerController::InputKey` 在坐卧期间按 `IsMouseButton()` 拦截输入。UE 5.8 的 MouseX、MouseY、Mouse2D 同样带 MouseButton 标志，因此移动鼠标在到达 Turn/LookUp 之前就被吞掉。

本次仅将三个转头轴从该拦截条件排除，继续沿原输入路径处理；鼠标点击、滚轮和快捷栏仍被阻止。角色身体仍由坐卧组件固定，开菜单后的输入规则不变。没有清空其他系统的 IgnoreLookInput，也没有修改家具动作资产。FPSGAMEEditor 与 FPSGAME 的 Win64 Development 后台构建均成功，构建记录位于 `SourceAssets/FurnitureRest20261022/FreeLook20261023`；本轮未启动游戏做视角实测。

## 2026-10-23 RelaxedSeatV5 深坐与手部放松

用户允许脚悬空，要求坐得更深、手部更自然。本版不再要求坐稳时双脚落地：臀部相对原座位锚点向后移动 24 cm，大腿保持接近水平、小腿在家具前缘外自然下垂，两脚略有前后差和跖屈。退出使用独立时序，先前移到座沿并落脚，再站起，避免深坐位置直接上升。腰背保留轻微自然曲度，不通过胸椎后仰来凑手部接触。

中间座位双手错开放在腿上；左右扶手座位以外侧手搭在扶手圆角前缘，手指向下垂、腕部随前臂走向，另一手搭腿。原生参考姿态本来就有指节弯曲，因此扶手手指适当舒展而非继续叠加握拳。两手不同时间落下、抬起，手指略晚于肩肘就位，保持阶段有小幅呼吸与指节变化。所有轨道维持原骨长。

覆盖 StaffLiving 与 ReceptionHall 两种通用沙发，以及当前独立配置的 ApartmentSofa 加宽沙发，共九个座位、六种坐姿变体、十八段进入/保持/退出动作。公寓扶手按实际 1.2 倍平面缩放适配；预览与几何检查也同步使用组件缩放和缩放后的座位锚点。普通椅子、长凳、卧姿和第一人称自由转头逻辑未修改。

作者脚本 `Tools/FurnitureRest/relaxed_seat.py`；资产已保存到 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2/RelaxedSeatV5`，保存命令正常退出。`player_body.json` 仅通过公共事务写入本版十八个动作键，家具配置从当前文件读取后仅合并对应动作、类型与座位变体，不覆盖公寓床或其他并行配置。来源、保存回执与离线检查结果位于 `SourceAssets/FurnitureRest20261022/RelaxedSeatV5`。

保存后的十八段压缩动作已读回检查，阶段交接最大骨点位置差约 0.0088 cm、旋转差约 0.161 度；九个座位的全阶段几何采样无超过 0.7 cm 阈值的穿插标记。已查看侧面坐姿和进入/退出分帧图，修正了初稿指尖穿扶手及手腕上翘的问题。实际保存动作的离线 GIF 为 `RelaxedSeatV5/ReviewSaved/relaxed_sitting.gif`，数据为 `verification.json` 和 `delivery.json`；本轮未启动游戏、未做 E 键或联机实测，不将离线结果当作用户审美认可。

## 2026-10-23 HangingEntryV6 先垂手再入座

用户要求入座前双手自然下垂，再缓慢过渡到搭放。V5 站姿的腕部目标过低、超出骨链可达范围，导致肘屈曲仅约 4 度；进入前段还在沿用这一接近伸直的解。V6 将悬垂腕点限制在实际臂长的 97.3%～97.7%，起始左右肘保留约 24.6/26.7 度的轻微弯曲，掌心朝向大腿、指尖向下，并在身体外侧留出指节空间。

扶手侧从约 0.55 秒开始抬手，另一侧约 0.68/0.8 秒后跟随，分别在 2.18/2.36/2.5 秒接回 V5 已有落点。肩肘先走、转腕略后、手指最后收拢到搭放姿势，路径从大腿外侧绕过。起身最后一段同步返回相同垂手姿势，保证退出与下次进入的端点一致。骨盆、脊柱、头部、腿脚、时长、相机轨道和六段保持动作保留 V5，不另写家具配置。

`Tools/FurnitureRest/hanging_entry.py` 为作者入口，十二段 Enter/Exit 新资产已保存至 `RefineV2/HangingEntryV6` 并按角色键事务接入，六段 Idle 继续引用 V5。源文件、保存回执、分帧预览与检查记录位于 `SourceAssets/FurnitureRest20261022/HangingEntryV6`。新增手部对躯干/大腿检查按骨骼层级排除整条手臂，避免把腕部辅助骨误当成身体，或把 indextoe 当成 index 手指；入座前段三个通用座位的 15 个姿态样本无超过 0.5 cm 的标记，九个家具座位全阶段采样无超过 0.7 cm 的标记。

本版保存及压缩动作读回均正常退出；十八段组合的阶段交接骨点误差最大约 0.0095 cm、旋转差约 0.161 度，六段 Idle 和所有非手臂源轨道与 V5 相同。保存后九座位采样仍无超过 0.7 cm 的标记，已查看最终分帧图。新旧同机位对比 GIF：`HangingEntryV6/ReviewSaved/entry_before_after.gif`；本轮未运行游戏或联机测试。

## 2026-10-23 ReversedExitV7 按入座倒放起身

用户指出起身手部仍僵硬，要求参考入座倒放。六种沙发座位的 Exit 改为逐帧反向复用 HangingEntryV6 的 Enter，反向运动 2.8 秒，随后保持自然垂手站姿 0.3 秒，总时长仍为 3.1 秒。手指、手腕、肘和肩沿同一条反向轨迹依次离开支撑；身体和腿脚采用对应的反向时序，约 1.65 秒回到座沿并落脚后，再完成站起。已有 Enter、Idle、座位锚点与自由转头逻辑保留。

作者入口 `Tools/FurnitureRest/reverse_exit.py`，只新增并接入六段 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/RefineV2/ReversedExitV7` 起身资产。对应 Exit 相机位置从同一姿态重新生成，并只合并六个动作的元数据；家具类型、座位、其他动作和并行配置保持当前文件内容。后台资产保存正常退出，回执位于 `SourceAssets/FurnitureRest20261022/ReversedExitV7`。

保存后的十八段组合已读回，六段新 Exit 的源姿态逐帧等于对应 Enter 的倒序加九帧站姿保持，十二段 Enter/Idle 保持原版。阶段交接骨点误差最大约 0.0113 cm、旋转差约 0.046 度；九座位几何采样无超过 0.7 cm 的穿插标记。已查看最终起身分帧图；同机位旧新 GIF 为 `ReversedExitV7/ReviewSaved/exit_before_after.gif`。本轮没有启动游戏或执行联机测试。

## 2026-10-23 BedNaturalV8 躺床动作优化

按用户要求检查并优化当前全部床铺：Bed、BedKing、Bunk、Hospital、Ward、ApartmentBed 六类，覆盖 11 个具体网格路径及 18 段进入、保持、退出动作。公寓床按当前 1.4 倍平面缩放适配，四款下铺分别检查被褥与床架。原沙发、椅子动作及第一人称自由转头逻辑不改。

入床前双手自然下垂，保留轻微屈肘；支撑手先扶床面，另一手稍后跟随，两条腿错时抬起、转入床面。躺稳后再把左手缓慢移到腹部，降低肘部支点，舒展手指；右手留在身体旁。补充 0.6 秒手部安放时间，起身逐帧反向复用进入动作，并保留 0.3 秒站稳。普通床进入/退出为 5.2/5.5 秒，公寓床为 5.9333/6.2333 秒。

根据实际床面重新标定头颈和枕头接触。预览原来把含有肩颈皮肤的整个头部网格刚性跟随头骨，导致枕头接触读数不可靠；本版从 UE 读取头部蒙皮权重，按运行时 CopyPoseFromMesh 的身体骨骼祖先计算中性面部姿态。后脑支撑测量与肩颈皮肤分开，旧预览的头部间距不能直接与本版混用。仍省略毛发与面部表情动画。

病床将躯干向床头移动，缓解过度屈膝；床脚位置按骨链可达范围调整，保持原骨长。原卧姿脚跟离床面约 6～8 cm，本版降低脚跟并重新解算双腿。下铺支撑手增加绕过被褥的抬手弧线及少量局部高度，避免一款褶皱被褥在起身时擦到手指。

作者入口为 `Tools/FurnitureRest/bed_natural.py`。最终动作目录为 `RefineV2/BedNaturalV8/ContactRefine`，首轮资产保留作制作记录。动作表通过公共事务仅更新十八个床铺角色键；两份家具配置仅更新对应动作时长和眼位轨道，沿用现有家具锚点和交互。过程数据、源姿态、头颈与脚跟标定、保存和读回日志位于 `SourceAssets/FurnitureRest20261022/BedNaturalV8`。

本轮检查包含床体及头颈蒙皮采样、手掌对躯干/腿的采样、阶段衔接、倒放关系和眼位轨道；最终回执以该目录 `verification.json`、`delivery.json` 为准。GIF 为实际保存压缩动画与项目几何的中性材质离线预览，位于 `ReviewSaved/bed_and_bunk.gif`、`ReviewSaved/apartment_and_hospital.gif`，另有六类总览。没有启动交互式 UE 编辑器、PIE 或联机游戏，游戏内交互和装备组合仍未验收。

最终保存及读回 commandlet 均以退出码 0 完成。按约 15 Hz 读回压缩动作后，11 个模型的进出及保持采样无超过 0.7 cm 的床体穿插标记，六类动作的双手与身体采样无超过 0.5 cm 的标记。阶段交接最大误差约 0.0079 cm / 0.134 度，眼位轨道已随新头颈姿态重新生成。脚跟对床面的最低采样间距约 -0.07～0.79 cm；这些结果只覆盖本轮身体、头部与家具几何，不作为任意衣物装备或游戏内联机通过的证明。

## 2026-10-24 BedSupportedV9：修复悬空和腿部内拧

用户否定 V8，指出悬空、腿部扭曲，要求坐到床上参考沙发入座。V8 的穿插采样结论不能证明关节转向正确或身体受到支撑；V8 进入/退出不再作为有效动作模板。旧版部分床型的膝关节相对正常屈伸轴偏差超过 100 度，普通床单帧骨骼转角最高约 27.57 度。旧床沿骨盆位于床边外侧，且抬腿后仍使用固定骨盆高度，造成支撑不足。

V9 读取 HangingEntryV6 的 Sofa.Enter 0～1.15 秒，复用入座重心、脊柱和腿部关节参考，映射到各床型床沿内侧。双腿用同一解剖屈伸轴解算，脚点与膝盖方向随身体统一转动，不再把不同时间的脚、膝目标混在一起；保持原骨长。先坐稳，再错时抬腿、转入床面。按真实臀部蒙皮与床面标定入床阶段的骨盆高度，双手在身体侧后方支撑并错时换位，避免转身时手掌穿到腿下。下铺先屈膝降低身体、低头，再进入低净空区。

六类床沿用既有 11 个模型路径、锚点、高亮和自由转头逻辑，更新十八段动作及对应眼位轨道。进入 5.8 秒，退出为进入倒放加 0.3 秒站稳，共 6.1 秒；保持动作 4 秒。作者入口 `Tools/FurnitureRest/bed_supported_v9.py`，输入、接触标定、骨骼检查、保存与读回回执位于 `SourceAssets/FurnitureRest20261022/BedSupportedV9`，最终结果以 `verification.json` 与 `delivery.json` 为准。

检查新增膝关节偏轴、骨长、阶段交接及臀部支撑测量，并保留身体/头部对家具、双手对身体的采样。预览为保存压缩动画和实际蒙皮几何的离线渲染，旧新同阶段对照为 `ReviewSaved/bed_before_after.gif`。不将离线通过视为用户认可或游戏内、任意衣物及联机验收。

压缩姿态的帧间采样另外暴露了下铺和高位病床各一处拇指擦被褥：`bed_supported_thumb_clearance.py` 在对应短时段仅增加 1.3/1.5 cm 抬手弧线，保持所有腿部轨道不变，分别保存到 V9 的 `BunkThumbClearance`、`WardThumbClearance` 子目录。完整重制顺序为主作者脚本、该手部细修脚本、保存及按键接入。两次局部更新后重新回读、检查和重渲染对应床型，其他床型使用同一版已保存动作的检查与帧序列。

最终十八段动作保存、重新读取均正常完成。压缩动作中六类床的膝关节最大偏轴小于 0.001 度，骨长保持；阶段交接最大差约 0.0103 cm / 0.118 度。11 个模型的床体采样无超过 0.7 cm 的标记，手部对身体采样无超过 0.5 cm 的标记。已查看床沿坐下、抬腿、转身和最终手部修订分帧，并生成对照 GIF；没有启动游戏进行交互或联机验收。

## 2026-10-24 BedHandDriveV10：通过手臂支撑表现挪动

用户指出 V9 的挪动僵硬、像整体平移。排查发现，转入床面时两只手的目标随骨盆移动，手掌没有真正固定在床上，无法表现承重。V10 将挪动改成找支点、屈肘承重、撑臂带动躯干和骨盆跟进、另一只手换位的交替过程。普通床、公寓床、下铺和普通病床分两次挪动，加大床与高位病床分三次。身体转向与平移跟随这两个或三个发力时段，中间保留换手停顿。

支撑期间手掌固定在家具坐标中，根据实际床面和整段肩部运动寻找可达支点；手腕与手指随手掌保持接触。手离床后先抬起，再绕开身体换位。脊柱分段承担重心转移和左右承重倾斜，头颈适当反向补偿，避免一处腰部折转和抬头仰望。下铺单独抬高肘部路径，较宽床和高病床的收手增加向外绕行；最后一次挪动完成后及时卸力收手，再进入躺下。

保留 V9 的腿部解剖屈伸轴、骨长、床沿接触高度和最终六段 Idle，只对原有下半身姿态按支撑节奏重新采样。起身沿新进入动作倒放并加 0.3 秒站稳。两次挪动的 Enter/Exit 为 6.7/7 秒，三次为 7.6/7.9 秒；相机位置轨道随新姿态同步生成，自由转头逻辑保留。继续覆盖六类床与 11 个模型路径。

作者入口 `Tools/FurnitureRest/bed_hand_drive_v10.py`，制作输出目录 `SourceAssets/FurnitureRest20261022/BedHandDriveV10`。`choreography.json` 记录换手、支点、发力时段和逐帧目标；`hand_drive_saved.json` 记录保存压缩动作中的固定手掌误差及承重期间屈肘范围。十二段新 Enter/Exit 保存到 `RefineV2/BedHandDriveV10`，六段 Idle 复用原资产。配置按动作角色键合并，最终保存与离线检查结果以该目录的 `verification.json`、`delivery.json` 为准。

保存后的密集采样发现下铺换手途中掌缘擦到一处被褥褶皱，额外提高 4 cm 抬手弧线，最终下铺两段资产位于 `BedHandDriveV10/BunkContactClearance`；其余五类沿用首轮已保存资产。支点误差采用 UE 直接在 30 Hz 设计时刻求值压缩动作并读取 WORLD 骨骼位置，原先把 15 Hz 离线预览姿态插到 30 Hz 会引入额外关节插值误差，不用于判定实际手掌滑动。直接读回的六类最大支点误差约 0.0083 cm；普通床承重期间左肘屈曲约 37～62 度、右肘约 24～54 度。

家具动作库当前为进程内静态缓存；已经运行过旧动作的编辑器需重启后读取新的时长与眼位配置。制作过程仅使用后台 commandlet，没有重启正在运行的编辑器。

最终保存与新进程读回均以退出码 0 完成。十八段组合的阶段交接最大误差约 0.00892 cm / 0.118 度；六类膝关节偏轴最大约 0.00104 度，骨长保持。按约 15 Hz 读回压缩姿态，11 个床体模型采样没有超过 0.7 cm 的穿插标记，六类手部对身体没有超过 0.5 cm 的标记。已查看最终六类阶段分帧与手臂近景。`ReviewSaved/bed_hand_drive_detail.gif` 为手臂近景慢放对照，`bed_before_after.gif` 为完整旧新流程对照，另有床型组合 GIF。均为实际保存动画和项目蒙皮几何的中性材质离线预览；未进行游戏内或联机验收。

## 2026-10-24 改用完整上床动作来源，等待 Meshy 导出

用户再次否定 V10 的自然度，要求寻找实际上床动作，并明确素材必须可商用、可发布。V10 的数值检查不代表用户认可；当前仍保留其运行时引用，不能将其记录为已验收版本。SAMP、TRUMANS 的非商业数据不进入项目。Mesh2Motion CC0 源动作已经离线预览，Sleeping 是卧姿保持，LayToIdle 是地面起身，均不是完整上床进入段。

用户确认有 Meshy 会员并授权使用 Meshy。下一候选为官方 `Sit_Lie_Bed`（action_id 371）；官方条目说明 Pro 及以上导出可商用，并支持 FBX/GLB。该结论来自条目说明，尚未取得或检查会员导出的实际动作。来源记录位于 `SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024/source_request.json`。

本轮会话没有可用的浏览器控制通道，本机也未配置 Meshy API 凭据，定向查找下载目录未发现该动作。需要从会员账号导出含人物、骨架和完整动画的 FBX（也可 GLB），保留原始时序与位移。源文件到位后先运行 `Tools/FurnitureRest/inspect_meshy_bed_source.py`，记录骨架、帧率、动作范围与文件散列，保留未重定向的 Blender 场景供检查。该入口仅已编写，尚未用 Meshy 文件执行；没有新增或接入 UE 动作资产。

后续先适配普通 Bed 的进入段，按原动作检查坐稳、手臂承重、抬腿、转躯干和躺下，之后再判断其余床型适配。不能只按动作名称推断全过程完整，也不能把新来源重新压成 V10 的程序位移时序。

## 2026-10-24 ChairReuse：推广到其余可交互椅子

用户将当前工作优先级改为复用坐姿到其他可交互椅子。按运行时 `FPSFurnitureRestComponent` 实际读取的模型路径和座位配置，本次覆盖 9 个椅子／长凳模型、16 个座位、6 种动作类型。当前三款沙发已经使用 V5/V6/V7，继续沿用；床铺素材获取仍待 Meshy 文件。

| 类型 | 家具范围 | 模型数 | 座位数 | 本版坐深／手部落点 |
| --- | --- | --- | --- | --- |
| Chair | 员工生活区、接待大厅普通椅 | 2 | 2 | 加深 8 cm，双手搭腿 |
| Chair50 | 医务办公室会客椅 | 1 | 1 | 加深 8 cm，双手搭扶手 |
| Chair52 | 医务办公室人体工学椅 | 1 | 1 | 加深 14 cm，双手搭扶手 |
| Chair53 | 公寓训练凳 V2、V3 | 2 | 2 | 加深 10 cm，双手搭腿 |
| Chair55 | 四座候诊椅 | 1 | 4 | 加深 14 cm，双手搭腿 |
| Bench | 员工生活区、接待大厅更衣长凳 | 2 | 6 | 加深 8 cm，双手搭腿 |

复用 RelaxedSeatV5 的放松躯干与坐稳姿态、HangingEntryV6 的先垂手再落手节奏、ReversedExitV7 的入座倒放规则，保留原生骨长。各椅型保留原有座面高度和进出锚点，再按实际坐深适配。深坐后小腿自然悬垂，不强制把脚拉到地面；膝关节使用既有解剖屈伸轴方法。无扶手座位的手指舒展，拇指从大腿外侧经过后落手；扶手座位先抬手越过扶手，再逐渐落下。入座 2.8 秒、保持 4 秒循环、起身 3.1 秒（倒放 2.8 秒加站稳 0.3 秒）。

作者入口为 `Tools/FurnitureRest/chair_reuse.py`，保存入口为 `save_chair_reuse.py`，发布入口为 `publish_chair_reuse.py`。Jason 新资产保存到 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/ChairReuse20261024`；通过项目既有 `RTG_Jason_Kaitlin` 重定向的 Kaitlin 资产保存到 `/Game/Characters/KaitlinPlayer20261023/ChairReuse20261024`。男女各 18 段，共 36 段；后台 commandlet 退出码 0，保存后时长与家具阶段一致。

通过共享配置事务只更新 `player_body.json` 的 18 个默认动作键及 Kaitlin 对应 18 个键。`furniture_rest.json` 使用现有家具写入锁、字段差量与原子替换，仅更新相应 18 段时长／眼位轨道。家具路径、座位数量、交互高亮、E 键入口和自由转头仍由现有公共实现承接；无需修改 C++。正在运行的进程如果已经缓存旧家具动作库，需要在下次启动时读取新配置，本轮未主动打开或重启编辑器／游戏。

按本对话此前的动作自查要求，离线检查覆盖 Jason 作者姿态的身体、头部、椅子几何与手部对身体接触。完成了大腿压座面、拇指进入大腿和掌缘擦扶手的修订，最终 16 个座位的采样没有超过 0.7 cm 的家具穿插标记，六类手部采样没有超过 0.5 cm 的身体穿插标记。该范围不等于连续碰撞证明，也不代表任意衣物、Kaitlin 重定向后的几何或游戏内／联机验收。

来源清单、制作与保存回执、本地发布回执和检查范围位于 `SourceAssets/FurnitureRest20261022/ChairReuse20261024`。预览 `PreviewFinal/chair_reuse.gif` 使用最终 Jason 作者姿态和项目家具几何，未冒充游戏录像或 UE 压缩动作读回；Kaitlin 已保存接入，尚未单独进行几何／视觉检查。此轮没有 Git 提交或推送。

## 2026-10-24 ArmrestExit：办公椅／会客椅起身手臂翻转

用户指出两侧扶手限制下的起身手臂仍然扭曲。本轮针对 `Chair50` 会客椅和 `Chair52` 办公椅的 Exit，读取作者姿态、实际运行选择入口以及保存压缩动作。旧版为躲避扶手加了 24 cm 高的腕部弧线，再整段倒放；约 1.1～1.5 秒处，混合后的肘部 pole 在肩腕轴上的投影趋近退化，肘部由外侧翻入身体内侧。Jason 的会客椅左前臂单帧变化约 45.52 度，办公椅约 37.04 度；旧 Kaitlin 对应约 43.71／35.63 度。此前零穿插采样没有覆盖这一关节翻转问题，不能作为旧版手臂自然度合格的依据。

起身改为先保留扶手支撑，轻抬掌面，再沿扶手前方撤手，待离开扶手后逐渐转腕、舒指并恢复垂臂。两手有 0.06 秒错峰。肘部在肩腕轴垂直的弯曲圆上做连续角度插值，不再直接插值 pole 点；恢复垂手时先把原生肘部弯曲方向旋转到当前肩腕方向，避免再投影到不同轴时出现一次翻转。上臂和前臂按原生端点骨轴渐变，手腕不独自承担全部转向。

作者脚本 `Tools/FurnitureRest/armrest_exit.py` 只修改两段 Exit 的手臂旋转轨道；非手臂轨道、局部骨骼位置／缩放、骨长、首尾姿态、3.1 秒时长及原眼位轨道保持。Enter、Idle 继续使用 ChairReuse。公共保存／发布入口新增内部 revision 参数与 changed_roles 过滤，两个专用 wrapper 为 `save_armrest_exit.py` 和 `publish_armrest_exit.py`，防止重存其他椅子和其他阶段。

Jason 两段新资产位于 `/Game/Characters/JasonPlayer20261003/FurnitureRest20261022/ArmrestExit20261024`；Kaitlin 两段位于 `/Game/Characters/KaitlinPlayer20261023/ArmrestExit20261024`。后台保存与压缩采样正常退出，四个动作引用已通过共享字段事务接入。家具时长／眼位内容没有变化。本轮首次后台进程等待引擎 AutoSDK 的共享 Build.bat 锁；确认尚未执行资产脚本后，仅停止本任务的等待进程及其 SDK 子进程。第二次使用引擎 `TargetPlatformManagerModule.cpp` 已提供的 `UE_SKIP_UBT_SDK_SETUP=1`，只在该启动进程环境中跳过平台 SDK 检查；没有停止其他任务、修改引擎或持久化系统环境。

`read_armrest_exit_saved.py` 在资产完成编译保存后，按 30 Hz 读取男女角色旧新 Exit 的压缩姿态。Jason 本版前臂单帧最大变化约 7.21 度，Kaitlin 约 7.15 度；肘部均保持在肩的外侧，最小外侧距离约 4.10／4.18 cm。旧新首尾手臂骨点最大差小于 0.0061 cm、旋转差小于 0.024 度。Jason 新 Exit 的全部 94 帧进行了手部对身体采样，并以全帧检查身体／头部对两款椅子，未见超过 0.5 cm／0.7 cm 阈值的穿插标记。Kaitlin 本轮完成骨骼轨迹与衔接检查，未单独渲染其蒙皮几何或任意服装。

数据与回执位于 `SourceAssets/FurnitureRest20261022/ArmrestExit20261024`：`arm_metrics.json` 为源动作诊断，`saved_arm_review.json` 为男女压缩动作对照，`geometry_audit_saved.json`、`hand_body_contact_saved.json` 为 Jason 接触采样，`publication.json` 为本地引用接入记录。`armrest_exit_before_after.gif` 与 `saved_exit_comparison.jpg` 使用旧新实际保存压缩动作、Jason 蒙皮和项目家具几何，从前侧观察双臂；属于离线预览。没有打开交互式编辑器、运行游戏或进行联机验收，也没有 Git 提交／推送。

## 2026-10-24 MeshyBed20261024：会员导出动作接入普通双人床

用户提供 `Downloads/Meshy_AI_Gray_Full_Body_Manneq_All_Animations.glb`，确认 Meshy 会员并要求可商用发布。原始文件已完整复制到 `SourceAssets/FurnitureRest20261022/MeshySitLieBed37120261024`，SHA-256 为 `79b88af4e6639f55af4e0f5bc1e5e32f4137562f387518aa0ced63b4d8e639cf`。导出含 Running、Walking、Sit_Lie_Bed 和 sleep；实际骨架 28 骨，没有独立手指。离线查看发现 Sit_Lie_Bed 是坐姿后仰再坐起的循环，sleep 才有坐姿支撑、后移、抬腿、躺下的完整过程。因此采用单独命名的 sleep，不将其误标为动作 371，也不视为开源素材。商用授权依据是用户已确认的会员导出，项目保留原文件与来源记录。

源动作经 FBX 中间文件导入 `FurnitureRest20261022/MeshySource20261024`，建立源骨架到 Jason 的 IK 重定向。保留 sleep 的 5.7 秒完整时长，前接 2.8 秒已有入座和 0.4 秒姿态过渡。普通 Bed 从床尾入座，入口调整为家具坐标 `[-32,167,0]`、入口转角 0，避免给没有转身阶段的源动作强加侧向旋转。原生手指使用放松展开姿态；手掌、脚部根据实际床垫与床框接触适配，保留肘膝弯曲平面。修复首帧手腕跳变、接近伸直时的手臂解算突变、脚目标跨床框边界的不连续，并延后入座前的抬脚。枕头接触使用实际头部蒙皮标定。

本次仅更新 Bed 的两个 Queen 模型路径：`CyberpunkApartmentRebuild20261022/Meshes/SM_AP_BedQueen` 与 `RefinementV2/Meshes/SM_AP_BedQueen`。Jason、Kaitlin 各保存 Enter、Idle、Exit 共 6 个新资产，分别位于 `JasonPlayer20261003/FurnitureRest20261022/MeshyBed20261024` 和 `KaitlinPlayer20261023/MeshyBed20261024`。Enter 8.9 秒、Idle 4 秒、Exit 9.2 秒；退出沿进入倒放并保留 0.3 秒站稳。共享字段事务已接入 6 个身体动作引用、3 个时长/眼位轨道以及 Bed 入口参数。其他床型、椅子及已修复的扶手椅退出保持原有引用，沿用已有高亮与第一人称自由转头逻辑。

后台 commandlet 完成动画编译、保存及压缩姿态读回，退出码 0。Jason Enter/Exit 全帧及 Idle 采样在两个床模型上没有超过 0.7 cm 的床体穿插标记；手与身体 548 个姿态采样没有超过 0.5 cm 的标记。头部对枕头最低采样间距约 0.662 cm，入口胶囊对床几何间隙约 8.70 cm。男女角色阶段衔接最大骨点误差小于 0.010 cm、旋转小于 0.118 度。Kaitlin 完成原生骨架、动作及衔接检查，未单独进行蒙皮接触或衣物组合验收。这些采样不代表自然度已获用户认可。

最终记录位于 `SourceAssets/FurnitureRest20261022/MeshyBed20261024/delivery.json`，保存/接入记录为 `assets_saved.json`、`save_complete.json`、`publication.json`。`ReviewSaved/bed_entry.gif` 与 `bed_full_cycle.gif` 使用实际保存的压缩姿态、Jason 身体/头部和项目床模型离线渲染，已查看阶段分帧。没有启动交互式 UE 编辑器或游戏，也未进行联机验收。已缓存旧家具库的编辑器需用户重启后读取新时长与入口配置。

## 2026-10-24 MeshyBedSideHands20261024：坐稳时双手自然放在体侧

用户指出坐到床上时双手悬在大腿上方、动作僵硬，要求自然放在两侧。定位到旧入座终点使用腿前手位，sleep 开始段又有前伸抬手，叠加形成悬手。以 MeshyBed20261024 为基础，仅修改 Enter 约 0.45～4.48 秒的上臂、前臂、手腕和手指旋转：坐稳后手位按骨盆两侧定位，双肘保留轻微弯曲，手指保持放松，左右手错开 0.08 秒，再平顺恢复到源动作的后撑轨迹。按实际手部蒙皮和床面补偿过渡中的指尖接触，最大腕部抬升约 2.27 cm。Exit 按新 Enter 倒放同步更新。

作者源 `Tools/FurnitureRest/meshy_bed_side_hands.py`；数据、保存及接入回执位于 `SourceAssets/FurnitureRest20261022/MeshyBedSideHands20261024`。Jason、Kaitlin 各保存 Enter/Exit 共 4 个新动作，已按字段事务接入；Idle、时长、入口和眼位配置没有变化。源数据比较确认身体、头、腿、骨骼平移及缩放均保持原值。后台 commandlet 完成编译、保存与压缩姿态读回，未启动交互式编辑器或游戏。

保存后的 Jason Enter/Exit 全帧及 Idle 采样，在两个普通 Queen 床模型上没有超过 0.7 cm 的床体穿插标记，手对身体 548 个姿态没有超过 0.5 cm 的标记；男女原生骨架的阶段衔接检查完成。Kaitlin 未单独进行蒙皮接触与服装组合检查。`ReviewSaved/bed_entry.gif`、`bed_full_cycle.gif` 使用已保存压缩动作和项目实际几何离线渲染，已查看坐稳体侧手位；最终自然度与游戏内效果由用户确认。详见 `delivery.json`，无 Git 提交或推送。

## 2026-10-24 MeshyBedSupportedHands20261024：按关节与承重关系复查

用户要求自行检查细节并符合人体工学。本轮扩大到关节几何与实际支撑，不把此前零穿插等同于姿态合理。复查发现：Jason 后撑阶段腕部最大后折约 92.09 度，手掌短暂离开床面；约 4.5～5 秒躯干后仰后又抬起；入座前段脚底离地而臀部尚未接触床沿。以上均为原生骨骼和实际蒙皮采样，不作为医学关节活动度认证。

新作者 `Tools/FurnitureRest/meshy_bed_supported_hands.py` 保留 Meshy 主体时钟和骨长，将回落分配到多段脊柱与肩带，头颈随实际胸部变化补偿；依据脚底/臀部的实际接触调整入座高度，床尾处短时修正小腿净空；体侧放松手腕随前臂方向转动，后撑双掌使用固定床面支点。根据手掌皮肤底面标定掌面小幅转角，保留原手指姿态，使掌根参与接触。躺平前轻微卸力抬手，防止前臂擦床褥。退出沿更新后的进入倒放，时长仍为 Enter 8.9 秒、Exit 9.2 秒，Idle 保留；眼位轨道已同步更新。

Jason 与 Kaitlin 各保存 Enter/Exit 两段。Kaitlin 重定向产生约 2.81/2.36 cm 支撑漂移，随后按其原生上下臂骨长单独固定手位，修订资产位于 `KaitlinPlayer20261023/MeshyBedSupportedHands20261024/NativePalmContact`。四个实际引用和 Enter/Exit 相机轨道已按字段事务接入；两个普通 Queen 模型继续共用 Bed 类型，其余家具不变。

实际压缩姿态读回：Jason 腕部最大后折约 70.83 度，Kaitlin 约 76.01 度；支撑时段 4.7～6.6 秒两只手的最大漂移均小于 0.013 cm。Jason 支撑掌根距床面约 0.60～0.63 cm，坐稳后臀部接触采样约 0.45 cm。全帧 Enter/Exit 与 Idle 采样中，两款床体没有超过 0.7 cm 的穿插标记，548 个手/身体姿态没有超过 0.5 cm 的标记。男女阶段衔接最大骨点差约 0.012 cm，旋转小于 0.093 度。Kaitlin 完成原生关节、支点与阶段检查，未单独复核其蒙皮接触或服装组合。

最终回执 `SourceAssets/FurnitureRest20261022/MeshyBedSupportedHands20261024/delivery.json` 汇总 `native_ergonomics_review.json`、`support_contacts_saved.json`、接触采样与发布结果；`ReviewSaved/bed_entry.gif`、`bed_full_cycle.gif` 为实际保存 Jason 压缩动作与项目几何离线预览，已查看阶段分帧。未启动交互式 UE 编辑器、游戏或联机验收，无 Git 提交/推送。最终自然度与游戏效果仍由用户确认；已缓存旧眼位轨道的编辑器需用户重启后读取新配置。

## 2026-10-24 公寓卧室床补接与范围内直接就位

用户反馈游戏里仍播放旧动画，并确认测试对象为公寓/卧室双人床。实际路由追踪发现，前几轮 Meshy 修订只更新 `Rest.Bed.*`；三款公寓床均命中独立 `ApartmentBed` 类型，仍播放 V10，不能用普通床的发布回执代表它们已经接入。同时，Kaitlin 的独立家具眼位仍保留部分旧动作/时长，原家具库又是进程静态缓存。此次确认主动作映射、模型类型、阶段时钟、目标身体眼位和构建产物各自的真实消费入口。

三款目标为 `CyberpunkApartmentRebuild20261022/RefinementV14/Meshes/SM_AP14_Bed`、`CyberpunkBedroomPilot20261024/RefinementV2/Meshes/721e9428ac/SM_BP_BedRefined` 与 `RefinementV3/Meshes/f16c0e5d2e/SM_BP_BedRefined`。它们实际使用 `[1.4,1.4,1]` 的场景缩放，不能直接把普通床锚点搬过去。新 `MeshyApartmentBed20261024` 保留已适配的大床侧入座/转身，衔接 Meshy 的新躺下段，并适配床面脚位、枕头和手部净空；进入 11 秒、保持 4 秒、退出 11.3 秒。男性及女性各三段资产已实际保存，女性支撑手进一步原生修正到 `NativePalmContact` 子目录。三款床均保留 ApartmentBed 类型，新入口为 `[-200,0,0]`、入口角 90 度；原型 V14 的局部座点 Y 为 10，另外两款为 0，均保持原场景缩放。

`FPSFurnitureRestComponent.cpp` 对所有 lying 类型改为：准星在 250 cm 交互范围内命中可用床后，由服务器校验并直接设置动画就位点；不再要求当前玩家到起点的路径能绕过床体。目标空位和占用判断仍沿现有逻辑，座椅的原移动路径检查保留。就位同样在客户端应用复制状态时执行，保留第一人称自由转头。家具数据按播放世界缓存，新一局重新读取，不在活动动画中途替换时钟；日志记录本次命中的模型、类型、实际 Enter 资产与直接就位标记。

补齐 Jason/Kaitlin 的 Bed 与 ApartmentBed 原生眼位轨道，依据当前已保存压缩姿态和各自头部/眼睛绑定生成，逐角色键发布。`FPSPlayerBodyVariants.cpp` 跳过 animation 标记与当前 clip 不匹配的旧眼位。公寓配置只更新 ApartmentBed 的时长、眼位、类型入口及三个目标的座点，身体配置通过共享事务写入 18 个字段，保留其他动作和并行修改。

Editor/Game 常规后台构建均以退出码 0 完成，两个二进制均包含新交互标记；没有启动交互式编辑器或游戏。保存后 Jason 的完整进出及保持采样在三款模型上没有超过 0.7 cm 的家具穿插标记，674 个手/身体姿态没有超过 0.5 cm 的标记；男女阶段衔接最大位置误差小于 0.017 cm、旋转小于 0.078 度。发布后核对三模型 × 两身体 × 三阶段共 18 条实际路由，其包、时长和原生眼位对应一致。Kaitlin 未单独做蒙皮/服装接触验收；未进行游戏内或联机验收。重新进入游戏后才读取新配置，已加载的旧实例不会被强制替换。

制作和回执：`Tools/FurnitureRest/author_apartment_meshy_bed.py`、`save_apartment_meshy_bed.py`、`publish_apartment_meshy_bed.py`；`SourceAssets/FurnitureRest20261022/MeshyApartmentBed20261024/delivery.json` 汇总实际引用、保存及离线结果，`ReviewSaved/bed_entry.gif` 展示实际公寓床模型和已保存动作。C++ 构建记录位于 `ApartmentIntegration20261024`。没有 Git 提交或推送。

## 2026-10-24 躺床休息恢复 SAN

按用户要求，所有 `lying=true` 家具在已躺稳的 Idle 阶段提供基础 **5 SAN/秒** 恢复。普通床、公寓床、病床和上下铺沿同一类型标记生效；入床、起身、坐椅与坐沙发不提供这项恢复。`Content/ColdSteelData/survival.json` 新增 `bedRestSanityPerSecond: 5.0`，组件无配置时也默认 5。

由 `UFPSSurvivalComponent` 复用已有 0.25 秒服务端调度，按实际游戏 DeltaTime 积分并夹紧到 MaxSanity；客户端继续读取拥有者复制状态，存档和 HUD 不另设数值。暂停、死亡及非玩家沿用既有停止条件。原地牢自然 SAN 消耗仍与基础恢复合并计算；SAN 从 0 恢复后，既有属性/状态边界通知解除耗尽惩罚。未新增计时器或逐帧恢复逻辑。

Editor/Game 常规后台构建均已成功，最终回执为 `SourceAssets/FurnitureRest20261022/ApartmentIntegration20261024/bed-san-03-*`。构建中对 `FPSBodyOutfitResources.h` 补齐 JSON 共享字符串键到 FString 的最小转换，以兼容 UE 5.8 的字符串接口；保留其他服装逻辑。本轮没有启动游戏或追加测试，实际游戏效果交由用户测试。

## 2026-10-25 接入完成度与联机复查

本节以当前运行配置为准，前文的慢速上床版本属于制作历史。两份家具配置合计 25 个模型路径、38 个座位／床位、18 种动作类型，其中椅子／沙发／长凳 12 个模型，床铺 13 个模型。Jason、Kaitlin 各 54 个 Rest 动作角色，共 108 个当前引用；均存在原生资产，加载后的骨架与各自身体一致，保存时长与阶段配置匹配。六类床的 Enter 都为 3.3 秒，加就位 0.6 秒为 3.9 秒；Exit 为 3.4 秒。当前引用与具体模型、座位清单见 `SourceAssets/FurnitureRest20261022/CompletionAudit20261025/inventory.json`，由 `Tools/FurnitureRest/completion_inventory.py` 从正式配置生成。

本轮发现并修复三项：

- 打包遗漏：JSON 动态引用的 Jason 家具动作中有 7 个目录未被显式 AlwaysCook 覆盖。`Config/DefaultGame.ini` 已补入 ChairReuse、ArmrestExit、MeshyApartmentBed、ApartmentFastRestR2、ApartmentReverseExit 及两版 BedFamilyReuse。108 个当前动作引用均有显式目录覆盖；这不是实际 Cook／打包运行回执。
- 受击退出跳帧：Idle 中受击触发 Exit 后，旧代码仍用 Idle 的阶段年龄判断结束，休息较久会直接跳过起身。现在在受击处理之后重新计算阶段年龄，完整播放新 Exit。
- 远端交互视点：服务器不再对远端玩家读取可能滞后的 PlayerCameraManager 缓存，改为角色权威眼位与控制朝向；本地视角仍沿用原来的交互视点入口。该约定与门交互一致。

`FurnitureRestAudit` 后台 commandlet 使用隔离 UserDir／Profile、真实角色组件、真实家具碰撞和正式配置，逐个位置调用实际 Interact 与阶段逻辑。仅人为推进阶段年龄以缩短等待，不注入成功的休息状态；远端控制器故意提供错误的相机缓存，以覆盖服务器眼位修复。最终 `audit-07-authority.json` 为 437 项通过、0 失败、38 个位置实际进入；覆盖占位拒绝、躺稳后基础 SAN +5/秒、坐姿／进出阶段不恢复 SAN、受击后完整起身与退出后移动输入恢复。检查身体为 Jason；Kaitlin 在本轮覆盖资产、骨架和时长，未覆盖蒙皮／衣物视觉。早期失败轮次包含检查场景未等待网格编译、缺少 PlayerState、瞄准射线未命中床体及清理不完整，最终轮次已修正这些检查场景问题并以进程退出码 0 完成。

Editor/Game 最新构建均退出码 0，回执为同目录 `audit-06-FPSGAMEEditor.json`、`audit-06-FPSGAME.json`。当前源码、构建产物和检查回执均已落盘；没有提交或推送。`Before/` 实际为三项修复之后的源码快照，不能作为修复前回退副本，目录内 `SNAPSHOT_NOTE.txt` 已明确标注。

真实 UDP 检查由 `Tools/FurnitureRest/run_completion_wire.ps1` 复用现有公寓网络用例，启动三个独立后台进程，使用隔离 UserDir／Profile。`wire-01/result.json` 六阶段均通过，`receipt.json` 记录完成；日志确认 PktLag=60 ms、PktLoss=5 已设置。家具覆盖正常加入和晚加入时休息状态初始化，以及 Phase 0 复制后解除休息和关闭该组件 Tick。该用例在服务器注入 Phase 3／0，家具角色没有被客机控制，不测试实际入座 RPC、抢座竞争或 SAN 的网络复制；关闭身体渲染加载以控制内存，也不提供动画画面验收。进程已正常结束。用例同时经过公寓柜门观察者与设备复制分支，这些结果没有扩大为整个公寓玩法验收。

覆盖边界：上下铺目前只有下铺；倒伏家具和不匹配配置缩放的实例不支持休息。25 个模型路径的覆盖不等于所有地图摆放实例的普查。真实客户端 E 键 RPC、多人同时抢同一座位、跨机器联机、各体型衣物穿模、实际打包后加载仍需要对应实测，不能由本节的隔离权威检查和注入状态的 UDP 检查替代。正式资产继续经 `D:/FPS3D/FPSGAME/Content` 联接到 `F:/FPSGAMEData/Content`，DDC 经 `D:/FPS3D/DerivedDataCache` 联接到 `F:/FPSGAMEData/Caches/DerivedDataCache`；本轮未移动 NAS／保留副本。

## 2026-10-25 双人床两侧独立占位

按用户新增要求，7 个双人床模型（两款 Queen、两款 King、公寓床和两款卧室精修床）配置左右各一位，总交互位置由 38 增至 45。单人病床、下铺、单椅维持一位；沙发和长凳仍按已有独立座位分别占用。双人床先选择瞄准侧，该侧占用时自动选择另一空侧；两侧满员、单人床或目标座位占用时显示“已被占用”，取消可用高亮，E 不会让其他玩家进入该位置。

服务器在真实交互入口按家具组件、ISM 实例编号及槽位编号确认占用，成功进入就位阶段即保留该槽位，直到起身结束；死亡、家具失效、断线后的原有退出及 EndPlay 清理继续释放。槽位编号、用于本地提示的位置、左右镜像状态和原有阶段一起复制，客户端只显示已有占用信息，最终分配由服务器重新求值，不能由客户端自行声明空位。替换原先只比较动作 Root 距离的 55 cm 排斥，避免同床左右共用动作基准而错误互锁。

两侧继续使用当前男女原生动作。`FFurnitureMirrorLayer` 在家具动作与普通动作混合之前，依据每个身体的参考骨架镜像完整骨骼链；未使用人物负缩放。入口偏移、入口转角、倒放下床落点和原生眼位采用相同镜像方向。两侧动作基准各向外留出 10 cm，交互选侧点为中心左右 50 cm，并按家具配置缩放换算到模型局部坐标。现有 3.9 秒上床、3.4 秒下床和每位玩家独立 SAN +5/秒逻辑保留。

发布入口 `Tools/FurnitureRest/publish_double_occupancy.py` 使用家具配置写锁、当前数据差量与原子替换；只更改两份家具配置中的目标模型，不改 `player_body.json` 或动画资产引用。修改前 7 个文件的副本保留在 `SourceAssets/FurnitureRest20261022/DoubleOccupancy20261025/Before`。本轮未启动游戏、未执行新测试；上节 437 项与 UDP 回执属于更改前版本，不能作为双人同床功能的测试结果。构建回执使用本目录 `build-*-*-receipt.json`，由 `Tools/FurnitureRest/build_double_occupancy.ps1` 后台生成。

本轮 `build-01-FPSGAMEEditor-receipt.json` 与 `build-01-FPSGAME-receipt.json` 均为退出码 0，Editor DLL 和 Game EXE 已生成。主客机均需使用此次构建及两份新家具配置；未启动编辑器或联机验收。
