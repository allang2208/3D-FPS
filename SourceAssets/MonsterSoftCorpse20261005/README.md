# 非人形连续软体死亡：本机制作数据

本机已保存 11 个角色条目、10 个独立网格绑定的尸体网格、骨架、数据、材质与活体附加元数据；巨手和小皮肤手共用绑定。范围与状态见 [死亡标准](../../Docs/Monsters/continuous-soft-corpse-standard-20261005.md)。

Git 只包含 `Tools/MonsterSoftCorpse` 作者配方和公共 C++ 接口。本目录的原表面导出、四面体、绑定权重、源模型信息、日志、备份与回执不公开。需要先恢复各怪物合法的完整本机资产，并完成对应原生类型构建。

制作次序为 UE 无界面 `prepare_sources.py`、外部 Python `author_cages.py`、UE 无界面 `install_corpses.py`；`build_assets.py` 组合三个制作步骤，路径按本机 Python 3.11 配置。续跑不要用已经重绑的尸体代替原始导出。修改源模型后建立新的版本目录。

M08 属于其他对话尚未发布的独立模块，完整目标表需要其本机类和资产；它继承 Wolf 的通用死亡入口。M25 已在本次推送衔接期间由独立提交 `20a763c3` 发布，本轮直接整合其软体挂接。旧交接补丁无需重复应用。

原 `Before` 备份已移到 `trash/m14-retired-20261005/SourceAssets/MonsterSoftCorpse20261005/Before`，散列见公开归档清单。游戏效果未测试，用户自行体验。
