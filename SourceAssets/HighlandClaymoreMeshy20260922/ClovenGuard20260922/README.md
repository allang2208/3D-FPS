# Highland Cloven Guard / 裂角护手

独有护手：格挡体力 -10%；成功弹反后 4 秒内，下次普攻立即释放无需蓄力的重击，物理伤害 +25%、韧性伤害 +40%。最多一次，弹反刷新，发起即消耗。

制作入口 `author_guard.py`，安装入口 `install_guard.py`（通过工程 `mcp_call_codex.ps1` 执行）。`source_guard.json` 记录原装翼部截面，仅用于制作。`production.json` 包含作者源、挂点、材质槽、数值及图标朝向。

`Highland_ClovenGuard_Editable.blend` 为可编辑装配源；`Highland_ClovenGuard_MenuIcon_Editable.blend` 为交付图标源。FBX 在 Export，透明菜单 PNG 在 Icons。模型中央接口与 PBR 继承用户选定高地剑；新增材质只用于嵌纹及槽底。

游戏接入回执 `install_receipt.json`，必要构建日志 `build-native.log`，完成状态 `delivery.json`。未做游戏测试或验收。
