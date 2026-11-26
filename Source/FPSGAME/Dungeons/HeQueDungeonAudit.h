#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "HeQueDungeonAudit.generated.h"

/** Opt-in test driver owned by the real player controller; gameplay requests
 * still use the production PlayerState inventory and team-travel RPCs. */
UCLASS()
class AHeQueDungeonAuditPeer : public AActor
{
    GENERATED_BODY()
public:
    AHeQueDungeonAuditPeer();
    virtual void Tick(float Dt) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UFUNCTION(Server,Reliable) void ServerReport(int32 InPhase,const FString& Json);
    UPROPERTY(Replicated) int32 Phase=0;
    UPROPERTY(Replicated) FString AuditRole;
    UPROPERTY(Replicated) FString RunId;
    UPROPERTY(Replicated) FString ChestName;
    UPROPERTY(Replicated) FString PortalName;
    UPROPERTY(Replicated) FString ExpectedReward;
    UPROPERTY(Replicated) int64 ContainerRevision=0;
    UPROPERTY(Replicated) double ExecuteAt=0.;
    int32 ReportPhase=0;
    FString Report;
private:
    int32 LocalPhase=0,SentPhase=0;
    double BeganAt=0.;
    bool Requested=false;
    TWeakObjectPtr<AActor> CachedChest,CachedPortal;
};

/** Persists the audit across the actual dungeon -> hub ServerTravel. */
UCLASS()
class UHeQueDungeonAuditSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
    GENERATED_BODY()
public:
    virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Tick(float Dt) override;
    virtual TStatId GetStatId() const override;
    virtual bool IsTickable() const override { return !HasAnyFlags(RF_ClassDefaultObject)&&!Done; }
    virtual UWorld* GetTickableGameObjectWorld() const override { return GetWorld(); }
private:
    void Finish(const FString& Reason);
    void Check(bool Pass,const FString& Detail);
    void Command(int32 Phase);
    bool ReportsReady(int32 Phase);
    bool PlaceRoom(int32 Node);
    bool PlaceNear(AActor* Target,bool Portal);
    void KillSpawned();
    void CaptureProfiles(TMap<FString,FColdSteelProfile>& Into);
    void CheckPeerProfiles();
    UPROPERTY() TArray<TObjectPtr<AHeQueDungeonAuditPeer>> Peers;
    TWeakObjectPtr<UWorld> AuditWorld;
    TWeakObjectPtr<AActor> Chest,Portal;
    TArray<int32> RouteRooms;
    TArray<FString> Failures;
    TMap<FString,FColdSteelProfile> BeforeLoot,AfterLoot;
    TMap<FString,int64> Loot;
    FString RunId,Destination,SharedSlot,ChestKey;
    int64 RaceRevision=0,PostRaceRevision=0;
    int32 Step=0,RouteCursor=0,Checks=0,ValidatedPhase=0,LastPlacedRoom=INDEX_NONE;
    double Started=0.,StepAt=0.,LastMove=0.,LastKill=0.,LastDiagnostic=0.;
    bool Done=false,StartedLogged=false;
};

