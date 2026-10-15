#pragma once
#include "CoreMinimal.h"
#include "MonsterCharacterMovementComponent.h"
#include "M66MovementComponent.generated.h"
UCLASS()
class FPSGAME_API UM66MovementComponent : public UMonsterCharacterMovementComponent
{
    GENERATED_BODY()
public:
    virtual float GetMaxSpeed() const override;
    virtual void PhysicsRotation(float DeltaSeconds) override;
    virtual void OnTeleported() override;
private:
    bool DesiredHeading(float& Yaw) const;
    bool bPivot=false;
    float TurnVelocity=0;
};
