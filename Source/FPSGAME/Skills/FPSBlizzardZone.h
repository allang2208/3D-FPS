#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "BlizzardTypes.h"
#include "FPSBlizzardZone.generated.h"
class UNiagaraComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
class UInstancedStaticMeshComponent;
class USoundBase;

UCLASS()
class FPSGAME_API AFPSBlizzardZone : public AActor
{
    GENERATED_BODY()
public:
    AFPSBlizzardZone();
    bool InitializeZone(APawn* Shooter,const FBlizzardCast& Spell,const FVector& Point,const FVector& Normal,const FVector& LongAxis,const TArray<TObjectPtr<UObject>>& Assets);
    void ActivateZone();
protected:
    virtual void Tick(float Delta) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> CloudFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> SnowFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> MistFX;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> Frost;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> FrostMID;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Hail;
    UPROPERTY(Transient) TObjectPtr<UInstancedStaticMeshComponent> Spikes;
    struct FChunk{FVector Position=FVector::ZeroVector,Velocity=FVector::ZeroVector;float Age=0,Size=0;bool bActive=false,bFragment=false;float Roll=0;};
    FChunk Chunks[48];
    TWeakObjectPtr<APawn> Caster;
    FBlizzardCast CastSnapshot;
    FBlizzardRewards Rewards;
    FVector Center=FVector::ZeroVector,SurfaceNormal=FVector::UpVector,AxisX=FVector::ForwardVector,AxisY=FVector::RightVector,Wind=FVector::ZeroVector;
    FRandomStream Random;
    float Age=0,NextDamage=0,CloudHeight=0,CosmeticClock=0,SpawnClock=0,Detail=1,NextLandingSound=0;
    bool bActivated=false,bFinished=false;
    void DamageTick();
    void Finish();
    void UpdatePresentation(float Delta);
    void SpawnChunk();
    void ScatterFragments(const FVector& Point,const FVector& Normal);
    UPROPERTY(Transient) TObjectPtr<USoundBase> HitSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> LandingSound;
    void PlayLandingSound(const FVector& Point,bool bSnowball);
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeHearts;
    UPROPERTY(Transient) TArray<TObjectPtr<UInstancedStaticMeshComponent>> SpikeShells;
};
