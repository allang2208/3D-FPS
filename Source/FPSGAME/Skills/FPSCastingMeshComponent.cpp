#include "FPSCastingMeshComponent.h"
#include "FPSFireballComponent.h"
#include "QuickCombatPistolMotion.h"
#include "QuickCombatRifleMotion.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "TwoBoneIK.h"

namespace
{
FQuat LimbFrame(const FVector& Direction,const FVector& Plane)
{ return FRotationMatrix::MakeFromXZ(Direction,Plane).ToQuat(); }
}

void UFPSCastingMeshComponent::CacheCastSkeleton()
{
    PoseMesh=GetSkeletalMeshAsset();ReferencePose.Reset();LeftBones.Reset();EntryLocal.Reset();EntrySerial=0;
    BashHandR=GetBoneIndex(TEXT("hand_r"));   // 打击探针（命中射线起点）用的握把手骨
    CastClavicleIndex=GetBoneIndex(TEXT("clavicle_l"));CastUpperIndex=GetBoneIndex(TEXT("upperarm_l"));CastLowerIndex=GetBoneIndex(TEXT("lowerarm_l"));CastHandIndex=GetBoneIndex(TEXT("hand_l"));
    if(!PoseMesh.IsValid() || CastClavicleIndex==INDEX_NONE || CastUpperIndex==INDEX_NONE || CastLowerIndex==INDEX_NONE || CastHandIndex==INDEX_NONE)return;
    const auto& Ref=PoseMesh->GetRefSkeleton();ReferencePose=Ref.GetRefBonePose();
    for(int32 I=0;I<ReferencePose.Num();++I)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        if(Parent>=0)ReferencePose[I]=ReferencePose[I]*ReferencePose[Parent];
        if((I==CastClavicleIndex || Ref.BoneIsChildOf(I,CastClavicleIndex)) && Ref.GetBoneName(I).ToString().EndsWith(TEXT("_l")))LeftBones.Add(I);
    }
    const int32 Index=GetBoneIndex(TEXT("index_01_l")),Middle=GetBoneIndex(TEXT("middle_01_l")),Pinky=GetBoneIndex(TEXT("pinky_01_l"));
    if(Index==INDEX_NONE || Middle==INDEX_NONE || Pinky==INDEX_NONE){LeftBones.Reset();return;}
    const FVector Origin=ReferencePose[CastHandIndex].GetLocation();
    const FVector Forward=ReferencePose[Middle].GetLocation()-Origin;
    // UE coordinates: index-to-pinky winding points out of the left palm.
    const FVector Normal=(ReferencePose[Index].GetLocation()-Origin)^(ReferencePose[Pinky].GetLocation()-Origin);
    ReferencePalm=FRotationMatrix::MakeFromXZ(Forward,Normal).ToQuat();
}

void UFPSCastingMeshComponent::FinalizeBoneTransform()
{
    auto* Magic=bApplyLeftHandCast&&GetOwner()?GetOwner()->FindComponentByClass<UFPSFireballComponent>():nullptr;
    const bool bCastActive=Magic&&Magic->IsOccupyingLeftHand();
    bool bApplied=false;
    if(bCastActive&&IsVisible()&&!bHiddenInGame){ApplyCastPose(Magic);bApplied=true;}
    // 火球施法结束（不再占用左手）时清入场快照，下一次施法重新捕获。
    if(!bCastActive){EntrySerial=0;EntryLocal.Reset();}
    Super::FinalizeBoneTransform();
}

void UFPSCastingMeshComponent::ApplyCastPose(UFPSFireballComponent* Magic)
{
    if(PoseMesh.Get()!=GetSkeletalMeshAsset())CacheCastSkeleton();
    if(LeftBones.IsEmpty())return;
    auto& Pose=GetEditableComponentSpaceTransforms();
    if(Pose.Num()!=ReferencePose.Num())return;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();if(!Camera)return;
    const auto& Ref=PoseMesh->GetRefSkeleton();
    const FTransform MeshWorld=GetComponentTransform(),CameraWorld=Camera->GetComponentTransform();
    const auto ToCamera=[&](const FTransform& Bone){return (Bone*MeshWorld).GetRelativeTransform(CameraWorld);};
    const auto ToMesh=[&](const FVector& Point){return MeshWorld.InverseTransformPosition(CameraWorld.TransformPosition(Point));};
    const FQuat CameraToMesh=MeshWorld.GetRotation().Inverse()*CameraWorld.GetRotation();
    SourcePose=Pose;
    if(EntrySerial!=Magic->GetCastSerial() || EntryLocal.Num()!=Pose.Num())
    {
        EntrySerial=Magic->GetCastSerial();EntryLocal=SourcePose;
        for(int32 I:LeftBones)EntryLocal[I]=SourcePose[I].GetRelativeTransform(SourcePose[Ref.GetParentIndex(I)]);
        Magic->CaptureHandEntry(ToCamera(SourcePose[CastHandIndex]),ToCamera(SourcePose[CastClavicleIndex]),ToCamera(SourcePose[CastUpperIndex]).GetLocation(),ToCamera(SourcePose[CastLowerIndex]).GetLocation());
    }
    const auto& Settings=Magic->HandPose();
    const auto Phase=Magic->GetHandPhase();const float T=Magic->HandPhaseFraction();
    // Bone orientation is reconstructed from palm semantics for each loaded rig.
    const FQuat HandCorrection=ReferencePalm.Inverse()*ReferencePose[CastHandIndex].GetRotation();
    const FTransform CurrentHand=ToCamera(SourcePose[CastHandIndex]);
    const FVector EntryShoulder=Magic->HandEntryShoulder();
    FFireballArmMotion Current;
    Current.Wrist=CurrentHand.GetLocation();Current.Rotation=CurrentHand.GetRotation();
    Current.Shoulder=ToCamera(SourcePose[CastUpperIndex]).GetLocation();Current.Pole=ToCamera(SourcePose[CastLowerIndex]).GetLocation();
    const FFireballArmMotion Motion=Magic->SampleHandMotion(HandCorrection,Current);
    const FVector Wrist=Motion.Wrist,Shoulder=Motion.Shoulder,Pole=Motion.Pole;
    const FQuat HandRotation=Motion.Rotation;
    const float Release=Motion.Palm;
    FVector A=ToMesh(Shoulder);
    const FVector Target=ToMesh(Wrist);
    const FVector RefA=ReferencePose[CastUpperIndex].GetLocation(),RefE=ReferencePose[CastLowerIndex].GetLocation(),RefH=ReferencePose[CastHandIndex].GetLocation();
    const FVector RU=RefE-RefA,RL=RefH-RefE;
    // Translate the shoulder girdle towards an out-of-reach target instead of
    // locking/lengthening the arm. Keep elbow bend on each equipped skeleton.
    const FVector Reach=Target-A;
    const float SupportedReach=(RU.Size()+RL.Size())*.93f;
    if(Reach.Size()>SupportedReach)A+=Reach.GetSafeNormal()*(Reach.Size()-SupportedReach);
    FVector E,H;
    // Constant bone lengths: the elbow follows an outward/downward pole; no scale/stretch.
    AnimationCore::SolveTwoBoneIK(A,A+RU,A+RU+RL,ToMesh(Pole),Target,E,H,RU.Size(),RL.Size(),false,1.,1.);
    const FVector UD=(E-A).GetSafeNormal(),LD=(H-E).GetSafeNormal();
    FVector Plane=(UD^LD).GetSafeNormal();
    if(Plane.IsNearlyZero())Plane=(UD^(ToMesh(Pole)-A)).GetSafeNormal();
    const FVector RefPlane=(RU^RL).GetSafeNormal();
    FTransform UpperPose=ReferencePose[CastUpperIndex],LowerPose=ReferencePose[CastLowerIndex],HandPose=ReferencePose[CastHandIndex];
    UpperPose.SetLocation(A);UpperPose.SetRotation(LimbFrame(UD,Plane)*LimbFrame(RU,RefPlane).Inverse()*ReferencePose[CastUpperIndex].GetRotation());
    LowerPose.SetLocation(E);
    HandPose.SetLocation(H);HandPose.SetRotation(CameraToMesh*HandRotation);
    // Derive forearm roll from the palm's width/hinge axis. Aligning the full
    // hand quaternion first coupled wrist extension into forearm twist when
    // the upright push palm approached a right angle to the forearm.
    const FQuat HandDeform=HandPose.GetRotation()*ReferencePose[CastHandIndex].GetRotation().Inverse();
    const FVector RefAcross=ReferencePalm.GetAxisY();
    const FVector Across=HandDeform.RotateVector(RefAcross);
    const FQuat ForearmDeform=FRotationMatrix::MakeFromXY(LD,Across).ToQuat()*
        FRotationMatrix::MakeFromXY(RL,RefAcross).ToQuat().Inverse();
    LowerPose.SetRotation((ForearmDeform*ReferencePose[CastLowerIndex].GetRotation()).GetNormalized());
    // Share a small part of the palm turn through the upper arm. Keeping it
    // locked to the bend plane concentrated the entire roll at the elbow seam.
    const FVector UpperAcross=(UpperPose.GetRotation()*ReferencePose[CastUpperIndex].GetRotation().Inverse()).RotateVector(RefAcross);
    const FVector UpperSide=(UpperAcross-UD*(UpperAcross|UD)).GetSafeNormal();
    const FVector PalmSide=(Across-UD*(Across|UD)).GetSafeNormal();
    const float SupportRoll=FMath::Clamp(FMath::Atan2(UD|(UpperSide^PalmSide),UpperSide|PalmSide)*.18f,
        -FMath::DegreesToRadians(12.f),FMath::DegreesToRadians(12.f))*FireballCastMotion::Ease(Release);
    UpperPose.SetRotation((FQuat(UD,SupportRoll)*UpperPose.GetRotation()).GetNormalized());
    if(Phase==EFireballHandPhase::Recovering)
    {
        // Carry the live grip's axial orientation onto each solved bone axis.
        // Both rotations aim along that axis, so blending them preserves length
        // while returning roll progressively instead of during the final fade.
        const auto ReturnRoll=[&](int32 Index,const FVector& RestAxis,const FVector& Axis,const FQuat& Authored)
        {
            const FQuat SourceDeform=SourcePose[Index].GetRotation()*ReferencePose[Index].GetRotation().Inverse();
            const FQuat Aligned=FQuat::FindBetweenNormals(SourceDeform.RotateVector(RestAxis.GetSafeNormal()),Axis)*SourcePose[Index].GetRotation();
            return FQuat::Slerp(Authored,Aligned,FireballCastMotion::Ease(T)).GetNormalized();
        };
        UpperPose.SetRotation(ReturnRoll(CastUpperIndex,RU,UD,UpperPose.GetRotation()));
        LowerPose.SetRotation(ReturnRoll(CastLowerIndex,RL,LD,LowerPose.GetRotation()));
    }
    GoalPose=SourcePose;
    const float LayerBlend=Motion.Layer;
    const FQuat DesiredPalm=HandPose.GetRotation()*ReferencePose[CastHandIndex].GetRotation().Inverse()*ReferencePalm;
    for(int32 I:LeftBones)
    {
        const int32 Parent=Ref.GetParentIndex(I);const FString Name=Ref.GetBoneName(I).ToString();
        const FTransform RestLocal=Ref.GetRefBonePose()[I];
        if(I==CastClavicleIndex)
        {
            const auto& EntryClavicle=Magic->HandEntryClavicle();
            GoalPose[I]=EntryClavicle*CameraWorld;GoalPose[I]=GoalPose[I].GetRelativeTransform(MeshWorld);
            GoalPose[I].SetLocation(A+ToMesh(EntryClavicle.GetLocation())-ToMesh(EntryShoulder));
        }
        else if(I==CastUpperIndex)GoalPose[I]=UpperPose;
        else if(I==CastLowerIndex)GoalPose[I]=LowerPose;
        else if(I==CastHandIndex)GoalPose[I]=HandPose;
        else
        {
            GoalPose[I]=RestLocal*GoalPose[Parent];
            // Both upper/lower-arm helpers retain their complete rest-local
            // transform and follow their segment as a rigid group. Fractional
            // roll against a fully rolled parent pinched this mesh during cast.
            for(const auto& Digit:Settings.Digits)
            {
                if(!Name.StartsWith(Digit.Key.ToString()+TEXT("_")) || Name.Contains(TEXT("metacarpal")))continue;
                const int32 Segment=FCString::Atoi(*Name.Mid(Digit.Key.ToString().Len()+1,2))-1;
                if(Segment<0 || Segment>2)break;
                const int32 Next=GetBoneIndex(FName(*FString::Printf(TEXT("%s_%02d_l"),*Digit.Key.ToString(),Segment+2)));
                FVector RefDirection;
                if(Next!=INDEX_NONE)RefDirection=ReferencePose[Next].GetLocation()-ReferencePose[I].GetLocation();
                else
                {
                    const FVector ParentAxis=ReferencePose[Parent].GetRotation().UnrotateVector(ReferencePose[I].GetLocation()-ReferencePose[Parent].GetLocation());
                    RefDirection=ReferencePose[I].GetRotation().RotateVector(ParentAxis);
                }
                const float Spread=FMath::DegreesToRadians(Digit.Value.Spread[Segment]);
                const float Flex=FMath::DegreesToRadians(FMath::Lerp(Digit.Value.GatherFlex[Segment],Digit.Value.ReleaseFlex[Segment],Release));
                const FVector Direction=DesiredPalm.RotateVector(FVector(FMath::Cos(Flex)*FMath::Cos(Spread),FMath::Cos(Flex)*FMath::Sin(Spread),FMath::Sin(Flex)));
                const FQuat OpenRotation=LimbFrame(Direction,DesiredPalm.GetAxisZ())*LimbFrame(RefDirection,ReferencePalm.GetAxisZ()).Inverse()*ReferencePose[I].GetRotation();
                const FQuat OpenLocal=GoalPose[Parent].GetRotation().Inverse()*OpenRotation;
                const float FingerBlend=FireballCastMotion::FingerWeight(Motion.Fingers,Digit.Key,Segment);
                FQuat GripLocal=EntryLocal[I].GetRotation();
                if(Phase==EFireballHandPhase::Recovering)
                    GripLocal=FQuat::Slerp(GripLocal,SourcePose[Parent].GetRotation().Inverse()*SourcePose[I].GetRotation(),FireballCastMotion::Ease(T));
                const FQuat Local=FQuat::Slerp(GripLocal,OpenLocal,FingerBlend);
                GoalPose[I].SetRotation(GoalPose[Parent].GetRotation()*Local);
                break;
            }
        }
    }
    // Blend in local space so intermediate arm/finger segments retain their lengths.
    for(int32 I:LeftBones)
    {
        const int32 Parent=Ref.GetParentIndex(I);
        FTransform Local=EntryLocal[I];
        if(Phase==EFireballHandPhase::Recovering)
            Local.BlendWith(SourcePose[I].GetRelativeTransform(SourcePose[Parent]),FireballCastMotion::Ease(T));
        const FTransform DesiredLocal=GoalPose[I].GetRelativeTransform(GoalPose[Parent]);
        Local.BlendWith(DesiredLocal,LayerBlend);Pose[I]=Local*Pose[Parent];
    }
}

bool UFPSCastingMeshComponent::GetQuickCombatStrikeProbe(FVector& OutOrigin) const
{
    // 惰性初始化：砸击已经不走姿态层，不能假设 CacheCastSkeleton 被火球路径调用过；
    // 不初始化会让探针静默退化成"眼位起点"（V10 实机日志里就是这么暴露的）。
    if(PoseMesh.Get()!=GetSkeletalMeshAsset()||BashHandR==INDEX_NONE)
        const_cast<UFPSCastingMeshComponent*>(this)->CacheCastSkeleton();
    if(BashHandR==INDEX_NONE||!GetOwner())return false;
    const auto* Camera=GetOwner()->FindComponentByClass<UCameraComponent>();
    if(!Camera)return false;
    const FTransform CameraWorld=Camera->GetComponentTransform();
    // 握把底 = 手骨世界位置 + 相机空间的握把偏移：命中射线的起点与画面同源；
    // 方向由角色瞄准给出（与其它武器/技能同一合同），不再从眼位前扫。
    const FTransform HandWorld=GetSocketTransform(FName(TEXT("hand_r")),RTS_World);
    OutOrigin=HandWorld.GetLocation()+CameraWorld.TransformVectorNoScale(QuickCombatPistolMotion::GripPointOffset());
    return true;
}

bool UFPSCastingMeshComponent::GetRifleStockMeleeProbe(FVector& OutOrigin,bool bM4StockPoint) const
{
    // 步枪砸击是整枪动作：参考动作使用各枪自己的枪托点，必须读当前动画姿态的枪骨，
    // 而不是入场快照——挥击本身就在动枪，探针要跟画面同源。
    if(!GetSkeletalMeshAsset()||!GetOwner())return false;
    const int32 MuzzleIndex=GetBoneIndex(TEXT("WPN_SOCKET_Muzzle"));
    const int32 RootIndex=GetBoneIndex(TEXT("WPN_root"));
    if(bM4StockPoint)
    {
        if(RootIndex==INDEX_NONE)return false;
        const FTransform Root=GetSocketTransform(FName(TEXT("WPN_root")),RTS_World);
        OutOrigin=Root.GetLocation()+Root.TransformVectorNoScale(
            QuickCombatRifleMotion::ReferenceStockPointCM(GetSkeletalMeshAsset()->GetPathName()));
        return true;
    }
    if(MuzzleIndex==INDEX_NONE&&RootIndex==INDEX_NONE)return false;
    const FTransform Muzzle=MuzzleIndex!=INDEX_NONE
        ?GetSocketTransform(FName(TEXT("WPN_SOCKET_Muzzle")),RTS_World)
        :GetSocketTransform(FName(TEXT("WPN_root")),RTS_World);
    // 枪轴 = 枪根 → 枪口；枪口沿轴回撤固定距离得到「枪身前段」。
    FVector Axis=FVector::ForwardVector;
    if(MuzzleIndex!=INDEX_NONE&&RootIndex!=INDEX_NONE)
    {
        const FVector Delta=Muzzle.GetLocation()-GetSocketTransform(FName(TEXT("WPN_root")),RTS_World).GetLocation();
        if(Delta.SizeSquared()>1.f)Axis=Delta.GetSafeNormal();
    }
    OutOrigin=Muzzle.GetLocation()-Axis*QuickCombatRifleMotion::MuzzleBackOffCM;
    return true;
}
