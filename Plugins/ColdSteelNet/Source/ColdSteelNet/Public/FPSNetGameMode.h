#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameMode.h"
#include "FPSNetGameMode.generated.h"

class APlayerStart;

/**
 * 联机模式 GameMode（M1 地基）。
 *
 * 与 AFPSGAMEGameMode（AGameModeBase，单机基类）的区别：
 *  - 继承 AGameMode：为后续 match state / seamless travel / 重连流程留路；
 *  - 出生点分配：按会话占用轮转，替代原"迭代顺序 first-fit"（多人会挤同一个 PlayerStart）；
 *  - 连接可观测性：PostLogin/Logout 打 LogColdSteelNet 日志，供双进程冒烟断言。
 *
 * 通过 URL 覆盖启用（不改全局配置）：
 *   open /Game/GameMaps/DayNight_Lighting?listen?game=/Script/ColdSteelNet.FPSNetGameMode
 *
 * 注意：AFPSGAMEGameMode 里的传送门安装/天气补种等单机向逻辑有意不复刻，
 * 那些子系统带 NM_Standalone 闸门，多人化在 M4 处理（见计划文档 §3）。
 */
UCLASS()
class COLDSTEELNET_API AFPSNetGameMode : public AGameMode
{
    GENERATED_BODY()

public:
    AFPSNetGameMode();

    //~ AGameModeBase（ChoosePlayerStart 是 BlueprintNativeEvent，C++ 侧重写 _Implementation）
    virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;
    /** 登录链路插桩：定位 Login request 之后无日志卡死的具体环节。 */
    virtual void PreLogin(const FString& Options, const FString& Address, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage) override;
    virtual APlayerController* Login(UPlayer* NewPlayer, ENetRole InRemoteRole, const FString& Portal, const FString& Options, const FUniqueNetIdRepl& UniqueId, FString& ErrorMessage) override;
    virtual void RestartPlayer(AController* NewPlayer) override;
    virtual void PostLogin(APlayerController* NewPlayer) override;
    virtual void Logout(AController* Exiting) override;
    //~

protected:
    virtual void BeginPlay() override;

private:
    /** 会话内出生点占用表：控制器 -> 分到的 PlayerStart（断线 Logout 释放，重生复用原点位）。 */
    TMap<TWeakObjectPtr<AController>, TWeakObjectPtr<APlayerStart>> ClaimedStarts;

    /** 出生点轮转游标：无空位回退时用于错开。 */
    int32 NextStartIndex = 0;
};
