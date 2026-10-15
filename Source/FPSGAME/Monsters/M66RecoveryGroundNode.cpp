#include "M66RecoveryGroundNode.h"
#include "M66IncineratorMonster.h"
#include "MonsterGroundSupport.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkinWeightVertexBuffer.h"

void FM66RecoveryGroundNode::Cache(const AM66IncineratorMonster* Owner)
{
    auto* Mesh=Owner->GetMesh();auto* Asset=Mesh->GetSkeletalMeshAsset();if(CachedMesh==Asset)return;
    CachedMesh=Asset;Samples.Reset();SourceCS.Reset();if(!Asset)return;
    const auto* Render=Mesh->GetSkeletalMeshRenderData();const auto* Skin=Mesh->GetSkinWeightBuffer(0);
    if(!Render||Render->LODRenderData.IsEmpty()||!Skin||!Asset->GetLODInfo(0)->bAllowCPUAccess)return;
    const auto& LOD=Render->LODRenderData[0];if(!LOD.GetNumVertices())return;
    const auto& Ref=Asset->GetRefSkeleton();TArray<FTransform> Bind=Ref.GetRefBonePose();
    for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)>=0)Bind[I]*=Bind[Ref.GetParentIndex(I)];
    SourceCS=Bind;
    // Bounded surface samples, including small sections. These are cached once;
    // no CPU readback, whole-mesh skinning, or scene query runs on an anim worker.
    for(const auto& Section:LOD.RenderSections)
    {
        if(Section.bDisabled||!Section.NumVertices)continue;
        const int32 Count=FMath::Min(int32(Section.NumVertices),FMath::Max(24,int32(int64(2048)*Section.NumVertices/LOD.GetNumVertices())));
        for(int32 I=0;I<Count;++I)
        {
            const uint32 V=Section.BaseVertexIndex+uint32(int64(I)*(Section.NumVertices-1)/FMath::Max(1,Count-1));
            const FVector Point(LOD.StaticVertexBuffers.PositionVertexBuffer.VertexPosition(V));auto& Sample=Samples.AddDefaulted_GetRef();
            for(uint32 J=0;J<Skin->GetMaxBoneInfluences();++J)
            {
                const float W=Skin->GetBoneWeight(V,J)/65535.f;if(W<=0)continue;
                const int32 Bone=Section.BoneMap[Skin->GetBoneIndex(V,J)];Sample.Add({Bone,Bind[Bone].InverseTransformPosition(Point),W});
            }
        }
    }
}
void FM66RecoveryGroundNode::Prepare(const AM66IncineratorMonster* Owner,float Dt)
{
    if(!Owner)return;
    if(Owner->HoldKnockdownDeathPose())return; // Keep the same terrain transform while waiting for the corpse packet.
    const auto Phase=Owner->ReactionPhase();float Age=0;bool Loop=false;Owner->ReactionClip(Age,Loop);
    const bool Airborne=Phase==EM66Reaction::Airborne;
    if(Airborne&&!WasAirborne){Release=Enabled;ReleaseTilt=Tilt;ReleaseHeight=Height;}
    WasAirborne=Airborne;
    if(Airborne&&Release&&Age<.14f)
    {
        // Re-launch can interrupt the supported get-up. Release its correction
        // over the same .14 s as the pose transition, without pulling an airborne body to the floor.
        const float Fade=1.f-FMath::SmoothStep(0.f,.14f,Age);
        Height=ReleaseHeight*Fade;Tilt=FQuat::Slerp(FQuat::Identity,ReleaseTilt,Fade).GetNormalized();
        MeshWorld=Owner->GetMesh()->GetComponentTransform();Pivot=Owner->GetActorLocation()-FVector(0,0,Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
        return;
    }
    Release=false;
    const float NextWeight=Phase==EM66Reaction::Landing?FMath::SmoothStep(0.f,.22f,Age):
        Phase==EM66Reaction::Down?1.f:Phase==EM66Reaction::GetUp?1.f-FMath::SmoothStep(.9f,1.8f,Age):0.f;
    Enabled=NextWeight>0.f&&!Owner->Dead()&&!Owner->GetMesh()->IsSimulatingPhysics();Weight=NextWeight;
    if(!Enabled){Height=0;Tilt=FQuat::Identity;QueryAge=1;return;}
    Cache(Owner);if(Samples.IsEmpty()||SourceCS.IsEmpty())return;
    MeshWorld=Owner->GetMesh()->GetComponentTransform();
    Pivot=Owner->GetActorLocation()-FVector(0,0,Owner->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    QueryAge+=FMath::Max(0.f,Dt);if(QueryAge<.05f)return;QueryAge=0;
    FMonsterGroundProbe Probe(Owner);TArray<FVector,TInlineAllocator<5>> FloorPoints;
    for(const FVector Offset:{FVector::ZeroVector,FVector(80,0,0),FVector(-80,0,0),FVector(0,80,0),FVector(0,-80,0)})
    {
        FHitResult H;const FVector At=Pivot+Offset;
        if(Probe.Trace(Owner->GetWorld(),At+FVector(0,0,65),At-FVector(0,0,200),FVector::UpVector,.5f,H))FloorPoints.Add(H.ImpactPoint);
    }
    float PlaneHeight=0;FQuat PlaneTilt;
    if(!MonsterGroundSupport::FitPlane(FloorPoints,Pivot,32.f,PlaneHeight,PlaneTilt))return;
    Tilt=FQuat::Slerp(FQuat::Identity,PlaneTilt,Weight).GetNormalized();
    const FVector Normal=PlaneTilt.RotateVector(FVector::UpVector);
    TArray<FVector,TInlineAllocator<2048>> Points;FBox Bounds(ForceInit);
    for(const auto& Sample:Samples)
    {
        FVector P=FVector::ZeroVector;for(const auto& I:Sample)P+=SourceCS[I.Bone].TransformPosition(I.Point)*I.Weight;
        P=Pivot+Tilt.RotateVector(MeshWorld.TransformPosition(P)-Pivot);Points.Add(P);Bounds+=P;
    }
    FVector Lowest[64];bool Used[64]={};const FVector Cell=Bounds.GetSize()/8.;
    for(const auto& P:Points)
    {
        const int32 X=FMath::Clamp(FMath::FloorToInt((P.X-Bounds.Min.X)/FMath::Max(1.,Cell.X)),0,7),Y=FMath::Clamp(FMath::FloorToInt((P.Y-Bounds.Min.Y)/FMath::Max(1.,Cell.Y)),0,7),I=Y*8+X;
        if(!Used[I]||P.Z<Lowest[I].Z){Lowest[I]=P;Used[I]=true;}
    }
    double Gap=1.e9;
    for(int32 I=0;I<64;++I)
    {
        if(!Used[I])continue;const auto& P=Lowest[I];
        const double PlaneZ=Pivot.Z+PlaneHeight-(Normal.X*(P.X-Pivot.X)+Normal.Y*(P.Y-Pivot.Y))/FMath::Max(.5,Normal.Z);
        FHitResult H;
        // Search near the fitted tread plane, not the top of a stair handrail.
        if(Probe.Trace(Owner->GetWorld(),FVector(P.X,P.Y,PlaneZ+22),FVector(P.X,P.Y,PlaneZ-220),FVector::UpVector,.5f,H))
            Gap=FMath::Min(Gap,P.Z-H.ImpactPoint.Z);
    }
    if(Gap<1.e8)Height=float(FMath::Clamp(.5-Gap,-100.,100.))*Weight;
}
void FM66RecoveryGroundNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    if(SourceCS.Num())for(int32 I=0;I<Bones.GetCompactPoseNumBones();++I)
    {
        const FCompactPoseBoneIndex B(I);const int32 Index=Bones.MakeMeshPoseIndex(B).GetInt();
        if(SourceCS.IsValidIndex(Index))SourceCS[Index]=Output.Pose.GetComponentSpaceTransform(B);
    }
    if(!Enabled||Samples.IsEmpty())return;
    FTransform Root=Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0));
    const FVector P=MeshWorld.TransformPosition(Root.GetLocation());
    Root.SetLocation(MeshWorld.InverseTransformPosition(Pivot+Tilt.RotateVector(P-Pivot)+FVector(0,0,Height)));
    Root.SetRotation((MeshWorld.GetRotation().Inverse()*Tilt*MeshWorld.GetRotation()*Root.GetRotation()).GetNormalized());
    Out.Emplace(FCompactPoseBoneIndex(0),Root);
}
