#include "MonsterSurfaceGroundingNode.h"
#include "RootCrownRigPreview.h"
#include "MonsterGroundSupport.h"
#include "BlindSupplicantMonster.h"
#include "MantisM27Monster.h"
#include "SpiralPillarM14.h"
#include "VortexCofferM25.h"
#include "HumanoidKnockdownComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

FMonsterSurfaceGroundingNode::FMonsterSurfaceGroundingNode(UAnimInstance* Instance)
{
    Alpha=1.f;
    const auto* Mesh=Instance?Cast<USkeletalMeshComponent>(Instance->GetOuter()):nullptr;
    Configure(Mesh?Cast<ACharacter>(Mesh->GetOwner()):nullptr);
}

void FMonsterSurfaceGroundingNode::Configure(const ACharacter* Owner)
{
    if (!Owner || Rig!=ERig::None) return;
    if (Owner->IsA<ARootCrownRigPreview>()) Rig=ERig::Tripod;
    else if (Owner->IsA<AVortexCofferM25>()) Rig=ERig::Tendrils;
    else if (Owner->IsA<ASpiralPillarM14>()) Rig=ERig::RootFan;
    else if (Owner->IsA<ABlindSupplicantMonster>() || Owner->IsA<AMantisM27Monster>() ||
        Owner->ActorHasTag(TEXT("FacelessReceptionist")) || Owner->ActorHasTag(TEXT("FacelessSecurity")) ||
        Owner->ActorHasTag(TEXT("FacelessResearcher"))) Rig=ERig::Biped;
    else return;
    const int32 Count=Rig==ERig::Tripod?3:Rig==ERig::Biped?2:Rig==ERig::RootFan?8:32;
    Limbs.SetNum(Count);
    for (int32 I=0; I<Count; ++I)
    {
        auto& L=Limbs[I];
        if (Rig==ERig::Tripod)
        {
            // The distal pad remains level; the extra proximal joint on the
            // front chains keeps its authored support/traction motion.
            static const TCHAR* Names[3][3]={{TEXT("Bone_004"),TEXT("Bone_003"),TEXT("Bone_002")},
                {TEXT("Bone_007"),TEXT("Bone_006"),TEXT("Bone_005")},
                {TEXT("Bone_011"),TEXT("Bone_010"),TEXT("Bone_009")}};
            L.Upper.BoneName=Names[I][0];L.Lower.BoneName=Names[I][1];L.Foot.BoneName=Names[I][2];
        }
        else if (Rig==ERig::Biped)
        {
            const FString Side=I==0?TEXT("l"):TEXT("r");
            L.Upper.BoneName=FName(TEXT("thigh_")+Side);
            L.Lower.BoneName=FName(TEXT("calf_")+Side);
            L.Foot.BoneName=FName(TEXT("foot_")+Side);
        }
        else if (Rig==ERig::RootFan)
        {
            L.Upper.BoneName=FName(*FString::Printf(TEXT("rootfan_%02d"),I));
            L.Lower.BoneName=FName(*FString::Printf(TEXT("roottoe_%02d"),I));
            L.VirtualEnd=true;
        }
        else
        {
            const FString Prefix=FString::Printf(TEXT("tendril_%02d_"),I);
            L.Upper.BoneName=FName(Prefix+TEXT("base"));
            L.Lower.BoneName=FName(Prefix+TEXT("mid"));
            L.Foot.BoneName=FName(Prefix+TEXT("tip"));
        }
    }
}

void FMonsterSurfaceGroundingNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    for (auto& L:Limbs)
    {
        L.Upper.Initialize(Bones); L.Lower.Initialize(Bones);
        if (!L.VirtualEnd) L.Foot.Initialize(Bones);
    }
    ResetPose=true;
}

bool FMonsterSurfaceGroundingNode::IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones)
{
    if (!Enabled || !ReferenceReady) return false;
    // A reduced LOD can omit a decorative tendril without disabling the other contacts.
    for (const auto& L:Limbs)
        if (L.Upper.IsValidToEvaluate(Bones) && L.Lower.IsValidToEvaluate(Bones) &&
            (L.VirtualEnd || L.Foot.IsValidToEvaluate(Bones))) return true;
    return false;
}

void FMonsterSurfaceGroundingNode::CacheReference(const ACharacter* Owner)
{
    auto* Asset=Owner->GetMesh()->GetSkeletalMeshAsset();
    if (CachedMesh.Get()==Asset) return;
    CachedMesh=Asset; ReferenceReady=false; QueryAge=1.f; ResetPose=true;
    if (!Asset) return;
    const auto& Ref=Asset->GetRefSkeleton();
    TArray<FTransform> Bind=Ref.GetRefBonePose();
    UncorrectedPose.LocalTransforms=Bind;
    UncorrectedPose.BoneNames.SetNum(Bind.Num()); UncorrectedPose.bIsValid=false;
    for (int32 I=0; I<Bind.Num(); ++I)
    {
        UncorrectedPose.BoneNames[I]=Ref.GetBoneName(I);
        if (Ref.GetParentIndex(I)!=INDEX_NONE) Bind[I]*=Bind[Ref.GetParentIndex(I)];
    }
    const auto* Mesh=Owner->GetMesh();
    const float Scale=FMath::Max(.01f,float(Mesh->GetComponentScale().GetAbsMax()));
    ForwardCS=Mesh->GetComponentTransform().InverseTransformVectorNoScale(Owner->GetActorForwardVector()).GetSafeNormal();
    const float Floor=Asset->GetBounds().Origin.Z-Asset->GetBounds().BoxExtent.Z;
    PivotCS=FVector::ZeroVector;
    for (auto& L:Limbs)
    {
        const int32 U=Ref.FindBoneIndex(L.Upper.BoneName), K=Ref.FindBoneIndex(L.Lower.BoneName);
        L.EndMeshIndex=Ref.FindBoneIndex(L.VirtualEnd?L.Lower.BoneName:L.Foot.BoneName);
        if (U==INDEX_NONE || K==INDEX_NONE || L.EndMeshIndex==INDEX_NONE) return;
        const FTransform& EndFrame=Bind[L.EndMeshIndex];
        FVector End=EndFrame.GetLocation();
        if (L.VirtualEnd)
        {
            // M14's actual root tip, also used by its attack sweep authoring.
            const FVector Radial=(Bind[K].GetLocation()-Bind[U].GetLocation()).GetSafeNormal2D();
            End+=Radial*46.f-FVector::UpVector*8.5f;
            L.EndLocal=EndFrame.InverseTransformPosition(End);
        }
        const FVector Axis=(End-Bind[U].GetLocation()).GetSafeNormal();
        const FVector Knee=Bind[K].GetLocation()-Bind[U].GetLocation();
        L.ReferencePole=(Knee-Axis*FVector::DotProduct(Knee,Axis)).GetSafeNormal();
        const float Length=FVector::Distance(Bind[U].GetLocation(),Bind[K].GetLocation())+FVector::Distance(Bind[K].GetLocation(),End);
        const float HalfSole=Rig==ERig::Tripod?6.f/Scale:Rig==ERig::Biped?FMath::Min(Length*.08f,10.f/Scale):Rig==ERig::RootFan?4.f/Scale:0.f;
        for (int32 J=0; J<2; ++J)
        {
            FVector P=End+ForwardCS*(J==0?-HalfSole:HalfSole);
            P.Z=Floor;
            L.Sole[J]=EndFrame.InverseTransformPosition(P);
        }
        PivotCS+=FVector(End.X,End.Y,Floor)/Limbs.Num();
        L.Valid=false; L.Correction=0.f; L.SmoothNormal=FVector::UpVector;
    }
    ReferenceReady=true;
}

void FMonsterSurfaceGroundingNode::Prepare(const ACharacter* Owner, float DeltaSeconds)
{
    const bool WasEnabled=Enabled;
    Enabled=false;
    if (!Owner) return;
    Configure(Owner);
    if (Rig==ERig::None) return;
    const auto* Mesh=Owner->GetMesh();
    const auto* Move=Owner->GetCharacterMovement();
    if (!Move || !Move->IsMovingOnGround() || Mesh->IsSimulatingPhysics()) return;
    if(const auto* Crown=Cast<ARootCrownRigPreview>(Owner);Crown&&(Crown->Dead()||Crown->IsKnockedDown()))return;
    if (const auto* Humanoid=Cast<ANurseZombie>(Owner))
        if (Humanoid->State==ENurseState::Dead || (Humanoid->Knockdown && Humanoid->Knockdown->IsControlling())) return;
    if (const auto* Pillar=Cast<ASpiralPillarM14>(Owner); Pillar && Pillar->Dead()) return;
    if (const auto* Coffer=Cast<AVortexCofferM25>(Owner); Coffer && Coffer->Dead()) return;
    CacheReference(Owner);
    if (!ReferenceReady) return;
    const FTransform Next=Mesh->GetComponentTransform();
    const bool Reset=!WasEnabled || FVector::DistSquared(Next.GetLocation(),Frame.GetLocation())>FMath::Square(120.);
    Frame=Next; Enabled=true; Dt=FMath::Clamp(DeltaSeconds,0.f,.1f); PreparedFrame=GFrameCounter;
    if (Reset) { QueryAge=1.f; ResetPose=true; }
    QueryAge+=Dt;
    if (QueryAge>=MonsterGroundSupport::QueryInterval(Mesh,Rig==ERig::Tendrils?1.f/15.f:.05f))
    {
        QueryAge=0.f;
        FMonsterGroundProbe Probe(Owner);
        const FVector Pivot=Frame.TransformPosition(PivotCS);
        auto Trace=[&](const FVector& At,FHitResult& Hit)
        {
            return Probe.Trace(Owner->GetWorld(),FVector(At.X,At.Y,Pivot.Z+110.f),
                FVector(At.X,At.Y,Pivot.Z-160.f),FVector::UpVector,Move->GetWalkableFloorZ(),Hit);
        };
        TArray<FVector,TInlineAllocator<32>> Points;
        float Lowest=FLT_MAX;
        for (auto& L:Limbs)
        {
            const FTransform End=Mesh->GetBoneTransform(L.EndMeshIndex);
            const FVector Middle=End.TransformPosition((L.Sole[0]+L.Sole[1])*.5f);
            L.Valid=false;
            double Best=-TNumericLimits<double>::Max();
            for (int32 J=0; J<(Rig==ERig::Tendrils?1:2); ++J)
            {
                FHitResult Hit;
                if (!Trace(End.TransformPosition(L.Sole[J]),Hit)) continue;
                const FVector N=Hit.ImpactNormal;
                const double Z=Hit.ImpactPoint.Z-(N.X*(Middle.X-Hit.ImpactPoint.X)+N.Y*(Middle.Y-Hit.ImpactPoint.Y))/N.Z;
                if (Z>Best) {Best=Z; L.Contact=Hit.ImpactPoint; L.Normal=N; L.Valid=true;}
            }
            if (L.Valid) {Points.Add(FVector(Middle.X,Middle.Y,Best)); Lowest=FMath::Min(Lowest,float(Best-Pivot.Z));}
        }
        WantedHeight=0.f; WantedTilt=FQuat::Identity; MinimumHeight=-70.f;
        if (Rig==ERig::Biped)
        {
            // Lower to the supporting leg, allowing the higher leg to flex.
            if (!Points.IsEmpty()) WantedHeight=FMath::Clamp(Lowest,-45.f,30.f);
        }
        else if (MonsterGroundSupport::FitPlane(Points,Pivot,(Rig==ERig::RootFan || Rig==ERig::Tripod)?10.f:25.f,WantedHeight,WantedTilt))
        {
            // The pillar keeps its upright silhouette; only modest base lean is used.
            const float BellyClearance=Rig==ERig::RootFan?10.f:8.f;
            for (float Offset:{-45.f,0.f,45.f})
            {
                const FVector At=Pivot+Frame.TransformVectorNoScale(ForwardCS)*Offset;
                FHitResult Hit;
                if (Trace(At,Hit))
                {
                    const FVector Rotated=Pivot+WantedTilt.RotateVector(At-Pivot);
                    MinimumHeight=FMath::Max(MinimumHeight,float(Hit.ImpactPoint.Z-Rotated.Z-BellyClearance));
                }
            }
            WantedHeight=FMath::Clamp(FMath::Max(WantedHeight,MinimumHeight),-70.f,60.f);
        }
    }
    const float Blend=Reset?1.f:1.f-FMath::Exp(-12.f*Dt);
    Height=FMath::Lerp(Height,WantedHeight,Blend);
    Tilt=FQuat::Slerp(Tilt,WantedTilt,Blend).GetNormalized();
}

FTransform FMonsterSurfaceGroundingNode::Grounded(const FTransform& Bone, float Compression) const
{
    FTransform Result=Bone;
    const FVector Pivot=Frame.TransformPosition(PivotCS);
    Result.SetLocation(Frame.InverseTransformPosition(Pivot+Tilt.RotateVector(Frame.TransformPosition(Bone.GetLocation())-Pivot)
        +FVector(0,0,Height+Compression)));
    Result.SetRotation((Frame.GetRotation().Inverse()*Tilt*Frame.GetRotation()*Bone.GetRotation()).GetNormalized());
    return Result;
}

void FMonsterSurfaceGroundingNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    const bool NewFrame=EvaluatedFrame!=PreparedFrame;
    EvaluatedFrame=PreparedFrame;
    for (int32 I=0; I<Bones.GetCompactPoseNumBones(); ++I)
    {
        const FCompactPoseBoneIndex B(I), P=Bones.GetParentBoneIndex(B);
        const FTransform Bone=Output.Pose.GetComponentSpaceTransform(B);
        UncorrectedPose.LocalTransforms[Bones.MakeMeshPoseIndex(B).GetInt()]=P!=INDEX_NONE?
            Bone.GetRelativeTransform(Output.Pose.GetComponentSpaceTransform(P)):Bone;
    }
    UncorrectedPose.bIsValid=true;
    struct FGoal { bool Valid=false; FVector Position; FQuat Rotation; float Lift=0.f; };
    TArray<FGoal,TInlineAllocator<32>> Goals; Goals.SetNum(Limbs.Num());
    const float BaseZ=Frame.TransformPosition(PivotCS).Z;
    float Compression=0.f;
    for (int32 I=0; I<Limbs.Num(); ++I)
    {
        auto& L=Limbs[I]; auto& G=Goals[I];
        if (!L.Upper.IsValidToEvaluate(Bones) || !L.Lower.IsValidToEvaluate(Bones) ||
            (!L.VirtualEnd && !L.Foot.IsValidToEvaluate(Bones))) continue;
        const auto EndIndex=(L.VirtualEnd?L.Lower:L.Foot).GetCompactPoseIndex(Bones);
        const FTransform Source=Output.Pose.GetComponentSpaceTransform(EndIndex);
        const FVector SourceEnd=L.VirtualEnd?Source.TransformPosition(L.EndLocal):Source.GetLocation();
        FVector Goal=Frame.TransformPosition(SourceEnd);
        if (NewFrame)
            L.SmoothNormal=ResetPose?L.Normal:FMath::Lerp(L.SmoothNormal,L.Valid?L.Normal:FVector::UpVector,1.f-FMath::Exp(-14.f*Dt)).GetSafeNormal();
        const FVector Normal=L.SmoothNormal.Z>.1f?L.SmoothNormal:FVector::UpVector;
        const FQuat WorldRotation=(FQuat::FindBetweenNormals(FVector::UpVector,Normal)*Frame.GetRotation()*Source.GetRotation()).GetNormalized();
        const FTransform Rotated(WorldRotation,Frame.TransformPosition(Source.GetLocation()),Source.GetScale3D()*Frame.GetScale3D());
        double Gap=TNumericLimits<double>::Max(), Bottom=TNumericLimits<double>::Max();
        for (const FVector& Sole:L.Sole)
        {
            Gap=FMath::Min(Gap,FVector::DotProduct(Rotated.TransformPosition(Sole)-L.Contact,Normal));
            Bottom=FMath::Min(Bottom,Frame.TransformPosition(Source.TransformPosition(Sole)).Z);
        }
        // Preserve the authored swing, root sweep and M07's deliberate spell hover.
        G.Lift=FMath::Max(0.f,float(Bottom-BaseZ));
        const float Target=L.Valid?float((.5-Gap)/Normal.Z)+G.Lift:0.f;
        if (NewFrame) L.Correction=ResetPose?Target:FMath::FInterpConstantTo(L.Correction,Target,Dt,200.f);
        Goal.Z+=L.Correction;
        G.Position=Frame.InverseTransformPosition(Goal);
        G.Rotation=(Frame.GetRotation().Inverse()*WorldRotation).GetNormalized();
        G.Valid=L.Valid || FMath::Abs(L.Correction)>.05f;
        if (!G.Valid || G.Lift>5.f) continue;
        const FTransform Upper=Grounded(Output.Pose.GetComponentSpaceTransform(L.Upper.GetCompactPoseIndex(Bones)));
        const FTransform Lower=Grounded(Output.Pose.GetComponentSpaceTransform(L.Lower.GetCompactPoseIndex(Bones)));
        const FVector U=Frame.TransformPosition(Upper.GetLocation()),K=Frame.TransformPosition(Lower.GetLocation());
        const FVector E=Frame.TransformPosition(Grounded(Source).TransformPosition(L.VirtualEnd?L.EndLocal:FVector::ZeroVector));
        const double Reach=(FVector::Distance(U,K)+FVector::Distance(K,E))*.995;
        const double Vertical=Reach*Reach-FVector::DistSquared2D(U,Goal);
        if (Vertical>0. && U.Z>Goal.Z) Compression=FMath::Min(Compression,float(Goal.Z+FMath::Sqrt(Vertical)-U.Z));
    }
    Compression=FMath::Clamp(Compression,-20.f,0.f);
    if (Rig!=ERig::Biped) Compression=FMath::Max(Compression,FMath::Min(0.f,MinimumHeight-Height));
    Out.Emplace(FCompactPoseBoneIndex(0),Grounded(Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0)),Compression));
    for (int32 I=0; I<Limbs.Num(); ++I)
    {
        const auto& L=Limbs[I]; const auto& G=Goals[I]; if (!G.Valid) continue;
        const auto U=L.Upper.GetCompactPoseIndex(Bones),K=L.Lower.GetCompactPoseIndex(Bones);
        FTransform Upper=Grounded(Output.Pose.GetComponentSpaceTransform(U),Compression);
        FTransform Lower=Grounded(Output.Pose.GetComponentSpaceTransform(K),Compression);
        FTransform Foot=L.VirtualEnd?Lower:Grounded(Output.Pose.GetComponentSpaceTransform(L.Foot.GetCompactPoseIndex(Bones)),Compression);
        if (L.VirtualEnd) Foot.SetLocation(Lower.TransformPosition(L.EndLocal));
        const FVector Root=Upper.GetLocation(), Axis=(Foot.GetLocation()-Root).GetSafeNormal();
        const FVector Knee=Lower.GetLocation()-Root;
        FVector Bend=FVector::VectorPlaneProject(Knee,Axis).GetSafeNormal();
        if (Bend.IsNearlyZero()) Bend=Tilt.RotateVector(L.ReferencePole);
        const float Reach=FVector::Distance(Root,Lower.GetLocation())+FVector::Distance(Lower.GetLocation(),Foot.GetLocation());
        const FVector Target=Root+(G.Position-Root).GetClampedToMaxSize(Reach*.995f);
        AnimationCore::SolveTwoBoneIK(Upper,Lower,Foot,Root+Bend*Reach,Target,false,1.,1.);
        Out.Emplace(U,Upper); Out.Emplace(K,Lower);
        if (!L.VirtualEnd) {Foot.SetRotation(G.Rotation); Out.Emplace(L.Foot.GetCompactPoseIndex(Bones),Foot);}
    }
    Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
    ResetPose=false;
}
