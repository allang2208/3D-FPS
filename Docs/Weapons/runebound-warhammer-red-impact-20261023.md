# 符文战锤：破坏符文红色与命中炸散

用户要求将破坏魔力符文改为红色，强化符文苏醒后命中敌人的粒子炸开、飘散表现。

## 当前制作

破坏魔力符文在原有刻纹遮罩内改为暗红底色、赤红聚能流光与暖红裂光；保留周围锤体的原装 PBR 和法线。命中时刻纹增加短促的红色脉冲，原装与迅捷符文保留蓝色。

苏醒命中沿用服务器确认的有效攻击事件，每次攻击只触发一次。粒子从当前可见锤头炸开，发射位置固定在命中瞬间的世界坐标；挥锤收势或转身后，粒子继续留在空中飘散，不随锤子整团拖走。蓝色基础效果和迅捷效果共用新的炸散轨迹，破坏符文具有更大的红色爆发。

表现分为快、中、慢三层：短促放射光束、向外抛散的魔力碎片、减速悬浮并上升消失的细粒。发射错峰从最多 72 ms 缩短为 15 ms，粒子在 18 ms 内显现；快光束约 0.48–0.68 秒，碎片约 1.05–1.50 秒，细粒最长 2.35 秒。速度按指数阻力衰减，取代原先围绕锤头的小范围盘旋。

破坏符文常驻粒子由 48 提高为 60，单次命中由 200 提高为 240，并扩大炸散范围与碎片尺寸。仍复用一个动态网格、四个命中槽，几何容量保持 1020 个四边形；不为单个粒子创建 Actor、不新增动态灯。专用服务器不创建粒子表现。命中效果读取各观察端显示的锤头位置，沿用原网络命中通知，未更改伤害结算或存档格式。

精神与智力 +10%、苏醒附加魔法伤害翻倍、10 次有效攻击触发及 20 秒持续时间均保持现有数值。未改模型、改造槽或第一/第三人称动画。改造图标继续使用标准灰白符印，战斗颜色独立。

## 制作与接入入口

源目录：`SourceAssets/RuneboundWarhammer20261022/DestructionRedImpactV2/`。

- `DestructionRune.hlsl`、`DestructionMote.hlsl`：红色材质源。
- `build.ps1`：等待现有构建后，顺序构建 Editor 和 Game。
- `author_isolated.py` → `install_assets.py`：独立作者项目仅复制两份材质供体和四张原贴图，以无界面 commandlet 保存 V2 材质；之后只安装新路径的文件，不覆盖主工程已有资产。主工程接入窗口连续超时后改用该后台制作入口，不依赖主工程 DLL。
- `install.ps1`：保留主工程互斥入口；本轮两次等待超时，未启动 commandlet。
- `publish.py`：保存和 Editor 构建完成后，更新正式破坏符文配方及模块作者底表，只改变目标符文的外观字段；Game 目标单独记录，若仍受共享源码阻断，不宣称全部构建完成。

正式新资产位于 `/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2/`。实际保存、构建和接入状态分别以 `import_receipt.json`、`build_receipt.json`、`delivery_receipt.json` 为准；脚本存在本身不代表已保存。

未运行游戏、测试、截图或验收渲染。观感、遮挡和实际性能由用户在游戏中确认。

## 构建过程中遇到的共享源码问题

首轮 Editor 构建成功。Game 首轮被 `FacilityEncounterPacing.cpp` 的完整类型和局部变量遮蔽错误阻断：补充 `GameFramework/Character.h`，将两处局部 `Role` 及其引用改名为 `PacingRole`，没有改变地牢调度逻辑。

第二轮 Game 构建中新增的 `HeQuePumpControl.cpp` 引用了 `AHeQueMonster` 尚未提供的 `PumpCooldownUntil`、`ReceivePumpRelease`。保留该玩法实现，构建结果如实记录；不猜测其冷却和行为来补接口。最终各目标状态以本目录构建回执为准。

## 已落盘

两次主工程互斥入口等待超时，均未启动材质命令。随后通过独立作者项目完成材质编译保存：`import-isolated-01.log` 对应 commandlet 正常退出 0，两份新材质已安装到正式 Content 新目录，文件摘要记录于 `import_receipt.json`。

共享怪物源码随后已提供上述接口，本轮没有编辑其玩法。第三轮正式 `FPSGAMEEditor` 和 `FPSGAME` 构建均返回 `Result: Succeeded`，分别记录于 `build-FPSGAMEEditor-03.log`、`build-FPSGAME-03.log`。两款目标的产物时间及先前失败记录保存在 `build_receipt.json`。

`publish.py` 已更新正式模块表、改造介绍及对应作者底表的破坏符文外观字段；最新材质引用、构建目标和粒子参数记录于 `delivery_receipt.json`。未运行游戏或进行视觉验收。
