#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "../FPSGAMECharacter.h"
#include "AlchemyManualNetAudit.generated.h"
class AVoxelBuildPrefabActor;
class AVoxelBuildWorld;

UCLASS()
class AAlchemyManualNetAuditPawn : public AFPSGAMECharacter
{
    GENERATED_BODY()
public:
    AAlchemyManualNetAuditPawn();
    virtual void BeginPlay() override;
};
UCLASS()
class AAlchemyManualNetAuditProbe : public AActor
{
    GENERATED_BODY()
public:
    AAlchemyManualNetAuditProbe();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(Replicated) TObjectPtr<AVoxelBuildPrefabActor> Bench;
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) int32 ExpectedPage=0;
    UPROPERTY(Replicated) bool ExpectedOpen=true;
};
UCLASS()
class AAlchemyManualNetAuditController : public APlayerController
{
    GENERATED_BODY()
public:
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    UFUNCTION(Server,Reliable) void ServerHello(const FString& InRole);
    UFUNCTION(Server,Reliable) void ServerReport(int32 Phase,bool Pass);
    UFUNCTION(Client,Reliable) void ClientLeave();
    FString Label;
    int32 ReportedPhase=0;
    bool Failed=false;
private:
    int32 SeenPhase=0,SentPhase=0;
    double SeenAt=0;
};
/** Explicit opt-in fixture: real production station RPC and prefab replication. */
UCLASS()
class AAlchemyManualNetAuditGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AAlchemyManualNetAuditGameMode();
    virtual void BeginPlay() override;
    virtual void Tick(float Delta) override;
    virtual void Logout(AController* Controller) override;
private:
    void Seed(AAlchemyManualNetAuditController* Controller,bool Host);
    void Phase(int32 Number,int32 Page,bool Open=true);
    UPROPERTY() TObjectPtr<AAlchemyManualNetAuditProbe> Probe;
    UPROPERTY() TObjectPtr<AVoxelBuildWorld> Building;
    double Started=0;
    bool Done=false;
};
