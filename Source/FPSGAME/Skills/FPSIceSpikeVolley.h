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
    void Launch(const FVector& AimPoint);
    bool IsFlying() const {return bFlying;}
    /** Red trajectory preview: one segment per hovering shard, refreshed while held. */
    void SetAimPreviewActive(bool bActive);
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
        float Remaining=0;
        bool bActive=true,bAimEndpoint=false;
    };
    TArray<FFlight> Flights;
    TArray<FVector> PreviewPoints;
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
    UPROPERTY(Transient) TObjectPtr<class ULineBatchComponent> AimPreviewLines;
    float Age=0,FlightAge=0;
    double LastSound=-100;
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
