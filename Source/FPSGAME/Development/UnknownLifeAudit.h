#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "UnknownLifeAudit.generated.h"

USTRUCT()
struct FUnknownLifeProbe
{
    GENERATED_BODY()
    UPROPERTY() int32 Stage=0;
    UPROPERTY() int32 Step=-1;
    UPROPERTY() TObjectPtr<APawn> Pawn;
    UPROPERTY() float Health=0;
    UPROPERTY() TArray<TObjectPtr<class AUnknownHumanoid>> Monsters;
    UPROPERTY() int32 Zones=0;
    UPROPERTY() bool bMageDead=false;
};

/** Opt-in, isolated NullRHI fixture; never used by a shipping game mode. */
UCLASS()
class AUnknownLifeAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) FUnknownLifeProbe Probe;
    UFUNCTION(Server,Reliable) void ServerObserved(int32 Key,bool bOK,const FString& Detail);
    UFUNCTION(Client,Reliable) void ClientFinish();
    int32 Finished=-1;
private:
    TWeakObjectPtr<APawn> Attached;
    int32 Watching=-1,Reported=-1;
    double WatchingAt=0,ExitAt=-1;
};

UCLASS()
class AUnknownLifeAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AUnknownLifeAuditGameMode();
    virtual void StartPlay() override;
    virtual void Tick(float Delta) override;
    void Observe(int32 Key,bool bOK,const FString& Detail);
private:
    UPROPERTY() TArray<TObjectPtr<class AUnknownHumanoid>> Monsters;
    UPROPERTY() TObjectPtr<AUnknownLifeAuditController> Guest;
    TWeakObjectPtr<APawn> DeadPawn;
    int32 Stage=0,Step=-1;
    double Started=0,Deadline=0,ExitAt=-1;
    float StableHealth=0;
    bool Travelling=false;
    bool Record(bool bOK,const FString& Name,const FString& Detail=FString());
    void Publish(int32 Next,int32 Zones=0,bool Dead=false);
};
