#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "GameFramework/DamageType.h"
#include "../Skills/EnemyAttackDamage.h"
#include "MonsterCoreStats.h"
#include "HandBrainMonster.generated.h"
class UAnimSequence; class USoundBase; class UAudioComponent; class UStaticMeshComponent; class UMaterialInterface; class UMaterialInstanceDynamic; class USkeletalMesh; class UPhysicsAsset;
UCLASS()
class FPSGAME_API UHandBrainMagicDamage : public UEnemyRangedDamage { GENERATED_BODY() };
UENUM(BlueprintType)
enum class EHandBrainState : uint8 { Idle, Chase, Returning, Slam, Howl, Stagger, Dying, Ragdoll, Recovery };
/** Standalone village boss. Combat clock owns one-shot animations and damage events. */
UCLASS(Blueprintable)
class FPSGAME_API AHandBrainMonster : public ACharacter
{
 GENERATED_BODY()
public:
 AHandBrainMonster(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
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
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") EMonsterRank Rank=EMonsterRank::Lord;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") int32 ExperienceReward=2892;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float WalkSpeed=100.f;
 // 2026-09-23：移动速度在作者基准 WalkSpeed 上乘系数；MoveClip 的播放率按
 // 实际速度/WalkSpeed 归一，提速后步伐动画与脚步声自动同步加快。
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Stats") float MoveSpeedMultiplier=1.25f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|AI") float AggroRadius=1400.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|AI") float LeashRadius=2600.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamRadius=300.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamReach=160.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamTriggerRange=300.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float SlamCooldown=6.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float HowlRadius=600.f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") float HowlCooldown=30.f;
 // 弱点只存在于 Howl 吟唱窗口：命中这些骨骼（大小写不敏感的包含匹配）才算要害。
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Combat") TArray<FString> WeakpointBones;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Death",meta=(ToolTip="Fallback without a death clip; configured death clips hand off at 60%.")) float RagdollStartSeconds=1.15f;
 UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="HandBrain|Death") float CorpseSeconds=15.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") float Health=1500.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") EHandBrainState State=EHandBrainState::Idle;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") int32 SlamHits=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") int32 HowlHits=0;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") float StateSeconds=0.f;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") FVector SlamCenter;
 UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="HandBrain|Runtime") FVector Home;
 UFUNCTION(BlueprintCallable,Category="HandBrain|Combat") void InterruptAttack(float Seconds=.6f);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Combat") bool StartAttack(bool bHowl);
 /** 要害判定入口（ColdSteelSkills::IsCriticalHit 调用）：仅 Howl 期间的口部骨骼为弱点，其余时间无要害；随机暴击不受影响。 */
 UFUNCTION(BlueprintPure,Category="HandBrain|Combat") bool IsWeakpointHit(const FHitResult& Hit) const;
 UFUNCTION(BlueprintCallable,Category="HandBrain|Physics") static bool BuildPhysicsAsset(USkeletalMesh* InMesh,UPhysicsAsset* Asset);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Physics") static UPhysicsAsset* CreatePhysicsAsset(USkeletalMesh* InMesh);
 UFUNCTION(BlueprintCallable,Category="HandBrain|Placement",meta=(WorldContext="WorldContextObject")) static bool FindVillageSpawn(UObject* WorldContextObject,FVector Origin,FRotator Facing,FVector& Location);
private:
 void SetState(EHandBrainState NewState); void DealSlam(); void DealHowl(); void EnterRagdoll();
 bool CanSee(const AActor* Actor,FVector Origin) const; FVector GroundPoint(FVector Point) const;
 bool CanSlamTarget(const APawn* Pawn) const;
 bool CanHowlTarget(const APawn* Pawn) const;
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
