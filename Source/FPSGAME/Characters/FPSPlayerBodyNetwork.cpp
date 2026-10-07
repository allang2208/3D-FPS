#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace FPSBodyNetwork
{
bool IsTransition(const FFPSBodyState& A,const FFPSBodyState& B)
{
    return A.Action!=B.Action||A.ActionVariant!=B.ActionVariant||A.Motion!=B.Motion
        ||A.Contacts.Channel!=B.Contacts.Channel||A.Contacts.ConsumableSerial!=B.Contacts.ConsumableSerial
        ||A.Contacts.DiscardFlags!=B.Contacts.DiscardFlags
        ||A.BowClip!=B.BowClip||A.bBowArrow!=B.bBowArrow||A.bBowTakingArrow!=B.bBowTakingArrow
        ||A.bHasHandholds!=B.bHasHandholds||A.bDual!=B.bDual||A.bOffhandPistol!=B.bOffhandPistol
        ||A.RightHand.bReloading!=B.RightHand.bReloading||A.LeftHand.bReloading!=B.LeftHand.bReloading
        ||A.RightHand.bEquipping!=B.RightHand.bEquipping||A.LeftHand.bEquipping!=B.LeftHand.bEquipping
        ||A.AzureFlags!=B.AzureFlags
        ||(A.bHasActionProgress&&A.ActionProgress+.08f<B.ActionProgress)
        ||(A.Motion!=EFPSBodyMotion::Ground&&A.MotionProgress+.08f<B.MotionProgress)
        ||(A.RightHand.Progress+.08f<B.RightHand.Progress)
        ||(A.LeftHand.Progress+.08f<B.LeftHand.Progress);
}
float Rate(float Current,float Previous,float Delta)
{return Delta>SMALL_NUMBER?FMath::Clamp((Current-Previous)/Delta,0.f,30.f):0.f;}
float Unit(float Value,float Default=0.f)
{return FMath::IsFinite(Value)?FMath::Clamp(Value,0.f,1.f):Default;}
float SafeRate(float Value)
{return FMath::IsFinite(Value)?FMath::Clamp(Value,0.f,30.f):0.f;}
}

void UFPSPlayerBodyComponent::SendBodyPresentation(float Delta)
{
    using namespace FPSBodyNetwork;
    const float Now=ServerClock();
    const bool Edge=!bHasLocalPresentation||IsTransition(DisplayState,PreviousLocalPresentation);
    DisplayState.PresentationSampledAt=DisplayState.MotionSampledAt=Now;
    if(bHasLocalPresentation&&!Edge)
    {
        DisplayState.ActionProgressRate=Rate(DisplayState.ActionProgress,PreviousLocalPresentation.ActionProgress,Delta);
        DisplayState.MotionProgressRate=Rate(DisplayState.MotionProgress,PreviousLocalPresentation.MotionProgress,Delta);
        DisplayState.RightHand.ProgressRate=Rate(DisplayState.RightHand.Progress,PreviousLocalPresentation.RightHand.Progress,Delta);
        DisplayState.LeftHand.ProgressRate=Rate(DisplayState.LeftHand.Progress,PreviousLocalPresentation.LeftHand.Progress,Delta);
        DisplayState.BowClipRate=Delta>SMALL_NUMBER?FMath::Clamp((DisplayState.BowClipTime-PreviousLocalPresentation.BowClipTime)/Delta,-8.f,8.f):0.f;
    }
    PresentationSendCountdown-=Delta;
    if(GetNetMode()==NM_Client&&(Edge||PresentationSendCountdown<=0.f))
    {
        ++SentPresentationSequence;
        if(Edge)ServerBodyTransition(DisplayState,SentPresentationSequence);
        else ServerBodySnapshot(DisplayState,SentPresentationSequence);
        PresentationSendCountdown=.08f;
    }
    PreviousLocalPresentation=DisplayState;bHasLocalPresentation=true;
}

void UFPSPlayerBodyComponent::ServerBodyTransition_Implementation(const FFPSBodyState& State,uint32 Sequence)
{AcceptBodyPresentation(State,Sequence);}
void UFPSPlayerBodyComponent::ServerBodySnapshot_Implementation(const FFPSBodyState& State,uint32 Sequence)
{AcceptBodyPresentation(State,Sequence);}

void UFPSPlayerBodyComponent::AcceptBodyPresentation(const FFPSBodyState& Incoming,uint32 Sequence)
{
    using namespace FPSBodyNetwork;
    if(!GetOwner()->HasAuthority()||(bHasReportedPresentation&&static_cast<int32>(Sequence-ReceivedPresentationSequence)<=0))return;
    if(static_cast<uint8>(Incoming.Action)>static_cast<uint8>(EFPSBodyAction::StaffLight)
        ||static_cast<uint8>(Incoming.Motion)>static_cast<uint8>(EFPSBodyMotion::Mantle))return;
    const auto* Pawn=Cast<AFPSGAMECharacter>(GetOwner());if(!Pawn)return;
    const float Now=ServerClock();
    FFPSBodyState Next=Incoming;
    if(!Next.Contacts.IsSane())Next.Contacts=FFPSBodyMotionSample();
    Next.Contacts.Light=FMath::Clamp(Next.Contacts.Light,0.f,1.f);
    Next.ActionDuration=FMath::IsFinite(Next.ActionDuration)?FMath::Clamp(Next.ActionDuration,0.f,60.f):0.f;
    Next.ActionStartedAt=FMath::IsFinite(Next.ActionStartedAt)?FMath::Clamp(Next.ActionStartedAt,Now-60.f,Now):Now;
    Next.PresentationSampledAt=FMath::IsFinite(Next.PresentationSampledAt)?FMath::Clamp(Next.PresentationSampledAt,Now-.5f,Now):Now;
    Next.MotionSampledAt=Next.PresentationSampledAt;
    Next.ActionProgress=Unit(Next.ActionProgress);Next.ActionWeight=Unit(Next.ActionWeight,1.f);
    Next.BowClipTime=FMath::IsFinite(Next.BowClipTime)?FMath::Clamp(Next.BowClipTime,0.f,60.f):0.f;
    Next.BowClipRate=FMath::IsFinite(Next.BowClipRate)?FMath::Clamp(Next.BowClipRate,-8.f,8.f):0.f;
    Next.BowSeat=Unit(Next.BowSeat,1.f);
    Next.BowStringContact=Unit(Next.BowStringContact);
    if(Next.BowNock.ContainsNaN()||Next.BowNock.SizeSquared()>FMath::Square(250.f))
    {Next.BowClip=NAME_None;Next.BowNock=FVector::ZeroVector;Next.bBowArrow=false;}
    Next.ActionEntryFraction=FMath::Clamp(Unit(Next.ActionEntryFraction),0.f,Unit(Next.ContactFraction,.5f));
    Next.ContactFraction=Unit(Next.ContactFraction,.5f);Next.ReleaseFraction=Unit(Next.ReleaseFraction,.8f);
    Next.AzureSourceLength=FMath::IsFinite(Next.AzureSourceLength)?FMath::Clamp(Next.AzureSourceLength,0.f,10.f):0.f;
    Next.AzureEntryTime=FMath::IsFinite(Next.AzureEntryTime)?FMath::Clamp(Next.AzureEntryTime,0.f,Next.AzureSourceLength):0.f;
    Next.AzureChargeStartedAt=FMath::IsFinite(Next.AzureChargeStartedAt)?FMath::Clamp(Next.AzureChargeStartedAt,Now-30.f,Now):Now;
    Next.ActionProgressRate=SafeRate(Next.ActionProgressRate);Next.MotionProgressRate=SafeRate(Next.MotionProgressRate);
    Next.MotionProgress=Unit(Next.MotionProgress);Next.MotionContact=Unit(Next.MotionContact,.25f);
    Next.MotionRelease=FMath::Max(Next.MotionContact,Unit(Next.MotionRelease,.75f));
    Next.MotionHandContact=Unit(Next.MotionHandContact);
    Next.MotionDirection=Next.MotionDirection.ContainsNaN()?FVector(0,1,0):Next.MotionDirection.GetSafeNormal();
    for(auto* Hand:{&Next.RightHand,&Next.LeftHand})
    {
        Hand->Progress=Unit(Hand->Progress);Hand->ProgressRate=SafeRate(Hand->ProgressRate);
        Hand->LastShotAt=FMath::IsFinite(Hand->LastShotAt)?FMath::Clamp(Hand->LastShotAt,Now-10.f,Now):-100.f;
    }
    const bool Traversing=Next.Motion==EFPSBodyMotion::Vault||Next.Motion==EFPSBodyMotion::Mantle;
    Next.bHasHandholds&=Traversing&&!Next.RightHandhold.ContainsNaN()&&!Next.LeftHandhold.ContainsNaN()
        &&FVector::DistSquared(Next.RightHandhold,Pawn->GetActorLocation())<FMath::Square(500.f)
        &&FVector::DistSquared(Next.LeftHandhold,Pawn->GetActorLocation())<FMath::Square(500.f);
    if(!Next.bHasHandholds){Next.RightHandhold=Next.LeftHandhold=FVector::ZeroVector;Next.MotionHandContact=0.f;}
    // Do not apply client weapon/family/aim/locomotion flags or any gameplay value.
    // SampleRemoteAuthorityState copies only cosmetic fields from this record.
    ReportedPresentation=Next;ReceivedPresentationSequence=Sequence;
    LastPresentationReceivedAt=Now;bHasReportedPresentation=true;
    DisplayState=SampleRemoteAuthorityState();ReplicatedState=DisplayState;
    GetOwner()->ForceNetUpdate();
}

void UFPSPlayerBodyComponent::AdvanceBodyPresentation(FFPSBodyState& State,float Now)
{
    const float Age=FMath::Clamp(Now-State.PresentationSampledAt,0.f,.12f);
    State.BowClipTime=FMath::Clamp(State.BowClipTime+State.BowClipRate*Age,0.f,60.f);
    if(State.bHasActionProgress)State.ActionProgress=FMath::Clamp(State.ActionProgress+State.ActionProgressRate*Age,0.f,1.f);
    State.RightHand.Progress=FMath::Clamp(State.RightHand.Progress+State.RightHand.ProgressRate*Age,0.f,1.f);
    State.LeftHand.Progress=FMath::Clamp(State.LeftHand.Progress+State.LeftHand.ProgressRate*Age,0.f,1.f);
    State.MotionProgress=FMath::Clamp(State.MotionProgress+State.MotionProgressRate*FMath::Clamp(Now-State.MotionSampledAt,0.f,.12f),0.f,1.f);
}
