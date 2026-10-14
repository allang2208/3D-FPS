#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "ColdSteelNetConnectSubsystem.generated.h"

/**
 * M4 测试辅助：-MPConnect=<addr> -MPConnectDelay=<秒> 启动参数。
 *
 * 动机：重资产地图在"网络 travel 加载"路径上会 1.3s 静默失败（Failed to load package，
 * 直开同图正常——DayNight/丘陵均复现）。本子系统让客户端先本地直开目标图把资产编译
 * 热，再在延迟后从进程内发起 open <addr> 完成连线（旅行重载命中热缓存即可通过）。
 * 不依赖任何 GameMode，所有地图可用；只连一次。
 */
UCLASS()
class COLDSTEELNET_API UColdSteelNetConnectSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()

public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;

private:
    void TryConnect();

    FString Target;
    float Delay = 90.f;
    double ArmedAt = 0.0;
    FTimerHandle TimerHandle;
    bool bConnectIssued = false;
};
