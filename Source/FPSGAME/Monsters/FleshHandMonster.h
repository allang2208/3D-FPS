#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Components/ActorComponent.h"
#include "MonsterCoreStats.h"
#include "FleshHandMonster.generated.h"
class UAnimSequence; class UMonsterCombatComponent; class UStaticMesh; class UStaticMeshComponent; class UFleshHandKnockdownComponent;
class USkeletalMesh; class UPhysicsAsset; class USoundBase; class UMaterialInterface; class UMaterialInstanceDynamic;
UENUM(BlueprintType)
enum class EFleshHandState : uint8 { Idle, Walk, Returning, Telegraph, Hammer, Slam, GrandSlam, Stagger, Dying, Corpse, ChargeWindup, ChargeRush, ChargeRecover, KnockedDown };

/** Collision-swept, finite player displacement; survives the attacking hand's death. */
UCLASS()
class FPSGAME_API UFleshHandPushComponent : public UActorComponent
{
 GENERATED_BODY()
public:
 UFleshHandPushComponent();
 static void Apply(ACharacter* Target,FVector Direction,float Distance);
 virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Tick) override;
private:
 FVector Direction=FVector::ZeroVector; float Distance=0,Age=0;
};

/** Fly Hand's authored combat clock, with continuous skin geometry and local hand rig. */
UCLASS(Blueprintable)
class FPSGAME_API AFleshHandMonster : public ACharacter
{
 GENERATED_BODY()
public:
 AFleshHandMonster(const FObjectInitializer& Initializer=FObjectInitializer::Get());
 virtual void OnConstruction(const FTransform& Transform) override;
 virtual void BeginPlay() override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 virtual void Tick(float Dt) override;
 virtual void MoveBlockedBy(const FHitResult& Impact) override;
 virtual void Landed(const FHitResult& Hit) override;
 virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand") TObjectPtr<UMonsterCombatComponent> Combat;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UStaticMesh> PalmFistMesh;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> IdleClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> MoveClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> HammerClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> SlamClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> GrandSlamClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> DeathClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> ChargeWindupClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> ChargeRushClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UAnimSequence> ChargeRecoverClip;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<USoundBase> ImpactSound;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Assets") TObjectPtr<UMaterialInterface> WarningMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Summons") TSubclassOf<AFleshHandMonster> MinionClass;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|Stats") bool bMinion=false;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") float MaxHealth=1500;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") float PhysicalAttack=60;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") float MagicDefense=30;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") int32 Level=12;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") EMonsterRank Rank=EMonsterRank::Lord;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") int32 ExperienceReward=2892;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|Stats") float WalkSpeed=259.2f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|AI") float AggroRadius=1215;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="FleshHand|AI") float LeashRadius=2600;
 UPROPERTY(EditAnywhere,Category="FleshHand|Combat") float HammerRange=162;
 UPROPERTY(EditAnywhere,Category="FleshHand|Combat") float SlamRadius=405;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0")) float ChargeMinRange=450;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="1")) float ChargeMaxRange=1100;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0.1")) float ChargeWindupSeconds=1.2f;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0")) float ChargeCooldown=12;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="1")) float ChargeSpeed=1100;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="1")) float ChargeDistance=1200;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0")) float ChargeDamageMultiplier=3;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0")) float ChargeStunSeconds=2;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0.1")) float ChargeRecoverSeconds=.7f;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0",ClampMax="1.5")) float ChargeLeadStrength=1.f;
 UPROPERTY(EditAnywhere,Category="FleshHand|Charge",meta=(ClampMin="0",Units="cm")) float ChargeMaxLeadDistance=450.f;
 UPROPERTY(EditAnywhere,Category="FleshHand|Death") float CorpseSeconds=15;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand|Runtime") float Health=1500;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand|Runtime") EFleshHandState State=EFleshHandState::Idle;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand|Runtime") float StateSeconds=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand|Runtime") FVector Home;
 bool Dead() const {return Health<=0||State==EFleshHandState::Dying||State==EFleshHandState::Corpse;}
 bool Busy() const;
 bool CanAttack(APawn* P) const;
 bool StartAttack(APawn* P);
 void SetTarget(APawn* P) {Target=P;}
 void SetLocomotion(bool Moving,bool Returning);
 void InterruptAttack(float Seconds);
 void StartHitPresentation();
 void SetHitPresentationTime(float Elapsed,float Remaining);
 void FinishHitReaction();
 UFUNCTION(BlueprintCallable,Category="FleshHand|Authoring") static bool BuildQueryPhysics(USkeletalMesh* InMesh,UPhysicsAsset* Asset);
private:
 friend class UFleshHandKnockdownComponent;
 void SetState(EFleshHandState Next);
 void Impact(); void Summon(); void ContactDamage();
 bool CanReach(const APawn* P,float Range) const;
 void Play(UAnimSequence* Clip,bool Loop,bool Clock,float Blend=.1f);
 void UpdateFist();
 bool CanCharge(const APawn* P) const;
 bool BuildChargeDirection(const APawn* Victim,FVector& Direction) const;
 void BeginChargeRush();
 void StopChargeMotion();
 void TickCharge(float Dt);
 UPROPERTY() TObjectPtr<UStaticMeshComponent> PalmFist;
 UPROPERTY() TObjectPtr<UStaticMeshComponent> WarningRing;
 UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> RingMID;
 UPROPERTY() TObjectPtr<class UCombatStatusFormula> Status;
 TWeakObjectPtr<APawn> Target,LockedTarget;
 TArray<TWeakObjectPtr<AFleshHandMonster>> Children;
 FVector StrikeDirection=FVector::ForwardVector;
 FVector ChargeStart=FVector::ZeroVector,ChargePrevious=FVector::ZeroVector;
 uint16 ChargeMotionID=0;
 float ChargeLeft=0,ChargeBlockedSeconds=0;
 EFleshHandState Queued=EFleshHandState::Hammer;
 float HammerLeft=0,SlamLeft=0,GrandLeft=0,ControlSeconds=0,ContactLeft=.5f;
 bool bConsumed=false,bDizzyPresentation=false;
public:
 /** World speed matched to the original walk cycle at a play rate of one. */
 UPROPERTY(EditAnywhere,Category="FleshHand|Animation",meta=(ClampMin="1",Units="cm/s")) float AnimationWalkSpeed=216.f;
 UPROPERTY(EditAnywhere,Category="FleshHand|Combat",meta=(ClampMin="0",Units="cm")) float SlamKnockbackDistance=150.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="FleshHand") TObjectPtr<UFleshHandKnockdownComponent> Knockdown;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UMaterialInterface> ChargeDustMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UMaterialInterface> ChargeAirMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UMaterialInterface> ChargeSkinMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UMaterialInterface> ChargeChipMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UMaterialInterface> ChargeWarningMaterial;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UStaticMesh> ChargeFXPlane;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<UStaticMesh> ChargeFXCube;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<USoundBase> ChargeWindupSound;
 UPROPERTY(EditDefaultsOnly,Category="FleshHand|ChargeFX") TObjectPtr<USoundBase> ChargeRushSound;
 UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChargeRingMID;
};
UCLASS(Blueprintable)
class FPSGAME_API AFleshHandMinion : public AFleshHandMonster
{
 GENERATED_BODY()
public:
 AFleshHandMinion(const FObjectInitializer& Initializer=FObjectInitializer::Get());
};
