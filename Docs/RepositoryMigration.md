# UE5 仓库根目录切换 · 2026-09-10

基于远端 main `a56dd1dbf562fd66c09e00908b0256c4edb707f4`，用普通提交将当前文件树从 Godot 切换到 UE5；旧历史保留在 `archive/godot-before-ue5-20260910`，无强推或历史重写。

旧 Godot 工程、脚本、资源、测试及旧技能等 6199 个文件（4,551,481,865 字节）已从隔离发布目录移入本机 `E:/3d/trash/repository-ue5-root-20260910`。目录下的 `archive-manifest.json` 记录原路径、去向、大小和 SHA-256。原共享 `E:/3d/3-dfps` 和完整 UE 宿主保持原位置及运行内容。

当前根目录收录 UE 宿主的完整源码模块、targets、描述符、项目配置、JSON 数据及开发工具；忽略用户设置、缓存、插件/资源二进制和 trash。新增源码取样散列见 [SourceSnapshot.json](SourceSnapshot.json)，资源范围见 [AssetSetup](AssetSetup.md)。取样后的并行宿主修改不会自动进入此次提交。

保留 `unreal/` 作为迁移证据，当前可编译代码以根目录 `Source` 为准。此次不改变换弹动作或音效；此前动画结果属于既有验收，不能替代未来改动的真实音画检查。

本次验证结果见 [RepositoryValidation.json](RepositoryValidation.json)。旧 Godot 工程已退出当前分支；历史对象仍保留，因此正常完整 clone 的历史体积不会因为此提交立即缩小，可按需使用浅克隆。
