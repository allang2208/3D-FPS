# 村民对话、商店浮窗与目录图标

## 同一对话框接入不同角色

`ColdSteelNpcDialogueArtisans.h` 的 `FSpeaker` 保存称呼、开场、闲聊话题、交易按钮和可选教学入口。铁匠与木匠有各自的教学动作，共用 `UColdSteelNpcDialogue` 的页面、返回路径和焦点恢复。教学按当前老师发请求，避免只换文案、按钮仍找上一位 NPC 的情况。

`SColdSteelNpcSpeech` 按字符边界逐字呈现，用完整句预留换行高度；读完短暂停留后自动进入下一句。鼠标单击、双击都走 `RevealOrAdvance`，消费用于补句或翻句的输入；按钮也须在处理选项前判定补句。离开页面时停止当前计时器并解除回调。对话 HUD 与转身面向绑定本地玩家和当前会话，两人可以同时向同一 NPC 交谈。

## 把货架实例交给背包浮窗

`UColdSteelShopGrid` 向现有 HUD 传入 `FColdSteelItemTooltipPreview`，内含本批真实商品和货架位置、操作提示。普通背包能由背包实例 ID 找物品，尚未买入的货架货品需显式传预览值，否则品质、实际属性或详情会错位。沿用同一浮窗的悬停、固定与键盘焦点。货架更新后依商品键重找当前行；原批次售出时关闭该来源的固定浮窗。背包与附加收纳区共用物品底色规则。

## 无渲染设备也能解析目录图

`UColdSteelWeaponIcons::Request` 先算配方键。命中缓存直接返回；`!FApp::CanEverRender()` 或 `GUsingNullRHI` 时也返回键，省掉实时拍摄排队。商店绘制时优先已就绪的实时图，目录候选依次为配件变体、`Icons/<Definition>.png`、物品的 `ue_icon`。例如魔晶双手剑使用 `Content/ColdSteelData/Icons/ue_frost_crystal_sword.png`，此目录由 `FPSGAME.Build.cs` 的 UFS 运行时依赖随包携带。NullRHI 可用于读回路径和状态；图标的屏幕观感需要有渲染设备的画面。
