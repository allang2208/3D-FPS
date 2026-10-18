# 食物、手部装备与持弓交接整理发布

本次在正式工程 `D:/FPS3D/FPSGAME` 整理本段已完成的开发，目标为 `https://github.com/allang2208/3D-FPS.git` 的 `main`。起始提交为 `e22db72ebf7392bf91b7c666448c9b26f8488a71`；fetch 后本地与远端一致，未携带其他未推送提交。

## 发布范围

- 大羊排双手、原生拇指和向下退出镜头；六种食物的第三人称肘部辅助骨及移动上身稳定处理。
- Sparrow 第三人称 Carry、Draw、Ready、Hold、Release；持弓左手施法、进食、饮水的换手、显示、时钟和恢复，以及双手进食取消后的抬弓。
- 单手饮食收副手枪、双手饮食收整枪时的镭射／手电抑制，保留原开关状态；第一、第三人称使用同一装备归属。
- 硬壳手套完整主体与闭合腕口配方，ST6 原始袖子／身体材质覆盖和 3×3 旧实例迁移。
- 腐败食物五块结构的模型、图标制作配方和阶段色进度条；M870、SUPER90 原厂部件图标配方及 M870 肩口修正生成器。
- 对应手臂、服装、战术设备、联机与排查 SKILL；本机个人维护源与工程参考同步本轮新增经验。

共享文件从 HEAD 重放本轮差分，工作区中战锤、新枪、天气、死亡、步态和其他并行修改保留原样。物品目录只发布本轮外观与占格字段，身体动作表只合入对应弓和大羊排片段，未整体发布当前共享目录。

`published-files.json` 记录提交内容及散列；`patch-manifest.json` 记录不能独立接入的增量、前置文本散列和结果散列。补丁中的散列统一使用 UTF-8、LF、无 BOM 文本。应用前必须匹配前置宿主；已应用到本机的补丁不要再应用。

## 有意保留的宿主依赖

公开源码切片不能等同于完整可运行的工程备份，也没有本轮干净检出构建结论。

- 腐败进度 UI 的基础 `FoodSpoilage` 时钟、数据字段及共享浮窗宿主仍包含其他未发布开发。本次对该宿主的修改保存为八份具名前置补丁，不把整套食物经济系统纳入本次提交。当前本机已接入缩短的剩余鲜度条，绿／黄／红阈值来自同一函数。
- M870 肩口的 `M870ArmOpeningControls.inl` 是从本机授权皮肤提取的表面控制点，未公开。先按 `SourceAssets/M870LeftRoot20261017/write_controls.py` 从许可输入生成，再合入相应 C++ 补丁。本机修复已经存在。
- 食物、移动与弓的诊断源码以补丁保存；Sparrow 联机夹具依赖共享 `ShotgunWireAudit`、`BowSkillTrainingAuditCommandlet` 宿主及对应调用入口。它们的完整本机宿主还含其他工作，本次不整文件发布，也不宣称公开补丁可一键运行检查。
- ST6 公开配方记录本轮原始袖子与材质覆盖方案。本机后续 `ST6Refine20261018` 等领口／衣袖修订属于其他工作，保持当前接入，不能运行本次历史 reset 配方覆盖这些后续成果。
- 修正 `melee-gunsmith.json` 的字符串 effects 和独立检查工具的指针类型属于已在本机解除的构建阻塞；没有夹带该武器或其他怪物工具的整套未发布实现。

## 本机资产与恢复顺序

本仓库公开原创 C++、制作脚本、小型手部参数、文档和归档元数据。Fab/Sparrow 原素材、几何／权重／密集动作采样、FBX／Blend／贴图／音频、UE 包、构建二进制和原始运行回执不上传；使用许可不视为原始或派生资产公开再分发许可。

1. 保留本机原始武器、当前裸手原生绑定、Jason 全身与 Sparrow 供体；以实际网格与保存记录识别手模，不能仅凭历史路径的 V7 字样判断版本。
2. 大羊排第一人称使用 `FoodGrip20261003/lamb_food_motion.py`、`large_lamb_natural_grasp.json`、`lamb_thumb_profiles.json`；第三人称作者／保存入口在 `LambTwoView20261017`，六种食物的最终图修正在 C++。这些作者仍读取本机实际蒙皮输入。
3. 硬壳手套按 `HardKnuckleRepair20261017` 读取原生皮肤、制作闭合腕口、导入保存，再更新生产源；原 `BenelliM4Super9020261006/fix_glove_cuff.py` 转发该路径。ST6 同理保留原始供体，不恢复已否定躯干壳。
4. 腐败食物使用 `SpoiledFood20261016/author_asset.py`、`render_icon.py`、`import_assets.py`／`resume_mesh.py`、`publish_catalog.py`；当前五块结构与实际 PNG/UE 包留本机。M870/SUPER90 图标按各自目录的源图、生成及导入记录恢复，正式图像不随本次源码发布。
5. Sparrow 使用 `BowSparrowThirdPerson20261018` 的 `prepare.py`、`retarget_remaining.py`、`read_retargeted.py`、`author.py`／`fit_contact.py`、`save.py`、`publish.py`。当前动作目标仅为 `/Game/Characters/JasonPlayer20261003/BowSparrow20261018/AnimationsV3`；Retargeted、Rig 与原始供体仍是活动制作输入。

脚本是制作和恢复入口，不是自动测试授权；旧的制作、保存和检查入口各有前置资料及运行边界，不能按文件名字典序批量执行。

## 归档与证据

216 份文件（1,454,116,548 字节）已移入本机 `trash/bow-food-closeout-20261018/`，逐文件移动前后 SHA-256 相同。详见 `archive-manifest.json`：记录原路径、目标、大小、散列、退役原因和保留替代物。没有跟随目录链接，也没有移动其他任务的资产。

明确退役的是硬壳手套翻面前的旧包、ST6 被否定躯干壳的旧包与作者输出、腐败食物条带初稿、Blender 旧备份、Sparrow Animations／AnimationsV2，以及本次弓复查被最终结果替代的失败／中断／中间构建和检查输出。失败证据仍可恢复。仍被脚本读取的 Before 对照、原始手套／袖子、活动作者、Rig／Retargeted、V3 和最终构建／联机回执留原位；这些不是按日期判定的废案。

历史正式 Game／Editor 构建，以及最后 180 项隔离检查、28 组本地 UDP 检查记录，见 [持弓复查](../../Characters/bow-handoff-network-review-20261018.md) 和本机 `SourceAssets/BowHandoffReview20261018/delivery.json`。UDP 两轮每轮 14 组，每端 60 ms 延迟、5% 丢包；不是同一玩家持久档案重连、互联网、连续输入、渲染或完整库存经济事务验收。

本轮只执行用户要求的仓库整理和推送检查，未重新启动 UE、游戏、PIE、截图、渲染或玩法测试。旧记录中的已归档路径通过归档清单定位；历史成功不作为本次公开切片的新构建或视觉验收结论。
