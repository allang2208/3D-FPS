# 环绕飞剑快捷栏调整 · 2026-09-27

## 已落盘

- 图源：本次会话内置 image_gen 生成。完整提示词见 icon_prompt.txt。
- 作者源：rune_orb_blades_cold_steel.png；运行时同名 PNG 位于 Content/ColdSteelData/Skills。
- skills.json 的 runeBlades 图标路径、ColdSteelSkillRules.cpp 默认路径和 Tools/UI/prepare_cold_steel_skill_icons.py 恢复映射同步更新。
- UColdSteelQuickSlot 直接以 ImportFileAsTexture2D 加载 PNG，本次图标不依赖额外导入的 Texture2D uasset。
- G 槽及其分隔线、槽内可用状态和实际技能触发统一使用 URuneOrbBladesComponent::SwordEquipped()。
- 只在当前启用主手为 ue_rune_sword 且未切至生产工具时显示；其他剑、枪、弓、空手不显示。背包或备用武器组中的符文长剑不满足条件。
- 冷却中仍显示冷却遮罩及秒数；召唤后显示待发射数量。隐藏槽位不清零组件冷却。

## 原项目规则依据

E:/无尽轮回/长期备份/2026-7-13-1/game-dev/src/ui/quick-bar.js：特殊攻击槽默认 display:none；refreshSpecialAttack 只读 player.equipments[player.weaponMode]，不回退到另一组；不支持特殊攻击的当前武器调用 disableSpecialAttack，整格隐藏。该项目同时支持 nightFlame 和 runeSword；UE 本次只调整 G 键 runeBlades。

问题原因：此前 HUD 和槽内状态使用 URuneSwordComponent::IsEquipped()，该组件服务多种双手剑，范围比飞剑实际触发条件宽。

## 最终模型去向

用户后来选定幽蓝灵体剑，已制作并接入；后续蓝色加深、透明度和随机爆炸沿用 [当前作者入口](../RuneSpectralBlade20260927/README.md)。下面仅保留当时的概念比较，不再表示当前制作状态。

推荐符文晶刃：细长有刃面的实体核心，细化倒角及小护手，蓝色半透外层、独立细符文通道与受控边缘光；悬浮低频明暗、发射短收尖拖尾、命中少量晶片消散。避免整剑白亮与过密裂纹。

替代方向：幽蓝灵体剑（更淡、少实体边界）；符文长剑幻影（复用主武器辨识轮廓、金属与蓝色符文并存）。保持现有四剑、伤害、冷却、碰撞与手势时序。

## 交付边界

用户保存关闭 UE 后，已完成 FPSGAMEEditor Win64 Development 常规原生构建，182 项构建动作，UnrealEditor-FPSGAME.dll 链接完成，Result: Succeeded。日志见 native-build.log。未重开编辑器，未启动游戏，未执行测试或验收；由用户进入游戏查看。
