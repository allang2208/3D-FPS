# 缚群 V16：张嘴撕咬与前肢连续拍击

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

## 动作设计

保留当前主体、衣物、蒙皮、骨架、移动及已认可的触手抽打，增加两条 60 fps 原创全身动画。

- 撕咬：后缩、左右口缘张开，前身与嘴部突然前探，0.68 秒合口命中；随后侧拧撕扯、回收，全长 1.6 秒。沿用 55 基础伤害及 2.5 秒 CD。起手范围 280 cm、前方 ±35°，实际判定仍以嘴部为源点。
- 连拍：前两根不等长供体肢体抬起，后部肢体承重；左、右、左、右四次交替拍击，最后双前肢重拍，身体随各拍左右移重并在终结时下压。接触为 0.56、0.86、1.10、1.34、1.86 秒，总长 2.6 秒。前四拍每拍 18，最后一拍 32；最后双肢对同一目标只结算一次。4.5 秒 CD，起手范围 280 cm、前方 ±45°；判定球心从腕／踝向前移 10 cm 至掌／足面中部，保留不等长供体本身，不用放大骨长补触及距离。
- 拍击的加载、急落、短促随挥及回臂分别编排；60 fps 烘焙帧之间线性插值不等于动作匀速，位移由分段缓动／加速曲线生成。两条动画均为原地片段，容器根锁定参考姿态，身体前探由支撑骨和肢体 IK 配合，不缩放供体骨长。

节奏参考：[接肢贵族的连续向下攻击与重砸收尾描述](https://diamondlobby.com/elden-ring/reach-the-starting-location-elden-ring/)。这不是《艾尔登法环》游戏动画提取或重定向；未使用其模型、动作文件或音效，按缚群原生解剖结构重新制作。没有声称逐帧观看或复刻参考视频。

## AI 与判定合同

| 行为 | 起手／目标 | 转向 | 命中与退出 |
| --- | --- | --- | --- |
| 撕咬 | 范围、角度、地面、可见或挡路冰墙、技能冷却 | 前 0.42 秒以最高 110°/s 跟随，随后锁朝向 | 0.68 秒采样嘴部后单次伤害；结束后 0.22 秒决策空档 |
| 连拍 | 范围、角度、地面、可见或挡路冰墙、独立冷却 | 前 0.36 秒跟随，随后锁朝向 | 每拍采样打击前 0.12 秒的三帧，前掌／足骨路径作两段球扫与目标胶囊距离判定；身体到肢体、肢体到目标均检查遮挡 |
| 甩鞭 | 保留前方 120°、现有距离、2 秒 CD、原缠绕条件 | 保留现有动作 | 保留三次 F 近战挣脱、手部显示和底部提示 |

近距离按可用招式轮换“撕咬 → 连拍 → 甩鞭”，不让短 CD 甩鞭压住两种新招。不可用招式跳过；远处仍可用甩鞭。沿用共享 Behavior Tree 与 MonsterCombatComponent，不另建并行 AI。

死亡／受控进入原中断流程；目标失效或死亡取消当前近战。命中回调返回后先判断是否被弹反／死亡中断，不能继续剩余拍击。每拍计数在结算前推进；超过接触时刻 0.2 秒的旧打击跳过，避免卡帧后一次倾倒整套伤害。

新 Flurry 枚举追加到末尾，保留既有序号；TentacleActive 显式限制到 TentacleRecover，避免新近战误进入触手驱动。每拍最多三次骨姿态采样，不新增每帧全网格变形或布料重建。

## 制作与接入

- 作者源：`SourceAssets/BoundCongregateMeshy20261006/MeleeV16/BoundCongregate_MeleeV16.blend`；同目录两段 FBX、motion_contract.json、motion_manifest.json。
- 重建：`Tools/BoundCongregate/author_melee_v16.py`，使用当前 V14 原生骨架；同步生成 `BoundCongregateMeleeTiming.h`，时序不手写两份。
- 导入：`Tools/BoundCongregate/import_melee_v16.py`，只导入动作并更新当前 `BP_BoundCongregate` 的对应动画和攻击字段；保留现有视觉网格／衣物与其他动作。使用当前视觉网格所属 Skeleton，根骨使用 RefPose 锁定，沿用现有状态过渡和地面支撑节点。
- 目标动画目录：`/Game/Monsters/BoundCongregate/MeleeV16`；F6 原“缚群”入口继续使用同一蓝图。
- 拍击音复用工程已有 `S_MeleeHit_Quick`，动作时钟触发，空间衰减继续使用怪物 ActionVoice；未新增外部素材。
- 状态：作者源与两段 FBX 已制作；FPSGAMEEditor、FPSGAME 的 Win64 Development 构建均成功。两段 AnimSequence、所属 Skeleton 及原 BP_BoundCongregate 已由后台 commandlet 实际保存，最终起手距离均为 280 cm。生产结果见同目录 `delivery.json`、`build-FPSGAMEEditor-ready.log`、`build-FPSGAME-ready.log`、`import-final.log`。
- 统一后台落盘入口：`Tools/BoundCongregate/finish_melee_v16.ps1`；使用已有导出构建两目标并导入保存，不调用测试或渲染。
- 未启动交互编辑器、游戏、测试、预览或截图；动作观感、衣物随动与实际命中由用户体验，构建／保存成功不代表运行验收通过。
