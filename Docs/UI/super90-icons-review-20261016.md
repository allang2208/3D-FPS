# SUPER90 改造图标逐项排查与修正（2026-10-16）

依据当前 `gunsmith.json` 专属选项、`common_options` 合并与 `M4GunsmithLayout.cpp` 实际解析顺序，覆盖 **8 个可见分类、36 个选项，共 44 个显示项**。trigger、tactical_secondary、bipod 当前未开放；本枪没有 pistol_grip_surface 追加项。

处理 **9 项**，保留 **35 项**：重制六张原厂实体图；补上逐发装填专属中性状态图；补齐战术垂直握把共享键；修正弹仓共享分类图的不当减号。所有运行 PNG 与九个 UE Texture2D 的保存情况以 `import_receipt.json` 为准。

原厂模型来源为当前 `SK_Super90_V7` 的已有导出和 `Super90CommonStocks20261013/FactoryStock.blend`。作者脚本保留原始 UV 与 WS1 表面配方，只在独立图标场景转换为灰阶。完整后照门不带前准星；枪口选项以完整原厂枪管及其前准星表示。单发装填表示无速装器模式，采用中性减号。

使用内置 imagegen，一项一图。参考、提示词、迭代和成图位于 `SourceAssets/Super90IconReview20261016` 的 `References`、`generation_manifest.json` 和 `Generated`。逐项看过原图与 48/64 像素缩略图；新图也按同样尺寸查看。此处为静态图标排查，不代表游戏内 UI、装配或动作验收。

共享边界：战术垂直握把使用与 SUPER90 制作记录一致的 M4 供体，原有合格图提升到通用键；弹仓分类继续遵守共享分类优先规则，使用现有无状态弹匣代表图，因此其他枪型也显示此共享修正。其他非原厂共享选项继续使用现有成图，不另做武器专属副本。

已替换文件按精确路径归档在 `trash/super90-icons-replaced-20261016/manifest.json`；原厂枪托与后握把的旧制作入口已改为恢复本轮正式母图，避免重跑时退回简化边框。仅修改图标与制作入口，无 C++ 修改，不需要原生构建。未启动编辑器界面、游戏或 PIE，游戏内效果交由用户测试。

|序号|类别|项目|处理|最终加载键|结论|
|---:|---|---|---|---|---|
|1|optic|optic|保留|`category_optic`|分类使用统一代表图，保留。|
|2|optic|原厂鬼环瞄具|修正|`ue_super90_optic_false`|原图是其他枪型机械瞄具；改为本枪完整鬼环后照门，保留底座与护耳。|
|3|optic|全息瞄准镜|保留|`optic_holographic`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|4|optic|EOTH全息瞄准镜|保留|`optic_eoth_holographic`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|5|optic|全景薄框红点瞄具|保留|`optic_panoramic_red_dot`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|6|optic|紧凑型二倍棱镜瞄具|保留|`optic_prism_scope_2x`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|7|optic|1–6× 低倍可变瞄准镜|保留|`optic_lpvo_1_6x`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|8|optic|热成像瞄准镜|保留|`optic_thermal_scope`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|9|muzzle|muzzle|保留|`category_muzzle`|分类使用统一代表图，保留。|
|10|muzzle|原厂枪口|修正|`ue_super90_muzzle_false`|原图是通用消焰器；改为本枪原厂裸枪管及原生前准星。|
|11|muzzle|收束器|保留|`muzzle_shotgun_choke`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|12|muzzle|鸟笼消焰器|保留|`muzzle_shotgun_birdcage_flash_hider`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|13|muzzle|散弹枪消音器|保留|`muzzle_shotgun_suppressor`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|14|muzzle|鸭舌收束器|保留|`muzzle_shotgun_duckbill`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|15|magazine|magazine|修正|`category_magazine`|原分类带减号状态；复用现有无状态标记的共享弹匣代表图。|
|16|magazine|原厂管式弹仓|修正|`ue_super90_magazine_false`|管式弹仓误用盒式弹匣加减号；改为原厂管体、封帽与原装连接结构。|
|17|magazine|加长管式弹仓|保留|`magazine_super90_extended_tube`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|18|reargrip|reargrip|保留|`category_reargrip`|分类使用统一代表图，保留。|
|19|reargrip|原厂后握把|修正|`ue_super90_reargrip_false`|原轮廓对应本枪，但简化边框、平涂表面不合格；按真实纹理与统一框重制。|
|20|reargrip|幻影后握把|保留|`reargrip_phantom_reargrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|21|reargrip|稳固防滑后握|保留|`reargrip_stable_antislip_reargrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|22|reargrip|均衡后握把|保留|`reargrip_balanced_reargrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|23|stock|stock|保留|`category_stock`|分类使用统一代表图，保留。|
|24|stock|原厂枪托|修正|`ue_super90_stock_false`|原轮廓对应本枪，但简化边框、平涂表面不合格；按独立固定枪托重制，最终保留五个托底孔。|
|25|stock|骨架枪托|保留|`stock_skeleton`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|26|stock|镂空轻型枪托|保留|`stock_core_stock`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|27|stock|高性能后托|保留|`stock_qr_performance`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|28|stock|战术伸缩枪托|保留|`stock_tactical_telescopic`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|29|stock|可调式战术后托|保留|`stock_legendary_adjustable_tactical_stock`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|30|tactical|tactical|保留|`category_tactical`|分类使用统一代表图，保留。|
|31|tactical|无战术挂件|保留|`tactical_false`|无配件使用中性减号，保留。|
|32|tactical|红色激光镭射|保留|`tactical_laser`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|33|tactical|战术手电筒|保留|`tactical_flashlight`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|34|tactical|赐福激光镭射|保留|`tactical_blessed_laser`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|35|underbarrel|underbarrel|保留|`category_underbarrel`|分类使用统一代表图，保留。|
|36|underbarrel|原厂护木|修正|`ue_super90_underbarrel_false`|原厂护木误用空槽减号；改为原厂长条护木，保留原生防滑槽。|
|37|underbarrel|垂直握把|保留|`underbarrel_vertical_foregrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|38|underbarrel|45°侧倾握把|保留|`underbarrel_canted_foregrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|39|underbarrel|战术垂直握把|修正|`underbarrel_tactical_vertical_foregrip`|缺图导致回退普通前握把分类图；把现有 M4 同款供体图提升为共享键，保留真实战术握把轮廓。|
|40|underbarrel|棱镜阻手器|保留|`underbarrel_prism_handstop`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|41|underbarrel|共振二代前握把|保留|`underbarrel_angled_foregrip`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
|42|reload_device|reload_device|保留|`category_reload_device`|分类使用统一代表图，保留。|
|43|reload_device|逐发装填|修正|`ue_super90_reload_device_false`|红色禁止标识与铜色弹药违反灰阶规则且语义不清；无速装器模式复用中性减号。|
|44|reload_device|管式快速装填器|保留|`reload_device_super90_tube_loader`|已查看大图及 48/64 像素图：共享成图的轮廓、朝向、灰阶主体及金属框保留。|
