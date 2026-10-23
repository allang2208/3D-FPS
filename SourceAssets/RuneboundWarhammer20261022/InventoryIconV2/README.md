# 符文战锤背包图标修正

旧兜底 PNG 来自 Blender 的模型制作场景；场景物体没有隔离且纹理链接丢失，最终画面出现紫色缺材质、遮挡及不完整武器。该图还进行了整把武器灰阶化，混用了改造配件图标规则。

背包首先请求 `UColdSteelWeaponIcons` 的动态模块化捕获，未就绪时读取 `Content/ColdSteelData/Icons/ue_runebound_warhammer.png`。本轮修正该实际兜底文件，并同步作者 Export 源图与已有 UI Texture2D。

`../author_icon.py` 现在委托 `Tools/UI/build_weapon_catalog_icons.ps1 -Definitions ue_runebound_warhammer`，由 `ColdSteelWeaponIconCatalog` 使用实际原装模块配方和原生 PBR 制作目录图。画布为 384×768，透明背景，正交侧视、长轴竖直、轮廓居中，主轴填充按共用捕获规则为 91%。ShowOnlyComponents 只包含武器装配，无手臂或制作场景几何；不对整把武器去色。改造实例继续使用现有动态捕获与配方缓存键。

作者入口在成功写出新 PNG 后同步 `../Export/ue_runebound_warhammer.png`，因此基础注册与资产重导不会再复制旧图。根目录 `import_assets.py` 和本轮定向 `import_icon.py` 同步采用 UI、EditorIcon、sRGB、NeverStream、NoMipmaps 设置。本轮不重新导入模型、贴图材质、动画或修改技能数值。

`Before/` 保存改前入口、两份错误 PNG 和旧图标资产；`production_receipt.json` 记录实际图像制作，`import_receipt.json` 记录实际 Texture2D 保存。未请求或运行游戏测试、截图及视觉验收；目录图渲染属于此次图标制作。

本轮实际完成 PNG 制作、Export 同步和 `/Game/ColdSteelData/Icons/ue_runebound_warhammer` 的定向重导保存。用户明确授权结束当前 PIE 后保存图标；停止请求完成退出后保存成功，保留编辑器，没有重新启动游戏。最终范围见 `delivery_receipt.json`。此次没有原生代码修改，无需 C++ 重编译。
