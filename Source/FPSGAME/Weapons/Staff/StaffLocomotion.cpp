#include "StaffLocomotion.h"
#include "../../FPSGAMECharacter.h"
#include "../../Movement/FPSFootstepAudioComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

void FStaffLocomotion::Reset(){*this=FStaffLocomotion();}

void FStaffLocomotion::Update(const AFPSGAMECharacter& Pawn,const UFPSFootstepAudioComponent* Footsteps,float Delta,bool bAction)
{
    if(Delta<=0)return;
    const FVector Velocity=Pawn.GetVelocity();const FRotator View=Pawn.GetControlRotation();
    if(!bInitialized){LaggedVelocity=Velocity;PreviousView=View;bInitialized=true;}
    IdleTime+=Delta;
    const auto* Movement=Pawn.GetCharacterMovement();
    const bool bGround=Movement&&Movement->IsMovingOnGround()&&!Pawn.IsSliding()&&!Pawn.IsDodging()&&!Pawn.IsTraversing();
    const float Speed=Velocity.Size2D();
    const bool bMoving=bGround&&Speed>15.f;
    // Keep sampling the existing distance/footfall clock during action suppression.
    // Stopping and changing walk/run only fade amplitude, never restart the cycle.
    if(bMoving&&Footsteps)Phase=Footsteps->GetStridePhaseRadians();
    const bool bRun=bMoving&&Pawn.IsSprinting()&&!Pawn.bIsCrouched&&!bAction;
    const float MoveTarget=bMoving&&!bAction?FMath::Clamp((Speed-15.f)/FMath::Max(1.f,Pawn.WalkSpeed-15.f),0.f,1.f):0.f;
    const auto Follow=[Delta](float Rate){return 1.f-FMath::Exp(-Rate*Delta);};
    MoveBlend=FMath::Lerp(MoveBlend,MoveTarget,Follow(bAction?22.f:9.f));
    RunBlend=FMath::Lerp(RunBlend,bRun?1.f:0.f,Follow(bRun?5.5f:10.f));
    const float Weight=MoveBlend*(Pawn.bIsCrouched?.6f:1.f);
    const float Side=FMath::Cos(Phase),Swing=FMath::Sin(Phase),Step=FMath::Sin(2.f*Phase);
    const FVector Walk(.55f*FMath::Sin(2.f*Phase-.3f),1.05f*Side,-.48f*(FMath::Cos(2.f*Phase)+.1f*FMath::Cos(4.f*Phase)));
    const FVector Run(2.5f*Swing,1.65f*Side,-.95f*(FMath::Cos(2.f*Phase)+.1f*FMath::Cos(4.f*Phase)));
    // Sprint carries the heavy head lower and farther forward instead of merely
    // accelerating the walk bob. All rotation remains around the upper grip.
    FVector Target=FMath::Lerp(Walk,Run,RunBlend)*Weight+FVector(-4,3,-6)*RunBlend;
    const float Breath=(1-MoveBlend)*(bAction?0.f:1.f);
    Target+=FVector(0,.06f*FMath::Sin(IdleTime*1.7f),.14f*FMath::Sin(IdleTime*1.9f))*Breath;
    LaggedVelocity=FMath::Lerp(LaggedVelocity,Velocity,Follow(6.f));
    const FVector Lag=FRotator(0,View.Yaw,0).UnrotateVector(LaggedVelocity-Velocity);
    if(bGround&&!bAction)Target+=FVector(FMath::Clamp(Lag.X*.006,-1.2,1.2),FMath::Clamp(Lag.Y*.005,-.9,.9),0);
    const double YawRate=FMath::Clamp(FMath::FindDeltaAngleDegrees(PreviousView.Yaw,View.Yaw)/Delta,-180.,180.);
    const double PitchRate=FMath::Clamp(FMath::FindDeltaAngleDegrees(PreviousView.Pitch,View.Pitch)/Delta,-140.,140.);
    PreviousView=View;
    const FRotator WalkAngles(-.8f*FMath::Sin(2.f*Phase-.35f),.9f*FMath::Sin(Phase-.25f),-1.1f*FMath::Cos(Phase-.2f));
    const FRotator RunAngles(-3.f*FMath::Sin(Phase-.3f),1.8f*FMath::Sin(Phase-.35f),-3.5f*FMath::Cos(Phase-.3f));
    FRotator Angles=FMath::Lerp(WalkAngles,RunAngles,RunBlend)*Weight+FRotator(-12,8,10)*RunBlend;
    if(!bAction)Angles+=FRotator(PitchRate*.008,-YawRate*.012,-YawRate*.006);
    Offset=FMath::Lerp(Offset,Target,Follow(bAction?24.f:16.f));
    Rotation=FQuat::Slerp(Rotation,Angles.Quaternion(),Follow(bAction?24.f:11.f)).GetNormalized();
    // Small shoulder transport and delayed elbow arcs avoid a stationary hinge
    // underneath a moving wrist. The left arm counterbalances the staff arm.
    const float Arc=Weight*FMath::Lerp(.45f,1.4f,RunBlend);
    RightShoulder=Offset*.18f+FVector(.12f*Swing,.18f*Side,.10f*Step)*Weight;
    RightElbow=Offset*.45f+FVector(Arc*FMath::Sin(Phase-.4f),Arc*.6f*Side,-1.5f*RunBlend);
    LeftShoulder=FVector(-.15f*Swing,-.16f*Side,.1f*Step)*Weight;
    LeftElbow=FVector(-Arc*FMath::Sin(Phase-.4f),-.4f*Arc*Side,-RunBlend);
    const FVector LeftOffset=FVector(-FMath::Lerp(.75f,4.f,RunBlend)*Swing,-.5f*Side,.3f*Step)*Weight+FVector(0,0,-2)*RunBlend;
    LeftHand=FTransform(FRotator(2.5f*Swing*Weight*RunBlend,0,1.5f*Side*Weight).Quaternion(),LeftOffset);
}
