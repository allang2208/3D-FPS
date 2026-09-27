# 地牢入口神像与遗迹地面调整

本轮移除 `AuthoredDungeonGenerator` 在起始通道创建的返程传送门；终点奖励室的返程门保留。

固定神像房每次成功进入新地牢，从六件已导入神像中等概率选一件。选择使用独立 `ShrineSelection` 种子域，资源随生成器分批预载，不消费路线、战利品或房间装饰的随机流。沿用原台座位置和朝向，不缩放完整房间。

| 现有作品 | 游戏赐福 | 效果 |
| --- | --- | --- |
| Diana（狄安娜） | 狩猎 | 物攻 +12%，移速 +8% |
| Venus（维纳斯） | 和悦 | 额外生命恢复 2 点/秒，法力恢复 +10% |
| Flora（花神） | 繁花 | 额外生命恢复 1 点/秒，耐力恢复 +25% |
| Muse（缪斯） | 灵感 | 魔攻 +15%，法力恢复 +20% |
| Magna-Mater-Brunnen（大母神） | 慈佑 | 领取时恢复最大生命的 30%，物防 +15% |
| Barockstatue（巴洛克女性像） | 守望 | 物防 +10%，魔防 +20% |

Barockstatue 的来源没有标明具体神祇；“无名守望者”仅为游戏内名称。来源与许可沿用 `DungeonGoddessStatue20260922/PROVENANCE.md` 和 `DungeonStatueSet20260922/PROVENANCE.md`。

玩家通过现有准星浮窗和 E 键祈求，保留 2.5 米视线、遮挡、独立运行和存活条件。每局只领取一次，不叠加。领取凭据与大母神的一次治疗通过现有角色存档事务一起提交；保存失败不消耗领取机会。加成由当前 `UDungeonRunSubsystem` 持有，退出世界或成功绑定另一局后消失，不进入永久属性。状态栏显示名称、具体效果及“本次地牢”。既有按战斗场次递减的事件增益保持原生命周期。

## 房间构造与材质

- 关闭原室内制作清单中已经被替代的旧整块地板、顶板、旧拱门和旧台座显示与碰撞。旧地板 Z=0 原本覆盖新版约 Z=-18 cm 的石板；保留新版地基、石板和原有过渡坡面。
- 单独制作破口、门槛、顶板悬挑和地面石板的材质分区副本，保留原几何、位置、法线、UV 与碰撞轮廓。原资产不删除。
- 混凝土截面使用已开发的 `WallUpgrade20260924/Materials/MI_BrokenConcrete`；表面仍为原混凝土。石板、墙石、拱门与台座使用同一石材家族，石材断面单独控制尺度和颗粒。
- 石材母材质复用已认可断墙表面的实例空间投影、法线转换、距离衰减和有界细节；取项目已持有的 `UnrealNormandy/T_StoneSurface_02A` 颜色、法线和 RHAOM 扫描纹理，按 R=粗糙度、B=AO 解码。未据颜色伪造高度，石材视差深度设为 0。

作者目录：`SourceAssets/DungeonShrine20260927/`。`Config/shrine.json` 为神像与赐福配置；`prepare_gameplay.py` 同步正式状态卡片目录；`author_sections.py` 制作局部几何；`install_shrine.py` 增量保存资产、固定场景与生成器目录，不运行地牢生成。

已完成后台落盘：3 个材质资产、4 个网格副本、固定场景外部 Actor 包及生成器目录已保存，六款神像已加入正式资源引用。`FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 常规构建均成功。

保存状态见该目录 `Receipts/install.json`，构建状态见 `Saved/DungeonShrine20260927/build-editor-console.log` 和 `build-game-console.log`。仅必要制作、导入、保存和构建；未运行游戏、截图或回归测试，实际视觉和交互效果由用户在下一次运行时测试。
