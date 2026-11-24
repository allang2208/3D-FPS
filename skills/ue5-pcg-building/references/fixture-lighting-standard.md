# 场景灯具、光源方向与照明层次

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-pcg-building/references/fixture-lighting-standard.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 灯具与实际发光方向

详见[维护源](../../_shared/ue5-pcg-building/references/fixture-lighting-standard.md)中的同名章节。

## 覆盖范围、分层补光与最低照明

详见[维护源](../../_shared/ue5-pcg-building/references/fixture-lighting-standard.md)中的同名章节。

## 保存、性能与交付边界

详见[维护源](../../_shared/ue5-pcg-building/references/fixture-lighting-standard.md)中的同名章节。

## 当前工程定位

详见[维护源](../../_shared/ue5-pcg-building/references/fixture-lighting-standard.md)中的同名章节。

## 铁匠铺的铁砧与炉膛

- 六家商店的灯位、朝向与修复状态由 `VillageShopTorches.cpp` 的挂点表维护，室内、外墙和破败保留位分别使用常亮、昼夜时钟和熄灯状态。灯体、链节和点光源复用 `AVillageShopChainLamp`。烘在关卡里的旧灯碗、火焰卡和点光源需随挂点迁移一起处理。炉膛火焰仍由炉膛系统负责。
- 复核性能时，可在同一机位交替采样点光源正常、隐藏两种状态，固定分辨率与限帧并留出预热帧。分别记录 GPU 帧时间与游戏线程高分位，注明修复、流送及联机负载。
- 炉膛需要贴近燃料的火光。`UpdateForgeLight` 从带 `VillageShop.HearthFire` 标签的火焰取得炉箅坐标，将小半径暖光放在煤层与铁罩之间，使罩和炉壁参与遮光。用同名组件随店铺修复状态切换可见性，避免重复刷新时叠灯。
