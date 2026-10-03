#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "ColdSteelNetWorldSubsystem.generated.h"

/**
 * 联机会话引导层：与 GameMode 解耦的玩家加入/离开钩子。
 *
 * 原实现把档案通道挂在 AFPSNetGameMode::PostLogin 上——地图级 GameMode
 * （如丘陵图 TemperateHillsGameMode）会顶掉 GlobalDefaultGameMode，
 * 不带 ?game= 启动时整条联机通道静默缺席。
 * 本类改走引擎的 FGameModeEvents 广播：任何 GameMode 下的 PostLogin/Logout
 * 都会到达这里，客人档案槽名登记、影子档案落盘不再依赖地图选哪个 GameMode。
 * 服务端专用；单机与其他端上空转。
 */
UCLASS()
class FPSGAME_API UColdSteelNetWorldSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()

public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

private:
    void OnPostLogin(AGameModeBase* GameMode, APlayerController* NewPlayer);
    void OnLogout(AGameModeBase* GameMode, AController* Exiting);
    FDelegateHandle PostLoginHandle;
    FDelegateHandle LogoutHandle;
};
