#pragma once
#include "CoreMinimal.h"
#include "WitchMonster.h"
#include "WitchRebuiltMonster.generated.h"

/** Sole playable Witch, retaining the rebuilt anatomy, garment and animation assets. */
UCLASS(Blueprintable, Placeable)
class FPSGAME_API AWitchRebuiltMonster : public AWitchMonster
{
    GENERATED_BODY()
public:
    AWitchRebuiltMonster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual bool CanCast(APawn* Candidate) const override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") TObjectPtr<UAnimSequence> TurnLeftClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") TObjectPtr<UAnimSequence> TurnRightClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") float WalkStrideScale = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Witch|Animation") float SourceWalkSpeed = 300.f;
    // Body, cloth extraction and binding are owned by this candidate's authoring pipeline.
    // The parameter is named SourceMesh: a parameter called Mesh shadows ACharacter::Mesh,
    // which UHT rejects outright.
    UFUNCTION(BlueprintCallable, Category="Witch|Authoring") static bool BuildDrape(USkeletalMesh* SourceMesh);
    UFUNCTION(BlueprintCallable, Category="Witch|Authoring") static bool PrepareRebuiltPhysics(USkeletalMesh* SourceMesh, bool bApply = true);
    UFUNCTION(BlueprintCallable, Category="Witch|Authoring", meta=(ScriptName="configure_distance_lods")) static bool ConfigureDistanceLODs(USkeletalMesh* SourceMesh);
protected:
    virtual void AlignVisual() override;
    virtual void AttachProps() override;
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void StartDeathPresentation() override;
private:
    void ResolveAssets();
    float SettledSeconds = 0.f;
    float PreviousYaw = 0.f;
    bool bWantsClothSimulation = true;
};
