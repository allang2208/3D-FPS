#include "StableHorseGroundMesh.h"
#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

namespace HorseGround
{
struct FGuardVertex
{
    FVector3f Rest;
    uint8 Bones[8];
    uint16 Weights[8];
};
struct FContactEdge {uint16 A,B;};
#include "StableHorseContactHull.inl"
const TConstArrayView<FContactEdge> ShoeEdges[]={
    MakeArrayView(Edges0),MakeArrayView(Edges1),MakeArrayView(Edges2),MakeArrayView(Edges3)};
const TConstArrayView<FGuardVertex> Guards[]={
    MakeArrayView(Hull0),MakeArrayView(Hull1),MakeArrayView(Hull2),MakeArrayView(Hull3),MakeArrayView(Hull4)};
#include "StableHorseShoeContact.inl"
const TConstArrayView<FVector> Shoes[]={MakeArrayView(Shoe0),MakeArrayView(Shoe1),MakeArrayView(Shoe2),MakeArrayView(Shoe3)};
const FName Feet[]={TEXT("finger_L"),TEXT("finger_R"),TEXT("toe_L"),TEXT("toe_R")};

struct FSurface
{
    FVector Point=FVector::ZeroVector,Normal=FVector::UpVector;
    double At(const FVector& P) const
    {
        return Point.Z-(Normal.X*(P.X-Point.X)+Normal.Y*(P.Y-Point.Y))/Normal.Z;
    }
};
struct FFootprint
{
    FSurface Ends[2];
    bool bRidge=false;
    const FSurface& At(const FVector& P) const
    {
        // Tangent planes meet on the true edge of a ramp. A crest takes the lower
        // plane and a hollow the higher. Parallel treads use the nearest sample.
        if((Ends[0].Normal-Ends[1].Normal).SizeSquared()<.0004)
            return FVector::DistSquared2D(P,Ends[0].Point)<FVector::DistSquared2D(P,Ends[1].Point)?Ends[0]:Ends[1];
        return (Ends[0].At(P)<Ends[1].At(P))==bRidge?Ends[0]:Ends[1];
    }
};

// On a convex lip, a triangle can intersect the crest between two clear vertices.
double CrestClearanceLift(const FFootprint& Bed,TConstArrayView<FVector> Points,TConstArrayView<FContactEdge> Edges)
{
    if(!Bed.bRidge || (Bed.Ends[0].Normal-Bed.Ends[1].Normal).SizeSquared()<.0004)return -BIG_NUMBER;
    TArray<double,TInlineAllocator<224>> Sides;Sides.Reserve(Points.Num());
    for(const auto& P:Points)Sides.Add(Bed.Ends[0].At(P)-Bed.Ends[1].At(P));
    double Lift=-BIG_NUMBER;
    for(const auto& E:Edges)
    {
        const double A=Sides[E.A],B=Sides[E.B];
        if((A<0.)==(B<0.))continue;
        const FVector P=FMath::Lerp(Points[E.A],Points[E.B],A/(A-B));
        Lift=FMath::Max(Lift,Bed.Ends[0].At(P)-P.Z+.65);
    }
    return Lift;
}

void TransformPose(TArray<FTransform>& Pose,const FTransform& Mesh,const FQuat& Tilt,const FVector& Offset)
{
    const FQuat Local=Mesh.GetRotation().Inverse()*Tilt*Mesh.GetRotation();
    const FVector Shift=Mesh.InverseTransformVector(Offset);
    for(auto& Bone:Pose)
    {
        Bone.SetLocation(Local.RotateVector(Bone.GetLocation())+Shift);
        Bone.SetRotation((Local*Bone.GetRotation()).GetNormalized());
    }
}
}

bool UStableHorseGroundMesh::CacheRig()
{
    auto* Asset=GetSkeletalMeshAsset();
    if(!Asset)return false;
    if(Rig.Get()==Asset)return bRigReady;
    Rig=Asset;bRigReady=false;
    const auto& Ref=Asset->GetRefSkeleton();
    for(int I=0;I<4;++I)
    {
        auto& L=Legs[I];L={};
        L.Toe=Ref.FindBoneIndex(HorseGround::Feet[I]);
        if(L.Toe<0 || (L.Ankle=Ref.GetParentIndex(L.Toe))<0 || (L.Knee=Ref.GetParentIndex(L.Ankle))<0 ||
           (L.Hip=Ref.GetParentIndex(L.Knee))<0)return false;
        const auto Bind=Ref.GetBoneAbsoluteTransform(L.Toe);
        for(const FVector& P:HorseGround::Shoes[I])
        {
            L.Pads.Add(Bind.InverseTransformPosition(P));
            L.RestSole+=P;
        }
        L.RestSole/=HorseGround::Shoes[I].Num();L.RestSole.Z=0.;
        for(int B=L.Hip+1;B<Ref.GetNum();++B)
            if(Ref.BoneIsChildOf(B,L.Hip))L.Children.Add(B);
    }
    GuardIndices.Reset();GuardInverseBind.Reset();TailBranch.Reset();
    for(const auto& Name:HorseGround::GuardBones)
    {
        const int32 B=Ref.FindBoneIndex(Name);
        if(B==INDEX_NONE)return false;
        GuardIndices.Add(B);GuardInverseBind.Add(Ref.GetBoneAbsoluteTransform(B).Inverse());
    }
    TailRoot=Ref.FindBoneIndex(TEXT("tail_01"));
    if(TailRoot==INDEX_NONE)return false;
    TailBranch.Add(TailRoot);
    for(int32 B=TailRoot+1;B<Ref.GetNum();++B)
        if(Ref.BoneIsChildOf(B,TailRoot))TailBranch.Add(B);
    if(TailBranch.Num()>=2)
    {
        const FVector Axis=Ref.GetRefBonePose()[TailBranch[1]].GetLocation().GetAbs();
        TailLengthAxis=Axis.X>Axis.Y?(Axis.X>Axis.Z?0:2):(Axis.Y>Axis.Z?1:2);
    }
    bRigReady=true;return true;
}

void UStableHorseGroundMesh::SetTailShape(float Length,float Width,float SweepCm)
{
    TailLength=Length;TailWidth=Width;TailSweepCm=SweepCm;
}

void UStableHorseGroundMesh::ShapeTail(TArray<FTransform>& Pose,const FVector& Side) const
{
    if(TailBranch.Num()<2 || !Pose.IsValidIndex(TailBranch.Last()))return;
    const FVector Dock=Pose[TailRoot].GetLocation();
    for(int32 I=1;I<TailBranch.Num();++I)
    {
        const float T=float(I)/(TailBranch.Num()-1);
        auto& Bone=Pose[TailBranch[I]];
        Bone.SetLocation(Dock+(Bone.GetLocation()-Dock)*TailLength+Side*(TailSweepCm*T*T));
        FVector Scale(FMath::Lerp(1.f,TailWidth,FMath::SmoothStep(0.f,.45f,T)));
        Scale[TailLengthAxis]=TailLength;
        Bone.SetScale3D(Bone.GetScale3D()*Scale);
    }
}

void UStableHorseGroundMesh::FinalizeBoneTransform()
{
    if(bNeedToFlipSpaceBaseBuffers && IsInGameThread())
        if(auto* Horse=Cast<AStableRidingHorse>(GetOwner());Horse && GetWorld() && GetWorld()->IsGameWorld() && Horse->GetCharacterMovement() && Horse->GetCapsuleComponent() && CacheRig())
        {
#if WITH_EDITOR
            const uint64 Start=bMeasureGroundFit?FPlatformTime::Cycles64():0;
#endif
            auto& Pose=GetEditableComponentSpaceTransforms();
            ShapeTail(Pose,GetComponentTransform().InverseTransformVectorNoScale(Horse->GetActorRightVector()));
            FitToGround(*Horse,Pose);
#if WITH_EDITOR
            if(bMeasureGroundFit)LastGroundFitUs=1000.*FPlatformTime::ToMilliseconds64(FPlatformTime::Cycles64()-Start);
#endif
        }
    Super::FinalizeBoneTransform();
}

void UStableHorseGroundMesh::FitToGround(AStableRidingHorse& Horse,TArray<FTransform>& Pose)
{
    using namespace HorseGround;
    if(Pose.Num()!=GetSkeletalMeshAsset()->GetRefSkeleton().GetNum())return;
    const auto* Move=Horse.GetCharacterMovement();
    const auto& Mesh=GetComponentTransform();
    if(!Move->IsMovingOnGround() && Move->MovementMode!=MOVE_None)
    {
        // Keep the takeoff continuous but let the authored airborne pose take over.
        const double Keep=FMath::Exp(-16.*GetWorld()->GetDeltaSeconds());
        LastTilt=FQuat::Slerp(FQuat::Identity,LastTilt,Keep);
        LastOffset*=Keep;
        if(!LastOffset.IsNearlyZero(.02) || !LastTilt.IsIdentity(.00001))TransformPose(Pose,Mesh,LastTilt,LastOffset);
        return;
    }
    const auto* Cap=Horse.GetCapsuleComponent();
    FCollisionQueryParams Q(SCENE_QUERY_STAT(StableShoeSupport),false,&Horse);
    FCollisionResponseParams Responses;Cap->InitSweepCollisionParams(Q,Responses);
    if(auto* Rider=Horse.GetRider())Q.AddIgnoredActor(Rider);
    const bool Parked=Move->MovementMode==MOVE_None && !Horse.GetRider() && !Horse.GetLeader();
    const double Now=GetWorld()->GetTimeSeconds();
    int32 SampleIndex=0;
    const auto Probe=[&](const FVector& XY,double Z,double Reach,FSurface& Out)
    {
        FVector P(XY.X,XY.Y,Z);
        auto& Cached=ParkedSamples[SampleIndex++];
        if(Parked && Now<Cached.Until && Cached.Base.IsValid() && FVector::DistSquared(P,Cached.Query)<1.)
        {
            Out={Cached.Point,Cached.Normal};
            Out.Point=FVector(P.X,P.Y,Out.At(P));
            return true;
        }
        Cached.Until=-1.;
        // Look near the predicted ground first, below any roof or overhead rail.
        FHitResult Hit;
        const auto Trace=[&](double Range)
        {
            const FVector Span(0,0,Range);
            return GetWorld()->LineTraceSingleByChannel(Hit,P+Span,P-Span,Cap->GetCollisionObjectType(),Q,Responses) &&
                !Hit.bStartPenetrating && Hit.ImpactNormal.Z>=.46 && !Cast<APawn>(Hit.GetActor());
        };
        if(!Trace(12.) && !Trace(Reach))return false;
        Out={Hit.ImpactPoint,Hit.ImpactNormal};
        if(Parked && Hit.Component.IsValid() && Hit.Component->Mobility==EComponentMobility::Static)
        {
            Cached.Query=P;Cached.Point=Out.Point;Cached.Normal=Out.Normal;Cached.Base=Hit.Component;Cached.Until=Now+.15;
        }
        return true;
    };
    const FVector Origin=Mesh.GetLocation();
    FSurface Centre;
    const double CapsuleFloor=Horse.GetActorLocation().Z-Cap->GetScaledCapsuleHalfHeight();
    // On a simulated proxy the visual mesh can trail the capsule by a network smoothing offset.
    // Centre the short probe on the visual feet; cover the possible grade to the capsule on fallback.
    const double VisualFloor=CapsuleFloor+Origin.Z-(Horse.GetActorLocation().Z+Horse.GetBaseTranslationOffset().Z);
    const double CentreReach=72.+1.74*FVector::Dist2D(Origin,Horse.GetActorLocation())+FMath::Abs(VisualFloor-CapsuleFloor);
    if(!Probe(Origin,VisualFloor,CentreReach,Centre))
    {
        LastTilt=FQuat::Identity;LastOffset=FVector::ZeroVector;return;
    }
    // The tangent estimate can be well below the ground at a convex lip,
    // even when the intended hoof is directly under the capsule.
    const auto ProbeGround=[&](const FVector& P,double Predicted,FSurface& Out)
    {
        const double Limit=Move->MaxStepHeight+1.74*FVector::Dist2D(P,Origin);
        return Probe(P,Predicted,FMath::Abs(Predicted-Centre.Point.Z)+Limit,Out);
    };
    const FQuat Guess=FQuat::FindBetweenNormals(FVector::UpVector,Centre.Normal);
    FVector Samples[4],Mean=FVector::ZeroVector;
    for(int I=0;I<4;++I)
    {
        // Sample the length of the stride, so the chest begins pitching before
        // an extended foreleg reaches a steep entry and the hind legs clear the lip.
        const FVector Support=Mesh.TransformVector(Legs[I].RestSole)+Horse.GetActorForwardVector()*(I<2?30.:-20.);
        const FVector P=Origin+Guess.RotateVector(Support);
        FSurface S;
        Samples[I]=ProbeGround(P,Centre.At(P),S)?
            S.Point:FVector(P.X,P.Y,Centre.At(P));
        Mean+=Samples[I]*.25;
    }
    // Fit z = ax + by + c through all four supports, including lateral slopes.
    double XX=0,YY=0,XY=0,XZ=0,YZ=0;
    for(const auto& P:Samples)
    {
        const FVector V=P-Mean;XX+=V.X*V.X;YY+=V.Y*V.Y;XY+=V.X*V.Y;XZ+=V.X*V.Z;YZ+=V.Y*V.Z;
    }
    const double Det=XX*YY-XY*XY;
    const FVector2D Grad=Det>1.?FVector2D((XZ*YY-YZ*XY)/Det,(YZ*XX-XZ*XY)/Det).GetClampedToMaxSize(1.733):FVector2D::ZeroVector;
    const FSurface Plane{Mean,FVector(-Grad.X,-Grad.Y,1.).GetSafeNormal()};
    LastTilt=FQuat::FindBetweenNormals(FVector::UpVector,Plane.Normal);
    LastOffset=FVector(0,0,Plane.At(Origin)-Origin.Z);
    FFootprint Ground[4];
    double Lift[4],Authored[4];double LowestAuthored=BIG_NUMBER;
    constexpr double SoleClearance=.65;
    for(int I=0;I<4;++I)
    {
        const auto& Foot=Pose[Legs[I].Toe];auto& Bed=Ground[I];
        const FVector Axis=Grad.SizeSquared()>.0025?FVector(Grad.X,Grad.Y,0).GetSafeNormal():Horse.GetActorForwardVector();
        FVector Extremes[2]={};double Lo=BIG_NUMBER,Hi=-BIG_NUMBER;
        Authored[I]=BIG_NUMBER;
        for(const FVector& Pad:Legs[I].Pads)
        {
            const FVector Local=Foot.TransformPosition(Pad);
            Authored[I]=FMath::Min(Authored[I],Local.Z);
            const FVector P=Origin+LastOffset+LastTilt.RotateVector(Mesh.TransformVector(Local));
            const double U=FVector::DotProduct(P-Origin,Axis);
            if(U<Lo){Lo=U;Extremes[0]=P;}if(U>Hi){Hi=U;Extremes[1]=P;}
        }
        for(int J=0;J<2;++J)
        {
            auto& End=Bed.Ends[J];
            if(!ProbeGround(Extremes[J],Plane.At(Extremes[J]),End))End=Plane;
        }
        Bed.bRidge=Bed.Ends[0].At(Bed.Ends[1].Point)>Bed.Ends[1].Point.Z;
        Authored[I]=FMath::Max(0.,Authored[I]);LowestAuthored=FMath::Min(LowestAuthored,Authored[I]);
        Lift[I]=-BIG_NUMBER;
        for(const FVector& Pad:Legs[I].Pads)
        {
            const FVector P=Origin+LastOffset+LastTilt.RotateVector(Mesh.TransformVector(Foot.TransformPosition(Pad)));
            const auto& GroundPlane=Bed.At(P);
            Lift[I]=FMath::Max(Lift[I],GroundPlane.At(P)-P.Z+(Authored[I]+SoleClearance)/GroundPlane.Normal.Z);
        }
    }
    // Share the load through the trunk, giving stance feet priority over swinging feet.
    double Shift=0.,Weight=0.,StanceLimit=BIG_NUMBER;
    for(int I=0;I<4;++I)
    {
        const double W=1./(1.+FMath::Square((Authored[I]-LowestAuthored)/5.));
        Shift+=W*Lift[I];Weight+=W;
        if(Authored[I]<LowestAuthored+3.5)StanceLimit=FMath::Min(StanceLimit,Lift[I]+1.5);
    }
    Shift=FMath::Clamp(FMath::Min(Shift/Weight,StanceLimit),-40.,30.);LastOffset.Z+=Shift;
    TransformPose(Pose,Mesh,LastTilt,LastOffset);
    const FVector Up=Mesh.InverseTransformVector(FVector::UpVector);
    const auto BendLeg=[&](const FLeg& L,const FVector& Offset)
    {
        const auto OldA=Pose[L.Hip],OldB=Pose[L.Knee],OldC=Pose[L.Ankle];
        auto A=OldA,B=OldB,C=OldC;
        const FVector Axis=(C.GetLocation()-A.GetLocation()).GetSafeNormal();
        const FVector Bend=FVector::VectorPlaneProject(B.GetLocation()-A.GetLocation(),Axis);
        if(!Bend.IsNearlyZero())
        {
            AnimationCore::SolveTwoBoneIK(A,B,C,A.GetLocation()+Bend.GetSafeNormal()*100.,
                OldC.GetLocation()+Offset,false,1.,1.);
            C.SetRotation(OldC.GetRotation());
            // Preserve animated hoof roll and all side branches below the solved joints.
            const auto& Ref=GetSkeletalMeshAsset()->GetRefSkeleton();
            for(int J:L.Children)
            {
                if(J==L.Knee||J==L.Ankle)continue;
                if(Ref.BoneIsChildOf(J,L.Ankle))Pose[J]=Pose[J].GetRelativeTransform(OldC)*C;
                else if(Ref.BoneIsChildOf(J,L.Knee))Pose[J]=Pose[J].GetRelativeTransform(OldB)*B;
                else Pose[J]=Pose[J].GetRelativeTransform(OldA)*A;
            }
            Pose[L.Hip]=A;Pose[L.Knee]=B;Pose[L.Ankle]=C;
        }
    };
    double SafetyLift=0.;
    for(int I=0;I<4;++I)
    {
        const auto& L=Legs[I];
        if(FMath::Abs(Lift[I]-Shift)>.12)BendLeg(L,Up*(Lift[I]-Shift));
        for(const FVector& Pad:Legs[I].Pads)
        {
            const FVector P=Mesh.TransformPosition(Pose[L.Toe].TransformPosition(Pad));
            const auto& S=Ground[I].At(P);
            SafetyLift=FMath::Max(SafetyLift,S.At(P)-P.Z+SoleClearance/S.Normal.Z);
        }
    }
    // Shoes alone do not enclose a folded knee or a hanging tail at the foot of a ramp.
    // Sample their original skinned silhouettes; a tail contact should bend the tail alone.
    // Use local float matrices for skinning, then add the double precision world origin.
    // With a common mesh transform the world-space weighted sum can be evaluated once.
    FMatrix44f Skinning[UE_ARRAY_COUNT(GuardBones)];
    FTransform Orientation=Mesh;Orientation.SetTranslation(FVector::ZeroVector);
    const FMatrix WorldBasis=Orientation.ToMatrixWithScale();
    const auto RefreshSkinning=[&]()
    {
        for(int K=0;K<GuardIndices.Num();++K)
            Skinning[K]=FMatrix44f((GuardInverseBind[K]*Pose[GuardIndices[K]]).ToMatrixWithScale()*WorldBasis);
    };
    RefreshSkinning();
    const auto SkinPoint=[&](const FGuardVertex& V)
    {
        const VectorRegister4Float Rest=VectorLoadFloat3_W1(&V.Rest.X);
        VectorRegister4Float Sum=VectorZeroFloat();
        for(int K=0;K<UE_ARRAY_COUNT(V.Bones) && V.Weights[K];++K)
            Sum=VectorMultiplyAdd(VectorTransformVector(Rest,&Skinning[V.Bones[K]]),
                VectorSetFloat1(float(V.Weights[K])*(1.f/65535.f)),Sum);
        FVector3f Local;VectorStoreFloat3(Sum,&Local.X);
        return Origin+FVector(Local);
    };
    const FVector Along=Grad.SizeSquared()>.0025?FVector(Grad.X,Grad.Y,0).GetSafeNormal():Horse.GetActorForwardVector();
    FFootprint GuardBeds[5];
    for(int I=0;I<UE_ARRAY_COUNT(Guards);++I)
    {
        TArray<FVector,TInlineAllocator<224>> Points;
        FVector Extremes[2]={};double Lo=BIG_NUMBER,Hi=-BIG_NUMBER;
        for(const auto& V:Guards[I])
        {
            const FVector P=SkinPoint(V);Points.Add(P);
            const double U=FVector::DotProduct(P-Origin,Along);
            if(U<Lo){Lo=U;Extremes[0]=P;}if(U>Hi){Hi=U;Extremes[1]=P;}
        }
        FFootprint Bed;
        for(int J=0;J<2;++J)
        {
            const FVector P=Extremes[J];
            if(!ProbeGround(P,Plane.At(P),Bed.Ends[J]))Bed.Ends[J]=Plane;
        }
        Bed.bRidge=Bed.Ends[0].At(Bed.Ends[1].Point)>Bed.Ends[1].Point.Z;
        const auto Depth=[&Bed](const FVector& P)
        {
            const auto& S=Bed.At(P);
            return S.At(P)-P.Z+.65/S.Normal.Z;
        };
        double DepthMax=0.;FVector Contact=FVector::ZeroVector;
        for(const auto& P:Points)
        {
            const double D=Depth(P);
            if(D>DepthMax){DepthMax=D;Contact=P;}
        }
        GuardBeds[I]=Bed;
        if(I<4)
        {
            DepthMax=FMath::Max(DepthMax,CrestClearanceLift(Bed,Points,ShoeEdges[I]));
            SafetyLift=FMath::Max(SafetyLift,DepthMax);continue;
        }
        if(DepthMax<=SafetyLift)continue;
        const FVector Pivot=Mesh.TransformPosition(Pose[TailRoot].GetLocation());
        const FVector Axis=FVector::CrossProduct((Contact-Pivot).GetSafeNormal2D(),FVector::UpVector).GetSafeNormal();
        if(Axis.IsNearlyZero())continue;
        double Lower=0.,Upper=FMath::DegreesToRadians(78.);
        for(int Iter=0;Iter<10;++Iter)
        {
            const double Angle=(Lower+Upper)*.5;
            const FQuat Bend(Axis,Angle);
            const bool Touching=Points.ContainsByPredicate([&](const FVector& P)
            {
                return Depth(Pivot+Bend.RotateVector(P-Pivot))+.55>SafetyLift;
            });
            if(Touching)Lower=Angle;else Upper=Angle;
        }
        const FQuat Turn=Mesh.GetRotation().Inverse()*FQuat(Axis,Upper)*Mesh.GetRotation();
        const FVector Base=Pose[TailRoot].GetLocation();
        for(int B:TailBranch)
        {
            Pose[B].SetLocation(Base+Turn.RotateVector(Pose[B].GetLocation()-Base));
            Pose[B].SetRotation((Turn*Pose[B].GetRotation()).GetNormalized());
        }
    }
    if(SafetyLift>0.)
    {
        LastOffset.Z+=SafetyLift;
        for(auto& Bone:Pose)Bone.AddToTranslation(Up*SafetyLift);
    }
    // On a sharp slope break a swinging knee can raise the trunk. Replant
    // loaded feet after that correction, preserving the airborne interval.
    for(int I=0;I<4;++I)
    {
        if(Authored[I]>3.5)continue;
        const auto& L=Legs[I];const auto& Bed=GuardBeds[I];
        double Drop=BIG_NUMBER;
        for(const auto& Pad:L.Pads)
        {
            const FVector P=Mesh.TransformPosition(Pose[L.Toe].TransformPosition(Pad));
            const auto& S=Bed.At(P);
            Drop=FMath::Min(Drop,P.Z-S.At(P)-(Authored[I]+SoleClearance)/S.Normal.Z);
        }
        if(Drop<=2.)continue;
        TArray<FTransform,TInlineAllocator<32>> Previous;
        Previous.Add(Pose[L.Hip]);
        for(int B:L.Children)Previous.Add(Pose[B]);
        for(int Attempt=0;Attempt<4;++Attempt)
        {
            BendLeg(L,-Up*Drop);
            RefreshSkinning();
            TArray<FVector,TInlineAllocator<224>> CrestPoints;
            bool Clear=true;
            for(const auto& V:Guards[I])
            {
                const FVector P=SkinPoint(V);
                if(P.Z<Bed.At(P).At(P)+.55){Clear=false;break;}
                if(Bed.bRidge)CrestPoints.Add(P);
            }
            if(Clear && (!Bed.bRidge || CrestClearanceLift(Bed,CrestPoints,ShoeEdges[I])<.01))break;
            Pose[L.Hip]=Previous[0];
            for(int J=0;J<L.Children.Num();++J)Pose[L.Children[J]]=Previous[J+1];
            Drop*=.5;
        }
    }
    if(LowestAuthored>3.5)return;
    // A nearly straight loaded leg has no remaining IK extension. Settle the
    // whole horse onto its closest support, with clearance for the tail and folded limbs.
    double Settle=BIG_NUMBER;
    for(int I=0;I<4;++I)
    {
        for(const auto& Pad:Legs[I].Pads)
        {
            const FVector P=Mesh.TransformPosition(Pose[Legs[I].Toe].TransformPosition(Pad));
            const auto& S=GuardBeds[I].At(P);
            Settle=FMath::Min(Settle,P.Z-S.At(P)-(LowestAuthored+SoleClearance)/S.Normal.Z);
        }
    }
    if(Settle<=1.5)return;
    RefreshSkinning();
    for(int I=0;I<UE_ARRAY_COUNT(Guards) && Settle>.02;++I)
    {
        const auto& Bed=GuardBeds[I];
        TArray<FVector,TInlineAllocator<224>> Points;
        for(const auto& V:Guards[I])
        {
            const FVector P=SkinPoint(V);
            const auto& S=Bed.At(P);
            Settle=FMath::Min(Settle,P.Z-S.At(P)-.75/S.Normal.Z);
            if(I<4 && Bed.bRidge)Points.Add(P);
        }
        if(!Points.IsEmpty())Settle=FMath::Min(Settle,-CrestClearanceLift(Bed,Points,ShoeEdges[I]));
    }
    if(Settle>.02)
    {
        LastOffset.Z-=Settle;
        for(auto& Bone:Pose)Bone.AddToTranslation(-Up*Settle);
    }
}
