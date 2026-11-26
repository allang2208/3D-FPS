#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../Dungeons/DungeonSharedProgress.h"
#include "HeQueNetAudit.generated.h"
class AHeQueMonster;
class ACharacter;

/** Opt-in real socket fixture. Normal dungeon maps never select this game mode. */
UCLASS()
class AHeQueNetAuditProbe : public AActor
{
    GENERATED_BODY()
public:
    AHeQueNetAuditProbe();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) FDungeonSharedProgress Progress;
    UPROPERTY(Replicated) int32 Phase=1;
    UPROPERTY(Replicated) TObjectPtr<AHeQueMonster> Boss;
    UPROPERTY(Replicated) TObjectPtr<ACharacter> PushedPawn;
    UPROPERTY(Replicated) FVector ExpectedEnd=FVector::ZeroVector;
};
UCLASS()
class AHeQueNetAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
    UFUNCTION(Server,Reliable) void ServerHello(const FString& InLabel);
    UFUNCTION(Server,Reliable) void ServerReport(int32 Phase,bool Pass,float Error,bool SawPush);
    FString Label;
    int32 ReportedPhase=0;
    bool Failed=false;
private:
    FDungeonSharedProgress Mirror;
    int32 SentPhase=0,ObservedPhase=0;
    double PhaseAt=0.;
    bool bSawPush=false;
};
UCLASS()
class AHeQueNetAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AHeQueNetAuditGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Dt) override;
private:
    UPROPERTY() TObjectPtr<AHeQueNetAuditProbe> Probe;
    double StartedAt=0.,PushAt=-1.;
    bool Done=false;
};
