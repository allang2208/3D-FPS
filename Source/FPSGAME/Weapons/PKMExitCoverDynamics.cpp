#include "PKMExitCoverDynamics.h"
#include "PKMOutletCoverGeometry.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"

void FPKMExitCoverDynamics::Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose,
    int32 Tab, int32 NewTab, const TArray<int32>& Clips,
    bool OldBeltVisible, bool NewBeltVisible, bool Active)
{
    using namespace PKMOutletCoverGeometry;
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    if (!Asset) return;
    const auto& Ref=Asset->GetRefSkeleton();
    if (SourceMesh.Get()!=Asset || BoneCount!=Ref.GetNum())
    {
        SourceMesh=Asset; BoneCount=Ref.GetNum();
        Bone=Ref.FindBoneIndex(TEXT("PKM_ExitCover"));
        Parent=Bone!=INDEX_NONE?Ref.GetParentIndex(Bone):INDEX_NONE;
        if (Bone!=INDEX_NONE) BindLocal=Ref.GetRefBonePose()[Bone];
        LastTime=-1.; Angle=Speed=0.f;
    }
    if (!Pose.IsValidIndex(Bone) || !Pose.IsValidIndex(Parent)) return;
    // Always rebuild from the animated top cover, not last frame's override.
    const FTransform Mount=BindLocal*Pose[Parent];
    constexpr float Maximum=85.f*PI/180.f;
    float Clearance=0.f;
    const auto Contact=[&](int32 Index,const FVector& Low,const FVector& High)
    {
        if (!Pose.IsValidIndex(Index) || Pose[Index].GetScale3D().IsNearlyZero()) return;
        // Sample the upper/lower faces of the measured cosmetic belt bounds.
        // A short guide at the exit supports the flap; the hanging tail does not.
        for (int32 X=0;X<3;++X) for (int32 Y=0;Y<3;++Y) for (int32 Z=0;Z<2;++Z)
        {
            const FVector Offset(FMath::Lerp(Low.X,High.X,X*.5),
                FMath::Lerp(Low.Y,High.Y,Y*.5),Z?High.Z:Low.Z);
            const FVector Point=Pose[Index].GetLocation()+Pose[Index].TransformVectorNoScale(Offset);
            const FVector P=Mount.InverseTransformVectorNoScale(Point-Mount.GetLocation());
            if (P.X<.06 || FMath::Abs(P.Y)>HalfWidth+.08 ||
                FMath::Square(P.X)+FMath::Square(P.Z)>FMath::Square(LipLength+.16)) continue;
            const double Required=FMath::Atan2(P.Z+.12,P.X)-RestLipAngle;
            Clearance=FMath::Max(Clearance,FMath::Clamp(static_cast<float>(Required),0.f,Maximum));
        }
    };
    // Section visibility is supplied by the same normal/empty reload clock.
    // Hidden old belts and parked new belts cannot prop up an empty gun.
    if (OldBeltVisible)
    {
        Contact(Tab,TabMin,TabMax);
        for (int32 Index:Clips) Contact(Index,ClipMin,ClipMax);
    }
    if (NewBeltVisible) Contact(NewTab,TabMin,TabMax);

    const auto* World=Mesh.GetWorld();
    const FTransform Frame=Mount*Mesh.GetComponentTransform();
    const FVector Position=Frame.GetLocation();
    if (!Active || !World)
    {
        LastTime=-1.; Angle=Clearance; Speed=0.f;
        Acceleration=FVector::ZeroVector;
    }
    else
    {
        const double Now=World->GetTimeSeconds(),Elapsed=Now-LastTime;
        if (LastTime<0. || Elapsed<0. || Elapsed>.25 || (Position-LastPosition).SizeSquared()>10000.)
        {
            LastTime=Now; LastPosition=Position; LastVelocity=Acceleration=FVector::ZeroVector;
            Angle=Clearance; Speed=0.f;
        }
        else if (Elapsed>UE_SMALL_NUMBER)
        {
            const FVector Velocity=(Position-LastPosition)/Elapsed;
            Acceleration=FMath::Lerp(Acceleration,
                ((Velocity-LastVelocity)/Elapsed).GetClampedToMaxSize(8000.),1.-FMath::Exp(-28.*Elapsed));
            const FVector Force=Frame.InverseTransformVectorNoScale(
                FVector(0,0,World->GetGravityZ()*.30)-Acceleration*.55);
            constexpr double Omega=2.*UE_PI*2.8,Damping=.38;
            const double Duration=FMath::Min(Elapsed,.06);
            const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*240.));
            const float Dt=static_cast<float>(Duration/Steps);
            const float Lift=FMath::Max(0.f,Clearance-Angle);
            Angle=FMath::Max(Angle,Clearance);
            if (Lift>0.f) Speed=FMath::Max(Speed,FMath::Min(Lift*12.f,.7f));
            for (int32 I=0;I<Steps;++I)
            {
                const FVector Lever=FVector(FMath::Cos(RestLipAngle+Angle),0,FMath::Sin(RestLipAngle+Angle))*(LipLength*.5);
                const double Torque=FMath::Clamp(FVector::DotProduct(FVector(0,-1,0),FVector::CrossProduct(Lever,Force))
                    / FMath::Max(.25,Lever.SizeSquared()),-220.,220.);
                Speed+=static_cast<float>(Torque-Omega*Omega*(Angle-Clearance)-2.*Damping*Omega*Speed)*Dt;
                Angle+=Speed*Dt;
                if (Angle<Clearance)
                {
                    Angle=Clearance;
                    Speed=FMath::Max(0.f,Speed);
                }
                if (Angle>Maximum) { Angle=Maximum; if (Speed>0.f) Speed*=-.12f; }
            }
            LastTime=Now; LastPosition=Position; LastVelocity=Velocity;
        }
    }
    // Resolve contact immediately even when the pose is evaluated twice in a
    // tick. A damped target alone would allow the belt through during lag.
    Angle=FMath::Clamp(FMath::Max(Angle,Clearance),0.f,Maximum);
    const FVector Axis=Mount.TransformVectorNoScale(FVector(0,-1,0)).GetSafeNormal();
    Pose[Bone]=Mount;
    Pose[Bone].SetRotation((FQuat(Axis,Angle)*Mount.GetRotation()).GetNormalized());
}
