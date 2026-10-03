#include "WitchRebuiltMonster.h"
#include "Animation/PoseSnapshot.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

namespace
{
// One bounded CPU skinning pass at corpse freeze, using the exact imported
// garment/anatomy vertices and weights. No GPU readback or ongoing corpse tick.
struct FCorpseSurface
{
    TArray<FVector> Core;
    TArray<FVector> Chest, Head, Hands[2];
    double FootBottom[2]={TNumericLimits<double>::Max(),TNumericLimits<double>::Max()};
};

FCorpseSurface SampleCorpseSurface(USkeletalMeshComponent* CharacterMesh)
{
    FCorpseSurface Result;
    const auto* Asset=CharacterMesh->GetSkeletalMeshAsset();
    const auto* Info=Asset->GetLODInfo(0);
    const auto* RenderData=CharacterMesh->GetSkeletalMeshRenderData();
    auto* Weights=CharacterMesh->GetSkinWeightBuffer(0);
    if (!Info || !Info->bAllowCPUAccess || !RenderData || RenderData->LODRenderData.IsEmpty() || !Weights) return Result;
    const auto& LOD=RenderData->LODRenderData[0];
    const int32 VertexCount=LOD.GetNumVertices();
    if (VertexCount==0 || Weights->GetNumVertices()!=static_cast<uint32>(VertexCount)) return Result;
    const auto& Ref=Asset->GetRefSkeleton();
    TArray<uint8> BoneRegion;
    BoneRegion.SetNumZeroed(Ref.GetNum());
    for (int32 Bone=0;Bone<BoneRegion.Num();++Bone)
    {
        const FString Name=Ref.GetBoneName(Bone).ToString();
        if (Name==TEXT("pelvis") || Name.StartsWith(TEXT("spine_")) || Name.StartsWith(TEXT("thigh_"))) BoneRegion[Bone]=1;
        if (Name==TEXT("spine_03") || Name==TEXT("spine_04") || Name==TEXT("spine_05")) BoneRegion[Bone]=4;
        else if (Name==TEXT("foot_l") || Name==TEXT("ball_l")) BoneRegion[Bone]=2;
        else if (Name==TEXT("foot_r") || Name==TEXT("ball_r")) BoneRegion[Bone]=3;
        else if (Name==TEXT("head") || Name.StartsWith(TEXT("neck_"))) BoneRegion[Bone]=5;
        else if (Name==TEXT("hand_l")) BoneRegion[Bone]=6;
        else if (Name==TEXT("hand_r")) BoneRegion[Bone]=7;
    }
    TArray<FMatrix44f> RefToLocal;
    CharacterMesh->GetCurrentRefToLocalMatrices(RefToLocal,0);
    const FTransform MeshWorld=CharacterMesh->GetComponentTransform();
    constexpr int32 MaxSamples=4096;
    int32 Remaining=MaxSamples;
    Result.Core.Reserve(MaxSamples);
    for (const auto& Section:LOD.RenderSections)
    {
        if (Section.bDisabled || Section.NumVertices==0 || Remaining==0) continue;
        const int32 Count=FMath::Min3(static_cast<int32>(Section.NumVertices),Remaining,
            FMath::Max(32,static_cast<int32>(int64(MaxSamples)*Section.NumVertices/VertexCount)));
        Remaining-=Count;
        for (int32 Sample=0;Sample<Count;++Sample)
        {
            const uint32 Vertex=Section.BaseVertexIndex+(Count==1?0:
                static_cast<uint32>(int64(Sample)*(Section.NumVertices-1)/(Count-1)));
            uint32 Offset=0,Influences=0;
            Weights->GetVertexInfluenceOffsetCount(Vertex,Offset,Influences);
            uint32 RegionWeight[8]={};
            uint32 Total=0;
            for (uint32 Influence=0;Influence<Influences;++Influence)
            {
                const uint32 Weight=Weights->GetBoneWeight(Vertex,Influence);
                const int32 LocalBone=Weights->GetBoneIndex(Vertex,Influence);
                if (!Section.BoneMap.IsValidIndex(LocalBone)) continue;
                const int32 Bone=Section.BoneMap[LocalBone];
                RegionWeight[BoneRegion[Bone]]+=Weight;
                Total+=Weight;
            }
            if (Total==0) continue;
            const FVector Point=MeshWorld.TransformPosition(FVector(USkinnedMeshComponent::GetSkinnedVertexPosition(
                CharacterMesh,Vertex,LOD,*Weights,RefToLocal)));
            if ((RegionWeight[1]+RegionWeight[4])*2>=Total) Result.Core.Add(Point);
            if (RegionWeight[4]*2>=Total) Result.Chest.Add(Point);
            if (RegionWeight[5]*2>=Total) Result.Head.Add(Point);
            for (int32 Side=0;Side<2;++Side) if (RegionWeight[Side+6]*2>=Total) Result.Hands[Side].Add(Point);
            for (int32 Side=0;Side<2;++Side) if (RegionWeight[Side+2]*2>=Total)
                Result.FootBottom[Side]=FMath::Min(Result.FootBottom[Side],Point.Z);
        }
    }
    return Result;
}

void FitCorpseSurface(USkeletalMeshComponent* CharacterMesh,const TArray<FVector>& Points)
{
    if (Points.IsEmpty()) return;
    FBox Bounds(ForceInit);
    for (const FVector& Point:Points) Bounds+=Point;
    // At most 64 terrain queries, distributed across the actual corpse footprint.
    FVector Lowest[64];
    bool Used[64]={};
    const FVector Cell=Bounds.GetSize()/8.;
    for (const FVector& Point:Points)
    {
        const int32 X=FMath::Clamp(FMath::FloorToInt((Point.X-Bounds.Min.X)/FMath::Max(1.,Cell.X)),0,7);
        const int32 Y=FMath::Clamp(FMath::FloorToInt((Point.Y-Bounds.Min.Y)/FMath::Max(1.,Cell.Y)),0,7);
        const int32 Index=Y*8+X;
        if (!Used[Index] || Point.Z<Lowest[Index].Z) { Lowest[Index]=Point; Used[Index]=true; }
    }
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchCorpseSurfaceSupport),true,CharacterMesh->GetOwner());
    double Gap=TNumericLimits<double>::Max();
    for (int32 Index=0;Index<64;++Index)
    {
        if (!Used[Index]) continue;
        FHitResult Floor;
        const FVector Point=Lowest[Index];
        if (CharacterMesh->GetWorld()->LineTraceSingleByObjectType(Floor,Point+FVector(0,0,35.),
            Point-FVector(0,0,150.),Objects,Query) && Floor.ImpactNormal.Z>.5f)
            Gap=FMath::Min(Gap,Point.Z-Floor.ImpactPoint.Z-.5);
    }
    if (Gap==TNumericLimits<double>::Max() || FMath::Abs(Gap)<.5) return;
    // Move the whole connected presentation before solving the feet; a foot
    // lowered first must not become a false support for an elevated torso.
    CharacterMesh->SetWorldLocation(CharacterMesh->GetComponentLocation()-FVector(0,0,Gap),
        false,nullptr,ETeleportType::TeleportPhysics);
}
}

void AWitchRebuiltMonster::GroundCorpsePose(FPoseSnapshot& Pose) const
{
    if (!Pose.bIsValid || !bCorpseVisualPrepared) return;
    auto* CharacterMesh=GetMesh();
    const FCorpseSurface Surface=SampleCorpseSurface(CharacterMesh);
    const FVector BeforeFit=CharacterMesh->GetComponentLocation();
    double FootClearance[2]={4.,4.};
    for (int32 Side=0;Side<2;++Side)
        if (Surface.FootBottom[Side]!=TNumericLimits<double>::Max())
            FootClearance[Side]=CharacterMesh->GetSocketLocation(Side==0?TEXT("foot_l"):TEXT("foot_r")).Z-Surface.FootBottom[Side]+.5;
    FitCorpseSurface(CharacterMesh,Surface.Core);
    const FVector SurfaceShift=CharacterMesh->GetComponentLocation()-BeforeFit;
    const auto& Ref=CharacterMesh->GetSkeletalMeshAsset()->GetRefSkeleton();
    const FTransform MeshWorld=CharacterMesh->GetComponentTransform();
    TArray<FTransform> World;
    World.SetNum(Pose.LocalTransforms.Num());
    TArray<int32> Parents;
    Parents.SetNum(World.Num());
    for (int32 Index=0;Index<Parents.Num();++Index)
    {
        const int32 Bone=Ref.FindBoneIndex(Pose.BoneNames[Index]);
        const int32 ParentBone=Ref.GetParentIndex(Bone);
        Parents[Index]=ParentBone==INDEX_NONE?INDEX_NONE:Pose.BoneNames.IndexOfByKey(Ref.GetBoneName(ParentBone));
    }
    auto Rebuild=[&]()
    {
        for (int32 I=0;I<World.Num();++I)
        {
            const int32 P=Parents[I];
            World[I]=Pose.LocalTransforms[I]*(P==INDEX_NONE?MeshWorld:World[P]);
        }
    };
    auto SetWorld=[&](int32 Index,const FTransform& Transform)
    {
        const int32 P=Parents[Index];
        Pose.LocalTransforms[Index]=Transform.GetRelativeTransform(P==INDEX_NONE?MeshWorld:World[P]);
        Rebuild();
    };
    Rebuild();
    FCollisionObjectQueryParams Objects;
    Objects.AddObjectTypesToQuery(ECC_WorldStatic); Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(WitchCorpseLegSupport),false,this);
    const int32 Spine=Pose.BoneNames.IndexOfByKey(FName(TEXT("spine_01")));
    FVector ChestPivot=FVector::ZeroVector;
    FQuat ChestRotation=FQuat::Identity;
    // A low skirt or hip is a lower-body support, not proof the chest/back has
    // settled. Articulate the spine at freeze while retaining anatomical length.
    if (Spine!=INDEX_NONE && !Surface.Chest.IsEmpty())
    {
        ChestPivot=World[Spine].GetLocation();
        struct FSupport { FVector Point; double Floor; };
        TArray<FSupport,TInlineAllocator<32>> Contacts;
        FVector Center=FVector::ZeroVector;
        const int32 Count=FMath::Min(32,Surface.Chest.Num());
        for (int32 I=0;I<Count;++I)
        {
            const FVector Point=Surface.Chest[int64(I)*Surface.Chest.Num()/Count]+SurfaceShift;
            FHitResult Floor;
            if (GetWorld()->LineTraceSingleByObjectType(Floor,Point+FVector(0,0,35),
                Point-FVector(0,0,150),Objects,Query) && Floor.ImpactNormal.Z>.5f)
            { Contacts.Add({Point,Floor.ImpactPoint.Z+.5}); Center+=Point; }
        }
        if (!Contacts.IsEmpty())
        {
            const FVector Along=(Center/Contacts.Num()-ChestPivot).GetSafeNormal2D();
            const FVector Axis=FVector::CrossProduct(Along,FVector::DownVector).GetSafeNormal();
            auto Gap=[&](double Angle)
            {
                double Result=TNumericLimits<double>::Max();
                const FQuat Rotation(Axis,Angle);
                for (const auto& Contact:Contacts)
                    Result=FMath::Min(Result,(ChestPivot+Rotation.RotateVector(Contact.Point-ChestPivot)).Z-Contact.Floor);
                return Result;
            };
            if (!Axis.IsNearlyZero() && Gap(0.)>1.)
            {
                double Low=0.,High=FMath::DegreesToRadians(35.);
                if (Gap(High)<0.)
                    for (int32 Step=0;Step<12;++Step)
                    { const double Mid=(Low+High)*.5; if (Gap(Mid)>0.) Low=Mid; else High=Mid; }
                ChestRotation=FQuat(Axis,High);
                FTransform Transform=World[Spine];
                Transform.SetRotation(ChestRotation*Transform.GetRotation());
                SetWorld(Spine,Transform);
            }
        }
    }
    auto ChestPoint=[&](const FVector& Point)
    { return ChestPivot+ChestRotation.RotateVector(Point+SurfaceShift-ChestPivot); };
    // Keep the head above its local floor when the relaxed spine lowers it.
    const int32 Neck=Pose.BoneNames.IndexOfByKey(FName(TEXT("neck_01")));
    const int32 Head=Pose.BoneNames.IndexOfByKey(FName(TEXT("head")));
    if (Neck!=INDEX_NONE && Head!=INDEX_NONE && !Surface.Head.IsEmpty())
    {
        FHitResult Floor;
        const FVector At=World[Head].GetLocation(),Pivot=World[Neck].GetLocation();
        if (GetWorld()->LineTraceSingleByObjectType(Floor,At+FVector(0,0,35),At-FVector(0,0,150),Objects,Query)
            && Floor.ImpactNormal.Z>.5f)
        {
            const FVector Axis=FVector::CrossProduct((At-Pivot).GetSafeNormal2D(),FVector::UpVector).GetSafeNormal();
            auto Bottom=[&](double Angle)
            {
                double Z=TNumericLimits<double>::Max();
                const FQuat Rotation(Axis,Angle);
                for (const FVector& Point:Surface.Head)
                    Z=FMath::Min(Z,(Pivot+Rotation.RotateVector(ChestPoint(Point)-Pivot)).Z);
                return Z;
            };
            const double Height=Floor.ImpactPoint.Z+.5;
            if (!Axis.IsNearlyZero() && Bottom(0.)<Height)
            {
                double Low=0.,High=FMath::DegreesToRadians(40.);
                if (Bottom(High)>Height)
                    for (int32 Step=0;Step<12;++Step)
                    { const double Mid=(Low+High)*.5; if (Bottom(Mid)<Height) Low=Mid; else High=Mid; }
                FTransform Transform=World[Neck];
                Transform.SetRotation(FQuat(Axis,High)*Transform.GetRotation());
                SetWorld(Neck,Transform);
            }
        }
    }
    int32 SideIndex=0;
    for (const bool bArm:{false,true}) for (const TCHAR* Side:{TEXT("l"),TEXT("r")})
    {
        const int32 SideNumber=SideIndex++%2;
        double Clearance=FootClearance[SideNumber];
        const FName FootName(*(FString(bArm?TEXT("hand_"):TEXT("foot_"))+Side));
        const int32 Upper=Pose.BoneNames.IndexOfByKey(FName(*(FString(bArm?TEXT("upperarm_"):TEXT("thigh_"))+Side)));
        const int32 Lower=Pose.BoneNames.IndexOfByKey(FName(*(FString(bArm?TEXT("lowerarm_"):TEXT("calf_"))+Side)));
        const int32 Foot=Pose.BoneNames.IndexOfByKey(FootName);
        if (Upper==INDEX_NONE || Lower==INDEX_NONE || Foot==INDEX_NONE) continue;
        const FTransform OldUpper=World[Upper],OldLower=World[Lower],OldFoot=World[Foot];
        const FVector Hip=OldUpper.GetLocation(),Knee=OldLower.GetLocation(),Ankle=OldFoot.GetLocation();
        if (bArm)
        {
            double Bottom=TNumericLimits<double>::Max();
            for (const FVector& Point:Surface.Hands[SideNumber]) Bottom=FMath::Min(Bottom,ChestPoint(Point).Z);
            Clearance=Bottom==TNumericLimits<double>::Max()?3.:Ankle.Z-Bottom+.5;
        }
        FHitResult Floor;
        if (!GetWorld()->LineTraceSingleByObjectType(Floor,Ankle+FVector(0,0,20.f),
            Ankle-FVector(0,0,150.f),Objects,Query) || Floor.ImpactNormal.Z<.5f) continue;
        FVector AnkleTarget=Ankle;
        AnkleTarget.Z=Floor.ImpactPoint.Z+Clearance;
        // Hands are moved only out of floor penetration introduced by torso
        // settling; airborne hands keep the captured grip and held props.
        if (bArm && AnkleTarget.Z<=Ankle.Z) continue;
        if (FMath::Abs(AnkleTarget.Z-Ankle.Z)<1.) continue;
        const double L1=FVector::Distance(Hip,Knee),L2=FVector::Distance(Knee,Ankle);
        const double Reach=L1+L2-.5;
        const double Height=AnkleTarget.Z-Hip.Z;
        if (Reach<=FMath::Abs(Height) || L1<1. || L2<1.) continue;
        // A distant ankle target moves along the leg's existing direction into
        // reach. The hip/torso stay fixed and both anatomical lengths are retained.
        const double HorizontalReach=FMath::Sqrt(Reach*Reach-Height*Height);
        const FVector Horizontal=(AnkleTarget-Hip).GetClampedToMaxSize2D(HorizontalReach);
        AnkleTarget.X=Hip.X+Horizontal.X; AnkleTarget.Y=Hip.Y+Horizontal.Y;
        const FVector Direction=(AnkleTarget-Hip).GetSafeNormal();
        const double Distance=FMath::Clamp(FVector::Distance(AnkleTarget,Hip),FMath::Abs(L1-L2)+.1,Reach);
        AnkleTarget=Hip+Direction*Distance;
        FVector Bend=(Knee-Hip)-Direction*FVector::DotProduct(Knee-Hip,Direction);
        if (Bend.IsNearlyZero()) Bend=FVector::UpVector-Direction*Direction.Z;
        if (Bend.IsNearlyZero()) Bend=FVector::CrossProduct(Direction,GetActorRightVector());
        Bend.Normalize();
        const double Along=(L1*L1-L2*L2+Distance*Distance)/(2.*Distance);
        const FVector NewKnee=Hip+Direction*Along+Bend*FMath::Sqrt(FMath::Max(0.,L1*L1-Along*Along));
        FTransform UpperWorld=OldUpper;
        UpperWorld.SetRotation(FQuat::FindBetweenVectors(Knee-Hip,NewKnee-Hip)*OldUpper.GetRotation());
        SetWorld(Upper,UpperWorld);
        FTransform LowerWorld=OldLower;
        LowerWorld.SetLocation(NewKnee);
        LowerWorld.SetRotation(FQuat::FindBetweenVectors(Ankle-Knee,AnkleTarget-NewKnee)*OldLower.GetRotation());
        SetWorld(Lower,LowerWorld);
        FTransform FootWorld=OldFoot;
        FootWorld.SetLocation(AnkleTarget);
        SetWorld(Foot,FootWorld);
    }
}
