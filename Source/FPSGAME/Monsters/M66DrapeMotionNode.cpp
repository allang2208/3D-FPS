#include "M66DrapeMotionNode.h"
#include "M66IncineratorMonster.h"
#include "Animation/AnimInstanceProxy.h"
#include "Components/SkeletalMeshComponent.h"

FM66DrapeMotionNode::FM66DrapeMotionNode()
{
    Alpha=1.f;Pelvis.BoneName=TEXT("Bone_001");
    for(int32 C=0;C<Chains;++C)for(int32 J=0;J<Joints;++J)
        Flesh[C*Joints+J].BoneName=FName(*FString::Printf(TEXT("M66_Drape_%02d_%02d"),C,J));
    const TCHAR* Names[]={TEXT("Bone_012"),TEXT("Bone_011"),TEXT("Bone_010"),TEXT("Bone_017"),TEXT("Bone_016"),TEXT("Bone_015")};
    for(int32 I=0;I<6;++I)Leg[I].BoneName=Names[I];
}
void FM66DrapeMotionNode::ResetDynamics(ETeleportType)
{Initialized=false;ResetRequested=true;Solved=MAX_uint64;}
void FM66DrapeMotionNode::InitializeBoneReferences(const FBoneContainer& Bones)
{
    Pelvis.Initialize(Bones);
    for(int32 I=0;I<Count;++I)
    {
        Flesh[I].Initialize(Bones);
        if(Flesh[I].IsValidToEvaluate(Bones))Local[I]=Bones.GetRefPoseTransform(Flesh[I].GetCompactPoseIndex(Bones));
    }
    for(auto& Bone:Leg)Bone.Initialize(Bones);
    ResetDynamics(ETeleportType::ResetPhysics);
}
bool FM66DrapeMotionNode::IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones)
{
    if(!Pelvis.IsValidToEvaluate(Bones))return false;
    for(const auto& Bone:Flesh)if(!Bone.IsValidToEvaluate(Bones))return false;
    for(const auto& Bone:Leg)if(!Bone.IsValidToEvaluate(Bones))return false;
    return true;
}
void FM66DrapeMotionNode::Prepare(const AM66IncineratorMonster* Owner,float DeltaSeconds)
{
    ++Serial;Dt=FMath::Clamp(DeltaSeconds,0.f,1.f/15.f);
    const auto* Mesh=Owner?Owner->GetMesh():nullptr;
    Enabled=Mesh&&Owner->GetNetMode()!=NM_DedicatedServer&&!Mesh->IsSimulatingPhysics();
    if(!Enabled){ResetDynamics(ETeleportType::ResetPhysics);return;}
    Frame=Mesh->GetComponentTransform();WorldScale=float(Frame.GetScale3D().GetAbsMax());
    ResetRequested|=DeltaSeconds>.1f;
}
void FM66DrapeMotionNode::EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out)
{
    if(!Enabled)return;
    const auto& Bones=Output.Pose.GetPose().GetBoneContainer();
    if(Solved!=Serial)
    {
        FTransform Rest[Count];FVector Target[Count],LegWorld[6];float Length[Count]{};
        const FTransform Parent=Output.Pose.GetComponentSpaceTransform(Pelvis.GetCompactPoseIndex(Bones));
        for(int32 C=0;C<Chains;++C)for(int32 J=0;J<Joints;++J)
        {
            const int32 I=C*Joints+J;
            // Use authored locals once. Transition snapshots must not feed a
            // previous simulation result back into the next rest pose.
            Rest[I]=Local[I]*(J?Rest[I-1]:Parent);
            Target[I]=Frame.TransformPosition(Rest[I].GetLocation());
            if(J)Length[I]=float(FVector::Distance(Target[I],Target[I-1]));
        }
        for(int32 I=0;I<6;++I)
            LegWorld[I]=Frame.TransformPosition(Output.Pose.GetComponentSpaceTransform(Leg[I].GetCompactPoseIndex(Bones)).GetLocation());
        const bool Reset=ResetRequested||!Initialized||FVector::DistSquared(Target[0],PreviousTarget[0])>FMath::Square(120.f*WorldScale);
        if(Reset)for(int32 I=0;I<Count;++I){Position[I]=PreviousTarget[I]=Target[I];Velocity[I]=FVector::ZeroVector;}
        const int32 Steps=FMath::Max(1,FMath::CeilToInt(Dt*120.f));const float H=Dt/Steps;
        auto Collide=[&](FVector& Point)
        {
            // Pose-driven thigh and shin capsules keep the tissue outside legs.
            // No gameplay collision or replicated rigid bodies are introduced.
            for(int32 L=0;L<2;++L)for(int32 S=0;S<2;++S)
            {
                const FVector A=LegWorld[L*3+S],B=LegWorld[L*3+S+1],Axis=B-A;
                const double T=FMath::Clamp(FVector::DotProduct(Point-A,Axis)/FMath::Max(1.,Axis.SizeSquared()),0.,1.);
                const FVector Centre=A+Axis*T;const float Radius=(S?12.f:19.f)*WorldScale;
                FVector Delta=Point-Centre;const double Distance=Delta.Size();
                if(Distance<Radius)
                {
                    if(!Delta.Normalize())Delta=Frame.TransformVectorNoScale(FVector::ForwardVector);
                    Point=Centre+Delta*Radius;
                }
            }
        };
        if(H>UE_SMALL_NUMBER)for(int32 Step=0;Step<Steps;++Step)
        {
            const float Fraction=float(Step+1)/Steps;FVector Before[Count],Goal[Count];
            for(int32 I=0;I<Count;++I)
            {
                Before[I]=Position[I];Goal[I]=FMath::Lerp(PreviousTarget[I],Target[I],Fraction);
                if(I%Joints==0){Position[I]=Goal[I];Velocity[I]=FVector::ZeroVector;continue;}
                const float Flex=float(I%Joints)/float(Joints-1);
                const FVector Force=(Goal[I]-Position[I])*FMath::Lerp(42.f,24.f,Flex)-Velocity[I]*4.5f+FVector(0,0,-980.f);
                Velocity[I]=(Velocity[I]+Force*H).GetClampedToMaxSize(300.f*WorldScale);
                Position[I]+=Velocity[I]*H;
            }
            for(int32 Pass=0;Pass<4;++Pass)for(int32 C=0;C<Chains;++C)for(int32 J=1;J<Joints;++J)
            {
                const int32 I=C*Joints+J;Collide(Position[I]);
                const FVector Reference=(Goal[I]-Goal[I-1]).GetSafeNormal();
                FVector Direction=(Position[I]-Position[I-1]).GetSafeNormal(UE_SMALL_NUMBER,Reference);
                const FQuat Bend=FQuat::FindBetweenNormals(Reference,Direction);
                const float Limit=FMath::DegreesToRadians(28.f);
                const float Weight=FMath::Min(1.f,Limit/FMath::Max(.0001f,float(Bend.GetAngle())));
                Direction=FQuat::Slerp(FQuat::Identity,Bend,Weight).RotateVector(Reference);
                Position[I]=Position[I-1]+Direction*Length[I];
            }
            for(int32 I=0;I<Count;++I)if(I%Joints)
                Velocity[I]=((Position[I]-Before[I])/H).GetClampedToMaxSize(300.f*WorldScale);
        }
        for(int32 C=0;C<Chains;++C)for(int32 J=0;J<Joints;++J)
        {
            const int32 I=C*Joints+J,A=J==Joints-1?I-1:I,B=A+1;
            const FVector Before=(Rest[B].GetLocation()-Rest[A].GetLocation()).GetSafeNormal();
            const FVector After=Frame.InverseTransformVector(Position[B]-Position[A]).GetSafeNormal();
            Result[I]=Rest[I];Result[I].SetLocation(Frame.InverseTransformPosition(Position[I]));
            Result[I].SetRotation((FQuat::FindBetweenNormals(Before,After)*Rest[I].GetRotation()).GetNormalized());
            PreviousTarget[I]=Target[I];
        }
        Initialized=true;ResetRequested=false;Solved=Serial;
    }
    for(int32 I=0;I<Count;++I)Out.Emplace(Flesh[I].GetCompactPoseIndex(Bones),Result[I]);
    Out.Sort(FCompareBoneTransformIndex());
}
