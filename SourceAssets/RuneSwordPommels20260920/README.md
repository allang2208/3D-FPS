# 星系三款配重制作源

陨星锤首、凝碧星核、疾星配重的当前主体制作源。三者已纳入 [六款剑类通用配重](../SixSharedSwordPommels20260920/README.md)，由符文长剑和寒晶剑共同选用，2026-09-20 用户确认达标。

保留制作顺序：`prepare_source.py` → `author_bases.py`／`author_interface.py` → `author_models.py` → `bake_export.py` → `import_models.py`；菜单图标由 `render_attachment_icons.py`、`import_attachment_icons.py` 制作和导入。作者脚本依赖本地已许可源模型、真实安装面和参考图；详见各脚本输入路径。Editable、PBR 与 Icons 三个 Blend、Export、Textures、Interface、References、Icons 继续保留，不公开上传源二进制。

三款只在共享目录定义一次，当前 `ballast_hardened`、`ballast_rune`、`ballast_magic_orb` ID 含义保持不变。寒晶铜色主题与正向接口在 `../SharedSwordPommels20260920`；符文剑安装寒晶原三款的反向接口与最终目录入口在 `../SixSharedSwordPommels20260920`。

旧符文剑专属安装器和替换前回滚目录已移至 `trash/six-sword-pommels-20260920`。目录安装统一使用最终六款入口，禁止重新写入旧武器过滤。现行 Content 配置和各阶段 import/model/icon 回执是恢复依据；回执中的归档前日志／原型路径属于历史生产记录。

本轮没有追加游戏测试；资源恢复边界见 [AssetSetup](../../Docs/AssetSetup.md)。
