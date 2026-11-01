# M24 弹匣抓握与装备上膛，2026-10-28

本次范围为标准 5 发、扩容 10 发的普通／空仓换弹左手，以及用户确认的“压实弹匣并拉栓上膛”装备动作。

## 制作

- `M24_GraspEquip_Editable.blend` 从上一版 `M24_BoltRoot_Editable.blend` 继续制作，保留 V9 手臂、115 个形态键和已修正的射击拉栓左臂根部、右手拇指。
- 左手从旧版托底、指尖夹持改为侧面包握。五发和十发分别设定掌位；拇指沿近侧弹匣面，四指绕前缘抓持，标准弹匣的小指兼顾底边。
- 肩位、骨长、手指关节平移与缩放不改。腕点改变后重解左臂两骨链，保持原屈肘平面，并同步前臂辅助骨。
- 换弹仅修改源帧 6–54 的左臂与手指。20–40 帧保持固定的手—弹匣关系，40–44 帧松指，44–54 帧回握。枪身、弹匣轨迹、右手以及空仓后段拉栓保持。
- 继续使用既有 `M24ReloadTiming`，不重复放慢或重写正常／空仓的业务时钟。
- 装备动作 106/30 秒：0–18 帧抬枪；18–30 帧握匣；30–38 帧压实；38–48 帧回扶；48–106 帧接当前拉栓循环。声音接触点为 34、73、88 帧，并服从既有装备速度倍率。
- 动作沿当前腰射安装坐标制作；不修改 ADS、枪械缩放、相机安装位置和战术冲刺。

## GitHub 源排查

之前的仓库是 [Terrydaktal/UnityZombies](https://github.com/Terrydaktal/UnityZombies)。这次读取仓库树并找到 [`animations/drawm24.anim`](https://github.com/Terrydaktal/UnityZombies/blob/master/animations/drawm24.anim)。该文件采样率 60 Hz，时长 0.56666666 秒，曲线的 path 均为空，只包含根对象位移和旋转，没有手臂、手指、弹匣和枪栓骨骼轨道。仓库树未见独立许可文件。

`github_tree.json` 与 `github_drawm24.anim` 仅为本次来源排查记录，没有导入或迁移到游戏。装备上膛使用当前项目已接入的 M24 原生循环与新制作的衔接；原始 DJMaesen 动作来源及授权继续遵循 `../M24CustomScope20261026/ATTRIBUTION.md`。

## 写入范围

- 两个正式握持 Profile：`/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip` 和 `DA_M24_Mag10`。
- 正式装备动画仍使用 `/Game/Weapons/M24/MotionMagazine20261027/Animations/A_M24_equip`，避免旧引用遗漏；对应新扩容作者动画保留在 `/Game/Weapons/M24/GraspEquip20261028/Authoring/A_M24_equip_mag10`。
- C++ 只增加 M24 装备压匣、开栓、闭栓音效时点；弹药数量与伤害不改。
- `Backups/` 保存写入前的目标资产和 Profile JSON。安装按当前目标轨道与读取快照比较后合并，保留其他动作和并行改动。

## 执行入口与状态

`contact_pose.py` 制作握姿，`author_actions.py` 制作动作并导出，`run_assets.ps1 -Stage install` 导入与保存，`build.ps1` 构建。

实际资产保存以 `install_receipt.json` 的 `complete` 与 `saved` 为准；构建以 `build-receipt.json` 为准。`Before/`、`Fit/` 和 `ActionContacts/` 是针对本次手势修改的源场景工作视图，不是 UE 实机验收。未启动游戏测试，最终效果由用户试玩确认。
