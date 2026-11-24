// 一支离弦的箭：分步推进 + 球形扫掠，每个目标至多结算一次，可携带穿心箭穿透快照。
// 箭模复用弦上箭部件。命中后的实弹箭靠近自动回收到弹药袋，也保留 E 拾取。
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TimerManager.h"
#include "../../Skills/ColdSteelSkillTypes.h"
#include "MountainEchoString.h"
#include "AuroraBeamVisual.h"
#include "BowArrow.generated.h"

class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UCapsuleComponent;
class USphereComponent;
class UPrimitiveComponent;
class UNiagaraComponent;
class UBowMountainEchoComponent;
class UMaterialInterface;
class UMaterialBillboardComponent;
struct FStreamableHandle;

USTRUCT()
struct FBowArrowPresentation
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<UStaticMesh> Shaft=nullptr;
    UPROPERTY() TObjectPtr<UStaticMesh> Head=nullptr;
    UPROPERTY() FString Ammo;
    UPROPERTY() float Radius=.3f;
    UPROPERTY() float Length=76.f;
    UPROPERTY() double FlightStartServerTime = 0.;
    // Cosmetic snapshot at release; does not alter the projectile's damage snapshot.
    UPROPERTY() bool bAuroraBeam=false;
    UPROPERTY() FVector_NetQuantize10 AuroraOrigin=FVector::ZeroVector;
    UPROPERTY() bool bFlameArmor=false;
    UPROPERTY() EArrowElement Element=EArrowElement::None;
    UPROPERTY() bool bIllumination=false;
    UPROPERTY() bool bMountainEcho=false;
    UPROPERTY() TObjectPtr<UMaterialInterface> EchoMaterial=nullptr;
};

/** A short-lived contact snapshot survives the initial replication of close hits. */
USTRUCT()
struct FBowMountainEchoContact
{
    GENERATED_BODY()
    UPROPERTY() bool bHit=false;
    UPROPERTY() FVector_NetQuantize Position=FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Normal=FVector::UpVector;
};

UCLASS()
class FPSGAME_API ABowArrow : public AActor
{
    GENERATED_BODY()
    friend class UBowSkillTrainingAuditCommandlet;

public:
    ABowArrow();
    /**
     * 由弓组件在生成后立刻配置。伤害与速度已经按拉距算好，箭自身不再二次换算；
     * `InShot` 是射击瞬间的修炼／符文快照，与枪械弹道共用同一结算口径。
     */
    void Configure(float InDamage, float InSpeed, float InGravityCM, float InRangeCM,
                   const FColdSteelSkillShot& InShot, UStaticMesh* InShaftMesh, UStaticMesh* InHeadMesh,
                   float InRadiusCM, float InLengthCM, const FString& InAmmoId,
                   bool bInRecoverable, float InRecoverySeconds);
    virtual void Tick(float Delta) override;
    void ResolveLaunchObstruction(const FVector& CameraOrigin);
    void SetIlluminationCast(const FIlluminationArrowCast& Snapshot);
    void SetElementalCast(const FElementalArrowCast& Snapshot);
    void ArmMountainEcho(UBowMountainEchoComponent* Source,uint32 Epoch,bool Gain,bool Release,const FVector& Eye);
    bool CanRecover() const { return bStuck && bRecoverable && !IsActorBeingDestroyed(); }
    FString RecoveryPrompt() const;
    bool TryRecover(APawn* Pawn);
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
    TWeakObjectPtr<UBowMountainEchoComponent> MountainSource;
    TSharedPtr<MountainEchoString::FImpact> MountainImpact;
    uint32 MountainEpoch=0;
    bool bMountainGain=false;
    UPROPERTY(ReplicatedUsing=OnRep_EchoPending) bool bEchoPending=false;
    FTimerHandle EchoDelay;
    UFUNCTION() void OnRep_EchoPending();
    void ApplyEchoPresentation();
    UPROPERTY(ReplicatedUsing=OnRep_MountainContact) FBowMountainEchoContact MountainContact;
    UFUNCTION() void OnRep_MountainContact();
    void FinishMountainEchoHit(const FHitResult& Hit);
    void StopMountainEchoVisual();
    void ReleaseMountainEchoVisual();
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> MountainFlightFX;
    TSharedPtr<FStreamableHandle> MountainFXLoad;
    bool bMountainFXRequested=false,bMountainContactPlayed=false;
    bool bMountainContactSoundPlayed=false;
    float ApplyEchoHit(const FHitResult& Hit,float RangeScale,FWeaponDamageResult& Result);
    FIlluminationArrowCast IlluminationCast;
    UPROPERTY(Transient) TObjectPtr<class UIlluminationArrowVisual> IlluminationVisual;
    FVector LastIlluminationScan=FVector::ZeroVector;double NextIlluminationScan=0;
    TSet<TWeakObjectPtr<AActor>> IlluminatedTargets;
    void ScanIllumination(const FVector& End,bool Force);
    void ApplyIlluminationImpact(const FHitResult& Hit);
    void UpdateIlluminationVisual(float Delta);
    FElementalArrowCast ElementalCast;
    UPROPERTY(Transient) TObjectPtr<class UElementalArrowVisual> ElementVisual;
    UPROPERTY(Replicated) bool bElementBurst=false;
    void UpdateElementVisual(float Delta);
    void BurstElement(const FHitResult& Hit);
    /** 命中结算：一次扫掠一个目标，命中后不再重复扣血。 */
    bool ApplyHit(const FHitResult& Hit,float ContactDistanceCM=0.f);
    bool AdvanceSegment(const FVector& Start,const FVector& End,float& Distance);
    /** 命中后插住：只留实弹箭的拾取查询，随被击组件移动，超时消失。 */
    void FinishStuck(const FHitResult& Hit);
    void UpdateAuroraBeam();
    UFUNCTION(NetMulticast,Unreliable) void MulticastAuroraPierce(const FAuroraBeamContact& Contact);
    void RecordAuroraContact(const FHitResult& Hit);
    UFUNCTION() void OnRep_AuroraContact();
    UPROPERTY(ReplicatedUsing=OnRep_AuroraContact) FAuroraBeamContact AuroraContact;
    TWeakObjectPtr<AAuroraBeamVisual> AuroraBeam;
    bool bAuroraFinished=false;
    void UpdateFlameVisual(float Delta);
    void StopFlameVisual();
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> FlameFX;
    TSharedPtr<FStreamableHandle> FlameLoad;
    FVector PreviousFlamePosition=FVector::ZeroVector,FlameVelocity=FVector::ZeroVector;
    bool bFlameHistoryValid=false,bFlameLoadRequested=false;

    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> FlightVisual;
    bool bFlightSettling = true;
    void UpdateFlightSettle();
    void RefreshFlightTick();
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Shaft;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Head;

    UPROPERTY(VisibleAnywhere) TObjectPtr<UMaterialBillboardComponent> FlightGlow;

    FVector Velocity = FVector::ZeroVector;
    FColdSteelSkillShot Shot;
    FString AmmoId;
    float Speed = 0.f;
    float Damage = 0.f, GravityCM = 0.f, TravelledCM = 0.f, EffectiveRangeCM = 0.f;
    bool bResolved = false;
    int32 RemainingPenetrations=0;
    TSharedPtr<struct FEclipseBowShot> EclipseShot;
    TSet<TWeakObjectPtr<AActor>> HitTargets;
    UPROPERTY(ReplicatedUsing=OnRep_Stuck) bool bStuck = false;
    UPROPERTY(ReplicatedUsing=OnRep_Presentation) FBowArrowPresentation Presentation;
    UFUNCTION() void OnRep_Presentation();
    UFUNCTION() void OnRep_Stuck();

    /** 无限备弹箭短暂保留，靠近可收走，但不返还真实库存。 */
    static constexpr float StickSeconds = 8.f;
    float CollisionRadiusCM = .35f;
    // Overlaps only: the E trace sees this shape, weapon blocking traces do not.
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> RecoveryShape;
    UPROPERTY(ReplicatedUsing=OnRep_Stuck) bool bRecoverable = false;
    float RecoverySeconds = 120.f;
    FString RecoveryCaption;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USphereComponent> AutoRecovery;
    FTimerHandle RecoveryTimer;
    UFUNCTION() void OnRecoveryOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
        UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex,bool bFromSweep,const FHitResult& SweepResult);
    UFUNCTION() void OnRecoveryEndOverlap(UPrimitiveComponent* OverlappedComponent,AActor* OtherActor,
        UPrimitiveComponent* OtherComponent,int32 OtherBodyIndex);
    void RecoverNearby();
    bool RecoverIntoPouch(APawn* Pawn);
};
