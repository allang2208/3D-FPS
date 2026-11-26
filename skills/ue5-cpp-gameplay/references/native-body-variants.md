# 原生身体变体、MetaHuman 与家具相机

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-cpp-gameplay/references/native-body-variants.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 来源与装配

详见[维护源](../../_shared/ue5-cpp-gameplay/references/native-body-variants.md)中的同名章节。

## 身体切换与外观生命周期

详见[维护源](../../_shared/ue5-cpp-gameplay/references/native-body-variants.md)中的同名章节。

## 家具与检查边界

详见[维护源](../../_shared/ue5-cpp-gameplay/references/native-body-variants.md)中的同名章节。

## 女性武器握持与坐卧观察

详见[维护源](../../_shared/ue5-cpp-gameplay/references/native-body-variants.md)中的同名章节。

## 铁匠与木匠共用 Jason R4

- R4 保留 Jason 的原生骨架。肩部与肱二头肌分别有左右形态 `R4_Shoulder_l/r` 和 `R4_Biceps_l/r`，由身体网格专属后处理动画蓝图随上臂、前臂姿态驱动。制作铁匠身体时用 `BodyOutfit/save.py` 从 R4 母版复制 `SK_Smith_Body` 及后处理图 `ABP_Smith_R4_Correctives`。修改肩袖或上臂衣料时要给抬臂和屈肘后的体积留量。
- 铁匠、木匠均从 `FVillageArtisanAppearance::Paths` 加载同一个 `SK_Smith_Body` 和 `A_Smith_StandingBreath`。各自的 Resident 只提供头部、工装的软路径。身体独立播放动画，两个从件以身体作 Leader Pose。待所需网格和待机就绪后一起显隐；呼吸起始相位取服务器时间对动作时长的余数，交谈转向取当前本地交谈者。
- 独立 R4 母版、工匠运行网格和玩家原版身体有各自的资产路径。调整某一张脸或一件工装时更换该角色的部件；同款体型或姿态形变维护在两位工匠共用的身体上。
