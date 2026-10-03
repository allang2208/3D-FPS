#pragma once
#include "MonsterCharacterMovementComponent.h"
#include "M10MovementComponent.generated.h"

/** M10 steering only; native path following and swept movement retain ownership. */
UCLASS()
class FPSGAME_API UM10MovementComponent : public UMonsterCharacterMovementComponent
{
    GENERATED_BODY()
public:
    virtual float GetMaxSpeed() const override;
    virtual void PhysicsRotation(float DeltaTime) override;
    virtual void OnTeleported() override;
    float GetTurnRate() const { return TurnRate; }
    bool IsPivoting() const { return bPivot; }
private:
    bool DesiredHeading(float& Yaw) const;
    float TurnRate=0.f;
    bool bPivot=false;
};
