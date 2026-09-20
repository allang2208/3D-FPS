#include "ProductionToolComponent.h"
#include "ProductionPickaxeImpactMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void UProductionToolComponent::UpdateTwoHandLocomotion(float Delta)
{
    const auto* Movement=Character->GetCharacterMovement();
    const float Speed=Character->GetVelocity().Size2D();
    const bool bAction=IsBusy() || Character->IsCastBlockingLeftHandAction();
    const bool bGroundStride=Movement->IsMovingOnGround() && !Character->IsSliding()
        && !Character->IsDodging() && !Character->IsTraversing();
    const bool bMoving=bGroundStride && Speed>15.f && !bAction;
    if(bMoving)
        if(const auto* Footsteps=Character->FindComponentByClass<UFPSFootstepAudioComponent>())
            AxeStridePhase=Footsteps->GetStridePhaseRadians();

    const float RunTarget=bMoving && Character->IsSprinting()?1.f:0.f;
    SprintBlend=FMath::Lerp(SprintBlend,RunTarget,1.f-FMath::Exp(-10.f*Delta));
    const float Weight=bMoving?FMath::Clamp((Speed-15.f)/FMath::Max(Movement->MaxWalkSpeed-15.f,1.f),0.f,1.f):0.f;
    const bool bPickaxe=Kind==TEXT("pickaxe");
    const FVector Travel=FMath::Lerp(bPickaxe?PickaxeWalkTravelCM:AxeWalkTravelCM,
        bPickaxe?PickaxeRunTravelCM:AxeRunTravelCM,SprintBlend);
    const FRotator Angles=FMath::Lerp(bPickaxe?PickaxeWalkAngles:AxeWalkAngles,
        bPickaxe?PickaxeRunAngles:AxeRunAngles,SprintBlend);
    const float Phase=AxeStridePhase;
    // One sideways cycle spans two steps. Two vertical pulses follow footfall;
    // the slight angular delay lets the heavy head follow the two-hand carry.
    const FVector TargetOffset=FVector(Travel.X*FMath::Sin(2.f*Phase),
        Travel.Y*FMath::Cos(Phase),
        -Travel.Z*(FMath::Cos(2.f*Phase)+.12f*FMath::Cos(4.f*Phase))/1.12f)*Weight;
    const FQuat TargetRotation=(FRotator(-Angles.Pitch*FMath::Sin(2.f*Phase-.25f),
        Angles.Yaw*FMath::Sin(Phase-.3f),-Angles.Roll*FMath::Cos(Phase-.18f))*Weight).Quaternion();
    const float Follow=1.f-FMath::Exp(-(bAction?28.f:18.f)*Delta);
    AxeLocomotionOffset=FMath::Lerp(AxeLocomotionOffset,TargetOffset,Follow);
    AxeLocomotionRotation=FQuat::Slerp(AxeLocomotionRotation,TargetRotation,Follow).GetNormalized();
    if(bHitConfirmed)
    {
        // Confirmed contact owns the complete lodged/frozen pose.
        AxeLocomotionOffset=FVector::ZeroVector;
        AxeLocomotionRotation=FQuat::Identity;
        if(bPickaxe)AxeLocomotionRotation=FRotator(
            ProductionPickaxeImpact::PryDegrees(Elapsed-ContactSeconds),0,0).Quaternion();
    }

    // Move both arms and the held tool together. Rotating around the grip midpoint
    // preserves the idle hand contacts and avoids a large orbit around the eye.
    const FQuat BaseRotation=FRotator(0,90,0).Quaternion();
    const FVector GripCenter=BaseRotation.RotateVector((
        Viewmodel->GetSocketTransform(TEXT("hand_l"),RTS_Component).GetLocation()+
        Viewmodel->GetSocketTransform(TEXT("hand_r"),RTS_Component).GetLocation())*.5f);
    const FVector Location=AxeLocomotionOffset+GripCenter-AxeLocomotionRotation.RotateVector(GripCenter);
    Viewmodel->SetRelativeLocationAndRotation(Location,AxeLocomotionRotation*BaseRotation);
}
