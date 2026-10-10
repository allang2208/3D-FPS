#include "M14SoftBodyDeath.h"
#include "M14XPBDConstraints.h"
#include "HumanoidRagdollBudget.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"

bool UM14SoftBodyDeathComponent::Start(USkeletalMeshComponent* LivingMesh,UM14SoftBodyData* InData,const FVector& InheritedVelocity)
{
    if(Data)return true;
    if(!LivingMesh||!InData||!InData->CorpseMesh||InData->Nodes.IsEmpty())return false;
    Data=InData;MeshToWorld=LivingMesh->GetComponentTransform();Origin=MeshToWorld.GetLocation();
    WorldSpacingCm=Data->SpacingCm*float(MeshToWorld.GetScale3D().GetAbsMax());
    const int32 Count=Data->Nodes.Num();Positions.SetNum(Count);Previous.SetNum(Count);Initial.SetNum(Count);
    Velocities.Init(FVector::ZeroVector,Count);GroundPoint.Init(FVector::ZeroVector,Count);
    GroundNormal.Init(FVector::ZeroVector,Count);WallPoint.Init(FVector::ZeroVector,Count);WallNormal.Init(FVector::ZeroVector,Count);
    InvMass.Init(1.f,Count);Grounded.Init(0,Count);
    TArray<FTransform> Pose;Pose.Reserve(Data->SourceBoneNames.Num());
    // Read the displayed pose before any Death clip/reset can change it.
    for(FName Bone:Data->SourceBoneNames)Pose.Add(LivingMesh->GetSocketTransform(Bone));
    for(int32 I=0;I<Count;++I)
    {
        const auto& N=Data->Nodes[I];FVector P=FVector::ZeroVector;
        for(int32 J=0;J<N.SourceBones.Num();++J)
        {
            const int32 B=N.SourceBones[J];
            P+=Pose[B].TransformPosition(Data->SourceRefFrames[B].InverseTransformPosition(N.Rest))*N.SourceWeights[J];
        }
        Positions[I]=ToSimulation(P);Initial[I]=Positions[I];
        const float Height=FMath::Clamp(float(N.Rest.Z/300.),0.f,1.f);
        const FVector Buckle=GetOwner()->GetActorForwardVector()*(.42*Height)+GetOwner()->GetActorRightVector()*(.10*FMath::Sin(Height*7.));
        Velocities[I]=Data->bCollapseInPlace?
            FVector(0,0,FMath::Clamp(InheritedVelocity.Z,-150.,0.))*.01:
            InheritedVelocity.GetClampedToMaxSize(150.)*.01+Buckle;
        if(I>=Data->SoftNodeCount)InvMass[I]=.35f;
    }
    Previous=Positions;TracePosition=Positions;
    TArray<uint8> Unsupported;Unsupported.Init(0,Count);
    if(Data->bCollapseInPlace)
        for(int32 I:Data->UnsupportedNodes)if(Unsupported.IsValidIndex(I))Unsupported[I]=1;
    RelaxedEdges.Reserve(Data->Edges.Num());RelaxedTets.Reserve(Data->Tets.Num());
    for(const auto& E:Data->Edges)RelaxedEdges.Add(E.Kind==0&&(Unsupported[E.A]||Unsupported[E.B]));
    for(const auto& T:Data->Tets)
    {
        uint8 Relaxed=0;for(int32 I:T.Nodes)Relaxed|=Unsupported[I];
        RelaxedTets.Add(Relaxed);
    }
    for(const auto& E:Data->Edges)Lengths.Add(float(FVector::Distance(Positions[E.A],Positions[E.B])));
    for(const auto& T:Data->Tets)
    {
        const auto& N=T.Nodes;
        Volumes.Add(float(M14XPBD::Volume(Positions[N[0]],Positions[N[1]],Positions[N[2]],Positions[N[3]])));
    }
    EdgeLambda.Init(0.f,Lengths.Num());VolumeLambda.Init(0.f,Volumes.Num());BarrierLambda.Init(0.f,Volumes.Num());
    for(const auto& H:Data->Hardware)
        HardwareRotation.Add(Pose[H.SourceBone].GetRotation()*Data->SourceRefFrames[H.SourceBone].GetRotation().Inverse()*MeshToWorld.GetRotation().Inverse());
    for(int32 I=0;I<Count;++I)RefreshContact(I);
    ProjectContacts();ProjectHardware();
    if(GetWorld()->GetNetMode()!=NM_DedicatedServer)
    {
        Display=NewObject<UPoseableMeshComponent>(GetOwner(),TEXT("M14SoftCorpseDisplay"));
        Display->SetSkinnedAssetAndUpdate(Data->CorpseMesh);
        // Preserve per-instance wound/skin parameters on the deformed-normal materials.
        for(int32 Slot=0;Slot<LivingMesh->GetNumMaterials();++Slot)
            if(auto* Source=LivingMesh->GetMaterial(Slot))
                if(auto* Base=Display->GetMaterial(Slot))
                {
                    auto* Material=UMaterialInstanceDynamic::Create(Base,Display);
                    Material->CopyMaterialUniformParameters(Source);
                    Display->SetMaterial(Slot,Material);
                }
        Display->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Display->SetBoundsScale(3.f);Display->SetForcedLOD(1);
        Display->RegisterComponent();Display->SetWorldTransform(MeshToWorld);
        Display->SetComponentTickEnabled(false);
        BindFrames=Data->CorpseMesh->GetRefSkeleton().GetRefBonePose();
        UpdateMesh();
        // Production LODs are reduced from the already XPBD-bound corpse and
        // retain its full skeleton. Single-LOD legacy corpses stay on LOD0.
        // The shared timer also updates settled corpses without restarting Tick.
        if(Display->GetNumLODs()>1)
            GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()->RegisterFrozenMesh(Display);
    }
    LivingMesh->SetVisibility(false,true);LivingMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    LivingMesh->SetSimulatePhysics(false);LivingMesh->SetComponentTickEnabled(false);LivingMesh->bPauseAnims=true;
    bBudget=GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()->Acquire(this,SimulatedBodyCount(),true);
    return true;
}

void UM14SoftBodyDeathComponent::RefreshContact(int32 I)
{
    FCollisionQueryParams Params(SCENE_QUERY_STAT(M14SoftDeathContact),true,GetOwner());
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    const FVector World=ToWorld(Positions[I]);FHitResult Hit;
    // Begin at the node, not above it: a hanging corpse's old +35 cm start
    // can cross a thin ceiling and mistake its upper face for floor support.
    // Initial overlap recovery belongs to the sphere sweep below.
    if(GetWorld()->LineTraceSingleByObjectType(Hit,World,World-FVector(0,0,650),Objects,Params)
        &&!Hit.bStartPenetrating&&Hit.ImpactNormal.Z>.15&&Hit.ImpactPoint.Z<=World.Z)
    {GroundPoint[I]=ToSimulation(Hit.ImpactPoint);GroundNormal[I]=Hit.ImpactNormal;}
    else GroundNormal[I]=FVector::ZeroVector;
    WallNormal[I]=FVector::ZeroVector;
    if(GetWorld()->SweepSingleByObjectType(Hit,ToWorld(TracePosition[I]),World,FQuat::Identity,Objects,FCollisionShape::MakeSphere(1.5f),Params))
    {
        // Cache a contact plane, never rewind a point to a sweep that began
        // several frames ago. Projection and velocity response happen together.
        const FVector Point=Hit.bStartPenetrating?
            ToWorld(TracePosition[I])+Hit.Normal*(Hit.PenetrationDepth-1.5):Hit.ImpactPoint;
        if(Hit.Normal.Z>=.5){GroundPoint[I]=ToSimulation(Point);GroundNormal[I]=Hit.Normal;}
        else {WallPoint[I]=ToSimulation(Point);WallNormal[I]=Hit.Normal;}
    }
    TracePosition[I]=Positions[I];
}

void UM14SoftBodyDeathComponent::ProjectContacts()
{
    for(int32 I=0;I<Positions.Num();++I)
    {
        Grounded[I]=0;
        if(!GroundNormal[I].IsNearlyZero())
        {
            const double D=(Positions[I]-GroundPoint[I]).Dot(GroundNormal[I]);
            if(D<.016)Positions[I]+=GroundNormal[I]*(.016-D);
            Grounded[I]=D<.025;
        }
        if(!WallNormal[I].IsNearlyZero())
        {
            const double D=(Positions[I]-WallPoint[I]).Dot(WallNormal[I]);
            if(D<.016)Positions[I]+=WallNormal[I]*(.016-D);
        }
    }
}

void UM14SoftBodyDeathComponent::ProjectHardware()
{
    for(int32 Index=0;Index<Data->Hardware.Num();++Index)
    {
        const auto& H=Data->Hardware[Index];FVector Center=FVector::ZeroVector;
        for(int32 N:H.Nodes)Center+=Positions[N];Center/=4.;
        FVector Columns[3]={FVector::ZeroVector,FVector::ZeroVector,FVector::ZeroVector};
        for(int32 N:H.Nodes)
        {
            const FVector Q=MeshToWorld.TransformVector(Data->Nodes[N].Rest-H.Center)*.01;
            const FVector P=Positions[N]-Center;Columns[0]+=P*Q.X;Columns[1]+=P*Q.Y;Columns[2]+=P*Q.Z;
        }
        FQuat& Rotation=HardwareRotation[Index];
        for(int32 Iteration=0;Iteration<6;++Iteration)
        {
            const FVector X=Rotation.GetAxisX(),Y=Rotation.GetAxisY(),Z=Rotation.GetAxisZ();
            const FVector Omega=(X.Cross(Columns[0])+Y.Cross(Columns[1])+Z.Cross(Columns[2]))/
                (FMath::Abs(X.Dot(Columns[0])+Y.Dot(Columns[1])+Z.Dot(Columns[2]))+1.e-10);
            const double Angle=Omega.Length();if(Angle<1.e-7)break;
            Rotation=FQuat(Omega/Angle,FMath::Min(Angle,.5))*Rotation;Rotation.Normalize();
        }
        // Contact uses actual patch support samples, not a tall chain's bounding sphere.
        for(int32 N:H.Nodes)if(!GroundNormal[N].IsNearlyZero())
        {
            double Minimum=DBL_MAX;
            for(const FVector& Offset:H.SupportOffsets)
                Minimum=FMath::Min(Minimum,(Center+Rotation.RotateVector(MeshToWorld.TransformVector(Offset)*.01)-GroundPoint[N]).Dot(GroundNormal[N]));
            if(Minimum<.014)Center+=GroundNormal[N]*(.014-Minimum);
        }
        for(int32 N:H.Nodes)
            Positions[N]=Center+Rotation.RotateVector(MeshToWorld.TransformVector(Data->Nodes[N].Rest-H.Center)*.01);
    }
}

void UM14SoftBodyDeathComponent::SelfContacts()
{
    const double Diameter=WorldSpacingCm*.006;
    const double RestExclusion=WorldSpacingCm*.0175;
    TMultiMap<FIntVector,int32> Grid;Grid.Reserve(Data->SoftNodeCount);
    auto Cell=[&](const FVector& P){return FIntVector(FMath::FloorToInt(P.X/Diameter),FMath::FloorToInt(P.Y/Diameter),FMath::FloorToInt(P.Z/Diameter));};
    for(int32 I=0;I<Data->SoftNodeCount;++I)Grid.Add(Cell(Positions[I]),I);
    for(int32 I=0;I<Data->SoftNodeCount;++I)
    {
        const FIntVector K=Cell(Positions[I]);
        for(int32 X=-1;X<=1;++X)for(int32 Y=-1;Y<=1;++Y)for(int32 Z=-1;Z<=1;++Z)
        {
            const FIntVector Neighbor=K+FIntVector(X,Y,Z);
            for(auto It=Grid.CreateConstKeyIterator(Neighbor);It;++It)
            {
                const int32 J=It.Value();if(J<=I||FVector::DistSquared(Initial[I],Initial[J])<RestExclusion*RestExclusion)continue;
                const FVector D=Positions[I]-Positions[J];const double Length=D.Length();
                const double Sum=InvMass[I]+InvMass[J];if(Length>=Diameter||Length<1.e-7||Sum<=0.)continue;
                const FVector C=D*((Diameter-Length)/(Length*Sum));Positions[I]+=C*InvMass[I];Positions[J]-=C*InvMass[J];
                SelfContactPairs.Emplace(I,J);
            }
        }
    }
}

void UM14SoftBodyDeathComponent::Substep(float Dt)
{
    Previous=Positions;Elapsed+=Dt;SelfContactPairs.Reset();
    for(int32 I=0;I<Positions.Num();++I)
    {
        InvMass[I]=I<Data->SoftNodeCount?1.f:.35f;
        // Only an actual floor contact can briefly hold the original footing.
        // Low bind-pose nodes on a hanging body are still airborne.
        if(!Data->bCollapseInPlace&&Elapsed<.12f&&Grounded[I]&&Data->Nodes[I].Rest.Z<12.){InvMass[I]=0.f;Velocities[I]=FVector::ZeroVector;continue;}
        const float AirDamping=Data->bCollapseInPlace?1.2f:3.f;
        Velocities[I]=(Velocities[I]+FVector(0,0,-9.81)*Dt)*FMath::Exp(-AirDamping*Dt);
        Positions[I]+=Velocities[I]*Dt;
    }
    PredictedVelocities=Velocities;
    for(float& L:EdgeLambda)L=0.f;for(float& L:VolumeLambda)L=0.f;for(float& L:BarrierLambda)L=0.f;
    for(int32 Iteration=0;Iteration<10;++Iteration)
    {
        for(int32 I=0;I<Data->Tets.Num();++I)
        {
            const auto& N=Data->Tets[I].Nodes;FVector* P[4]={&Positions[N[0]],&Positions[N[1]],&Positions[N[2]],&Positions[N[3]]};
            const double W[4]={InvMass[N[0]],InvMass[N[1]],InvMass[N[2]],InvMass[N[3]]};
            // Released appendages retain an inversion barrier, but their volume
            // pressure must no longer hold the torso up through the feet.
            const double Compliance=RelaxedTets[I]?3.e-5:3.e-7;
            M14XPBD::VolumeConstraint(P,W,Volumes[I],Compliance,Dt,VolumeLambda[I],BarrierLambda[I]);
        }
        for(int32 I=0;I<Data->Edges.Num();++I)
        {
            const auto& E=Data->Edges[I];
            if(RelaxedEdges[I]&&FVector::DistSquared(Positions[E.A],Positions[E.B])<=FMath::Square(Lengths[I]))
            {
                // A limp limb can fold/shorten; no restorative compression
                // force pushes its grounded end back against the body.
                EdgeLambda[I]=0.f;continue;
            }
            const double Compliance=E.Kind==0?3.e-4:E.Kind==1?0.:E.Kind==3?1.e-6:2.e-6;
            M14XPBD::Distance(Positions[E.A],Positions[E.B],InvMass[E.A],InvMass[E.B],Lengths[I],Compliance,Dt,EdgeLambda[I]);
        }
        if(Iteration==3||Iteration==7)SelfContacts();
        LimitSurfaceStrain();ProjectContacts();ProjectHardware();
    }
    // Finish with the visible surface limits, not a volume/rigid correction
    // that can immediately stretch the last iteration's edges again.
    for(int32 Iteration=0;Iteration<4;++Iteration){LimitSurfaceStrain();ProjectContacts();}
    for(int32 I=0;I<Positions.Num();++I)
        Velocities[I]=(Positions[I]-Previous[I])/Dt;
    DampInternalVelocity(Dt);
    for(int32 I=0;I<Positions.Num();++I)
    {
        if(Grounded[I])
        {
            const double NormalSpeed=Velocities[I].Dot(GroundNormal[I]);
            const FVector Tangent=Velocities[I]-NormalSpeed*GroundNormal[I];
            // Zero restitution: depenetration cannot become a new upward kick.
            const double AllowedOutward=FMath::Max(0.,PredictedVelocities[I].Dot(GroundNormal[I]));
            Velocities[I]=GroundNormal[I]*FMath::Clamp(NormalSpeed,0.,AllowedOutward)+Tangent*FMath::Exp(-18.f*Dt);
        }
        if(!WallNormal[I].IsNearlyZero()&&(Positions[I]-WallPoint[I]).Dot(WallNormal[I])<.025)
        {
            const double Speed=Velocities[I].Dot(WallNormal[I]);
            const double Outward=FMath::Max(0.,PredictedVelocities[I].Dot(WallNormal[I]));
            Velocities[I]+=WallNormal[I]*(FMath::Clamp(Speed,0.,Outward)-Speed);
        }
        Velocities[I]=Velocities[I].GetClampedToMaxSize(8.);
    }
}

void UM14SoftBodyDeathComponent::LimitSurfaceStrain()
{
    for(int32 I=0;I<Data->Edges.Num();++I)
    {
        const auto& E=Data->Edges[I];
        const double Length=FVector::Distance(Positions[E.A],Positions[E.B]);
        const bool Metal=E.Kind==3;
        const double Target=FMath::Clamp(Length,Metal?Lengths[I]*.85:0.,Lengths[I]*(Metal?1.08:1.20));
        if(FMath::Abs(Target-Length)>1.e-7)
        {float L=0.f;M14XPBD::Distance(Positions[E.A],Positions[E.B],InvMass[E.A],InvMass[E.B],Target,0.,1.,L);}
    }
}

void UM14SoftBodyDeathComponent::DampInternalVelocity(float Dt)
{
    // Dissipate only relative strain velocity, preserving whole-body falling
    // and rotation instead of masking chatter by freezing the visible mesh.
    for(int32 Pass=0;Pass<2;++Pass)for(int32 I=0;I<Data->Edges.Num();++I)
    {
        const auto& E=Data->Edges[I];
        const double Sum=InvMass[E.A]+InvMass[E.B];if(Sum<=0.)continue;
        const FVector Axis=(Positions[E.A]-Positions[E.B]).GetSafeNormal();
        const double Relative=(Velocities[E.A]-Velocities[E.B]).Dot(Axis);
        const double Damping=1.-FMath::Exp(-(RelaxedEdges[I]?.7:E.Kind==3?12.:4.)*Dt);
        const FVector Impulse=Axis*(Relative*Damping/Sum);
        Velocities[E.A]-=Impulse*InvMass[E.A];Velocities[E.B]+=Impulse*InvMass[E.B];
    }
    for(const FIntPoint& Pair:SelfContactPairs)
    {
        const int32 A=Pair.X,B=Pair.Y;const FVector Delta=Positions[A]-Positions[B];
        if(Delta.Length()>WorldSpacingCm*.0066)continue;
        const double Sum=InvMass[A]+InvMass[B];if(Sum<=0.)continue;
        const FVector Axis=Delta.GetSafeNormal();
        const double Speed=(Velocities[A]-Velocities[B]).Dot(Axis);
        const double Outward=FMath::Max(0.,(PredictedVelocities[A]-PredictedVelocities[B]).Dot(Axis));
        const FVector Impulse=Axis*((FMath::Clamp(Speed,0.,Outward)-Speed)/Sum);
        Velocities[A]+=Impulse*InvMass[A];Velocities[B]-=Impulse*InvMass[B];
    }
}

void UM14SoftBodyDeathComponent::UpdateMesh()
{
    if(!Display)return;
    Display->BoneSpaceTransforms=BindFrames;
    const FTransform Root=BindFrames[0];
    for(int32 I=0;I<Data->SoftNodeCount;++I)
    {
        const FVector Local=MeshToWorld.InverseTransformPosition(ToWorld(Positions[I]));
        Display->BoneSpaceTransforms[Data->Nodes[I].RenderBone]=FTransform(FQuat::Identity,Local).GetRelativeTransform(Root);
    }
    for(int32 I=0;I<Data->Hardware.Num();++I)
    {
        const auto& H=Data->Hardware[I];FVector Center=FVector::ZeroVector;
        for(int32 N:H.Nodes)Center+=Positions[N];Center/=4.;
        const FQuat LocalRotation=MeshToWorld.GetRotation().Inverse()*HardwareRotation[I]*MeshToWorld.GetRotation();
        const FTransform Local(LocalRotation,MeshToWorld.InverseTransformPosition(ToWorld(Center)));
        Display->BoneSpaceTransforms[H.RenderBone]=Local.GetRelativeTransform(Root);
    }
    Display->MarkRefreshTransformDirty();Display->RefreshBoneTransforms();
}

bool UM14SoftBodyDeathComponent::Advance(float Dt)
{
    if(!Data||bSettled)return bSettled;
    if(!bBudget)
    {
        BudgetRetry-=Dt;if(BudgetRetry>0.f)return false;BudgetRetry=.2f;
        bBudget=GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()->Acquire(this,SimulatedBodyCount(),true);
        if(!bBudget)return false; // Keep the captured pose; never fall back to the broken morph collapse.
    }
    // Ground support is cached for every point. Refresh a bounded moving subset
    // and sweep its path for walls; no full-resolution collision or vertex readback.
    for(int32 J=0;J<FMath::Min(64,Positions.Num());++J)
    {RefreshContact(ContactCursor);ContactCursor=(ContactCursor+1)%Positions.Num();}
    Accumulator=FMath::Min(Accumulator+Dt,.05f);
    constexpr float Step=1.f/120.f;
    while(Accumulator>=Step){Substep(Step);Accumulator-=Step;}
    UpdateMesh();
    double Energy=0.;int32 Contacts=0;
    for(int32 I=0;I<Velocities.Num();++I){Energy+=Velocities[I].SquaredLength();Contacts+=Grounded[I]?1:0;}
    const bool Quiet=Elapsed>2.f&&Contacts>FMath::Max(6,Data->SoftNodeCount/12)&&Energy/Velocities.Num()<.0016;
    QuietSeconds=Quiet?QuietSeconds+Dt:0.f;
    if(QuietSeconds>.7f){bSettled=true;ReleaseBudget();}
    return bSettled;
}
void UM14SoftBodyDeathComponent::FreezeForBudget()
{if(CanReleaseCorpseBudget()){bSettled=true;ReleaseBudget();}}
void UM14SoftBodyDeathComponent::ReleaseBudget()
{
    if(bBudget&&GetWorld())GetWorld()->GetSubsystem<UHumanoidRagdollBudget>()->Release(this);
    bBudget=false;
}
void UM14SoftBodyDeathComponent::EndPlay(const EEndPlayReason::Type Reason)
{ReleaseBudget();Super::EndPlay(Reason);}
