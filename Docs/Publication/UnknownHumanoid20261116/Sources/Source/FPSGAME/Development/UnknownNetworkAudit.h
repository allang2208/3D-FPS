#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Monsters/UnknownHumanoid.h"
#include "UnknownNetworkAudit.generated.h"

/** Explicit opt-in, isolated transport fixture. No production map or save edits. */
UCLASS()
class AUnknownNetworkAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(Replicated) TObjectPtr<AUnknownHumanoid> Subject;
    UPROPERTY(Replicated) TObjectPtr<class AFPSHolyLightEffect> Light;
    UPROPERTY(Replicated) FUnknownLoadout ExpectedLoadout;
    UPROPERTY(Replicated) FUnknownMotion ExpectedMotion;
    UPROPERTY(Replicated) float ExpectedHealth=0;
    UPROPERTY(Replicated) bool ExpectedBlades=false;
    UPROPERTY(Replicated) bool ExpectedArmor=false;
    UPROPERTY(Replicated) uint32 ExpectedImpact=0;
    UPROPERTY(Replicated) int32 Case=-1;
    UFUNCTION(Server,Reliable) void ServerObserved(int32 Index,bool Passed,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientFinish(bool Passed);
    int32 Finished=-1;
    bool AllPassed=true;
    TArray<TSharedPtr<class FJsonValue>> Results;
private:
    int32 Watching=-1,Reported=-1;
    double Started=0,ExitAt=-1;
};

UCLASS()
class AUnknownNetworkAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AUnknownNetworkAuditGameMode();
    virtual void StartPlay() override;
    virtual void PostLogin(APlayerController* Player) override;
    virtual void Tick(float Delta) override;
private:
    UPROPERTY() TObjectPtr<AUnknownNetworkAuditController> Guest;
    UPROPERTY() TObjectPtr<AUnknownHumanoid> Subject;
    int32 Prepared=-1;
    double Started=0,ExitAt=-1;
    bool Passed=true;
};
