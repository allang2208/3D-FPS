#include "ProductionToolComponent.h"
#include "ProductionPickaxeImpactMotion.h"
#include "WarhammerHeavyMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSFootstepAudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
constexpr float ThunderChargeSideCM=6.5f;

FQuat ThunderChargeSightRotation(float Weight)
{
    // Camera +Y is right. Cant the top of the shaft right while yawing the
    // complete grasp slightly, without rotating either wrist relative to it.
    return FQuat(FVector::UpVector,FMath::DegreesToRadians(8.f*Weight))*
        FQuat(FVector::ForwardVector,FMath::DegreesToRadians(-6.f*Weight));
}

void ApplyToolCarryFrame(USkeletalMeshComponent* Arms,const FVector& Offset,const FQuat& Rotation)
{
    const FQuat BaseRotation=FRotator(0,90,0).Quaternion();
    const FVector GripCenter=BaseRotation.RotateVector((
        Arms->GetSocketTransform(TEXT("hand_l"),RTS_Component).GetLocation()+
        Arms->GetSocketTransform(TEXT("hand_r"),RTS_Component).GetLocation())*.5f);
    Arms->SetRelativeLocationAndRotation(Offset+GripCenter-Rotation.RotateVector(GripCenter),Rotation*BaseRotation);
}
}

void UProductionToolComponent::UpdateTwoHandLocomotion(float Delta)
{
    if(bBluntHeavy&&Elapsed>=0.f)
    {
        AxeLocomotionOffset=FVector::ZeroVector;AxeLocomotionRotation=FQuat::Identity;
        if(UsesThunderThrowHeavy())
        {
            // Keep the raised frame continuous at release input, then return to
            // the original launch frame before the .24 s projectile handoff.
            const float Weight=1.f-FMath::SmoothStep(0.f,.18f,AuthoredElapsed());
            AxeLocomotionOffset=FVector(0,ThunderChargeSideCM*Weight,0);
            AxeLocomotionRotation=ThunderChargeSightRotation(Weight);
            ApplyToolCarryFrame(Viewmodel,AxeLocomotionOffset,AxeLocomotionRotation);
        }
        return; // The stable slam frame was set before the floor/arm solve.
    }
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
    if(Kind!=TEXT("warhammer"))SprintBlend=FMath::Lerp(SprintBlend,RunTarget,1.f-FMath::Exp(-10.f*Delta));
    const float StrideBlend=Kind==TEXT("warhammer")?RunTarget:SprintBlend;
    const float Weight=bMoving?FMath::Clamp((Speed-15.f)/FMath::Max(Movement->MaxWalkSpeed-15.f,1.f),0.f,1.f):0.f;
    const bool bPickaxe=UsesPickaxeMotion();
    const FVector Travel=FMath::Lerp(bPickaxe?PickaxeWalkTravelCM:AxeWalkTravelCM,
        bPickaxe?PickaxeRunTravelCM:AxeRunTravelCM,StrideBlend);
    const FRotator Angles=FMath::Lerp(bPickaxe?PickaxeWalkAngles:AxeWalkAngles,
        bPickaxe?PickaxeRunAngles:AxeRunAngles,StrideBlend);
    const float Phase=AxeStridePhase;
    // One sideways cycle spans two steps. Two vertical pulses follow footfall;
    // the slight angular delay lets the heavy head follow the two-hand carry.
    FVector TargetOffset=FVector(Travel.X*FMath::Sin(2.f*Phase),
        Travel.Y*FMath::Cos(Phase),
        -Travel.Z*(FMath::Cos(2.f*Phase)+.12f*FMath::Cos(4.f*Phase))/1.12f)*Weight;
    FQuat TargetRotation=(FRotator(-Angles.Pitch*FMath::Sin(2.f*Phase-.25f),
        Angles.Yaw*FMath::Sin(Phase-.3f),-Angles.Roll*FMath::Cos(Phase-.18f))*Weight).Quaternion();
    if(bThunderThrowSeat&&(bBluntCharging||bBluntReturningCharge))
    {
        const float Charge=FMath::SmoothStep(.15f,.8f,BluntChargePoseSeconds()/WarhammerHeavy::ChargeSeconds);
        TargetOffset+=FVector(0,ThunderChargeSideCM*Charge,0);
        TargetRotation=ThunderChargeSightRotation(Charge)*TargetRotation;
    }
    const float Follow=1.f-FMath::Exp(-(bAction?28.f:18.f)*Delta);
    AxeLocomotionOffset=FMath::Lerp(AxeLocomotionOffset,TargetOffset,Follow);
    AxeLocomotionRotation=FQuat::Slerp(AxeLocomotionRotation,TargetRotation,Follow).GetNormalized();
    if(bHitConfirmed)
    {
        // Confirmed contact owns the complete lodged/frozen pose.
        AxeLocomotionOffset=FVector::ZeroVector;
        AxeLocomotionRotation=FQuat::Identity;
        // 撬动关键帧是作者秒：改造后的真实时间先换算回作者时间。
        if(Kind==TEXT("pickaxe"))
        {
            const float Pry=ProductionPickaxeImpact::PryDegrees(AuthoredElapsed()-ContactSeconds);
            AxeLocomotionRotation=FRotator(Pry,0,0).Quaternion();
        }
    }

    // Move both arms and the held tool together. Rotating around the grip midpoint
    // preserves the idle hand contacts and avoids a large orbit around the eye.
    ApplyToolCarryFrame(Viewmodel,AxeLocomotionOffset,AxeLocomotionRotation);
}
