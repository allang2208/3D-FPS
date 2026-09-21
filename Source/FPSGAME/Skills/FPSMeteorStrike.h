#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FireMagicTypes.h"
#include "FPSMeteorStrike.generated.h"
class UStaticMeshComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class UAudioComponent;
class USoundBase;

UCLASS()
class FPSGAME_API AFPSMeteorStrike : public AActor
{
    GENERATED_BODY()
public:
    AFPSMeteorStrike();
    bool InitializeStrike(APawn* Caster,const FFireMagicCast& Spell,const FVector& Point,const FVector& SurfaceNormal);
    virtual void Tick(float Delta) override;
protected:
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Rock;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Mantle;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Trail;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> GroundFlames;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Glow;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UAudioComponent> Burning;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ImpactSystem;
    UPROPERTY(Transient) TObjectPtr<USoundBase> LandSound;
    TWeakObjectPtr<APawn> Shooter;
    FFireMagicCast CastSnapshot;
    FFireMagicRewards Rewards;
    FVector Destination,Normal,Start;
    float Age=0,LavaAge=0,NextLavaTick=0;
    bool bImpacted=false,bSettled=false;
    void Impact();
    void DamageArea(bool bExplosion);
    void Finish();
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Fragments;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInstanceDynamic> FragmentMaterial;
    TArray<FVector> FragmentVelocities,FragmentScales;
    TArray<FRotator> FragmentSpins;
    FQuat InitialRockRotation=FQuat::Identity;
    FVector SpinAxis=FVector::UpVector;
    void BreakRock();
    void AnimateFragments(float Delta);
};
