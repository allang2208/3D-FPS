#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace FPSBodyNetwork
{
bool IsTransition(const FFPSBodyState& A,const FFPSBodyState& B)
{
    if(A.Lasers.Num()!=B.Lasers.Num())return true;
    for(int32 I=0;I<A.Lasers.Num();++I)
        if(A.Lasers[I].RigIndex!=B.Lasers[I].RigIndex||A.Lasers[I].PartIndex!=B.Lasers[I].PartIndex
            ||A.Lasers[I].Schema!=B.Lasers[I].Schema)return true;
    if(A.WeaponInstance!=B.WeaponInstance||A.OffhandInstance!=B.OffhandInstance
        ||A.Contacts.Wrists!=B.Contacts.Wrists||A.Contacts.Rigs.Num()!=B.Contacts.Rigs.Num())return true;
    for(int32 I=0;I<A.Contacts.Rigs.Num();++I)
    {
        const auto& X=A.Contacts.Rigs[I];const auto& Y=B.Contacts.Rigs[I];
        if(X.Valid!=Y.Valid||X.Schema!=Y.Schema||X.Visible!=Y.Visible||X.ReloadPropVisible!=Y.ReloadPropVisible
            ||X.Sections!=Y.Sections||X.VisibleParts!=Y.VisibleParts)return true;
    }
    return A.Weapon!=B.Weapon||A.Family!=B.Family||A.Action!=B.Action||A.ActionVariant!=B.ActionVariant||A.Motion!=B.Motion
        ||A.Contacts.Channel!=B.Contacts.Channel||A.Contacts.ConsumableSerial!=B.Contacts.ConsumableSerial
        ||A.Contacts.DiscardFlags!=B.Contacts.DiscardFlags
        ||A.BowClip!=B.BowClip||A.bBowClipLooping!=B.bBowClipLooping||A.bBowArrow!=B.bBowArrow||A.bBowTakingArrow!=B.bBowTakingArrow
        ||A.bHasHandholds!=B.bHasHandholds||A.bDual!=B.bDual||A.bOffhandPistol!=B.bOffhandPistol
        ||A.RightHand.bReloading!=B.RightHand.bReloading||A.LeftHand.bReloading!=B.LeftHand.bReloading
        ||A.RightHand.bEquipping!=B.RightHand.bEquipping||A.LeftHand.bEquipping!=B.LeftHand.bEquipping
        ||A.AzureFlags!=B.AzureFlags
        ||A.Contacts.FloatingBook!=B.Contacts.FloatingBook
        ||(A.bHasActionProgress&&A.Action!=EFPSBodyAction::Guard&&A.ActionProgress+.08f<B.ActionProgress)
        ||(A.Motion!=EFPSBodyMotion::Ground&&A.MotionProgress+.08f<B.MotionProgress)
        ||(A.RightHand.Progress+.08f<B.RightHand.Progress)
        ||(A.LeftHand.Progress+.08f<B.LeftHand.Progress);
}
float Rate(float Current,float Previous,float Delta)
{return Delta>SMALL_NUMBER?FMath::Clamp((Current-Previous)/Delta,-30.f,30.f):0.f;}
float Unit(float Value,float Default=0.f)
{return FMath::IsFinite(Value)?FMath::Clamp(Value,0.f,1.f):Default;}
float SafeRate(float Value)
{return FMath::IsFinite(Value)?FMath::Clamp(Value,-30.f,30.f):0.f;}
}

void UFPSPlayerBodyComponent::SendBodyPresentation(float Delta)
{
    using namespace FPSBodyNetwork;
    const float Now=ServerClock();
    CaptureLaserPresentation();
    const bool Edge=!bHasLocalPresentation||IsTransition(DisplayState,PreviousLocalPresentation);
    const bool Shot=bHasLocalPresentation&&(DisplayState.LastShotAt>PreviousLocalPresentation.LastShotAt
        ||DisplayState.RightHand.LastShotAt>PreviousLocalPresentation.RightHand.LastShotAt
        ||DisplayState.LeftHand.LastShotAt>PreviousLocalPresentation.LeftHand.LastShotAt);
    DisplayState.PresentationSampledAt=DisplayState.MotionSampledAt=Now;
    if(bHasLocalPresentation&&DisplayState.WeaponInstance==PreviousLocalPresentation.WeaponInstance
        &&DisplayState.OffhandInstance==PreviousLocalPresentation.OffhandInstance)
    {
        const auto& P=PreviousLocalPresentation;
        if(DisplayState.Action==P.Action&&DisplayState.ActionVariant==P.ActionVariant
            &&(DisplayState.Action==EFPSBodyAction::Guard||DisplayState.ActionProgress+.08f>=P.ActionProgress))
            DisplayState.ActionProgressRate=Rate(DisplayState.ActionProgress,P.ActionProgress,Delta);
        if(DisplayState.Motion==P.Motion&&DisplayState.MotionProgress+.08f>=P.MotionProgress)
            DisplayState.MotionProgressRate=Rate(DisplayState.MotionProgress,P.MotionProgress,Delta);
        const auto HandRate=[&](FFPSBodyHandState& Hand,const FFPSBodyHandState& Before)
        {
            if(Hand.bReloading==Before.bReloading&&Hand.bEquipping==Before.bEquipping&&Hand.Progress+.08f>=Before.Progress)
                Hand.ProgressRate=Rate(Hand.Progress,Before.Progress,Delta);
        };
        HandRate(DisplayState.RightHand,P.RightHand);HandRate(DisplayState.LeftHand,P.LeftHand);
        if(DisplayState.BowClip==P.BowClip&&DisplayState.bBowClipLooping==P.bBowClipLooping)
        {
            float Travel=DisplayState.BowClipTime-P.BowClipTime;
            if(DisplayState.bBowClipLooping&&Travel<0.f)Travel+=DisplayState.BowClipLength;
            DisplayState.BowClipRate=Delta>SMALL_NUMBER?FMath::Clamp(Travel/Delta,-8.f,8.f):0.f;
        }
    }
    PresentationSendCountdown-=Delta;
    if(GetNetMode()==NM_Client&&(Edge||Shot||PresentationSendCountdown<=0.f))
    {
        ++SentPresentationSequence;
        if(Edge)ServerBodyTransition(DisplayState,SentPresentationSequence);
        else ServerBodySnapshot(DisplayState,SentPresentationSequence);
        // A short wrist throw or bolt cycle can fit between the former 80 ms
        // samples. Active poses use 25 Hz; idle presentation retains 12.5 Hz.
        const bool Active=!DisplayState.Lasers.IsEmpty()||DisplayState.Action!=EFPSBodyAction::None||DisplayState.Contacts.Wrists!=0
            ||DisplayState.RightHand.bReloading||DisplayState.LeftHand.bReloading
            ||DisplayState.RightHand.bEquipping||DisplayState.LeftHand.bEquipping
            ||DisplayState.Family==TEXT("Bow")||Now-DisplayState.LastShotAt<.15f;
        PresentationSendCountdown=Active?.04f:.08f;
    }
    if(GetOwner()->HasAuthority()&&(Edge||Shot||(!DisplayState.Lasers.IsEmpty()&&PresentationSendCountdown<=0.f)))
    {
        GetOwner()->ForceNetUpdate();
        if(!DisplayState.Lasers.IsEmpty())PresentationSendCountdown=.04f;
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
    SanitizeLaserPresentation(Next);
    Next.LastShotAt=FMath::IsFinite(Next.LastShotAt)?FMath::Clamp(Next.LastShotAt,Now-10.f,Now):-100.f;
    if(!Next.Contacts.IsSane())Next.Contacts=FFPSBodyMotionSample();
    Next.Contacts.Light=FMath::Clamp(Next.Contacts.Light,0.f,1.f);
    Next.ActionDuration=FMath::IsFinite(Next.ActionDuration)?FMath::Clamp(Next.ActionDuration,0.f,60.f):0.f;
    Next.ActionStartedAt=FMath::IsFinite(Next.ActionStartedAt)?FMath::Clamp(Next.ActionStartedAt,Now-60.f,Now):Now;
    Next.PresentationSampledAt=FMath::IsFinite(Next.PresentationSampledAt)?FMath::Clamp(Next.PresentationSampledAt,Now-.5f,Now):Now;
    Next.MotionSampledAt=Next.PresentationSampledAt;
    Next.ActionProgress=Unit(Next.ActionProgress);Next.ActionWeight=Unit(Next.ActionWeight,1.f);
    Next.BowClipTime=FMath::IsFinite(Next.BowClipTime)?FMath::Clamp(Next.BowClipTime,0.f,60.f):0.f;
    Next.BowClipRate=FMath::IsFinite(Next.BowClipRate)?FMath::Clamp(Next.BowClipRate,-8.f,8.f):0.f;
    Next.BowClipLength=FMath::IsFinite(Next.BowClipLength)?FMath::Clamp(Next.BowClipLength,0.f,60.f):0.f;
    Next.bBowClipLooping&=Next.BowClipLength>SMALL_NUMBER;
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
    DisplayState=SampleRemoteAuthorityState();
    if(DisplayState.WeaponInstance!=ReplicatedState.WeaponInstance||DisplayState.OffhandInstance!=ReplicatedState.OffhandInstance)
        bEquipmentDirty=true;
    ReplicatedState=DisplayState;
    GetOwner()->ForceNetUpdate();
}

void UFPSPlayerBodyComponent::AdvanceBodyPresentation(FFPSBodyState& State,float Now)
{
    const float Age=FMath::Clamp(Now-State.PresentationSampledAt,0.f,.12f);
    State.BowClipTime=FMath::Clamp(State.BowClipTime+State.BowClipRate*Age,0.f,60.f);
    if(State.bBowClipLooping&&State.BowClipLength>SMALL_NUMBER)State.BowClipTime=FMath::Fmod(State.BowClipTime,State.BowClipLength);
    if(State.bHasActionProgress)State.ActionProgress=FMath::Clamp(State.ActionProgress+State.ActionProgressRate*Age,0.f,1.f);
    State.RightHand.Progress=FMath::Clamp(State.RightHand.Progress+State.RightHand.ProgressRate*Age,0.f,1.f);
    State.LeftHand.Progress=FMath::Clamp(State.LeftHand.Progress+State.LeftHand.ProgressRate*Age,0.f,1.f);
    State.MotionProgress=FMath::Clamp(State.MotionProgress+State.MotionProgressRate*FMath::Clamp(Now-State.MotionSampledAt,0.f,.12f),0.f,1.f);
}

void UFPSPlayerBodyComponent::PresentRecentGunShots(float Now)
{
    float* Shots[]={&DisplayState.LastShotAt,&DisplayState.RightHand.LastShotAt,&DisplayState.LeftHand.LastShotAt};
    const bool Changed=ShotWeaponInstance!=DisplayState.WeaponInstance||ShotOffhandInstance!=DisplayState.OffhandInstance;
    if(!bHaveShotPresentation||Changed)
    {
        // First sight establishes a baseline. A later weapon swap clears the
        // old visual kick but keeps the causal stamps: if the new gun's first
        // shot shares that packet, it must still be presented below.
        for(int32 I=0;I<3;++I)
        {
            if(!bHaveShotPresentation)ReceivedShotAt[I]=*Shots[I];
            PresentedShotAt[I]=-100.f;
        }
        ShotWeaponInstance=DisplayState.WeaponInstance;ShotOffhandInstance=DisplayState.OffhandInstance;
        bHaveShotPresentation=true;
    }
    const bool Gun=DisplayState.Family==TEXT("Rifle")||DisplayState.Family==TEXT("Pistol")||DisplayState.bOffhandPistol;
    for(int32 I=0;I<3;++I)
    {
        const float Source=*Shots[I];
        if(Source>ReceivedShotAt[I])
        {
            ReceivedShotAt[I]=Source;
            // Retain a visible onset when network transit exceeds the 130 ms
            // recoil envelope. Only this observer's cosmetic clock is rebased.
            if(Gun&&Source>=0.f&&Now-Source<.6f&&DisplayState.Action!=EFPSBodyAction::Dead)
                PresentedShotAt[I]=Now-FMath::Clamp(Now-Source,0.f,.025f);
        }
        *Shots[I]=PresentedShotAt[I];
    }
}
