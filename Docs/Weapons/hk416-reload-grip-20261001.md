# HK416 普通、扩容与弹鼓换弹抓握修正

用户反馈：普通／扩容换弹时左手悬空，弹鼓能抓到但手指张得较开。当前制作仅针对这两种接触问题；未运行游戏、PIE、渲染或验收。

普通／扩容使用独立 HK416 Skeleton 的 `base/reload`、`base/reload_empty`，不是旧 M4 ExtMagContact。原作者把机械骨挂点迁到 HK416，却没有将左手同步注册到新弹匣壳，产生空间偏差。运行时还有 vertical、canted、prism、angled、drum 五个 `UWeaponGripProfile`，只改动画会被旧局部差值覆盖。

## 制作

- 从当前原生 RAW 动画提取样本与实际蒙皮／静态弹匣几何，保留已有机械与拍击动作。
- 参考已认可的 M4／AKM 自然抓握，把掌腕与手指放进弹匣壳坐标系。普通／扩容保护了同一上段形状，以供弹口为高度参照共用抓握；在原生指腹上做有界的截面配准，同时约束插入时的机匣净空。
- 普通弹匣保留原生臂段长度、前臂 twist，联动肩肘到新腕点；手指按局部旋转过渡，不拉长指骨。普通抓新匣窗口为作者帧 43–61–95–108，空仓为 35–43–80–100。
- 弹鼓冻结掌腕和整臂，仅修四指的 12 条关节旋转轨道。使用实际可见指部蒙皮确定屈曲／聚拢方向，在真实鼓面制作指腹贴合；小指补充屈曲。拇指、掌骨、所有位移与缩放保留。
- 共制作 base、vertical、canted、prism、angled 的四种换弹角色，共 20 条。普通／扩容空仓 130／162、弹鼓空仓 116／148 的拍击／结束时钟及回握尾段沿用当前资产。
- 同步重烘五个运行时 Profile 对应四种动作项，释放 Python `Clips` 结构体视图后才执行 `BakeClip`，不修改其他动作项。

## 文件与保存边界

制作源在 `SourceAssets/HK416ReloadGrip20261001/`：`standard_tracks.json.gz`、`drum_tracks.json.gz`、完整原生样本及 `HK416_ReloadGrip_Editable.blend`。Blender 源包含 20 条独立动作，骨架、V7 手臂、材质与权重保留。

当前联机工程 `D:/FPS3D/FPSGAME-mp/Content` 是主库 Content 的目录联接，且禁用了 PythonScriptPlugin。后台保存已停止在 `delivery.json` 记录的 18 条动画边界；不得把另一工程名视作资产隔离，也不能绕过其已加载／未保存状态。

其余动作与 Profile 已在独立 `PackageStaging` 内容副本中制作并保存。五个 Profile 中四个有这四种换弹条目；`DA_drum` 无对应差值项，沿用修正后的基础弹鼓动作，保留原 Profile。只剩 2 条动画与 4 个 Profile 需要写回主库。

用户确认结束 PIE 后，桥接续接时编辑器节点已退出。最终通过 `publish.py` 完成发布：确认没有进程使用同一 Content，按 25 个包的制作前文件归属保护并行修改，仅写回剩余 2 条动画和 4 个 Profile，共 6 个包。其他 18 条动画此前已保存，`DA_drum` 保留；非目标包仅作为读取依赖，不发布。

`publication.json` 记录 6 个包的最终写回；`delivery.json` 已记录 20 条动画、四种动作的 Profile 处理结果、`saved=true`、`staged=false`。主库接入已完成。制作与用户实际观感分别记录，未运行测试或渲染。

隔离项目完成发布后释放，保留制作源、原包备份及保存回执。未主动打开或重启编辑器。
