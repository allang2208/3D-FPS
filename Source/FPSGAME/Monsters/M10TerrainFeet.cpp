#include "M10FootPlantNode.h"
#include "M10Mawcrawler.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

void FM10FootPlantNode::CacheSupportGeometry(const AM10Mawcrawler* Monster)
{
    auto* Mesh=Monster->GetMesh();auto* Asset=Mesh->GetSkeletalMeshAsset();auto* Physics=Mesh->GetPhysicsAsset();
    if(PreparedMesh.Get()==Asset&&PreparedPhysics.Get()==Physics)return;
    PreparedMesh=Asset;PreparedPhysics=Physics;TraceElapsed=1.f;
    for(auto& S:Supports)S=FSupport();
    if(!Asset)return;
    const auto& Ref=Asset->GetRefSkeleton();TArray<FTransform> Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)!=INDEX_NONE)Bind[I]*=Bind[Ref.GetParentIndex(I)];
    BaseFloorZ=Asset->GetBounds().Origin.Z-Asset->GetBounds().BoxExtent.Z;
    const int32 Front=Ref.FindBoneIndex(TEXT("body_front")),Rear=Ref.FindBoneIndex(TEXT("body_rear"));
    if(Front!=INDEX_NONE&&Rear!=INDEX_NONE)ReferenceForward=(Bind[Front].GetLocation()-Bind[Rear].GetLocation()).GetSafeNormal2D();
    for(int32 I=0;I<8;++I)
    {
        auto& S=Supports[I];S.Bone=Ref.FindBoneIndex(Legs[I].Foot.BoneName);
        if(S.Bone==INDEX_NONE)continue;
        S.ReferenceFoot=Bind[S.Bone].GetLocation();
        if(Physics)for(const auto& Body:Physics->SkeletalBodySetups)
        {
            if(!Body||Body->BoneName!=Legs[I].Foot.BoneName)continue;
            for(const auto& Convex:Body->AggGeom.ConvexElems)
            {
                const int32 Step=FMath::Max(1,FMath::DivideAndRoundUp(Convex.VertexData.Num(),32));
                for(int32 V=0;V<Convex.VertexData.Num()&&S.Sole.Num()<32;V+=Step)
                    S.Sole.Add(Convex.GetTransform().TransformPosition(Convex.VertexData[V]));
            }
        }
        if(S.Sole.IsEmpty())S.Sole.Add(Bind[S.Bone].InverseTransformPosition(FVector(S.ReferenceFoot.X,S.ReferenceFoot.Y,BaseFloorZ)));
    }
}

void FM10FootPlantNode::Prepare(const AM10Mawcrawler* Monster,float Phase,float Stance,float Weight,float Rate,float DeltaSeconds,bool IsWalking)
{
    Serial=GFrameCounter;Dt=FMath::Clamp(DeltaSeconds,0.f,.1f);
    CyclePhase=Phase;StanceFraction=Stance;PlantWeight=Weight;Walking=IsWalking;
    StepSeconds=FMath::Clamp(.28f/FMath::Max(1.f,Rate),.045f,.22f);
    if(!Monster){Enabled=GroundEnabled=false;return;}
    auto* Mesh=Monster->GetMesh();const auto* Move=Monster->GetCharacterMovement();
    const FTransform Next=Mesh->GetComponentTransform();
    if(FVector::DistSquared(Next.GetLocation(),Frame.GetLocation())>FMath::Square(100.))
    {GroundHeight=WantedGroundHeight=0.f;GroundRotation=WantedGroundRotation=FQuat::Identity;TraceElapsed=1.f;}
    Frame=Next;CacheSupportGeometry(Monster);
    PoseLiftAllowed=Monster->Busy();
    GroundEnabled=!Mesh->IsSimulatingPhysics()&&PreparedMesh.IsValid();
    Enabled=GroundEnabled&&!Monster->Dead()&&Move->IsMovingOnGround();
    // Preserve the last body support through the authored death/physics handoff.
    if(!Enabled)
    {
        if(!Monster->Dead())
        {GroundHeight=FMath::FInterpTo(GroundHeight,0.f,Dt,8.f);GroundRotation=FQuat::Slerp(GroundRotation,FQuat::Identity,1.f-FMath::Exp(-8.f*Dt));}
        return;
    }
    TraceElapsed+=Dt;
    if(TraceElapsed>=.05f)
    {
        TraceElapsed=0.f;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(M10TerrainFeet),false,Monster);
        FCollisionObjectQueryParams Objects;
        Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);Objects.AddObjectTypesToQuery(ECC_PhysicsBody);
        const float BaseZ=Frame.TransformPosition(FVector(0,0,BaseFloorZ)).Z;
        auto Trace=[&](FVector At,FHitResult& Hit)
        {
            const bool Found=Monster->GetWorld()->LineTraceSingleByObjectType(Hit,FVector(At.X,At.Y,BaseZ+100.f),FVector(At.X,At.Y,BaseZ-160.f),Objects,Query);
            return Found&&!Hit.bStartPenetrating&&Hit.ImpactNormal.Z>=Move->GetWalkableFloorZ()&&Hit.GetComponent()&&Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
        };
        FVector Points[8];int32 Count=0;FVector Mean=FVector::ZeroVector;
        for(int32 I=0;I<8;++I)
        {
            auto& S=Supports[I];if(S.Bone==INDEX_NONE)continue;
            // Read the previous evaluated contact on the game thread only.
            FHitResult Hit;S.Valid=Trace(Mesh->GetBoneTransform(S.Bone).GetLocation(),Hit);
            if(S.Valid){S.Point=Hit.ImpactPoint;S.Normal=Hit.ImpactNormal;Points[Count]=S.Point;Mean+=Points[Count++];}
        }
        if(Count>=3)
        {
            Mean/=Count;double XX=0,YY=0,XY=0,XZ=0,YZ=0;
            for(int32 I=0;I<Count;++I)
            {const FVector D=Points[I]-Mean;XX+=D.X*D.X;YY+=D.Y*D.Y;XY+=D.X*D.Y;XZ+=D.X*D.Z;YZ+=D.Y*D.Z;}
            const double Det=XX*YY-XY*XY;
            if(Det>1.)
            {
                FVector Normal(-(XZ*YY-YZ*XY)/Det,-(YZ*XX-XZ*XY)/Det,1.);Normal.Normalize();
                FQuat Tilt=FQuat::FindBetweenNormals(FVector::UpVector,Normal);
                const float Angle=Tilt.GetAngle(),Limit=FMath::DegreesToRadians(22.f);
                if(Angle>Limit)Tilt=FQuat::Slerp(FQuat::Identity,Tilt,Limit/Angle);
                Normal=Tilt.RotateVector(FVector::UpVector);
                const FVector Origin=Frame.TransformPosition(FVector(0,0,BaseFloorZ));
                float Height=Mean.Z-(Normal.X*(Origin.X-Mean.X)+Normal.Y*(Origin.Y-Mean.Y))/Normal.Z-Origin.Z;
                // Three belly supports prevent a best-fit plane from lowering
                // the broad torso through a step or a rock between the feet.
                for(float X:{-110.f,0.f,110.f})
                {
                    const FVector Local=ReferenceForward*X+FVector(0,0,BaseFloorZ);const FVector At=Frame.TransformPosition(Local);FHitResult Hit;
                    if(Trace(At,Hit))
                    {
                        const FVector Rotated=Origin+Tilt.RotateVector(At-Origin);
                        Height=FMath::Max(Height,float(Hit.ImpactPoint.Z-Rotated.Z-8.f));
                    }
                }
                WantedGroundHeight=FMath::Clamp(Height,-80.f,60.f);WantedGroundRotation=Tilt;
            }
        }
    }
    GroundHeight=FMath::FInterpTo(GroundHeight,WantedGroundHeight,Dt,8.f);
    GroundRotation=FQuat::Slerp(GroundRotation,WantedGroundRotation,1.f-FMath::Exp(-6.f*Dt)).GetNormalized();
}

FTransform FM10FootPlantNode::Grounded(const FTransform& Bone) const
{
    if(!GroundEnabled)return Bone;
    FTransform Result=Bone;
    const FVector Pivot=Frame.TransformPosition(FVector(0,0,BaseFloorZ));
    Result.SetLocation(Frame.InverseTransformPosition(Pivot+GroundRotation.RotateVector(Frame.TransformPosition(Bone.GetLocation())-Pivot)+FVector(0,0,GroundHeight)));
    Result.SetRotation((Frame.GetRotation().Inverse()*GroundRotation*Frame.GetRotation()*Bone.GetRotation()).GetNormalized());
    return Result;
}

FTransform FM10FootPlantNode::RemoveGrounding(const FTransform& Bone) const
{
    if(!GroundEnabled)return Bone;
    FTransform Result=Bone;
    const FVector Pivot=Frame.TransformPosition(FVector(0,0,BaseFloorZ));
    Result.SetLocation(Frame.InverseTransformPosition(Pivot+GroundRotation.Inverse().RotateVector(Frame.TransformPosition(Bone.GetLocation())-Pivot-FVector(0,0,GroundHeight))));
    Result.SetRotation((Frame.GetRotation().Inverse()*GroundRotation.Inverse()*Frame.GetRotation()*Bone.GetRotation()).GetNormalized());
    return Result;
}
