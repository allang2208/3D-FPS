#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/BoundCongregateCaptureComponent.h"
#include "GameFramework/Controller.h"

void URuneSwordComponent::AdvanceZhufeng(float FromTime,float ToTime)
{
    const float SpinEnd=WhirlwindTuning.ReadySeconds+WhirlwindTuning.SpinSeconds;
    const float Seconds=FMath::Max(0.f,FMath::Min(ToTime,SpinEnd)-FMath::Min(FromTime,SpinEnd));
    if(bLungeBlocked||Seconds<=0.f)return;
    auto* Pawn=Character.Get();
    auto* Movement=Pawn?Cast<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement()):nullptr;
    const auto* Status=Pawn?Pawn->FindComponentByClass<UCombatStatusFormula>():nullptr;
    if(!Movement||Movement->IsMeleeLungeRejected()||Pawn->IsTraversing()||Pawn->IsDodging()||
        UBoundCongregateCaptureComponent::IsCaptured(Pawn)||(Status&&Status->BlocksMovement())||
        (Pawn->GetController()&&Pawn->GetController()->IsMoveInputIgnored()))
    {bLungeBlocked=true;return;}
    const float Requested=ZhufengSpeed*Seconds;
    FVector Moved;
    if(Movement->IsFalling())
    {
        const FVector Before=Pawn->GetActorLocation();FHitResult Hit;
        Movement->SafeMoveUpdatedComponent(ZhufengDirection*Requested,Pawn->GetActorQuat(),true,Hit);
        Moved=Pawn->GetActorLocation()-Before;
        if(Hit.bBlockingHit)bLungeBlocked=true;
    }
    else Moved=Movement->ApplyMeleeLungeStep(ZhufengDirection,Requested);
    const float Accepted=FMath::Max(0.f,float(FVector::DotProduct(Moved,ZhufengDirection)));
    Movement->RecordMeleeLungeStep(Accepted);
    if(Accepted+.01f<Requested)bLungeBlocked=true;
}
