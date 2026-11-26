# 双手锤第三人称普通攻击 V3 与头颈稳定

本版本的重编排动画已被用户否定，运行引用已切换到 `steel-warhammer-direct-kwang-v5-20261016.md` 所述完整 Kwang 素材，V5 正式构建与切换均已完成。头颈稳定处理保留；下文为历史制作记录。

## 本次修改

- 普通三连击与三个命中回收使用独立 `NormalComboV3` 资产。
- 直接读取已导入的 Epic Paragon Sevarog `Swing1/2/3_120fps` 原始组件空间动作。以源 Idle 和 Jason 的中立姿态校准，去掉旧版将重定向局部旋转直接配上原生骨长的错误。
- 依据肩线统一朝向，按实际臂长和腿长迁移运动；五节脊柱插值对应源三节脊柱。保留髋部位移、肩腰转动和源肘部弯曲方向。
- 两手作为同一握柄组合拟合；沿用 SprintLiftV2 的连续肘极与前臂扭转分配。武器和双掌沿同一运动轨迹。
- 普通攻击保留原有 1.75 秒作者时钟、0.97 秒接触、连击窗口和第一人称/伤害逻辑；源时间映射采用单调曲线，避免分段线性映射产生速度突变。
- 命中回收保留原有 0.8 秒与三段停顿时间；从接触姿态短暂停住后收锤，身体继承源动作的后续发力与收势。取消把完整数秒 Return2Idle 压缩进 0.8 秒的做法。

## 头颈

`FPSPlayerBodyAnimInstance.cpp` 为双手锤缓存中立姿态的 `neck_01 / neck_02 / head` 局部变换，最终姿态合成后恢复这三根骨骼。头颈不再继承素材或走跑的独立转动，只跟随胸部。此前禁止双手锤镜头俯仰驱动躯干的处理保留。

保持消费动作口部接触的权重，翻越和死亡继续由各自的外层动作控制。双手剑和其他武器不使用这个覆盖。

## 可编辑输入及接入

- 作者脚本：`SourceAssets/WarhammerThirdPersonSevarog20261016/NormalComboV3/author_combo.py`
- 作者结果：同目录 `adapted-actions.json`
- 保存入口：`SourceAssets/WarhammerThirdPersonSevarog20261016/save_normal_combo.py`
- 新资产目录：`/Game/Characters/JasonPlayer20261003/WarhammerSevarog20261016/NormalComboV3/Animations`
- 保存回执：同目录 `assets-saved.json`；实际引用替换回执：`assets-published.json`。
- 仅替换 `player_body.json` 中六个 `Warhammer.FullBody.Slash*` 键，保留冲刺 V2 和其他动作。

素材沿用 Epic Sevarog 原许可，作者脚本不赋予重新分发原始素材的许可。

## 交付状态

六个普通攻击/命中回收资产已由后台 commandlet 保存，并写入实际配置；`assets-saved.json` 的 `complete` 与 `assets-published.json` 的 `published` 均记录完成。头颈固定代码已正式编入 `UnrealEditor-FPSGAME.dll`；后台 Editor 构建成功，日志为 `Saved/BuildEditor/build-20261016-200606.log`，本批构建输出保存在作者目录 `build-editor.log`。未启动编辑器、游戏、PIE、自动测试或视觉验收，最终动作和手感由用户测试。
