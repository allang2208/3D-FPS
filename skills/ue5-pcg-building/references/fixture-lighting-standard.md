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

- 铁砧靠侧光显出砧面和边沿。在 `HillsBlacksmith.cpp` 的 `UpdateSmithTorches` 中，将工作火把挂在前拱柱内侧，让光从操作侧掠过砧面，后墙落在直接照明半径外。宽光源配合较低的镜面强度可收住亮斑。工作火把单独调参，门口和阁楼各沿用自己的灯位。
- 炉膛需要贴近燃料的火光。`UpdateForgeLight` 从带 `VillageShop.HearthFire` 标签的火焰取得炉箅坐标，将小半径暖光放在煤层与铁罩之间，使罩和炉壁参与遮光。用同名组件随店铺修复状态切换可见性，避免重复刷新时叠灯。
