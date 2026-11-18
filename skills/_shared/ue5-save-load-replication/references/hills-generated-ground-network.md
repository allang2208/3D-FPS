# 静态生成地面与联机身份

适用于 FPSGAME 本地重建地形、来宾直达及版本兼容，不表示所有 DynamicMesh 都应静态。

- 两端高度摘要一致不代表角色能正常移动。异步生成的不可寻址动态组件可能让角色纠正引用客机无法解析的相对移动基底，日志为 `could not resolve ... ignoring server correction`。固定世界根与地面块变换不移动时设为 Static，纠正使用世界坐标；保留地形更新和碰撞生成。
- 地标直达经拥有者 PlayerState 的可靠 Server RPC 请求；服务端计算目的地、等碰撞、校验胶囊落点。允许权威端处理远端控制器，落地恢复 Walking 并同步客机朝向。
- Seed、WorldId、生成版本和采集 ID 不是构建版本。排序后的生成源码及相关资产散列可注册独立网络版本，不为拒绝旧内容而改存档身份。资产更新后须重新构建签名，它不替代整包完整性校验。
- 用户要求联机检查时保留真实 Pawn、生产交互 RPC 与保存路径，覆盖晚加入、实际移动、资源耗尽、断线同档重连及不兼容内容拒绝。让生产 Logout 完成后再重连，不在夹具里提前清理状态。
- 无效移动纠正与残余 `FNetGUIDCache::SupportsObject` 警告分别记录，功能检查通过不代表无警告。NullRHI、本机 UDP 不证明双端画面、公网或专用服务器支持。

入口：`TemperateHillsCompatibility`、`TemperateHillsQuarryTravel`、`HillsSceneryNetworkProbe`、`Run-HillsSceneryNetwork.ps1`。夹具只在明确要求相应检查时运行；冻结构建与回执匹配，默认不能指向已被失败运行淘汰的模块。 原因：异步消息可能在动作结束或装备切换后到达，只有匹配当前身份才能修改现态。
