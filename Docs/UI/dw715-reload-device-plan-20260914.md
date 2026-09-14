# 715 装填装置栏目

交付阶段：游戏接入。入口为现有枪匠工作台 → Dan-Wesson 715 → 装填装置，提供“逐发装填（原厂）”与“六发速装器”。本轮不运行测试或预览，由用户测试。

- 复用 M4GunsmithLayout、UGunsmithSystem、ColdSteelUIStyle 的左目录、中央配件卡片、右侧实值汇总、固定应用／撤销操作。栏目加入目录末尾；仅 715 可选，其他枪沿用既有“待扩展”禁用展示。
- 宽屏、紧凑、窄窗和矮窗继续由工作台现有响应容器处理；目录、卡片、汇总沿用各自滚动容器，页脚不随内容滚动。新增两张卡片，不修改断点。
- 沿用 Noto Sans SC 文本、JetBrains Mono 数字、银灰中性图标和共享玻璃主题。栏目及两张选项图为本轮程序绘制的 RGBA 图标，加载失败沿用现有分类图回退；不另建图片队列或交互状态。
- 数据来自 gunsmith.json：槽位 reload_device，未安装／false 表示逐发，dw715_speedloader 表示速装器。按目录顺序显示，统计与真实换弹都读实际已安装项；选择草稿只更新对比，应用才保存。
- 单发时长按本次需要和可用弹药裁剪，面板普通／空仓时长分别对应补 5／6 发的基准；速装器对应 3.6／3.85 秒，属性和巧手乘数继续作用于整段动作。容量仍为 6。
- Select → CanApply → Apply／Undo 使用既有业务入口及物品 gunsmith_parts 保存事务；不增加物品成本。旧存档无此键自然使用逐发，无版本迁移。忙碌、武器移出及数据改变沿用现有拒绝反馈，关闭恢复已安装状态。
- 文件范围：gunsmith.json、DanWesson715WeaponAssets、GunsmithSystem、Character／ProfileRuntime；分类 Texture 与两张配件 PNG；逐发 Blend／FBX／AnimSequence。无退役文件，无新面板生命周期或输入逻辑。
