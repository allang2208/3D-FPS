#pragma once

#include "CoreMinimal.h"
#include "GameFramework/RootMotionSource.h"
#include "FPSDodgeRootMotionSource.generated.h"

// Integrated ease-out displacement, consumed by native CharacterMovement sweeps.
USTRUCT()
struct FPSGAME_API FRootMotionSource_FPSDodge : public FRootMotionSource_ConstantForce
{
    GENERATED_BODY()
    FRootMotionSource_FPSDodge();
    virtual FRootMotionSource* Clone() const override;
    virtual UScriptStruct* GetScriptStruct() const override;
    virtual void PrepareRootMotion(float SimulationTime, float MovementTickTime,
        const ACharacter& Character, const UCharacterMovementComponent& MoveComponent) override;
};

template<>
struct TStructOpsTypeTraits<FRootMotionSource_FPSDodge> : TStructOpsTypeTraitsBase2<FRootMotionSource_FPSDodge>
{
    enum { WithNetSerializer = true, WithCopy = true };
};
