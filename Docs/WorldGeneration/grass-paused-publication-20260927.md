# 动态草地暂停、归档与源码发布（2026-09-27）

用户再次反馈“没成功”，要求记入待办、整理废案并推送源码。本批仅整理和发布，不继续制作材质、构建、启动游戏或测试。

## 当前状态

**倒伏与恢复的视觉效果未达标，暂停开发。** 不把编译成功、RT 数值正确或历史断言通过表述为草地效果完成。

- v12：34 项功能／数据／捕获断言通过，留有原始帧及 GIF；当时也记录了低伏通道不清楚。它们没有测量最终草尖高度或最终顶点旋转。
- v13：源码与实际资产制作完成，保持 0.6 秒＋恢复 1.8 秒；用户反馈实机几乎无变化。
- v14：发现 `InstanceLocalBounds` 已包含 WPO 扩展量，会让弯折限幅反向削弱转角；约 18° 是典型模型条件下的公式估算，不是实测，也未证明这是唯一原因。`rest_bounds.py` 与材质作者已修改，12 项基础资产保存、六项材质编译错误为空；**材质实例原始尺寸参数未全部保存，v14 仍是部分接入候选**。
- v14 第一次实例制作被 UE 向量 setter 的固定 false 返回值误判阻断；此脚本问题已修。之后 PIE 再次运行，未继续落盘。用户此次要求转待办，因此不自动续跑作者。
- 原生层保持已构建的 v13 响应时序；没有关闭运行入口或回退当前内容。高草地图和传送门保留为后续复现入口，历史返回主场景失败仍须单列复核。

待办集中在 [Docs/Backlog.md](../Backlog.md) 的“GPU 草交互”节。

## 后续恢复顺序（仅用户重新要求开发时）

1. 先读取真实使用的材质和已保存实例参数，明确是否仍处于 v14 部分接入状态；不要把函数 metadata 版本等同于整套资产完成。
2. 决定是否继续 v14：保留前一版快照对照，完成原始尺寸参数制作后记录所有保存对象及回执。不要继续盲目放大角度、半径或延长恢复。
3. 用户明确要求测试时，采用少量草片、固定相机、同一动作的启用／关闭对照，区分 RT 压力、材质输出、实际顶点位移以及第一人称可见性；测倒伏高度、连续低伏带和恢复过程，再扩展到密集草场。
4. 单独检查主场景／丘陵与高草场的往返；与草材质效果分别判定。

## 保留内容与恢复边界

- `Source/FPSGAME/WorldGeneration/GrassDeform/`：运行时、配置、测试场类和显式启用的诊断夹具；GameMode／SceneTestPortal 的草场往返接入及地图 cook 条目。
- `Tools/GrassDeform/`：当前 M1/M3 作者、原始边界作者、地图生成、脚步修正、只读模型诊断和用户授权时使用的录制脚本。`Tools/WorldGeneration/build_temperate_grass.py` 同步保存原始尺寸参数。
- 本机有效恢复备份：`SourceAssets/GrassDeform20260927/BeforeV12-*`、`BeforeV13-*`、`BeforeV14-*`，分别保留 v11、v12、v13/修复前状态；密集场首次覆盖前地图备份也保留。它们是失败对照／恢复材料，不按版本号当废案删除。
- 本机记录：`SourceAssets/GrassDeform20260926/authoring-*.json`、`SourceAssets/GrassDeform20260927/authoring-*.json`、`SourceAssets/GrassDenseTest20260926/`、`SourceAssets/GrassFootstepRepair20260926/` 的回执。
- 本机证据：`Saved/GrassShape20260927/`、`Saved/GrassResponseInputs20260927/`、`Saved/GrassResponseAudit20260927/v12-capture-01/`、`Saved/GrassDenseValidation20260926/`。纹理／网格数据导出、原始图像与 GIF 不进入公共源码仓库。
- 运行资产依赖合法本机 `Content/PN_GrassLibrary`、`WorldGeneration/TemperateHills/Grass`、`WorldGeneration/GrassDeform`、`GameMaps/L_GrassDeformDenseTest`。AutoFootstep 插件及其脚步委托改动也需本机恢复；Git 克隆不包含这些许可内容，不等于可直接运行的完整工程。

## 废案归档

归档目录：`trash/grass-paused-20260927/`。仅转移明确被替代的早期形变备份、旧热扰动脚步资源备份、一次性占用查询和过时的手工接线说明；不移动当前运行资产或有效作者源。逐文件原路径、新路径、大小及 SHA-256 见 [归档清单](../AssetArchives/grass-paused-20260927.json)。

本次共归档 **49 个文件，2,028,939 字节**，移动后大小及 SHA-256 一致。使用本机可恢复移动，未永久删除。历史制作回执中的原备份路径按清单查新位置，不改写历史证据。

## 本次发布检查

仅执行仓库发布所需的文件归属、归档散列、暂存差异、敏感信息、内容许可和远端检查；未重新构建或运行游戏。公开范围为项目源码、制作脚本、文字记录、SKILL 和归档散列清单，不包含 UE 包、第三方模型／纹理／插件或本机诊断数据。
