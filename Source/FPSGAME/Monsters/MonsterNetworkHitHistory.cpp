#include "MonsterNetworkHitHistory.h"
#include "BoundCongregate.h"
#include "BoundCongregateTentacleGround.h"
#include "HeQueMonster.h"
#include "M10Mawcrawler.h"
#include "M66IncineratorMonster.h"
#include "MonsterCombatComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

bool FMonsterNetworkHitHistory::Supports(const AActor* Owner)
{
    return Owner&&(Owner->IsA<AM10Mawcrawler>()||Owner->IsA<AM66IncineratorMonster>()||
        Owner->IsA<AHeQueMonster>()||Owner->IsA<ABoundCongregate>());
}
FMonsterNetworkHitHistory::FMonsterNetworkHitHistory(ACharacter* Owner):Character(Owner),Mesh(Owner->GetMesh())
{
    if(Owner->IsA<AM10Mawcrawler>())Bones.Add(TEXT("head"));
    else if(Owner->IsA<AM66IncineratorMonster>())Bones={TEXT("Bone_001"),TEXT("Bone_006")};
    else if(Owner->IsA<ABoundCongregate>())
        for(int32 I=7;I<=56;++I)Bones.Add(*FString::Printf(TEXT("attack_tentacle_%02d"),I));
    else if(const auto* Physics=Mesh->GetPhysicsAsset())
        for(const auto& Body:Physics->SkeletalBodySetups)if(Body&&Body->DefaultInstance.GetCollisionEnabled()!=ECollisionEnabled::NoCollision)
        {
            const int32 Bone=Bones.AddUnique(Body->BoneName);
            for(const auto& Convex:Body->AggGeom.ConvexElems)
            {
                if(Convex.GetCollisionEnabled()==ECollisionEnabled::NoCollision||Convex.GetCollisionEnabled()==ECollisionEnabled::PhysicsOnly)continue;
                FHull Hull;Hull.Bone=Bone;Hull.Local=Convex.GetTransform();Convex.GetPlanes(Hull.Planes);
                if(Hull.Planes.Num()>=4)Hulls.Add(MoveTemp(Hull));
            }
        }
    History.Reserve(32);
}
double FMonsterNetworkHitHistory::Clock() const
{
    const auto* World=Character.IsValid()?Character->GetWorld():nullptr;
    const auto* State=World?World->GetGameState():nullptr;
    return State?State->GetServerWorldTimeSeconds():World?World->GetTimeSeconds():0.;
}
void FMonsterNetworkHitHistory::Capture()
{
    if(!Character.IsValid()||!Character->HasAuthority()||!Mesh.IsValid()||Bones.IsEmpty())return;
    if(const auto* Combat=Character->FindComponentByClass<UMonsterCombatComponent>();Combat&&Combat->IsDead())return;
    const double Now=Clock();
    const auto* Bound=Cast<ABoundCongregate>(Character.Get());
    const bool Active=Bound&&Bound->TentacleActive()&&!Bound->TentacleRecovering();
    const bool Changed=Active!=bWasTentacleActive;
    if(Active&&!bWasTentacleActive)TentacleStartedAt=Now;
    bWasTentacleActive=Active;
    if(!Changed&&!History.IsEmpty()&&Now-History.Last().At<1./30.)return;
    FPose Pose;Pose.At=Now;Pose.bTentacleActive=Active;Pose.Frames.Reserve(Bones.Num());
    for(const FName Bone:Bones)Pose.Frames.Add(Mesh->GetSocketTransform(Bone));
    if(History.Num()==32)History.RemoveAt(0,1,EAllowShrinking::No);
    History.Add(MoveTemp(Pose));
}
bool FMonsterNetworkHitHistory::PoseAt(double At,FPose& Out) const
{
    if(History.IsEmpty()||At<History[0].At-.04||At>History.Last().At+.1)return false;
    int32 Upper=0;while(Upper<History.Num()-1&&History[Upper].At<At)++Upper;
    const auto& B=History[Upper];const auto& A=History[FMath::Max(0,Upper-1)];
    const float Alpha=B.At>A.At?FMath::Clamp(float((At-A.At)/(B.At-A.At)),0.f,1.f):1.f;
    Out.At=At;Out.bTentacleActive=Alpha<1.f?A.bTentacleActive:B.bTentacleActive;
    Out.Frames.SetNum(Bones.Num());
    for(int32 I=0;I<Bones.Num();++I)Out.Frames[I].Blend(A.Frames[I],B.Frames[I],Alpha);
    return true;
}
bool FMonsterNetworkHitHistory::HeartContact(const FHitResult& Hit,const FPose& Pose,FHitResult& Out) const
{
    const FVector Direction=(Hit.ImpactPoint-Hit.TraceStart).GetSafeNormal();if(Direction.IsNearlyZero())return false;
    const FVector End=Hit.ImpactPoint+Direction*30.f;
    double Best=DBL_MAX;int32 Bone=INDEX_NONE;FVector Point,Normal;
    // Test all historical bodies, so an intervening limb cannot grant a heart hit.
    for(const auto& Hull:Hulls)
    {
        const FTransform Frame=Hull.Local*Pose.Frames[Hull.Bone];
        const FVector S=Frame.InverseTransformPosition(Hit.TraceStart),E=Frame.InverseTransformPosition(End);
        double Enter=0.,Exit=1.;FVector EntryNormal=-Direction;bool Inside=true;
        for(const auto& Plane:Hull.Planes)
        {
            const double DS=Plane.PlaneDot(S),DE=Plane.PlaneDot(E);
            if(DS>0.&&DE>0.){Inside=false;break;}
            if(DS<=0.&&DE<=0.)continue;
            const double T=DS/(DS-DE);
            if(DS>DE){if(T>Enter){Enter=T;EntryNormal=Plane.GetNormal();}}
            else Exit=FMath::Min(Exit,T);
            if(Enter>Exit){Inside=false;break;}
        }
        if(Inside&&Enter<Best)
        {Best=Enter;Bone=Hull.Bone;Point=FMath::Lerp(Hit.TraceStart,End,Enter);Normal=Frame.TransformVectorNoScale(EntryNormal).GetSafeNormal();}
    }
    if(Bone<0||FVector::DistSquared(Point,Hit.ImpactPoint)>FMath::Square(60.f))return false;
    Out=Hit;Out.Component=Mesh;Out.BoneName=Bones[Bone];Out.Location=Out.ImpactPoint=Point;
    Out.Normal=Out.ImpactNormal=Normal;return true;
}
bool FMonsterNetworkHitHistory::Resolve(FHitResult& Hit,double At) const
{
    if(!Character.IsValid()||!Mesh.IsValid()||Hit.GetActor()!=Character.Get())return false;
    const double Now=Clock();if(At<=0.)At=Now;
    if(!FMath::IsFinite(At)||At<Now-.9||At>Now+.1||Hit.ImpactPoint.ContainsNaN()||Hit.TraceStart.ContainsNaN())return false;
    const auto* Bound=Cast<ABoundCongregate>(Character.Get());
    if(Bound)
    {
        if(!ABoundCongregate::IsTentaclePart(Hit))return true;
        if(!Bound->TentacleActive()||Bound->TentacleRecovering()||Bound->TentacleHealth<=0.f||At<TentacleStartedAt-.04)return false;
        const int32 I=Bones.IndexOfByKey(Hit.BoneName);if(I<0)return false;
        for(double Offset:{0.,-.05,-.1})
        {
            FPose Pose;if(!PoseAt(At+Offset,Pose)||!Pose.bTentacleActive)continue;
            const FVector A=Pose.Frames[I].GetLocation(),B=Pose.Frames[FMath::Min(I+1,Bones.Num()-1)].GetLocation();
            if(FMath::PointDistToSegment(Hit.ImpactPoint,A,B)>FCongregateTentacleGround::Radius(I+7)+20.f)continue;
            const float Alpha=FMath::Clamp(FVector::DotProduct(Hit.ImpactPoint-A,B-A)/FMath::Max(1.,(B-A).SizeSquared()),0.,1.);
            // The part still exists now. Rebase the accepted contact to its current
            // segment for the existing damage-pool guard; never redirect it to HP.
            Hit.Location=Hit.ImpactPoint=FMath::Lerp(Mesh->GetSocketLocation(Bones[I]),Mesh->GetSocketLocation(Bones[FMath::Min(I+1,Bones.Num()-1)]),Alpha);
            return true;
        }
        return false;
    }
    if(Character->IsA<AHeQueMonster>())
    {
        for(double Offset:{0.,-.05,-.1}){FPose Pose;FHitResult Contact;if(PoseAt(At+Offset,Pose)&&HeartContact(Hit,Pose,Contact)){Hit=Contact;return true;}}
        Hit.BoneName=NAME_None;Hit.Component=Mesh;return true;
    }
    const int32 I=Bones.IndexOfByKey(Hit.BoneName);if(I<0)return true;
    const FTransform Current=Mesh->GetSocketTransform(Hit.BoneName);
    for(double Offset:{0.,-.05,-.1})
    {
        FPose Pose;if(!PoseAt(At+Offset,Pose))continue;
        const auto& Then=Pose.Frames[I];FHitResult Contact=Hit;Contact.Component=Mesh;
        const auto Rebase=[&](const FVector& P){return Current.TransformPosition(Then.InverseTransformPosition(P));};
        Contact.Location=Contact.ImpactPoint=Rebase(Hit.ImpactPoint);Contact.TraceStart=Rebase(Hit.TraceStart);Contact.TraceEnd=Rebase(Hit.TraceEnd);
        Contact.Normal=Contact.ImpactNormal=Current.TransformVectorNoScale(Then.InverseTransformVectorNoScale(Hit.ImpactNormal)).GetSafeNormal();
        const bool Weak=Character->IsA<AM10Mawcrawler>()?CastChecked<AM10Mawcrawler>(Character.Get())->IsWeakpointHit(Contact):
            CastChecked<AM66IncineratorMonster>(Character.Get())->IsWeakpointHit(Contact);
        if(Weak){Hit=Contact;return true;}
    }
    // A shell/torso contact must not become critical because the head moved into
    // the old world point while the packet was in flight.
    Hit.BoneName=NAME_None;return true;
}
