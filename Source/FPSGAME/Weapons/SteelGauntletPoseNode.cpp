#include "SteelGauntletPoseNode.h"
#include "FPSGunplayAnimInstance.h"
#include "WeaponGripProfile.h"
#include "../Characters/FPSModularOutfitComponent.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "GameFramework/Actor.h"
#include "UObject/Package.h"

struct FSteelGauntletKey
{
    float Time;
    FQuat Rotation[6];
    FVector HandOffset=FVector::ZeroVector;
};
struct FSteelGauntletClip
{
    const TCHAR* Package;
    int32 Count;
    const FSteelGauntletKey* Keys;
};

// Generated offline from native animation poses and the final armor geometry.
// Compiled curves avoid disk reads, UObject loads and collision queries in PreUpdate.
#include "SteelGauntletPoseCurves.inl"

namespace SteelGauntletPose
{
void Sample(const FSteelGauntletClip* Clip, float Time, FQuat (&Result)[6], FVector& HandOffset)
{
    for (FQuat& Rotation : Result) Rotation=FQuat::Identity;
    HandOffset=FVector::ZeroVector;
    if (!Clip || Clip->Count==0) return;
    int32 Lower=0, Upper=Clip->Count-1;
    while (Upper-Lower>1)
    {
        const int32 Middle=(Lower+Upper)/2;
        if (Clip->Keys[Middle].Time<=Time) Lower=Middle; else Upper=Middle;
    }
    const auto& A=Clip->Keys[Lower];
    const auto& B=Clip->Keys[Upper];
    const float Alpha=B.Time>A.Time ? FMath::Clamp((Time-A.Time)/(B.Time-A.Time),0.f,1.f) : 0.f;
    for (int32 I=0;I<6;++I) Result[I]=FQuat::Slerp(A.Rotation[I],B.Rotation[I],Alpha).GetNormalized();
    HandOffset=FMath::Lerp(A.HandOffset,B.HandOffset,Alpha);
}
FTransform ComponentPose(const FCompactPose& Pose,FCompactPoseBoneIndex Index)
{
    FTransform Result=Pose[Index];
    for (auto Parent=Pose.GetParentBoneIndex(Index);Parent.GetInt()!=INDEX_NONE;Parent=Pose.GetParentBoneIndex(Parent))
        Result=Result*Pose[Parent];
    return Result;
}
}

FSteelGauntletPoseNode::FSteelGauntletPoseNode()
{
    static const FName Names[]={TEXT("pinky_01_r"),TEXT("pinky_02_r"),TEXT("pinky_03_r"),
        TEXT("pinky_01_l"),TEXT("pinky_02_l"),TEXT("pinky_03_l")};
    for (int32 I=0;I<6;++I) { Fingers[I].BoneName=Names[I];Corrections[I]=FQuat::Identity; }
    SupportHand.BoneName=TEXT("hand_l");
}

const FSteelGauntletClip* FSteelGauntletPoseNode::ResolveClip(int32 Slot,UAnimSequence* Sequence)
{
    if (!Sequence) { Sequences[Slot]=nullptr;Clips[Slot]=nullptr;return nullptr; }
    if (Sequences[Slot].Get()==Sequence) return Clips[Slot];
    Sequences[Slot]=Sequence;Clips[Slot]=nullptr;
    if (Sequence)
    {
        const FString Package=Sequence->GetOutermost()->GetName();
        for (const auto& Clip : GSteelGauntletClips)
            if (Package==Clip.Package) { Clips[Slot]=&Clip;break; }
    }
    return Clips[Slot];
}

void FSteelGauntletPoseNode::Configure(const UFPSGunplayAnimInstance& Instance)
{
    // The proxy is recreated with its owning mesh/anim instance. Resolve once on
    // the game thread, then read only the current glove slot each update.
    if (!bOwnerResolved)
    {
        if (AActor* Owner=Instance.GetOwningActor())
            Outfit=Owner->FindComponentByClass<UFPSModularOutfitComponent>();
        bOwnerResolved=true;
    }
    const auto* Equipment=Outfit.Get();
    bEnabled=Equipment && Equipment->IsSteelGauntletEquipped();
    if (!bEnabled) return;
    UAnimSequence* Idle=Instance.IdleClip.Get();
    UAnimSequence* Aim=Instance.AimClip ? Instance.AimClip.Get() : Idle;
    const float IdleTime=Idle && Idle->GetPlayLength()>SMALL_NUMBER ? FMath::Fmod(Instance.BaseTime,Idle->GetPlayLength()) : 0.f;
    // RSH shares the 715 sequences, but its private grip already fits both hands
    // with this glove shell. The donor's support offset would separate them.
    static const FName RSHBase(TEXT("DA_RSH12_base")), RSHVertical(TEXT("DA_RSH12_vertical")),
        RSHCanted(TEXT("DA_RSH12_canted")), RSHPrism(TEXT("DA_RSH12_prism")), RSHAngled(TEXT("DA_RSH12_angled"));
    const FName ProfileName=Instance.GripProfile?Instance.GripProfile->GetFName():NAME_None;
    const bool bRSHForegrip=ProfileName==RSHVertical||ProfileName==RSHCanted||ProfileName==RSHPrism||ProfileName==RSHAngled;
    const bool bFittedRSHGrip=ProfileName==RSHBase||bRSHForegrip;
    FQuat IdlePose[6], AimPose[6], ActionPose[6];
    FVector IdleOffset,AimOffset,ActionOffset;
    SteelGauntletPose::Sample(bFittedRSHGrip?nullptr:ResolveClip(0,Idle),IdleTime,IdlePose,IdleOffset);
    SteelGauntletPose::Sample(bFittedRSHGrip?nullptr:ResolveClip(1,Aim),Aim==Idle?IdleTime:0.f,AimPose,AimOffset);
    const auto* Action=ResolveClip(2,Instance.ActionClip.Get());
    SteelGauntletPose::Sample(Action,Instance.ActionTime,ActionPose,ActionOffset);
    if(bRSHForegrip)
    {
        // Keep the firing hand's accepted glove corrections; only the support
        // hand is owned by the new foregrip contact/release layer.
        for(int32 I=3;I<6;++I)ActionPose[I]=FQuat::Identity;
        ActionOffset=FVector::ZeroVector;
    }
    const float Sprint=Instance.SprintClip ? FMath::Clamp(Instance.SprintAlpha,0.f,1.f) : 0.f;
    const float AimAlpha=FMath::Clamp(Instance.AimAlpha,0.f,1.f);
    const float ActionAlpha=Instance.ActionClip && Action ? FMath::Clamp(Instance.ActionAlpha,0.f,1.f) : 0.f;
    for (int32 I=0;I<6;++I)
    {
        const FQuat Base=FQuat::Slerp(IdlePose[I],FQuat::Identity,Sprint);
        const FQuat Aimed=FQuat::Slerp(Base,AimPose[I],AimAlpha);
        Corrections[I]=FQuat::Slerp(Aimed,ActionPose[I],ActionAlpha).GetNormalized();
    }
    SupportClearance=FMath::Lerp(FMath::Lerp(IdleOffset*(1.f-Sprint),AimOffset,AimAlpha),ActionOffset,ActionAlpha);
}

void FSteelGauntletPoseNode::Initialize_AnyThread(const FAnimationInitializeContext& Context)
{ Source.Initialize(Context); }
void FSteelGauntletPoseNode::CacheBones_AnyThread(const FAnimationCacheBonesContext& Context)
{
    Source.CacheBones(Context);
    const auto& Bones=Context.AnimInstanceProxy->GetRequiredBones();
    for (auto& Finger : Fingers)
        if (Bones.GetReferenceSkeleton().FindBoneIndex(Finger.BoneName)!=INDEX_NONE) Finger.Initialize(Bones);
    if (Bones.GetReferenceSkeleton().FindBoneIndex(SupportHand.BoneName)!=INDEX_NONE) SupportHand.Initialize(Bones);
}
void FSteelGauntletPoseNode::Update_AnyThread(const FAnimationUpdateContext& Context)
{ Source.Update(Context); }
void FSteelGauntletPoseNode::Evaluate_AnyThread(FPoseContext& Output)
{
    Source.Evaluate(Output);
    if (!bEnabled) return;
    const auto& Bones=Output.Pose.GetBoneContainer();
    if (!SupportClearance.IsNearlyZero() && SupportHand.IsValidToEvaluate(Bones))
    {
        const auto Index=SupportHand.GetCompactPoseIndex(Bones);
        const auto Parent=Output.Pose.GetParentBoneIndex(Index);
        if (Parent.GetInt()!=INDEX_NONE)
        {
            const FTransform Hand=SteelGauntletPose::ComponentPose(Output.Pose,Index);
            const FTransform ParentPose=SteelGauntletPose::ComponentPose(Output.Pose,Parent);
            // Authoring offsets are centimetres in the posed hand frame. The
            // native rigs include different root scales; invert the parent
            // transform instead of treating centimetres as local bone units.
            Output.Pose[Index].AddToTranslation(ParentPose.InverseTransformVector(Hand.GetRotation().RotateVector(SupportClearance)));
        }
    }
    for (int32 I=0;I<6;++I)
    {
        if (!Fingers[I].IsValidToEvaluate(Bones)) continue;
        FTransform& Local=Output.Pose[Fingers[I].GetCompactPoseIndex(Bones)];
        Local.SetRotation((Local.GetRotation()*Corrections[I]).GetNormalized());
    }
}
