#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/DataAsset.h"
#include "ZombieDogAppearanceComponent.generated.h"

class USkeletalMeshComponent;
class UMaterialInstanceDynamic;

/** Rest-space centimetres: +X left side, +Y muzzle, +Z up. */
USTRUCT(BlueprintType)
struct FZombieDogWoundSurface
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FVector A = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FVector B = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FVector C = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) FVector Normal = FVector::UpVector;
    UPROPERTY(EditAnywhere) float Area = 0.f;
    /** 0/1 flanks, 2/3 shoulders, 4 neck, 5 back, 6/7 upper legs. */
    UPROPERTY(EditAnywhere) int32 Region = 0;
};

UCLASS(BlueprintType)
class FPSGAME_API UZombieDogWoundSurfaceSet : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere) TArray<FZombieDogWoundSurface> Surfaces;
};

USTRUCT(BlueprintType)
struct FZombieDogWoundPlacement
{
    GENERATED_BODY()
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FVector Center = FVector::ZeroVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FVector TangentU = FVector::ForwardVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FVector TangentV = FVector::UpVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FVector Normal = FVector::RightVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) FVector Radii = FVector::OneVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) float Severity = 1.f;
    /** 0 tear, 1 abrasion, 2 healed scar, 3 irregular tissue loss. */
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Style = 0;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) float Healing = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly) int32 Region = 0;
};

/** Generates once per seed and sends eight bounded wound masks to per-dog materials. */
UCLASS(ClassGroup=(Monsters), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UZombieDogAppearanceComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UZombieDogAppearanceComponent();
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wounds") bool bEnabled = false;
    /** Zero chooses a seed once. A positive seed reproduces the same layout. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, SaveGame, Category="Wounds", meta=(ClampMin="0")) int32 RandomSeed = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wounds", meta=(ClampMin="0", ClampMax="8")) int32 MinWounds = 3;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wounds", meta=(ClampMin="0", ClampMax="8")) int32 MaxWounds = 5;
    UPROPERTY(EditAnywhere, Category="Wounds") TObjectPtr<UZombieDogWoundSurfaceSet> SurfaceSet;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wounds") TArray<FZombieDogWoundPlacement> Wounds;
    UFUNCTION(BlueprintCallable, CallInEditor, Category="Wounds") void RerollWounds();
    void ApplyAppearance(USkeletalMeshComponent* Mesh);
private:
    void GenerateLayout();
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;
    int32 AppliedSeed = INDEX_NONE;
    int32 AppliedMin = INDEX_NONE;
    int32 AppliedMax = INDEX_NONE;
    TWeakObjectPtr<UZombieDogWoundSurfaceSet> AppliedSurfaceSet;
};
