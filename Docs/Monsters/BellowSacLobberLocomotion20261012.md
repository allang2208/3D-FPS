# 鼓囊投掷者待机与移动接入（2026-10-12）

## 用户范围

使用下载目录内用户已经减面、绑骨的 `Meshy_AI_Character_output.glb` 接入 UE，先完成待机和移动。源文件与可编辑动作位于 `SourceAssets/BellowSacLobberMeshy20261012`。

## 游戏接入

- F6 → 怪物生成 → **鼓囊投掷者（待机／移动）**。
- 蓝图：`/Game/Monsters/BellowSacLobber/BP_BellowSacLobber`。
- 版本资产：`/Game/Monsters/BellowSacLobber/V01/`。
- 动画配置：`DA_BellowSacLobber_Locomotion`，Idle/IdleAlert 使用呼吸待机，Walk 使用慢速步行，Run 槽使用正常移动。
- 普通移动 80 cm/s；复用统一未发现玩家游荡机制，速度为 40 cm/s。
- 复用 `AWolfMonster` 的四足 Character 及 `UQuadrupedTemplateAnimInstance` 播放框架，使用鼓囊自身的网格、骨架和动作。关闭狼嚎、预测扑击、狼皮外观替换和本阶段布娃娃；不配置咬击、扑击等攻击动作。
- F6 使用 135 cm 生成占地；物理胶囊半径 62 cm、半高 90 cm；沿用已有导航代理，未新增导航规格或重建地图。
- 本阶段基础参数：普通档、等级 3、240 生命值、0 经验，尚非正式战斗数值。攻击伤害为 0；投掷攻击和专用死亡动作留待后续制作。
- `Config/DefaultGame.ini` 包含该怪物目录的烘焙引用，避免仅由开发面板软路径引用的资产遗漏。

## 动作与材质

保留用户原来的拓扑、UV、骨骼层级、绑定姿态和蒙皮权重。待机 4.8 秒；慢速与正常移动各 1.2 秒；全部以 60 fps 导出原地循环。四足依次踏步，背囊和喷口有轻微随动。动画导入时匹配绑定骨架的根部单位，并在保存前等待动画编译完成。

从 GLB 提取原始 BaseColor、Normal、MetallicRoughness 贴图；法线适配 UE 的绿色通道约定，金属度取 B、粗糙度取 G。材质以 Substrate 方式接入骨骼网格。

## 交付边界

实际资产保存记录以 `SourceAssets/BellowSacLobberMeshy20261012/Records/ue_import_v01.json` 为准。后台导入及必要编译日志在 `Saved/BellowSacLobber20261012/`。

本次模型、材质、三个动画、动画配置和蓝图已经通过无界面导入保存。Editor 与 Game 的 Win64 Development 构建均返回 `Succeeded`；本次构建报告目标已是最新，无需新增编译动作。构建成功不代表运行时动作观感已验收。

未加入迎宾大厅、分流大厅的正式怪物池；待攻击和战斗数值完成后再纳入每厅首波总量。未主动运行 PIE、游戏、渲染或动作验收，由用户测试待机、移动和实际落脚观感。
