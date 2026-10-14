#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FireMagicTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSFireMagicComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class USoundBase;
class AFPSMeteorStrike;
struct FStreamableHandle;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSFireMagicComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSFireMagicComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger(FName Skill);
    void CancelPending();
    bool HasQueuedAction() const{return !QueuedSkill.IsNone();}
    FName UnreleasedSkill() const{return CommittedSkill;}
    FString StatusText(FName Skill) const;
    float CooldownFraction(FName Skill) const;
    bool IsHandOccupiedNotice(FName Skill) const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    float ArmorRemaining() const{return ArmorTime;}
    void OnWeaponHit(AActor* Target,const FVector& Point);
    void NotifyMeteorImpact(const FVector& Point);
    void GetCameraMotion(FVector& Location,FRotator& Rotation) const;
    // ── 联机 ──
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FFireMagicCast& Spell);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
    void NetDragonCastResult(uint8 Phase,uint8 Code,uint32 CastId);
    void NetStopDragonBreath(uint32 CastId);
    void FinishDragonBreathForRemoval();
    bool IsDragonBreathActive() const;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> DragonSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> DragonFX;
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
    bool StartDragonBreath(const FFireMagicCast& Spell,bool bPredict=false,uint32 CastId=0,const FVector& NozzleOffset=FVector(95,17,4));
    const FDragonBreathState& DragonView() const;
    FVector CaptureDragonNozzle() const;
    void RequestDragonStop();
    void ConfirmDragonRelease(uint32 CastId);
    void PresentDragonBreath();
    void PlayDragonStartSound();
    void TickDragonBreath(float Delta);
    void StopDragonBreath(bool bTrain);
    void DragonBreathHit();
    void DragonBreathFrame(FVector& Origin,FQuat& Rotation) const;
    void UpdateDragonBreathOcclusion(const FVector& Origin,const FQuat& Rotation);
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> AuraSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> WeaponSystem;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> SparkSystem;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> AuraFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> WeaponFX;
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> MeteorAssets;
    TArray<TWeakObjectPtr<AFPSMeteorStrike>> Strikes;
    FName QueuedSkill,CommittedSkill,MessageSkill,NoticeSkill;
    FFireMagicCast CastSnapshot,ArmorSnapshot;
    FFireMagicRewards ArmorRewards;
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
    void ServiceQueue();
    void ReleaseAtContact();
    void Feedback(FName Skill,const FString& Text);
    void RejectHeldHand(FName Skill);
    void StartArmor();
    void TickArmor(float Delta);
    void EndArmor(bool bTrain);
    void ClearEffects();
    void Sparks(const FVector& Point);
    FVector PreviousWeaponBase=FVector::ZeroVector,PreviousWeaponTip=FVector::ZeroVector;
    bool bWeaponSampleValid=false;
    // ── 联机：焰甲激活态复制——远端副本仅演火环/武器火，伤害结算留在服务端 ──
    UPROPERTY(ReplicatedUsing=OnRep_Armor) FFlameArmorNetState NetArmor;
    uint32 AppliedArmorSerial=0;
    UFUNCTION() void OnRep_Armor();
    bool bNetPaid=false;
    void SpawnArmorFX();
};
