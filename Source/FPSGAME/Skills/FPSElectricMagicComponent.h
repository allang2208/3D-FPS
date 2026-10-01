#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "ElectricMagicTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSElectricMagicComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraComponent;
class AFPSLightningArc;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSElectricMagicComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    void Trigger(FName Skill);
    void ReleaseLance();
    void CancelPending(bool bRefund=true);
    void ClearEffects();
    bool IsCharging() const{return CommittedSkill==TEXT("thunderLance");}
    float LanceChargeFraction() const{return IsCharging()&&bChargeAtContact?FMath::Clamp(ChargeAge/FMath::Max(.01f,PendingCast.MaxCharge),0.f,1.f):0.f;}
    float LanceSpreadTangent() const{return FMath::Tan(FMath::DegreesToRadians(6.f))*(1.f-LanceChargeFraction());}
    FVector2D LanceCrosshairExtent(FVector2D LocalSize) const;
    bool HasQueuedAction() const{return !QueuedSkill.IsNone();}
    FName UnreleasedSkill() const{return CommittedSkill;}
    float DomainRemaining() const{return bDomainActive&&!bDomainFading?FMath::Max(0.f,DomainCast.Duration-DomainAge):0.f;}
    FString StatusText(FName Skill) const;
    float CooldownFraction(FName Skill) const;
    bool IsHandOccupiedNotice(FName Skill) const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    UFPSElectricMagicComponent();
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> CloudFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> ChargeFX;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ChargeCircle;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChargeCircleMaterial;
    TSharedPtr<FStreamableHandle> AssetLoad;
    TArray<TWeakObjectPtr<AFPSLightningArc>> Arcs;
    TArray<TWeakObjectPtr<UNiagaraComponent>> Bursts;
    FElectricMagicCast PendingCast,DomainCast;
    FElectricMagicRewards DomainRewards;
    FName QueuedSkill,CommittedSkill,NoticeSkill,MessageSkill;
    FString Message;
    double MessageUntil=0;
    float ChargeAge=0,DomainAge=0,DomainVisualAge=0,NextStrike=0;
    bool bAssetsReady=false,bChargeAtContact=false,bDomainActive=false,bDomainFading=false;
    FFPSLeftHandNotice HandNotice;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    void ServiceQueue();
    void AtContact();
    void FireLance();
    void Strike();
    void FinishDomain(bool bTrain);
    void Feedback(FName Skill,const FString& Text);
    bool Enemy(AActor* Actor) const;
    bool Visible(AActor* Origin,AActor* Target,const FVector& Start) const;
    TArray<AActor*> Nearby(const FVector& Center,float Radius) const;
    FVector CastOrigin() const;
    void UpdateChargeVisual();
    void DestroyChargeVisual();
    void SpawnArc(const FVector& Start,const FVector& End,const FLightningCast& Spell,bool bBeam=false);
    void SpawnBurst(const FVector& Point,float Size=1.f);
    void ApplyStatus(AActor* Target,const FLightningCast& Spell,FElectricMagicRewards& Rewards);
    void Overload(AActor* Origin,const FLightningCast& Spell,FElectricMagicRewards& Rewards);
    void GrantCastBuffs(const FLightningCast& Spell);
};
