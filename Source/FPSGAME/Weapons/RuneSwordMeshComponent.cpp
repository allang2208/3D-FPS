#include "RuneSwordMeshComponent.h"
#include "RuneSwordComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"
#include "WeaponGripProfile.h"
#include "ModularSwordVisual.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "Animation/AnimSequence.h"

namespace
{
void SupportRidgeHighCarry(URuneSwordMeshComponent& Mesh,const TArray<FTransform>& Idle)
{
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    if(Idle.Num()!=Pose.Num())return;
    const int32 SupportHand=Mesh.GetBoneIndex(TEXT("hand_l"));
    if(!Pose.IsValidIndex(SupportHand))return;
    // On this rig +Y is behind the eye. Bring the entire high grip past the
    // right shoulder together. Pulling only the elbow around the camera here
    // made the support wrist fold when the sprint turned into a thrust.
    const double Raise=FMath::SmoothStep(-24.,-2.,Pose[SupportHand].GetLocation().Y);
    const FVector CarryOffset=FVector(8.,16.,0.)*Raise;
    for(FTransform& Bone:Pose)Bone.AddToTranslation(CarryOffset);
    for(const TCHAR* Side:{TEXT("r"),TEXT("l")})
    {
        const auto Bone=[&](const TCHAR* Stem){return Mesh.GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        const int32 M=Bone(TEXT("middle_01")),R=Bone(TEXT("ring_01"));
        if(U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE||M==INDEX_NONE||R==INDEX_NONE)continue;
        const FVector S=Pose[U].GetLocation(),E=Pose[L].GetLocation(),Hand=Pose[H].GetLocation();
        const FVector Fore=(Hand-E).GetSafeNormal();
        const FVector Palm=((Pose[M].GetLocation()+Pose[R].GetLocation())*.5-Hand).GetSafeNormal();
        const double Bend=FMath::Acos(FMath::Clamp(Palm|Fore,-1.,1.));
        const double Limit=FMath::DegreesToRadians(36.);
        // Ease into the limit over a few degrees as the blade rises. Support
        // the raised wrist by bringing its elbow around, keeping the fist fixed.
        const double Weight=FMath::SmoothStep(0.,FMath::DegreesToRadians(20.),Bend-Limit);
        FVector NewFore=Fore;
        if(Weight>0.)
        {
            const FVector Across=(Fore-Palm*(Palm|Fore)).GetSafeNormal();
            if(!Across.IsNearlyZero())
            {
                const double SupportedBend=FMath::Lerp(Bend,Limit,Weight);
                NewFore=Palm*FMath::Cos(SupportedBend)+Across*FMath::Sin(SupportedBend);
            }
        }
        const FVector NewE=Hand-NewFore*(Hand-E).Size();
        const FVector NewUpper=(NewE-S).GetSafeNormal(),NewS=NewE-NewUpper*(E-S).Size();
        const FQuat PalmTurn=Pose[H].GetRotation()*Idle[H].GetRotation().Inverse();
        const FVector IdleFore=(Idle[H].GetLocation()-Idle[L].GetLocation()).GetSafeNormal();
        const FVector IdleUpper=(Idle[L].GetLocation()-Idle[U].GetLocation()).GetSafeNormal();
        const FQuat SupportedFore=FQuat::FindBetweenNormals(PalmTurn.RotateVector(IdleFore),NewFore)*PalmTurn;
        const FQuat SupportedUpper=FQuat::FindBetweenNormals(SupportedFore.RotateVector(IdleUpper),NewUpper)*SupportedFore;
        // The sprint asset carries an independent axial roll on its forearm
        // keys. Use a single rest frame through raise, loop and lower; mixing
        // the authored roll back in halfway can swap the quaternion arc.
        const auto Place=[&](int32 I,const FVector& To,const FQuat& Support,const FVector& IdleOrigin)
        {
            if(I==INDEX_NONE)return;
            Pose[I].SetLocation(To+Support.RotateVector(Idle[I].GetLocation()-IdleOrigin));
            Pose[I].SetRotation((Support*Idle[I].GetRotation()).GetNormalized());
        };
        for(int32 I:{Bone(TEXT("clavicle")),U,Bone(TEXT("upperarm_twist_01")),Bone(TEXT("upperarm_twist_02"))})
            Place(I,NewS,SupportedUpper,Idle[U].GetLocation());
        for(int32 I:{L,Bone(TEXT("lowerarm_twist_02")),Bone(TEXT("lowerarm_twist_01"))})
            Place(I,NewE,SupportedFore,Idle[L].GetLocation());
    }
}

void RaiseQuickCombatWindup(URuneSwordMeshComponent& Mesh)
{
    using namespace RuneSwordPommelRhythm;
    // Read the sampled animation clock, not the component's previous-frame
    // elapsed time. The 0.20 s windup and the contact pose stay in sync.
    const float Time=Mesh.GetPosition();
    const float Weight=Time<=ContactStart
        ? RecoveryEase((Time-TurnEnd*.5f)/(RaiseEnd-TurnEnd*.5f))
        : 1.f-RecoveryEase((Time-ContactStart)/(ExtensionEnd-ContactStart));
    if(Weight<=0.f)return;
    const int32 Weapon=Mesh.GetBoneIndex(TEXT("WPN_root"));
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    if(!Asset||Weapon==INDEX_NONE)return;
    const auto& Ref=Asset->GetRefSkeleton();
    auto& Pose=Mesh.GetEditableComponentSpaceTransforms();
    const TArray<FTransform> Source=Pose;
    // The mesh has only a yaw mounting rotation: local +Z is camera-up.
    // Lift the actual grip group by 10 cm, retaining both hands' grip frames.
    const FVector Lift(0.,0.,10.*Weight);
    for(int32 I=0;I<Pose.Num();++I)
        if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))Pose[I].AddToTranslation(Lift);
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const auto Bone=[&](const TCHAR* Stem){return Mesh.GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 C=Bone(TEXT("clavicle")),U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
        const FVector OldA=Source[U].GetLocation(),OldE=Source[L].GetLocation(),OldH=Source[H].GetLocation();
        const FVector Target=OldH+Lift;
        const double UpperLength=(OldE-OldA).Size(),LowerLength=(OldH-OldE).Size();
        // A small shoulder rise supports the higher grip; retain some elbow
        // bend even at maximum reach rather than stretching either bone.
        FVector ShoulderShift=Lift*.16;
        const FVector Reach=Target-OldA-ShoulderShift;
        ShoulderShift+=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-(UpperLength+LowerLength)*.98);
        const FVector A=OldA+ShoulderShift;
        FVector E,Hand;
        AnimationCore::SolveTwoBoneIK(A,OldE+ShoulderShift,OldH+ShoulderShift,
            OldE+Lift*.5,Target,E,Hand,UpperLength,LowerLength,false,1.,1.);
        const FQuat LowerDelta=FQuat::FindBetweenNormals((OldH-OldE).GetSafeNormal(),(Hand-E).GetSafeNormal());
        // Transport the forearm frame through the upper arm too. Independent
        // shortest-swing rotations can concentrate an axial twist at the elbow.
        const FQuat UpperDelta=FQuat::FindBetweenNormals(
            LowerDelta.RotateVector((OldE-OldA).GetSafeNormal()),(E-A).GetSafeNormal())*LowerDelta;
        FTransform Upper=Source[U],Lower=Source[L],Wrist=Source[H];
        Upper.SetLocation(A);Upper.SetRotation((UpperDelta*Upper.GetRotation()).GetNormalized());
        Lower.SetLocation(E);Lower.SetRotation((LowerDelta*Lower.GetRotation()).GetNormalized());
        Wrist.SetLocation(Hand);
        for(int32 I=C;I<Pose.Num();++I)
        {
            // WPN_root and modular attachments already moved with the grip.
            if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))continue;
            if(I==C)Pose[I].AddToTranslation(ShoulderShift);
            else if(I==U)Pose[I]=Upper;
            else if(I==L)Pose[I]=Lower;
            else if(I==H)Pose[I]=Wrist;
            else if(Ref.BoneIsChildOf(I,C))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Source[I].GetRelativeTransform(Source[Parent])*Pose[Parent];
            }
        }
    }
}
}

void URuneSwordMeshComponent::CaptureWhirlwindEntry()
{
    EntryMesh=GetSkeletalMeshAsset();
    EntryPose=GetComponentSpaceTransforms();
    EntryTime=0.f;EntryDuration=EntrySeconds;
    bEntryShaftGrip=false;
    bEntryFromWrists=false;EntryTargetPose.Reset();
}

void URuneSwordMeshComponent::SetWhirlwindEntryTime(float Seconds)
{
    EntryTime=FMath::Max(0.f,Seconds);
    if(EntryTime>=EntryDuration)ClearWhirlwindEntry();
}

void URuneSwordMeshComponent::ClearWhirlwindEntry()
{
    EntryPose.Reset();EntryTargetPose.Reset();EntryMesh.Reset();EntryTime=0.f;
}

void URuneSwordMeshComponent::CaptureLocomotionEntry(float Seconds,bool bPreserveShaftGrip,bool bFromWrists)
{
    // Share the grip-constrained solver across locomotion and action handoffs.
    CaptureWhirlwindEntry();
    EntryDuration=FMath::Max(.001f,Seconds);
    bEntryShaftGrip=bPreserveShaftGrip;
    bEntryFromWrists=bFromWrists;
}

void URuneSwordMeshComponent::LimitLocomotionEntry(float Seconds)
{
    // A resumed windup can have less than 100 ms before contact. Finish the
    // visual handoff within that time so sweeps use the authored strike pose.
    EntryDuration=FMath::Min(EntryDuration,FMath::Max(0.f,Seconds));
    if(EntryTime>=EntryDuration)ClearWhirlwindEntry();
}

void URuneSwordMeshComponent::AdvanceLocomotionEntry(float Delta)
{
    if(!EntryPose.IsEmpty())SetWhirlwindEntryTime(EntryTime+FMath::Max(0.f,Delta));
}

void URuneSwordMeshComponent::FinalizeBoneTransform()
{
    if(auto* Single=GetSingleNodeInstance())
    {
        GripLayer.Apply(GripProfile,Cast<UAnimSequence>(Single->GetCurrentAsset()),GetPosition(),*this);
        if(bRefreshGripIdle&&Single->GetCurrentAsset()&&Single->GetCurrentAsset()->GetName().EndsWith(TEXT("_Idle")))
        {bCaptureRecoveryIdle=true;bRefreshGripIdle=false;}
    }
    if(bCaptureRecoveryIdle)GripClearance.CaptureIdle(*this);
    const auto* Sword=GetOwner()?GetOwner()->FindComponentByClass<URuneSwordComponent>():nullptr;
    GripClearance.Apply(*this,Sword?Sword->GripMode():ESwordGripMode::Adaptive);
    if(bCaptureRecoveryIdle)
    {
        // Capture the sampled idle before any action/casting overlay is applied.
        RecoveryMesh=GetSkeletalMeshAsset();
        RecoveryIdlePose=GetEditableComponentSpaceTransforms();
        bCaptureRecoveryIdle=false;
    }
    if(Sword&&Sword->UsesRidgeSprintCarry()&&RecoveryMesh.Get()==GetSkeletalMeshAsset())
        SupportRidgeHighCarry(*this,RecoveryIdlePose);
    // Build the raised target before entry blending so the entering frame
    // still matches the currently displayed pose. Ordinary combo #4 shares
    // this animation but does not receive the quick-combat-only lift.
    if(Sword&&Sword->IsQuickCombatActive())RaiseQuickCombatWindup(*this);
    if(!EntryPose.IsEmpty())ApplyWhirlwindEntry();
    if(RecoveryWeight>0.f)ApplyQuickCombatRecovery();
    Super::FinalizeBoneTransform();
}

void URuneSwordMeshComponent::SetGripClearance(const FColdSteelItem* Item)
{
    if(!Item)
    {
        GripFitDefinition.Reset();GripFitData.Reset();GripClearance.Configure({});return;
    }
    if(GripFitDefinition==Item->Definition&&GripFitData==Item->Data)return;
    GripFitDefinition=Item->Definition;GripFitData=Item->Data;
    if(GripClearance.Configure(ColdSteelModularSword::GripClearance(*Item)))
    {RecoveryMesh.Reset();RecoveryIdlePose.Reset();bRefreshGripIdle=true;}
}

void URuneSwordMeshComponent::CacheQuickCombatIdlePose()
{
    // Equipment changes request a capture on the next idle evaluation.
    RecoveryMesh.Reset();
    RecoveryIdlePose.Reset();
    RecoveryWeight=0.f;
    bCaptureRecoveryIdle=true;
}

void URuneSwordMeshComponent::SetQuickCombatRecoveryWeight(float Weight)
{
    RecoveryWeight=FMath::Clamp(Weight,0.f,1.f);
}

void URuneSwordMeshComponent::ApplyQuickCombatRecovery()
{
    auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(!Mesh||RecoveryMesh.Get()!=Mesh||RecoveryIdlePose.Num()!=Pose.Num())return;
    if(RecoveryWeight>=1.f){Pose=RecoveryIdlePose;return;}
    const TArray<FTransform> Incoming=Pose;
    BlendSupportedPoses(Incoming,RecoveryIdlePose,RecoveryWeight,true);
}

void URuneSwordMeshComponent::ApplyWhirlwindEntry()
{
    auto* Mesh=GetSkeletalMeshAsset();
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(!Mesh||EntryMesh.Get()!=Mesh||EntryPose.Num()!=Pose.Num())
    {ClearWhirlwindEntry();return;}
    if(bEntryFromWrists&&EntryTargetPose.IsEmpty())EntryTargetPose=Pose;
    // The first sample must keep exactly the pose the player was already seeing.
    if(EntryTime<=0.f){Pose=EntryPose;return;}
    const float T=FMath::Clamp(EntryTime/EntryDuration,0.f,1.f);
    const float Alpha=T*T*T*(T*(T*6.f-15.f)+10.f);
    if(bEntryFromWrists){BlendRidgeEntry(Alpha);return;}
    const TArray<FTransform> Incoming=Pose;
    BlendSupportedPoses(EntryPose,Incoming,Alpha,bEntryShaftGrip,bEntryShaftGrip);
}

void URuneSwordMeshComponent::BlendRidgeEntry(float Alpha)
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const TArray<FTransform> Target=Pose;
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    const int32 Weapon=GetBoneIndex(TEXT("WPN_root"));
    if(!Pose.IsValidIndex(Weapon))return;
    // Decay the fixed rotation difference measured at the start. Picking a
    // fresh shortest arc to a moving target can change sides at 180 degrees.
    const auto Blend=[&](const FTransform& From,const FTransform& First,const FTransform& To)
    {
        const FQuat Delta=From.GetRotation()*First.GetRotation().Inverse();
        const FQuat Rotation=FQuat::Slerp(FQuat::Identity,Delta,1.f-Alpha)*To.GetRotation();
        return FTransform(Rotation.GetNormalized(),FMath::Lerp(From.GetLocation(),To.GetLocation(),double(Alpha)),
            FMath::Lerp(From.GetScale3D(),To.GetScale3D(),double(Alpha)));
    };
    const auto Relative=[&](int32 Bone,int32 Anchor)
    {
        return Blend(EntryPose[Bone].GetRelativeTransform(EntryPose[Anchor]),
            EntryTargetPose[Bone].GetRelativeTransform(EntryTargetPose[Anchor]),
            Target[Bone].GetRelativeTransform(Target[Anchor]));
    };
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        Pose[I]=(I==Weapon||Parent==INDEX_NONE)?Blend(EntryPose[I],EntryTargetPose[I],Target[I]):
            Relative(I,Parent)*Pose[Parent];
    }
    for(const TCHAR* Side:{TEXT("r"),TEXT("l")})
    {
        const auto Bone=[&](const TCHAR* Stem){return GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 C=Bone(TEXT("clavicle")),U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
        FTransform Grip=Relative(H,Weapon);
        const auto GripPoint=[&](const TArray<FTransform>& Frame)
        {return Frame[H].GetRelativeTransform(Frame[Weapon]).GetLocation();};
        const FVector A=GripPoint(EntryPose),B=GripPoint(EntryTargetPose),D=GripPoint(Target);
        const double Offset=FMath::FindDeltaAngleRadians(FMath::Atan2(B.Y,B.X),FMath::Atan2(A.Y,A.X));
        const double Angle=FMath::Atan2(D.Y,D.X)+(1.-Alpha)*Offset;
        const double Radius=FMath::Lerp(A.Size2D(),D.Size2D(),double(Alpha));
        Grip.SetLocation(FVector(Radius*FMath::Cos(Angle),Radius*FMath::Sin(Angle),FMath::Lerp(A.Z,D.Z,double(Alpha))));
        Pose[H]=Grip*Pose[Weapon];
        // Build the chain backwards from the supported wrist. Each shaft keeps
        // its length and its native direction in bone space, even when a source
        // guard and the chamber have opposing elbow planes.
        const auto PlaceShaft=[&](int32 Shaft,int32 Tip)
        {
            const FQuat Q=Pose[Tip].GetRotation()*Relative(Shaft,Tip).GetRotation();
            const FVector Old=EntryPose[Tip].GetLocation()-EntryPose[Shaft].GetLocation();
            const FVector New=Target[Tip].GetLocation()-Target[Shaft].GetLocation();
            const FVector Axis=FMath::Lerp(EntryPose[Shaft].GetRotation().UnrotateVector(Old.GetSafeNormal()),
                Target[Shaft].GetRotation().UnrotateVector(New.GetSafeNormal()),double(Alpha)).GetSafeNormal();
            Pose[Shaft].SetRotation(Q.GetNormalized());
            Pose[Shaft].SetLocation(Pose[Tip].GetLocation()-Q.RotateVector(Axis)*FMath::Lerp(Old.Size(),New.Size(),double(Alpha)));
        };
        PlaceShaft(L,H);
        PlaceShaft(U,L);
        // A hand-relative upper arm can swing the cut shoulder into the camera
        // when leaving a wide guard. Seat it towards the two actual shoulders.
        const FVector Elbow=Pose[L].GetLocation();
        const FVector Upper=Elbow-Pose[U].GetLocation();
        const FVector Shoulder=FMath::Lerp(EntryPose[U].GetLocation(),Target[U].GetLocation(),double(Alpha));
        const FVector ToElbow=(Elbow-Shoulder).GetSafeNormal();
        const FQuat ShoulderSwing=FQuat::FindBetweenNormals(Upper.GetSafeNormal(),ToElbow);
        Pose[U].SetLocation(Elbow-ToElbow*Upper.Size());
        Pose[U].SetRotation((ShoulderSwing*Pose[U].GetRotation()).GetNormalized());
        Pose[C]=Relative(C,U)*Pose[U];
        for(int32 I=C+1;I<Pose.Num();++I)
            if(I!=U&&I!=L&&I!=H&&I!=Weapon&&!Ref.BoneIsChildOf(I,Weapon)&&Ref.BoneIsChildOf(I,C))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Relative(I,Parent)*Pose[Parent];
            }
    }
}

void URuneSwordMeshComponent::BlendSupportedPoses(const TArray<FTransform>& From,
    const TArray<FTransform>& To,float Alpha,bool bPreserveBoneLengths,bool bPreserveShaftGrip)
{
    auto& Pose=GetEditableComponentSpaceTransforms();
    const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
    // Blend in parent space so the upper arm and forearm do not shorten along
    // the interpolation chord. The WPN_root uses this same blend and clock.
    for(int32 I=0;I<Pose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        const FTransform A=Parent==INDEX_NONE?From[I]:From[I].GetRelativeTransform(From[Parent]);
        const FTransform B=Parent==INDEX_NONE?To[I]:To[I].GetRelativeTransform(To[Parent]);
        FTransform Local;Local.Blend(A,B,Alpha);
        Pose[I]=Parent==INDEX_NONE?Local:Local*Pose[Parent];
    }
    const int32 Weapon=GetBoneIndex(TEXT("WPN_root"));
    if(Weapon==INDEX_NONE)return;
    const TArray<FTransform> Blended=Pose;
    for(const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const auto Bone=[&](const TCHAR* Stem){return GetBoneIndex(FName(*(FString(Stem)+TEXT("_")+Side)));};
        const int32 C=Bone(TEXT("clavicle")),U=Bone(TEXT("upperarm")),L=Bone(TEXT("lowerarm")),H=Bone(TEXT("hand"));
        if(C==INDEX_NONE||U==INDEX_NONE||L==INDEX_NONE||H==INDEX_NONE)continue;
        FTransform Grip;
        Grip.Blend(From[H].GetRelativeTransform(From[Weapon]),
            To[H].GetRelativeTransform(To[Weapon]),Alpha);
        if(bPreserveShaftGrip)
        {
            // Warhammer WPN local Z follows the shaft. A straight translation
            // lerp would cut the palms through it when wrapping to the next cut.
            const FVector A=From[H].GetRelativeTransform(From[Weapon]).GetLocation();
            const FVector B=To[H].GetRelativeTransform(To[Weapon]).GetLocation();
            const double Start=FMath::Atan2(A.Y,A.X);
            const double Angle=Start+FMath::FindDeltaAngleRadians(Start,FMath::Atan2(B.Y,B.X))*Alpha;
            const double Radius=FMath::Lerp(A.Size2D(),B.Size2D(),double(Alpha));
            Grip.SetLocation(FVector(Radius*FMath::Cos(Angle),Radius*FMath::Sin(Angle),FMath::Lerp(A.Z,B.Z,double(Alpha))));
        }
        const FTransform Target=Grip*Pose[Weapon];
        const FVector OldA=Blended[U].GetLocation(),OldE=Blended[L].GetLocation(),OldH=Blended[H].GetLocation();
        // Recovery must not shorten the arm to meet an interpolated wrist.
        // Read lengths from the two source poses, before blending positions.
        const double UpperLength=bPreserveBoneLengths
            ? FMath::Lerp((From[L].GetLocation()-From[U].GetLocation()).Size(),
                (To[L].GetLocation()-To[U].GetLocation()).Size(),double(Alpha)):(OldE-OldA).Size();
        const double LowerLength=bPreserveBoneLengths
            ? FMath::Lerp((From[H].GetLocation()-From[L].GetLocation()).Size(),
                (To[H].GetLocation()-To[L].GetLocation()).Size(),double(Alpha)):(OldH-OldE).Size();
        const FVector Reach=Target.GetLocation()-OldA;
        const double SupportedReach=FMath::Max(0.,UpperLength+LowerLength-.01);
        const FVector ShoulderShift=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-SupportedReach);
        const FVector A=OldA+ShoulderShift;
        FVector E,Hand;
        AnimationCore::SolveTwoBoneIK(A,OldE+ShoulderShift,OldH+ShoulderShift,
            OldE+ShoulderShift,Target.GetLocation(),E,Hand,UpperLength,LowerLength,false,1.,1.);
        FTransform Upper=Blended[U],Lower=Blended[L],Wrist=Blended[H];
        const FQuat LowerTurn=FQuat::FindBetweenNormals((OldH-OldE).GetSafeNormal(),(Hand-E).GetSafeNormal());
        const FQuat UpperTurn=bPreserveShaftGrip?
            FQuat::FindBetweenNormals(LowerTurn.RotateVector((OldE-OldA).GetSafeNormal()),(E-A).GetSafeNormal())*LowerTurn:
            FQuat::FindBetweenNormals((OldE-OldA).GetSafeNormal(),(E-A).GetSafeNormal());
        Upper.SetLocation(A);
        Upper.SetRotation((UpperTurn*Upper.GetRotation()).GetNormalized());
        Lower.SetLocation(E);
        Lower.SetRotation((LowerTurn*Lower.GetRotation()).GetNormalized());
        Wrist.SetLocation(Hand);Wrist.SetRotation(Target.GetRotation());
        // Rebuild helpers and fingers from their blended local transforms.
        // Both wrists follow the shared weapon grip, not independent lerps.
        for(int32 I=C;I<Pose.Num();++I)
        {
            // The weapon is the constraint driver even on rigs parenting it
            // under a hand. Do not carry it a second time with that arm's IK.
            if(I==Weapon||Ref.BoneIsChildOf(I,Weapon))continue;
            if(I==C)Pose[I].AddToTranslation(ShoulderShift);
            else if(I==U)Pose[I]=Upper;
            else if(I==L)Pose[I]=Lower;
            else if(I==H)Pose[I]=Wrist;
            else if(Ref.BoneIsChildOf(I,C))
            {
                const int32 Parent=Ref.GetParentIndex(I);
                Pose[I]=Blended[I].GetRelativeTransform(Blended[Parent])*Pose[Parent];
            }
        }
    }
}
