#pragma once

#include "CoreMinimal.h"
#include "FPSGAMEGameMode.h"
#include "FPSNetGameMode.generated.h"

class APlayerStart;

/**
 * 联机模式 GameMode（M1 地基）。
 *
 * 重构后继承 AFPSGAMEGameMode（单机基类）：自动获得 DefaultPawnClass /
 * PlayerControllerClass / PlayerStateClass（AColdSteelPlayerState）与各地图通用的
 * 安全出生探测——任何图 ?listen 不再依赖地图恰好选这个 GameMode。
 *
 * 本类保留联机专属职责：
 *  - 出生点分配：按会话占用轮转，替代原"迭代顺序 first-fit"（多人会挤同一个 PlayerStart）；
 *  - 连接可观测性：PostLogin/Logout 打 LogColdSteelNet 日志，供双进程冒烟断言；
 *  - seamless travel / MaxPlayers=4 / -MPAutoWalk 取证钩 / 服务端坐标探针。
 *
 * 玩家档案/影子档案/命中通道改由 UColdSteelNetWorldSubsystem + AColdSteelPlayerState
 * 承载，与本 GameMode 解耦——TemperateHills 等地图 GameMode 接管时通道照常工作。
 *
 * 通过 URL 覆盖启用（不改全局配置）：
 *   open /Game/GameMaps/DayNight_Lighting?listen?game=/Script/ColdSteelNet.FPSNetGameMode
 */
UCLASS()
class COLDSTEELNET_API AFPSNetGameMode : public AFPSGAMEGameMode
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
    virtual void Tick(float DeltaSeconds) override;
    //~

protected:
    virtual void BeginPlay() override;

private:
    /** 会话内出生点占用表：控制器 -> 分到的 PlayerStart（断线 Logout 释放，重生复用原点位）。 */
    TMap<TWeakObjectPtr<AController>, TWeakObjectPtr<APlayerStart>> ClaimedStarts;

    /** 出生点轮转游标：无空位回退时用于错开。 */
    int32 NextStartIndex = 0;

    /** 视觉验收演示：MPAutoWalk 启动参数开启后，服务端驱动远端玩家 pawn 来回走动。 */
    bool bAutoWalkDemo = false;
    float AutoWalkTime = 0.f;
    /** 各远端 pawn 的往返基准 X（首次纳入时取出生点 +150cm 错开主机玩家）。 */
    TMap<TWeakObjectPtr<APawn>, float> AutoWalkBaseX;
    /** M4 取证：服务器侧玩家坐标探针计时。 */
    float PositionProbeTimer = 0.f;
};
