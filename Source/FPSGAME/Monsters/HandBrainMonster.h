#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/DamageType.h"
#include "HandBrainMonster.generated.h"
class UAnimSequence; class USoundBase; class UAudioComponent; class UStaticMeshComponent; class UMaterialInterface; class UMaterialInstanceDynamic; class USkeletalMesh; class UPhysicsAsset;
UCLASS()
class FPSGAME_API UHandBrainMagicDamage : public UDamageType { GENERATED_BODY() };
UENUM(BlueprintType)
enum class EHandBrainState : uint8 { Idle, Chase, Returning, Slam, Howl, Stagger, Dying, Ragdoll, Recovery };
/** Standalone village boss. Combat clock owns one-shot animations and damage events. */
UCLASS(Blueprintable)
class FPSGAME_API AHandBrainMonster : public ACharacter
{
 GENERATED_BODY()
public:
 AHandBrainMonster();
 friend class UMonsterCombatComponent;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Combat") TObjectPtr<class UMonsterCombatComponent> Combat;
 virtual void OnConstruction(const FTransform& Transform) override;
 virtual void BeginPlay() override;
 virtual void Tick(float DeltaSeconds) override;
 virtual float TakeDamage(float Damage,const FDamageEvent& Event,AController* Instigator,AActor* Causer) override;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UAnimSequence> IdleClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UAnimSequence> MoveClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UAnimSequence> SlamClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UAnimSequence> HowlClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UAnimSequence> DeathClip;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<USoundBase> SlamSound;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<USoundBase> HowlSound;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<USoundBase> MoveSound;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Assets") TObjectPtr<UMaterialInterface> GroundRingMaterial;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float MaxHealth=1500.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float PhysicalAttack=50.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float MagicAttack=55.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float MagicDefense=65.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") int32 Level=12;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") int32 ExperienceReward=2892;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float WalkSpeed=100.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|AI") float AggroRadius=1400.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|AI") float LeashRadius=2600.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamRadius=300.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamReach=160.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamTriggerRange=300.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamCooldown=6.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float HowlRadius=600.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float HowlCooldown=30.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Death") float RagdollStartSeconds=1.15f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Death") float CorpseSeconds=20.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") float Health=1500.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") EHandBrainState State=EHandBrainState::Idle;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") int32 SlamHits=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") int32 HowlHits=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") float StateSeconds=0.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") FVector SlamCenter;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") FVector Home;
 UFUNCTION(BlueprintCallable,Category="HandBrain|Combat") void InterruptAttack(float Seconds=.6f);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Combat") bool StartAttack(bool bHowl);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Physics") static bool BuildPhysicsAsset(USkeletalMesh* InMesh,UPhysicsAsset* Asset);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Physics") static UPhysicsAsset* CreatePhysicsAsset(USkeletalMesh* InMesh);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Placement",meta=(WorldContext="WorldContextObject")) static bool FindVillageSpawn(UObject* WorldContextObject,FVector Origin,FRotator Facing,FVector& Location);
private:
 void SetState(EHandBrainState NewState); void DealSlam(); void DealHowl(); void EnterRagdoll();
 bool CanSee(const AActor* Actor,FVector Origin) const; FVector GroundPoint(FVector Point) const;
 void ShowRing(UStaticMeshComponent* Ring,FVector Point,float Radius,FLinearColor Color,float Opacity);
 bool Dead() const { return State==EHandBrainState::Dying||State==EHandBrainState::Ragdoll; }
 UPROPERTY() TObjectPtr<UStaticMeshComponent> SlamRing;
 UPROPERTY() TObjectPtr<UStaticMeshComponent> HowlRing;
 UPROPERTY() TObjectPtr<UAudioComponent> Voice;
 UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> SlamMaterial;
 UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> HowlMaterial;
 TWeakObjectPtr<APawn> Target;
 float SlamLeft=0,HowlLeft=2.f,NextHowlTick=.5f,LostSeconds=0,StaggerSeconds=.6f,StepClock=0;
 bool bSlamConsumed=false;
 FVector LastImpulse=FVector::ZeroVector;
};
