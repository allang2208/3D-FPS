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
    // ── 联机 ──
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> CloudFX;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> ChargeFX;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ChargeCircle;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChargeCircleMaterial;
    // 悬钟式蓄力：内卷粒子 + 虹膜光斑；汇聚线条用真实电弧（SpawnArc 池）。
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> GatherFX;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> ChargeIris;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChargeIrisMID;
    // 发射瞬间的定向冲击盘面（虹膜网格沿瞄准轴放大淡出）。
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> MuzzleIris;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MuzzleIrisMID;
    float MuzzleFlashAge=0,MuzzleFlashScale=1;
    double NextChargeArc=0;
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
    void SpawnArc(const FVector& Start,const FVector& End,const FLightningCast& Spell,bool bBeam=false,float ChargeRatio=1.f,float Width=1.f,bool bContactLight=true,float Brightness=50.f);
    void SpawnBurst(const FVector& Point,float Size=1.f,const FRotator& Rotation=FRotator::ZeroRotator,UObject* System=nullptr);
    /** 枪口定向闪光：冲击盘面 + 前锥爆闪；非复制表现，客户端释放本地也调一次。 */
    void MuzzleFlashFX(const FVector& Start,const FVector& Dir,float Visual);
    void ApplyStatus(AActor* Target,const FLightningCast& Spell,FElectricMagicRewards& Rewards);
    void Overload(AActor* Origin,const FLightningCast& Spell,FElectricMagicRewards& Rewards);
    void GrantCastBuffs(const FLightningCast& Spell);
    /** 雷枪命中结算主体：本地释放与服务端权威释放共用。 */
    void FireLanceBody(APawn* P,UColdSteelStatusModel* M,const FVector& Eye,const FVector& Dir,float Ratio,const FElectricMagicCast& Spell);
    /** 雷云 FX——本地激活与服务端激活共用（远端靠复制态重演）。 */
    void SpawnDomainFX();
    // ── 联机：雷云激活态复制（远端副本看云；电弧/雷枪柱经 AFPSLightningArc 复制）──
    UPROPERTY(ReplicatedUsing=OnRep_Domain) bool bNetDomain=false;
    UPROPERTY(Replicated) FElectricMagicCast NetDomainCast;
    UFUNCTION() void OnRep_Domain();
    bool bNetPaid=false;
};
