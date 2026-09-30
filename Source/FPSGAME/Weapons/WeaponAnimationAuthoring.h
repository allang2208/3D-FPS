#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "WeaponAnimationAuthoring.generated.h"

class UAnimSequence;
class USkeleton;

/** Native authoring operation missing from the Python animation API. */
UCLASS()
class FPSGAME_API UWeaponAnimationAuthoring : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    /** Rebind an animation copy without converting its local bone transforms. */
    UFUNCTION(BlueprintCallable, Category="Weapons|Authoring")
    static bool RebindNativeAnimation(UAnimSequence* Sequence, USkeleton* TargetSkeleton);
};
