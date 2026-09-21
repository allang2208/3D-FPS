#pragma once
#include "CoreMinimal.h"
#include "HAL/IConsoleManager.h"

/**
 * 建筑系统的诊断日志开关。2026-09-16 清理：原先的 VOXEL_AIM / VOXEL_REJECT 等诊断直接写
 * LogTemp:Warning，每帧刷屏（一次会话几十万行、几百 KB），现在统一由 fps.Building.DebugLog 控制，
 * 默认关闭。真正的错误（存档失败、调色板缺条目）仍然无条件记录。
 */
namespace VoxelBuildDebug
{
    inline bool Enabled()
    {
        // 审计 C12：原来每次调用都做一次哈希字符串查找（FindConsoleVariable），
        // 而本函数在瞄准/拒绝/审计路径上被高频调用。CVar 由另一个翻译单元的
        // TAutoConsoleVariable 持有，在其生命周期内指针稳定，因此缓存是安全的；
        // 若尚未注册（返回空）则不缓存，下次再试。
        static const IConsoleVariable* Cached=nullptr;
        if(!Cached)Cached=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Building.DebugLog"));
        return Cached&&Cached->GetInt()!=0;
    }
}
