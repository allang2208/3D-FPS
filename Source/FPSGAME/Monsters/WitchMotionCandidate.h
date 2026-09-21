#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "WitchMotionCandidate.generated.h"

class UAnimSequence;
class UStaticMeshComponent;
class USkeletalMesh;
class USkeleton;

/** Stage-one complete-body locomotion candidate, independently selectable in F6. */
UCLASS()
class FPSGAME_API AWitchMotionCandidate : public ACharacter
{
    GENERATED_BODY()
public:
    AWitchMotionCandidate();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    UFUNCTION(BlueprintCallable, Category="Witch Foundation|Authoring")
    static void AssignFoundationSkeleton(USkeletalMesh* TargetMesh, USkeleton* TargetSkeleton);

    UPROPERTY(EditDefaultsOnly, Category="Motion") TObjectPtr<UAnimSequence> IdleClip;
    UPROPERTY(EditDefaultsOnly, Category="Motion") TObjectPtr<UAnimSequence> WalkClip;
    UPROPERTY(EditDefaultsOnly, Category="Motion", meta=(ClampMin="0.3", ClampMax="1.0")) float WalkStrideScale = .5f;
    UPROPERTY(EditDefaultsOnly, Category="Motion") float SourceWalkSpeed = 300.f;
    UPROPERTY(VisibleAnywhere, Category="Props") TObjectPtr<UStaticMeshComponent> Staff;
    UPROPERTY(VisibleAnywhere, Category="Props") TObjectPtr<UStaticMeshComponent> Bottle;

private:
    void AlignBodyAndGrips();
    float NextPathAt = 0.f;
};
