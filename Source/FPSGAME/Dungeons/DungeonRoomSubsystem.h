#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Info.h"
#include "Subsystems/WorldSubsystem.h"
#include "DungeonRoomSubsystem.generated.h"

class AColdSteelPlayerState;
class AAuthoredDungeonGenerator;
class ULevelStreamingDynamic;
class USceneComponent;
class APostProcessVolume;
class UPostProcessComponent;
class UAudioComponent;

/** The persistent hub owns this small descriptor; all peers load the same named instance. */
UCLASS()
class FPSGAME_API ADungeonRoomState : public AInfo
{
    GENERATED_BODY()
public:
    ADungeonRoomState();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    UPROPERTY(ReplicatedUsing=OnRep_Instance) FGuid Instance;
    UFUNCTION() void OnRep_Instance();
};

/** A room is one network world. Moving between hub and dungeon never replaces that world. */
UCLASS()
class FPSGAME_API UDungeonRoomSubsystem : public UTickableWorldSubsystem
{
    GENERATED_BODY()
public:
    static UDungeonRoomSubsystem* Get(const UWorld* World);
    static bool Supports(const UWorld* World);
    static bool IsDungeonPawn(const APawn* Pawn);
    static bool IsDungeonActor(const AActor* Actor);
    static FVector DungeonOffset() { return FVector(200000,0,50000); }
    static FString LogicalMap(const AActor* Actor);
    /** Qualify generated event targets by instance; a late RPC cannot open a new run's same-named door. */
    static FString SceneActorKey(const AActor* Actor);
    virtual void Tick(float DeltaTime) override;
    virtual TStatId GetStatId() const override;
    virtual bool IsTickable() const override;
    virtual void Deinitialize() override;

    bool HasOccupants() const;
    bool HasPendingEntry() const { return !Pending.IsEmpty(); }
    bool HasInstance() const;
    bool QueueEntry(const TArray<AColdSteelPlayerState*>& Players,FString& Reason);
    bool ReturnPlayer(AColdSteelPlayerState* Player,AActor* Portal,bool Confirm,FString& Reason);
    void AcknowledgeEntry(AColdSteelPlayerState* Player,FGuid Token,FGuid Instance,APawn* Pawn);
    void CancelEntry(AColdSteelPlayerState* Player,FGuid Token);
    void ApplyInstance(ADungeonRoomState* State);
    bool LocalAssemblyReady(FGuid Instance) const;
    bool FindSpawn(bool Dungeon,APawn* Pawn,FTransform& Out) const;
    void RefreshPresentation();

private:
    struct FEntry
    {
        TWeakObjectPtr<AColdSteelPlayerState> Player;
        TWeakObjectPtr<APawn> Pawn;
        FGuid Token;
        double Started=0.;
        bool Ready=false;
    };
    UPROPERTY(Transient) TObjectPtr<ADungeonRoomState> RoomState;
    UPROPERTY(Transient) TObjectPtr<ULevelStreamingDynamic> Streaming;
    TArray<TWeakObjectPtr<ULevelStreamingDynamic>> Retiring;
    TArray<FEntry> Pending;
    TMap<TWeakObjectPtr<AColdSteelPlayerState>,FTransform> ReturnPositions;
    FGuid LoadedInstance;
    float Accumulator=0.f;
    bool bLoadFailed=false;
    double RetireRetryAt=0.;
    bool MovePlayer(AColdSteelPlayerState* Player,const FTransform& Destination);
    void FinishEntry(int32 Index,const FString& Reason);
    void ReleaseInstance();
    AAuthoredDungeonGenerator* Generator() const;

    struct FEnvironmentComponent { TWeakObjectPtr<USceneComponent> Component; bool Hidden=false; bool Dungeon=false; bool Suppressed=false; };
    struct FEnvironmentVolume { TWeakObjectPtr<APostProcessVolume> Volume; bool Enabled=true; bool Dungeon=false; bool Suppressed=false; };
    struct FEnvironmentPostProcess { TWeakObjectPtr<UPostProcessComponent> Component; bool Enabled=true; bool Dungeon=false; bool Suppressed=false; };
    struct FEnvironmentAudio { TWeakObjectPtr<UAudioComponent> Component; float Volume=1.f; bool Dungeon=false; bool Suppressed=false; };
    TArray<FEnvironmentComponent> EnvironmentComponents;
    TArray<FEnvironmentVolume> EnvironmentVolumes;
    TArray<FEnvironmentPostProcess> EnvironmentPostProcess;
    TArray<FEnvironmentAudio> EnvironmentAudio;
    TSet<TWeakObjectPtr<AActor>> EnvironmentActors;
    bool bPresentationDungeon=false;
    bool bPresentationInitialized=false;
    double NextEnvironmentScan=0.;
    void UpdateEnvironment(bool Dungeon);
    void RestoreEnvironment();
};
