#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FireMagicTypes.h"
#include "FPSLeftHandNotice.h"
#include "FlameArmorAttachments.h"
#include "FPSFireMagicComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class USoundBase;
class UAudioComponent;
class AFPSMeteorStrike;
class UDecalComponent;
class UMaterialInterface;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSFireMagicComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class UDragonBreathReadinessAuditCommandlet;
    friend class FPlayerSkillPreparation;
public:
    UFPSFireMagicComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger(FName Skill);
    void SetMeteorAimPreview(bool bActive);
    void ReleaseMeteorAimPreview();
    bool IsMeteorAimPreviewActive() const{return bMeteorAimPreview;}
    void CancelPending();
    bool HasQueuedAction() const{return !QueuedSkill.IsNone();}
    FName UnreleasedSkill() const{return CommittedSkill;}
    FString StatusText(FName Skill) const;
    float CooldownFraction(FName Skill) const;
    bool IsHandOccupiedNotice(FName Skill) const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    float ArmorRemaining() const{return ArmorTime;}
    UNiagaraSystem* GetArmorArrowSystem() const{return ArrowSystem;}
    void OnWeaponHit(AActor* Target,const FVector& Point);
    void NotifyMeteorImpact(const FVector& Point);
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
    // ── 联机 ──
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FFireMagicCast& Spell,bool bMeteorTargetLocked=false);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
    void NetDragonCastResult(uint8 Phase,uint8 Code,uint32 CastId);
    void NetArmorCastResult(uint8 Phase,uint8 Code,uint32 CastId);
    void NetMeteorCastResult(uint8 Phase,uint8 Code,uint32 CastId);
    void NetStopDragonBreath(uint32 CastId);
    void FinishDragonBreathForRemoval();
    void FinishFireMagicForRemoval();
    bool IsDragonBreathActive() const;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    friend class USkillNetworkAuditCommandlet;
    friend class ASkillWireAuditController;
    friend class ASkillWireAuditGameMode;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> DragonSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> DragonFX;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> DragonStartAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> DragonLoopAudio;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> DragonStopAudio;
    UPROPERTY(ReplicatedUsing=OnRep_DragonBreath) FDragonBreathState DragonState;
    UFUNCTION() void OnRep_DragonBreath();
    FDragonBreathState DragonPrediction;
    uint32 DragonLocalCastId=0,DragonCancelledCastId=0,DragonConfirmedCastId=0;
    uint32 DragonSoundCastId=0,DragonVisualCastId=0,DragonAuthoritySerial=0;
    TWeakObjectPtr<UColdSteelStatusModel> DragonRewardModel;
    TSharedPtr<FStreamableHandle> DragonLoad;
    FFireMagicRewards DragonRewards;
    float DragonNextDamage=0,DragonProbeClock=0,DragonTailTime=0;
    bool bDragonAwaitingRelease=false;
    bool bDragonGestureHeld=false;
    void LoadDragonBreath();
    void PrepareDragonBreathVisuals();
    bool IsDragonBreathVisualReady() const;
    bool StartDragonBreath(const FFireMagicCast& Spell,bool bPredict=false,uint32 CastId=0,const FVector& NozzleOffset=FVector(95,17,4),FString* Failure=nullptr);
    const FDragonBreathState& DragonView() const;
    FVector CaptureDragonNozzle() const;
    void RequestDragonStop();
    void ConfirmDragonRelease(uint32 CastId);
    void PresentDragonBreath();
    void PrepareDragonBreathAudio();
    void RefreshDragonBreathAudio();
    void StopDragonBreathAudio();
    void DestroyDragonBreathAudio();
    void TickDragonBreath(float Delta);
    void StopDragonBreath(bool bTrain);
    void DragonBreathHit();
    void DragonBreathFrame(FVector& Origin,FQuat& Rotation) const;
    void UpdateDragonBreathOcclusion(const FVector& Origin,const FQuat& Rotation);
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> AuraSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> WeaponSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> HammerSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SwordSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ArrowSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SparkSystem;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> AuraFX;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> WeaponFX;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> MeteorAssets;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> MeteorAimMaterial;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> MeteorAimDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MeteorAimMID;
    TSharedPtr<FStreamableHandle> MeteorAimLoad;
    FFireMagicCast MeteorPreviewSnapshot;
    FString MeteorPreviewFailure;
    FVector2D MeteorPreviewRadii=FVector2D::ZeroVector;
    bool bMeteorAimPreview=false,bMeteorPreviewValid=false;
    uint32 MeteorLocalCastId=0,MeteorResolvedCastId=0;
    float MeteorPendingRefund=0.f;
    bool bMeteorAwaitingResult=false;
    FFireMagicCast MeteorReleasedCast;
    TArray<TWeakObjectPtr<AFPSMeteorStrike>> Strikes;
    FName QueuedSkill,CommittedSkill,MessageSkill,NoticeSkill;
    FFireMagicCast CastSnapshot,ArmorSnapshot;
    FFireMagicRewards ArmorRewards;
    TWeakObjectPtr<UColdSteelStatusModel> ArmorRewardModel;
    uint32 ArmorLocalCastId=0,ArmorConfirmedCastId=0,ArmorRejectedCastId=0;
    float ArmorPendingRefund=0.f;
    bool bArmorAwaitingReplication=false;
    FFPSLeftHandNotice HandNotice;
    FVector LockedPoint,LockedNormal;
    float ArmorTime=0,AuraTimer=0;
    double MessageUntil=0;
    double ImpactTime=-1;
    float ImpactStrength=0;
    bool bMeteorAssetsReady=false;
    FString Message;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool SelectGround(const FFireMagicCast& Spell,FVector& Point,FVector& Normal,FString& Failure) const;
    bool Allowed(const FFireMagicCast& Spell,FString& Failure) const;
    bool PrepareCastRequest(FName Skill,FFireMagicCast& Spell,bool bRequireCastAssets=true);
    void QueueCast(FName Skill,bool bUsePreviewTarget);
    bool MeteorPreviewInputAvailable() const;
    void ResolveMeteorAssets();
    void RefreshMeteorPreview();
    void ServiceQueue();
    void ReleaseAtContact();
    void Feedback(FName Skill,const FString& Text);
    void RejectHeldHand(FName Skill);
    void StartArmor(UColdSteelStatusModel* RewardModel=nullptr,uint32 CastId=0);
    void RefreshArmorVisuals();
    void TickArmor(float Delta);
    void EndArmor(bool bTrain);
    void ClearEffects();
    void Sparks(const FVector& Point);
    FFlameArmorHistory WeaponHistory[FlameArmorAttachments::MaxLayers];
    FVector PreviousArmorFeet=FVector::ZeroVector;
    bool bArmorFeetValid=false;
    void UpdateArmorBodyFX(float Fade,const FVector& Feet);
    void UpdateArmorWeaponFX(float Delta,float Fade);
    // ── 联机：焰甲激活态复制——远端副本仅演火环/武器火，伤害结算留在服务端 ──
    UPROPERTY(ReplicatedUsing=OnRep_Armor) FFlameArmorNetState NetArmor;
    uint32 AppliedArmorSerial=0;
    UFUNCTION() void OnRep_Armor();
    bool bNetPaid=false;
    void SpawnArmorFX();
};
