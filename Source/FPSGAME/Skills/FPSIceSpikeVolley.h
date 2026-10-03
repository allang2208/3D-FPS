#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "IceSpikeTypes.h"
#include "FPSIceSpikeVolley.generated.h"
class UFPSIceSpikeComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UParticleSystem;
class USoundBase;
class UNiagaraComponent;
class UNiagaraSystem;

/** One cast owns every spike, its frozen formula and its single training transaction. */
UCLASS()
class FPSGAME_API AFPSIceSpikeVolley : public AActor
{
    GENERATED_BODY()
public:
    AFPSIceSpikeVolley();
    void Prepare(UFPSIceSpikeComponent* Source,APawn* Shooter,const FIceSpikeCast& Snapshot,const TArray<TObjectPtr<UStaticMesh>>& Spikes,UStaticMesh* Shard,UMaterialInterface* Material,UMaterialInterface* ShellMaterial,UParticleSystem* FX,USoundBase* Sound,UNiagaraSystem* Motes,UNiagaraSystem* ColdMist);
    void Launch();
    /** 联机：服务端按客官上报的瞄准点直接起飞（远端 pawn 无相机，AimPoint 不可信本地推导）。 */
    void LaunchAt(const FVector& AimPoint);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    bool IsFlying() const {return bFlying;}
    /** Red trajectory preview: one segment per hovering shard, refreshed while held. */
    void SetAimPreviewActive(bool bActive);
    /** Lock the target, keep following until the gesture launches the volley. */
    void CommitAimPreview();
    bool IsAimPreviewActive() const {return bAimPreview;}
    int32 RemainingCount() const;
    float CastSpeed() const {return Cast.CastSpeed;}
    virtual void Tick(float Delta) override;
protected:
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    struct FFlight
    {
        FVector Position=FVector::ZeroVector,Direction=FVector::ForwardVector;
        /** Ballistic launch state: the flight and the preview share this integration exactly. */
        FVector LaunchPosition=FVector::ZeroVector,LaunchVelocity=FVector::ZeroVector;
        FVector2D HoverNoiseSeed=FVector2D::ZeroVector,HoverNoiseRate=FVector2D::ZeroVector;
        float Remaining=0,NextFluidEnvironment=0;
        bool bActive=true,bAimEndpoint=false;
    };
    TArray<FFlight> Flights;
    TArray<FVector> PreviewPoints;
    UPROPERTY(Transient) FVector PreviewAimPoint=FVector::ZeroVector;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Cores;
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Hearts;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> Trails;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> Vapors;
    TArray<TWeakObjectPtr<AActor>> VaporHosts;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ShardMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> IceMaterial;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> ImpactFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    TWeakObjectPtr<UFPSIceSpikeComponent> Source;
    TWeakObjectPtr<APawn> Shooter;
    FIceSpikeCast Cast;
    FIceSpikeRewards Rewards;
    bool bFlying=false,bFinished=false;
    bool bAimPreview=false;
    bool bPreviewLaunchLocked=false;
    UPROPERTY(Transient) TObjectPtr<class ULineBatchComponent> AimPreviewLines;
    float Age=0,FlightAge=0;
    double LastSound=-100;
    // ── 联机复制态：服务端全量模拟；远端副本按这组字段摆同款表现壳 ──
    UPROPERTY(Replicated) TObjectPtr<APawn> NetShooter;
    UPROPERTY(Replicated) TObjectPtr<UFPSIceSpikeComponent> NetSource;
    UPROPERTY(Replicated) bool bNetFlying=false;
    UPROPERTY(Replicated) int32 NetCount=0;
    UPROPERTY(Replicated) float NetCastSpeed=1.f,NetSpeed=1600.f,NetGravity=400.f,NetHoverDuration=30.f;
    UPROPERTY(ReplicatedUsing=OnRep_Spikes) TArray<FVector_NetQuantize> NetPos;
    UPROPERTY(ReplicatedUsing=OnRep_Spikes) TArray<FVector_NetQuantizeNormal> NetDir;
    UPROPERTY(ReplicatedUsing=OnRep_Spikes) uint32 NetAlive=0;
    bool bNetInit=false;
    float NetAge=0;
    uint32 NetAliveLocal=0;
    void ResolveNetInit();
    void SyncNetFlights();
    UFUNCTION() void OnRep_Spikes();
    void NetPresent(float Delta);
    void NetShatter(int32 Index,const FVector& Position);
    void UpdateHover();
    void RefreshAimPreview();
    void UpdateVapor(int32 Index,const FVector& Previous,float Strength);
    void Shatter(int32 Index,const FVector& Position,const FVector& Normal,bool bEffect);
    void Finish();
};

UCLASS()
class FPSGAME_API AFPSIceSpikeFragments : public AActor
{
    GENERATED_BODY()
public:
    AFPSIceSpikeFragments();
    void Setup(UStaticMesh* Mesh,UMaterialInterface* Material,const FVector& Normal);
    virtual void Tick(float Delta) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Shards;
    TArray<FVector> Velocities;
    TArray<FRotator> Spins;
    float Age=0;
};
