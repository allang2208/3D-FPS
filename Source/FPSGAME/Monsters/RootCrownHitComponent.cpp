#include "RootCrownHitComponent.h"
#include "RootCrownRigPreview.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "PhysicsEngine/SkeletalBodySetup.h"

URootCrownHitComponent::URootCrownHitComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    PrimaryComponentTick.TickInterval=1.f/30.f;
}
void URootCrownHitComponent::InitializeSurface()
{
    Crown=Cast<ARootCrownRigPreview>(GetOwner());Hulls.Reset();History.Reset();
    if(!Crown.IsValid()||!Crown->HasAuthority()){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteComponent(Crown->GetMesh());
    const auto* Physics=Crown->GetMesh()->GetPhysicsAsset();
    if(!Physics)return;
    for(const auto& Body:Physics->SkeletalBodySetups)if(Body)
        for(const auto& Convex:Body->AggGeom.ConvexElems)
        {
            FRootCrownHitHull Hull;Hull.Bone=Body->BoneName;Hull.Local=Convex.GetTransform();
            Convex.GetPlanes(Hull.Planes);
            if(Hull.Planes.Num()>=4)Hulls.Add(MoveTemp(Hull));
        }
    History.Reserve(32);
    FRootCrownHitPose Initial;Initial.At=Crown->ActionClock();
    Initial.CapsuleCenter=Crown->GetCapsuleComponent()->GetComponentLocation();
    for(const auto& Hull:Hulls)Initial.Frames.Add(Hull.Local*Crown->GetMesh()->GetSocketTransform(Hull.Bone));
    History.Add(MoveTemp(Initial));
}
void URootCrownHitComponent::TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Dt,Type,Function);
    if(!Crown.IsValid()||Crown->Dead()){SetComponentTickEnabled(false);return;}
    if(Hulls.IsEmpty())return;
    FRootCrownHitPose Pose;Pose.At=Crown->ActionClock();Pose.Frames.Reserve(Hulls.Num());
    Pose.CapsuleCenter=Crown->GetCapsuleComponent()->GetComponentLocation();
    for(const auto& Hull:Hulls)Pose.Frames.Add(Hull.Local*Crown->GetMesh()->GetSocketTransform(Hull.Bone));
    if(History.Num()==32)History.RemoveAt(0,1,EAllowShrinking::No);
    History.Add(MoveTemp(Pose));
}
bool URootCrownHitComponent::ResolveAt(const FVector& Start,const FVector& Point,double At,bool Melee,bool CapsuleContact,FHitResult& Out,float RayPaddingCM) const
{
    if(History.IsEmpty())return false;
    int32 Upper=0;
    while(Upper<History.Num()-1&&History[Upper].At<At)++Upper;
    const auto& B=History[Upper];const auto& A=History[FMath::Max(0,Upper-1)];
    const float Alpha=B.At>A.At?FMath::Clamp(float((At-A.At)/(B.At-A.At)),0.f,1.f):1.f;
    if(CapsuleContact)
    {
        // Existing quick/area melee queries deliberately report the Pawn capsule.
        // Preserve their body hit semantics; a capsule contact can never be a weakpoint.
        const auto* Capsule=Crown->GetCapsuleComponent();
        const FVector Center=FMath::Lerp(A.CapsuleCenter,B.CapsuleCenter,Alpha);
        const double Radius=Capsule->GetScaledCapsuleRadius();
        const FVector Axis=FVector::UpVector*FMath::Max(0.,double(Capsule->GetScaledCapsuleHalfHeight())-Radius);
        const FVector Closest=FMath::ClosestPointOnSegment(Point,Center-Axis,Center+Axis);
        if(FVector::DistSquared(Point,Closest)>FMath::Square(Radius+18.))return false;
        Out=FHitResult();Out.bBlockingHit=true;Out.Location=Out.ImpactPoint=Point;
        Out.Normal=Out.ImpactNormal=(Point-Closest).GetSafeNormal();Out.TraceStart=Start;Out.TraceEnd=Point;
        Out.Component=Crown->GetCapsuleComponent();Out.HitObjectHandle=FActorInstanceHandle(Crown.Get());
        return true;
    }
    const FVector Direction=(Point-Start).GetSafeNormal();
    const FVector End=Point+Direction*15.f;
    double Best=DBL_MAX;FName Bone;FVector Impact=Point,Normal=-Direction;
    for(int32 I=0;I<Hulls.Num();++I)
    {
        FTransform Frame;Frame.Blend(A.Frames[I],B.Frames[I],Alpha);
        const FVector S=Frame.InverseTransformPosition(Start),E=Frame.InverseTransformPosition(End);
        // Melee sweeps can report a contact slightly outside a convex surface.
        const double Padding=(Melee?18.:double(RayPaddingCM))/FMath::Max(.001,Frame.GetScale3D().GetAbsMax());
        double Enter=0.,Exit=1.;FVector EntryNormal=-Direction;bool Inside=true;
        if(Melee)
        {
            const FVector P=Frame.InverseTransformPosition(Point);double Closest=-DBL_MAX;
            for(const auto& Plane:Hulls[I].Planes)
            {
                const double D=Plane.PlaneDot(P);
                if(D>Padding){Inside=false;break;}
                if(D>Closest){Closest=D;EntryNormal=Plane.GetNormal();}
            }
            if(Inside)
            {
                const double Score=FMath::Abs(Closest)*Frame.GetScale3D().GetAbsMax();
                if(Score<Best){Best=Score;Bone=Hulls[I].Bone;Impact=Point;Normal=Frame.TransformVectorNoScale(EntryNormal).GetSafeNormal();}
            }
            continue;
        }
        for(const auto& Plane:Hulls[I].Planes)
        {
            const double DS=Plane.PlaneDot(S)-Padding,DE=Plane.PlaneDot(E)-Padding;
            if(DS>0.&&DE>0.){Inside=false;break;}
            if(DS<=0.&&DE<=0.)continue;
            const double T=DS/(DS-DE);
            if(DS>DE){if(T>Enter){Enter=T;EntryNormal=Plane.GetNormal();}}
            else Exit=FMath::Min(Exit,T);
            if(Enter>Exit){Inside=false;break;}
        }
        if(Inside&&Enter<Best)
        {Best=Enter;Bone=Hulls[I].Bone;Impact=FMath::Lerp(Start,End,Enter);Normal=Frame.TransformVectorNoScale(EntryNormal).GetSafeNormal();}
    }
    if(Bone.IsNone()||(!Melee&&FVector::DistSquared(Impact,Point)>FMath::Square(35.f)))return false;
    Out=FHitResult();Out.bBlockingHit=true;Out.BoneName=Bone;Out.Location=Out.ImpactPoint=Impact;
    Out.Normal=Out.ImpactNormal=Normal;Out.TraceStart=Start;Out.TraceEnd=End;
    Out.Component=Crown->GetMesh();Out.HitObjectHandle=FActorInstanceHandle(Crown.Get());
    return true;
}
bool URootCrownHitComponent::ResolveRemoteContact(const FVector& Start,const FVector& Point,double At,bool Melee,FName ReportedComponent,FHitResult& Out) const
{
    if(!Crown.IsValid()||!Crown->HasAuthority()||Crown->Dead()||Start.ContainsNaN()||Point.ContainsNaN()||!FMath::IsFinite(At))return false;
    const double Now=Crown->ActionClock();if(At<=0.)At=Now;
    if(At<Now-.9||At>Now+.1)return false;
    // Allow the existing simulated-proxy smoothing delay, never a client-selected bone.
    const bool CapsuleContact=Melee&&ReportedComponent==Crown->GetCapsuleComponent()->GetFName();
    // Try the real surface first. Inflating every leaf can create an earlier
    // grazing contact far from a legitimate reported impact and reject it at
    // the 35 cm receipt bound. Retain padding only as the existing latency fallback.
    for(double Offset:{0.,-.05,-.1})if(ResolveAt(Start,Point,At+Offset,Melee,CapsuleContact,Out,0.f))return true;
    if(!Melee)for(double Offset:{0.,-.05,-.1})if(ResolveAt(Start,Point,At+Offset,false,false,Out,4.f))return true;
    return false;
}
