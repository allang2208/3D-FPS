#pragma once
#include "CoreMinimal.h"
#include "MonsterCharacterMovementComponent.h"
#include "RootCrownMovementComponent.generated.h"

/** One authority for steering; wide turns brake before the feet pivot. */
UCLASS()
class FPSGAME_API URootCrownMovementComponent : public UMonsterCharacterMovementComponent
{
    GENERATED_BODY()
public:
    virtual float GetMaxSpeed() const override;
    virtual void PhysicsRotation(float DeltaSeconds) override;
    virtual void OnTeleported() override;
private:
    bool DesiredHeading(float& Yaw) const;
    float TurnVelocity=0.f;
    bool bPivot=false;
};
