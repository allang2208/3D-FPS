# 升级奖励不能被公开镜像覆盖

适用：击杀和技能修炼正常发生，但角色始终停在旧等级，或升级属性点丢失。FPSGAME 的 Current 档案与公开 Level/AttributePoints 镜像在 Publish 前可能不同步。

StageTraining 得到奖励后状态 State 时，保留 Current 为奖励前状态，直接 PersistState(State,true)。不要先 Current=MoveTemp(State) 再保存 Snapshot()：Snapshot 会把尚未 Publish 的旧 Level/AttributePoints 回填，覆盖刚获得的等级。

持久化失败但奖励已被接受时，按原项目策略将本次 State 规范化、更新由上限变化带来的生命/魔法、发布公共镜像，标记待保存，并返回已接受。调用方据此标记怪物已奖励，避免下一次再次给同一击杀发经验。不能让失败路径只写 Current 而遗漏 Publish。

未升级的高频经验继续合并刷新/延迟落盘。进度提示比较奖励前后状态；HUD 经验数字、获得提示与升级事务是独立职责，不能为了修等级整体接管其他 UI 开发。

入口 Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp::StageTraining。发布共享文件时只选本修复增量，保留其他工作对经验 HUD、获取提示与网络档案的改动。需要测试时由用户授权，历史构建记录不证明读档或主客机升级已验收。
