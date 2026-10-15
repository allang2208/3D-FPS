# M66 V12 背孔黑烟与同款目盲

用户要求背后孔状结构像百目喷出同款黑烟，烟雾自然扩散并下沉，进入烟雾受到同款目盲。先接入持续排烟与区域目盲，作为下一种“背孔排烟”的基础；此轮不制作新的蓄压动作或替换已认可横扫。

## 制作与机制

- 读取已认可 V10 模型中四个排气孔的末端骨骼及孔缘顶点，得到高、后、前、侧四个喷口。原始挂点见 `Records/outlets.json`，通过参考骨架逆变换转为局部偏移，保留 UE 容器根 100 倍单位换算。
- 每只 M66 由服务器创建一个复制的 `AM66BackMist`，四个喷口共用一个 Niagara 组件。位置随背孔骨骼更新，烟粒出生时保存位置、漂移、地面高度；已经离体的烟不会被转身或移动拖回身体。
- 新 Niagara 直接复用百目 `M_SlagPersistentBodySmoke`、Mantaflow 密度图集和黑色密度表现；百目的上浮轨迹和原三喷口默认设置保留。
- M66 烟团先从小团扩散，向背后渐进漂移至约 110 cm，并逐渐达到 38 cm/s 下沉速度，中心最低停在出生地面上方 55 cm。浓烟保留 8 s，最后 1.5 s 消散。每秒 12 粒，约 114 粒存活上限；暴露历史最多 32 组，每组四个喷口。
- 目盲复用 `USlagMistViewComponent`：玩家眼点进入可见浓烟核心才触发，同款糊屏和状态图标，离开马上解除。烟团中心运动和浓度成长在 Niagara、暴露判定及运行包围盒中使用同一公式；墙体遮挡继续走现有百目规则。
- 只添加目盲，不新增伤害。服务器复制烟雾对象及停止发射状态，各玩家使用已有的独立目盲组件。死亡或移除 M66 后停止新烟，旧烟继续消散；重叠黑烟共用一层屏幕效果。
- 活体排烟时保留骨骼更新，确保服务端、客机和背后喷口位置可用；地面采样随有界烟迹组更新，没有新的粒子 Actor 或逐粒子射线。

## 文件与接入

- 原生：`M66BackMist.*`、`M66BackSmoke.cpp` 与 M66 生命周期；共享 `SlagBlackMist` 增加可选第四喷口和运动/密度扩展点，百目和 M10 毒雾保留原默认值。
- 新资源：`/Game/Monsters/IncineratorBossM66/BackSmokeV12/NS_M66DescendingSoot`。
- 作者：`author_smoke.py`；原角色保存：`install_character.py`。
- 原角色：`BP_M66RigPreview`；V10 模型、V08 横扫、V11 的 90 点伤害与 350 cm 起手距离继续使用。

当前：常规 Editor DLL 构建完成（`Saved/BuildEditor/build-20261015-003204.log`，Succeeded，复用已更新构建产物）；Niagara 已于后台编译保存，原角色排烟配置已保存，两个 commandlet 均退出码 0。回执见 `Records/niagara_install.json`、`Records/native_build.json`、`Records/character_install.json`，进程记录分别在 `Records/install-20261015-002904` 和 `Records/install-20261015-003342`。角色回执保留 V10 模型、V08 横扫、90 点伤害与 350 cm 起手距离。未运行游戏、截图、渲染或联机测试。
