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
    void FinishForRemoval();
    virtual void Tick(float Delta) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    friend class USkillNetworkAuditCommandlet;
    friend class ASkillWireAuditController;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> RewardModel;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> HeatMaterial;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInterface> ScorchMaterial;
    UPROPERTY(Transient) TObjectPtr<class UDecalComponent> ScorchDecal;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInstanceDynamic> ScorchMID;
    void PrepareScorch();
    void UpdateImpactPresentation();
    bool bImpactBreakPending=false;
    TSharedPtr<struct FStreamableHandle> VisualLoad;
    bool bVisualsReady=false;
    void PrepareVisuals();
    void PrepareGroundFire(class UNiagaraSystem* System);
    void UpdateGroundFire(float FieldAge,float Delta);
    TArray<FVector2D> GroundFireSamples;
    int32 NextGroundFireSample=0,GroundFireSourceCount=0;
    float GroundFireWindAge=0.f;
    void PresentImpact(bool Transient);
    double ServerClock() const;
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
    bool bWaterContact=false;
    float Age=0,LavaAge=0,NextLavaTick=0;
    bool bImpacted=false,bSettled=false;
    void Impact();
    void DamageArea(bool bExplosion);
    void SettleRewards();
    void Finish();
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> Fragments;
    UPROPERTY(Transient) TObjectPtr<class UMaterialInstanceDynamic> FragmentMaterial;
    struct FFragmentMotion
    {
        FVector Velocity=FVector::ZeroVector,Scale=FVector::OneVector,TraceFrom=FVector::ZeroVector;
        FRotator Spin=FRotator::ZeroRotator;
        float Age=0.f,Lifetime=2.f,Radius=5.f,Bounce=.1f,Retain=.4f,TraceAge=0.f;
        bool bSettled=false;
    };
    TArray<FFragmentMotion> FragmentMotion;
    FQuat InitialRockRotation=FQuat::Identity;
    FVector SpinAxis=FVector::UpVector;
    void BreakRock();
    void AnimateFragments(float Delta);
    // ── 联机复制态：服务端权威伤害；远端副本自建同款陨星表现 ──
    UPROPERTY(Replicated) TObjectPtr<APawn> NetCaster;
    UPROPERTY(Replicated) FFireMagicCast NetCast;
    UPROPERTY(Replicated) FVector_NetQuantize NetDestination;
    UPROPERTY(Replicated) FVector_NetQuantizeNormal NetNormal;
    UPROPERTY(Replicated) double NetStartedAt=-1.;
    bool bNetInit=false;
    void NetInit();
};
