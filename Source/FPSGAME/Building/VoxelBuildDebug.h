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
        const IConsoleVariable* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("fps.Building.DebugLog"));
        return CVar&&CVar->GetInt()!=0;
    }
}
