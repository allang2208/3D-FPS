#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AbsoluteZeroTypes.h"
#include "FPSAbsoluteZeroNova.generated.h"

class APawn;
class AFPSIceWall;
class UColdSteelStatusModel;
class UDynamicMeshComponent;
class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UPointLightComponent;
class USoundBase;
class UStaticMesh;
class UParticleSystem;
class UNiagaraComponent;
class UNiagaraSystem;

/** Authoritative 360-degree Glacial Nova + deterministic own-IceWall shrapnel barrage. */
UCLASS()
class FPSGAME_API AFPSAbsoluteZeroNova : public AActor
{
    GENERATED_BODY()
public:
    static constexpr int32 AssetCount=18;
    static const TCHAR* const* AssetPaths();
    static bool HasBasicAssets(const TArray<TObjectPtr<UObject>>& InAssets);

    AFPSAbsoluteZeroNova();
    bool InitializeNova(APawn* Shooter,const FAbsoluteZeroCast& Spell,const FVector& GroundCenter,const TArray<TObjectPtr<UObject>>& InAssets);
    void ActivateNova();
    void FinishForRemoval();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    struct FQueuedWall
    {
        TWeakObjectPtr<AFPSIceWall> Wall;
        FAbsoluteZeroDetonatedWall Snapshot;
        float TriggerDistance=0.f;
        bool bDetonated=false;
    };
    struct FRadialSpike
    {
        FVector BasePos=FVector::ZeroVector;
        FQuat Rotation=FQuat::Identity;
        FVector FullScale=FVector::OneVector;
        float TriggerRadius=0.f;
        float RiseSeconds=.10f;
        float HoldSeconds=1.42f;
        float Age=0.f;
        int32 MeshBucket=0;
        int32 InstanceIndex=INDEX_NONE;
        int32 ShellInstanceIndex=INDEX_NONE;
        bool bSpawned=false;
        bool bHoldSettled=false;
        bool bCollapsed=false;
        bool bShatterPopped=false;
        bool bHeroSpire=false;
    };
    struct FBurstSplinter
    {
        FVector Position=FVector::ZeroVector;
        FVector Velocity=FVector::ZeroVector;
        FRotator Rotation=FRotator::ZeroRotator;
        FRotator SpinRate=FRotator::ZeroRotator;
        float Scale=1.f;
        float Age=0.f;
        float Life=.75f;
        float Delay=0.f;
        int32 InstanceIndex=INDEX_NONE;
        bool bActive=true;
    };
    struct FWallShard
    {
        FVector Position=FVector::ZeroVector;
        FVector Velocity=FVector::ZeroVector;
        float DistanceTraveled=0.f;
        float MaxRange=1800.f;
        float HealthRatio=1.f;
        float Scale=1.f;
        int32 WallIndex=0;
        int32 InstanceIndex=INDEX_NONE;
        bool bActive=true;
    };

    UPROPERTY(Replicated) TObjectPtr<APawn> NetCaster;
    UPROPERTY(Replicated) FAbsoluteZeroCast NetCast;
    UPROPERTY(Replicated) FVector_NetQuantize NetCenter=FVector::ZeroVector;
    UPROPERTY(Replicated) TArray<FAbsoluteZeroDetonatedWall> NetWalls;
    UPROPERTY(Replicated) double NetStartedAt=0.;
    UPROPERTY(Replicated) bool bNetActivated=false;

    TWeakObjectPtr<APawn> Caster;
    TWeakObjectPtr<UColdSteelStatusModel> RewardModel;
    FAbsoluteZeroCast CastSnapshot;
    FAbsoluteZeroRewards Rewards;
    FVector Center=FVector::ZeroVector;
    TArray<FQueuedWall> QueuedWalls;
    TSet<TWeakObjectPtr<AActor>> HitTargets;
    TMap<TWeakObjectPtr<AActor>,int32> ShardHitsPerTarget;
    TArray<FWallShard> Shards;
    TArray<FRadialSpike> RadialSpikes;
    TArray<FBurstSplinter> BurstSplinters;
    TArray<bool> ClientWallDetonated;

    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> FrostSurface;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FrostMID;
    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> ShockRing;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ShockRingMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SpireMID;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> SpireShellMID;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> BurstWaveFX;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> FlashLight;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeISMs;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeShellISMs;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> BurstSplinterISM;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> ShardISM;

    float Age=0.f;
    float PreviousWaveRadius=0.f;
    int32 ShatterBurstsSpawned=0;
    bool bSecondTremorDone=false;
    bool bShatterAudioPlayed=false;
    bool bBurstSplintersDone=false;
    bool bActivated=false;
    bool bClientInitialized=false;
    bool bFinished=false;

    void BuildClientVisuals();
    void LoadAssetsSync();
    void StepWaveAuthority(float PrevRadius,float CurrRadius);
    void LaunchShardsForWall(int32 WallIndex,const FAbsoluteZeroDetonatedWall& Snap);
    void StepShards(float Delta);
    void UpdateVisuals(float Delta,float CurrRadius);
    void ShakeNearbyPlayers(float Multiplier=1.f) const;
    void Finish();
};
