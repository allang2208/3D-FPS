# 竖劈换位后的左手握柄接触

用户提供换位后的截图，指出左手没有抓到握柄。本轮只处理普通竖劈与冲刺竖劈的左手接触，继续保留左手靠护手、右手靠柄尾的顺序。

## 定向定位

读取已运行角色，其武器为唐刀，实际显示 `SM_TangDao_Grip_swift_grip`。读取该握柄的几何变换到实际世界武器 `WPN_root`，有效轴向范围约为 Z=-22.7 至 -5 cm。

已有原生动画诊断入口读取当前 `KwangSwordArmSwap20261010`，包括装备手指层。采样姿态中左食指根部约为 Z=-3.68 cm、末节约为 -4.37 cm：换位只交换了腕部高度，食指部分超出了握柄上沿。最小径向距离或两手腕间距不能代表整手已抓在实际有限长度的握柄上。

本轮读取没有驱动用户的运行角色、启动游戏或生成渲染。现场状态与握柄数据位于 `SourceAssets/ThirdPersonSwordLeftContact20261010/live-pair.json`、`handle-parts.json`；原生姿态与接触定位数据为 `native-contact.json`、`contact-diagnosis.json`。

## 修改与接入

制作源以已换位版本为基础，仅将左手整手沿剑柄向柄尾收回 2.4 cm，让左食指回到握柄上沿内；肘部按原生骨长跟随。左腕组件空间朝向、手指局部姿势、右臂、刀身轨迹及其补偿曲线、身体和动作时序保留。

制作脚本：`SourceAssets/ThirdPersonSwordLeftContact20261010/author_left_contact.py`。独立资产目录：`/Game/Characters/JasonPlayer20261003/KwangSwordLeftContact20261010/Animations`。保存、发布脚本分别为 `Tools/PlayerBody/save_sword_left_contact20261010.py`、`publish_sword_left_contact20261010.py`。

本版不改 C++，沿用上一版已编译的绕柄旋转和轴向挂接补偿。最初向现有编辑器互斥桥提交独立资产保存批次，但编辑器已于接入期间退出，桥未发现可用节点；等待该调用结束后，改用后台 Python commandlet 保存，没有重新打开可视编辑器。

两段资产均已保存，`assets-saved.json` 为 `complete: true`；`save-commandlet.log` 记录两段保存成功、`Success - 0 error(s)`，进程退出码为 0。两项竖劈引用已切换，`assets-published.json` 记录前后路径。

当前角色在 BeginPlay 读取 `player_body.json`；发布后的配置供下一次进入运行使用。本轮未运行修改后的游戏动画或进行后续验收，实际效果由用户测试。
