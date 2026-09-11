#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "HandBrainMonster.h"
#include "PoisonMaggotMonster.generated.h"
class UAnimSequence; class USkeletalMesh; class UPhysicsAsset; class UMaterialInterface; class USoundBase;
class UMonsterCombatComponent; class APoisonMaggotProjectile;
UCLASS()
class FPSGAME_API UMaggotVenomDamage : public UHandBrainMagicDamage { GENERATED_BODY() };
UCLASS()
class FPSGAME_API UMaggotPoisonDamage : public UDamageType { GENERATED_BODY() };
UENUM(BlueprintType)
enum class EPoisonMaggotState : uint8 { Idle, Chase, Returning, Spitting, Stagger, Recovery, Dying, Ragdoll };
/** BT owns decisions; this character owns the sole attack/animation clock. Standalone gameplay. */
UCLASS(Blueprintable)
class FPSGAME_API APoisonMaggotMonster : public ACharacter
{
 GENERATED_BODY()
public:
 APoisonMaggotMonster();
 virtual void OnConstruction(const FTransform& Transform) override;
 virtual void BeginPlay() override;
 virtual void Tick(float DeltaSeconds) override;
 virtual void EndPlay(const EEndPlayReason::Type Reason) override;
 virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer) override;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot") TObjectPtr<UMonsterCombatComponent> Combat;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<UAnimSequence> IdleClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<UAnimSequence> MoveClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<UAnimSequence> SpitClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<UAnimSequence> DeathClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<UMaterialInterface> VenomMaterial;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Assets") TObjectPtr<USoundBase> SpitSound;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Stats") float MaxHealth=800;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Stats") float MagicAttack=24;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Stats") float WalkSpeed=120;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Stats") int32 Level=4;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Stats") int32 ExperienceReward=240;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|AI") float AggroRadius=1400;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|AI") float LeashRadius=2400;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float AttackRange=600;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float CooldownSeconds=8;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float ProjectileSpeed=500;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float ProjectileRange=600;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float FanDegrees=45;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Spit") float PoisonChance=.33f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Death") float CorpseSeconds=20;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Maggot|Death") float RagdollStartSeconds=1.65f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") EPoisonMaggotState State=EPoisonMaggotState::Idle;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") float Health=800;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") float StateSeconds=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") float CooldownLeft=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") FVector Home;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") int32 ProjectilesFired=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") int32 ProjectileHits=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Maggot|Runtime") int32 RewardCount=0;
 TArray<float> EmissionTimes;
 bool Dead() const {return State==EPoisonMaggotState::Dying||State==EPoisonMaggotState::Ragdoll;}
 bool CanSpit(APawn* Victim) const;
 UFUNCTION(BlueprintCallable,Category="Maggot") bool StartSpit(APawn* Victim);
 UFUNCTION(BlueprintCallable,Category="Maggot") void InterruptAttack(float Seconds=.45f);
 void SetState(EPoisonMaggotState NewState);
 void SetTarget(APawn* Victim) {Target=Victim;}
 FVector Mouth() const;
 UFUNCTION(BlueprintCallable,Category="Maggot|Editor") static UPhysicsAsset* CreatePhysicsAsset(USkeletalMesh* InMesh);
 UFUNCTION(BlueprintCallable,Category="Maggot|Editor") static bool CompileMaterialAssets(const TArray<UMaterialInterface*>& Materials);
 static constexpr float Duration=3.f;
 static constexpr float FirstEmission=14.f/33.f*3.f;
 static constexpr float EndEmission=27.f/33.f*3.f;
 static constexpr float EmissionInterval=.05f;
private:
 void Emit(float ScheduledTime);
 void ClearProjectiles();
 void EnterRagdoll();
 TWeakObjectPtr<APawn> Target;
 TArray<TWeakObjectPtr<APoisonMaggotProjectile>> Projectiles;
 FVector LockedAim=FVector::ForwardVector;
 float LockedYaw=0,ReactionSeconds=0;
 int32 NextEmission=0;
};
