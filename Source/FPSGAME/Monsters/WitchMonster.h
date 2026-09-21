#pragma once
#include "CoreMinimal.h"
#include "NurseZombie.h"
#include "WitchMonster.generated.h"

class UStaticMeshComponent;
class AWitchProjectile;
class UWitchSpellAnimInstance;

/** Witch presentation and spell execution; the shared BT owns decisions. */
UCLASS(Blueprintable)
class FPSGAME_API AWitchMonster : public ANurseZombie
{
    GENERATED_BODY()
public:
    AWitchMonster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    bool CanCast(APawn* Candidate) const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") TObjectPtr<UAnimSequence> CastClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") TObjectPtr<UAnimSequence> ThrowClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat", meta=(Units="cm")) float SpellRange = 800.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat") float MagicAttack = 70.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat") float MagicCooldown = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat") float BottleCooldown = 8.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat") float ProjectileSpeed = 500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Combat") float PoisonRadius = 200.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Witch|Props") TObjectPtr<UStaticMeshComponent> Staff;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Witch|Props") TObjectPtr<UStaticMeshComponent> Bottle;
    UFUNCTION(BlueprintCallable, Category="Witch|Authoring") static bool PrepareCombatPhysics(USkeletalMesh* InMesh);
protected:
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual void SetWalkAnimationRate(float Rate) override;
    virtual void StartDeathPresentation() override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
private:
    UWitchSpellAnimInstance* GetSpellAnimation();
    void AlignVisual();
    void AttachProps();
    void ReleaseSpell();
    void StartRagdoll();
    bool bThrowing = false;
    bool bReleased = false;
    double NextMagicAt = 0.0;
    double NextBottleAt = 0.0;
    TWeakObjectPtr<APawn> SpellTarget;
    TArray<TWeakObjectPtr<AWitchProjectile>> Spells;
    FTimerHandle RagdollTimer;
};
