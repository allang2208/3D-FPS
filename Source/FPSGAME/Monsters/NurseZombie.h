#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "NurseZombie.generated.h"

class UAnimSequence;
class USkeletalMesh;
UENUM(BlueprintType)
enum class ENurseState : uint8 { Idle, Chase, Attack, Stagger, Dead, Recovery, KnockedDown, GettingUp };

UCLASS(Blueprintable)
class FPSGAME_API ANurseZombie : public ACharacter
{
    GENERATED_BODY()
public:
    ANurseZombie(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    friend class UMonsterCombatComponent;
    friend class UHumanoidKnockdownComponent;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Nurse|Combat") TObjectPtr<class UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Nurse|Combat") TObjectPtr<class UHumanoidKnockdownComponent> Knockdown;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Animation") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Animation") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Animation") TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Animation") TObjectPtr<UAnimSequence> AttackClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float MaxHealth = 120.f;
    // Source: tutorial-runtime.json enemyXp.zombie[0]. Tunable per encounter.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Rewards") int32 ExperienceReward = 241;
    // 配置等级与品阶（原 enemy-config 口径；奖励按等级/品阶核算，见 MonsterCoreStats）。
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Rewards") int32 Level = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Rewards") EMonsterRank Rank = EMonsterRank::Normal;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float AttackDamage = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float AggroRadius = 1200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float AttackRange = 145.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float ContactTime = 1.4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float ContactEnd = 1.7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float RecoveryTime = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float WalkSpeed = 90.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Nurse|Combat") float CorpseSeconds = 15.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Nurse|Combat") float Health = 120.f;
    /** 复制给远端：客户端 OnRep 重放 SetState 驱动同款动画/表现切换。 */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Nurse|Combat", ReplicatedUsing=OnRep_State) ENurseState State = ENurseState::Idle;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Nurse|Combat") int32 SuccessfulHits = 0;
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="Nurse|Combat") FVector SpawnPosition;
    UFUNCTION(BlueprintCallable, Category="Nurse|Combat") virtual void InterruptAttack(float Seconds = .25f);
    // Editor pipeline: call only on a separately duplicated clip, preserving the downloaded source.
    UFUNCTION(BlueprintCallable, Category="Nurse|Animation") static bool PrepareInPlaceAnimation(UAnimSequence* Clip);
    UFUNCTION(BlueprintCallable, Category="Nurse|Placement", meta=(WorldContext="WorldContextObject"))
    static bool FindTestSpawn(UObject* WorldContextObject, FVector Origin, FRotator Facing, float PreferredDistance, float Side, FVector& Location);
protected:
    virtual void StartDeathPresentation();
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration);
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining);
    virtual void StartStateAnimation(UAnimSequence* Clip,bool bLoop);
    virtual void SetAttackAnimationTime(float Seconds);
    virtual float GetAttackDuration() const;
    virtual void ProcessAttackContact(float Previous, float Current);
    bool AttackCooldownReady() const { return Cooldown <= 0.f; }
    APawn* CombatTarget() const { return Target.Get(); }
    virtual void SetWalkAnimationRate(float Rate);
    // Called once after the shared contact checks consume this attack.
    virtual float ApplyMeleeDamage(APawn* Victim);
private:
    void SetState(ENurseState NewState);
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UFUNCTION() void OnRep_State();
    bool CanSee(const AActor* Actor) const;
    void TryMelee();
    TWeakObjectPtr<APawn> Target;
    // Clip currently owned by the single-node reaction/state player, so repeated
    // bullets can refresh the pose instead of rebuilding the player per hit.
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PresentedClip;
    float StateTime = 0.f;
    float Cooldown = 0.f;
    float StaggerSeconds = .25f;
    bool bAttackConsumed = false;
};
