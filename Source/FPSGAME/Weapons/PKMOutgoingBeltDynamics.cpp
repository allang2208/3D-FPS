#include "PKMOutgoingBeltDynamics.h"
#include "PKMLowpolyWeaponAssets.h"
#include "Engine/World.h"

namespace
{
// Matches the accepted Belt08 visual spacing. Values are in viewmodel cm.
constexpr double Pitch=1.832636;
constexpr double TabLead=1.5;
// At the upper edge of the box, before the tail can reach the supporting arm.
constexpr double RetireDistance=14.7;
float Smooth(float X) { X=FMath::Clamp(X,0.f,1.f); return X*X*(3.f-2.f*X); }
FVector OutletPoint(double Distance, const FVector& Down)
{
    // The short straight part stays inside the feed exit; the unsupported
    // part bends down and hangs beside the receiver, never through its wall.
    constexpr double Straight=4.8, Radius=2.;
    const double Arc=FMath::Clamp(Distance-Straight,0.,Radius*UE_PI*.5);
    const double Angle=Arc/Radius;
    const double Tail=FMath::Max(0.,Distance-Straight-Arc);
    return FVector(FMath::Min(Distance,Straight)+Radius*FMath::Sin(Angle),0.,0.)+
        Down*(Radius*(1.-FMath::Cos(Angle))+Tail);
}
}

void FPKMOutgoingBeltDynamics::Configure(bool Enabled, bool Reloading, bool Empty,
    float SourceTime, int32 Rounds, int32 Capacity, bool Firing, float FireSourceTime, bool Inspection)
{
    bEnabled=Enabled;
    if (!Enabled) { bInitialized=false; OutletChain.Reset(); return; }
    Rounds=FMath::Max(0,Rounds);
    if (!bInitialized)
    {
        FedLinks=FMath::Max(0,Capacity-Rounds);
        bInitialized=true;
    }
    else if (Rounds>PreviousRounds || (bReloading && !Reloading &&
        ReloadTime>=PKMLowpolyWeaponAssets::ReloadEventTime(4.35f,Empty)))
        FedLinks=0;
    else if (Rounds<PreviousRounds && !Reloading)
        FedLinks+=PreviousRounds-Rounds;
    PreviousRounds=Rounds;
    bReloading=Reloading; bEmptyReload=Empty; ReloadTime=SourceTime; bInspection=Inspection;
    // The incoming animation and outgoing chain share exactly the same feed
    // phase. Completing a shot does not blend the outlet back into the gun.
    VisibleFeed=static_cast<float>(FedLinks);
    if (Firing && FedLinks>0 && !Reloading)
        VisibleFeed-=1.f-Smooth((FireSourceTime-.012f)/.068f);
    if (Inspection) VisibleFeed=0.f;
}

void FPKMOutgoingBeltDynamics::Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    if (!Asset) return;
    const auto& Ref=Asset->GetRefSkeleton();
    if (SourceMesh.Get()!=Asset || BoneCount!=Ref.GetNum())
    {
        SourceMesh=Asset; BoneCount=Ref.GetNum();
        Root=Ref.FindBoneIndex(TEXT("WPN_root"));
        Tip=Ref.FindBoneIndex(TEXT("PKM_Belt_00"));
        NewTip=Ref.FindBoneIndex(TEXT("New_PKM_Belt_00"));
        Tab=Ref.FindBoneIndex(TEXT("PKM_OutgoingTab"));
        NewTab=Ref.FindBoneIndex(TEXT("New_PKM_OutgoingTab"));
        Clips.Reset(); Bridges.Reset();
        for (int32 I=0;I<25;++I)
        {
            Clips.Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("PKM_OutgoingClip_%02d"),I))));
            Bridges.Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("PKM_OutgoingBridge_%02d"),I))));
        }
        BindLocal=Ref.GetRefBonePose();
        OutletChain.Reset();
    }
    if (!Pose.IsValidIndex(Root) || !Pose.IsValidIndex(Tab) || Pose.Num()!=BoneCount) return;
    const FTransform Gun=Pose[Root];
    const auto* World=Mesh.GetWorld();
    const bool Active=bEnabled && World && World->IsGameWorld() && Mesh.IsVisible() && !Mesh.bHiddenInGame;
    bool OldVisible=true,NewVisible=false;
    // Section visibility includes the final-shot feed grace period.
    if (Active)
        for (int32 M=0;M<Asset->GetMaterials().Num();++M)
        {
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString();
            if (Name.Contains(TEXT("__OldBelt"))) OldVisible=Mesh.IsMaterialSectionShown(M,0);
            if (Name.Contains(TEXT("__NewBelt"))) NewVisible=bReloading && Mesh.IsMaterialSectionShown(M,0);
        }
    ReloadBelts.Apply(Mesh,Pose,Active && bReloading && !bInspection,
        bEmptyReload,ReloadTime,OldVisible,NewVisible);
    // Reconstruct the authored tip's bind transform through its real parents.
    // This lets outgoing pieces follow the hand-held belt during both reloads.
    const auto TipMount=[&](int32 Index)
    {
        FTransform Local=FTransform::Identity;
        for (int32 I=Index;I!=INDEX_NONE && I!=Root;I=Ref.GetParentIndex(I)) Local=Local*BindLocal[I];
        return Local*Gun;
    };
    const int32 Follow=bReloading && Active?Tip:INDEX_NONE;
    const auto Mounted=[&](int32 Index, int32 FollowIndex)
    {
        FTransform Result=BindLocal[Index]*Gun;
        if (Pose.IsValidIndex(FollowIndex)) Result=Result.GetRelativeTransform(TipMount(FollowIndex))*Pose[FollowIndex];
        return Result;
    };
    if (Clips.IsEmpty() || !Pose.IsValidIndex(Clips[0])) return;
    const FVector Origin=Mounted(Clips[0],Follow).GetLocation();
    FQuat Frame=Gun.GetRotation();
    if (Pose.IsValidIndex(Follow))
        Frame=Pose[Follow].GetRotation()*TipMount(Follow).GetRotation().Inverse()*Frame;
    const FVector Forward=Frame.RotateVector(FVector::ForwardVector);
    // Gravity is evaluated in the held tip frame during reload. The loose
    // tail can fall independently instead of rotating as one rigid bracket.
    const FVector GravityCS=Mesh.GetComponentTransform().InverseTransformVectorNoScale(FVector(0,0,-1));
    FVector Down=Frame.UnrotateVector(GravityCS);
    Down.X=0.; Down=Down.GetSafeNormal(UE_SMALL_NUMBER,FVector(0,0,-1));
    TArray<FVector> Guide,Curve;
    for (int32 I=0;I<10;++I) Guide.Add(Origin+Frame.RotateVector(OutletPoint(I*Pitch,Down)));
    if (bOutletFollowingHand!=(Follow!=INDEX_NONE)) OutletChain.Reset();
    bOutletFollowingHand=Follow!=INDEX_NONE;
    if (Active && OldVisible && !bInspection)
        OutletChain.Solve(Guide,Mesh.GetComponentTransform(),World->GetTimeSeconds(),
            World->GetGravityZ(),3,false,1.,3.2,Curve);
    else { OutletChain.Reset(); Curve=Guide; }
    const auto Sample=[&](double Distance)
    {
        const double U=FMath::Clamp(Distance/Pitch,0.,double(Curve.Num()-1));
        const int32 I=FMath::Min(FMath::FloorToInt(U),Curve.Num()-2);
        return FMath::Lerp(Curve[I],Curve[I+1],U-I);
    };
    const auto Place=[&](int32 Index,const FVector& Point,const FVector& Direction,double Visibility)
    {
        if (!Pose.IsValidIndex(Index)) return;
        FTransform Result=Mounted(Index,Follow);
        const FQuat Turn=FQuat::FindBetweenNormals(Forward,Direction.GetSafeNormal(UE_SMALL_NUMBER,Forward));
        Result.SetLocation(Point);
        Result.SetRotation((Turn*Result.GetRotation()).GetNormalized());
        Result.SetScale3D(Result.GetScale3D()*Visibility);
        Pose[Index]=Result;
    };
    // Absolute generation order, with a ring of leaf bones. Retirement is
    // per link at the box edge; crossing 25 shots never clears the whole belt.
    const double Feed=Active?FMath::Max(0.f,VisibleFeed):0.;
    const int32 Newest=FMath::CeilToInt(Feed)-1;
    const auto Fade=[](double Distance) { return 1.-Smooth((Distance-(RetireDistance-.65))/.65); };
    for (int32 I=0;I<25;++I)
    {
        const int32 Generation=Newest-((Newest-I+25)%25);
        const double Distance=(Feed-Generation)*Pitch;
        const double Visibility=Active && OldVisible && Generation>=0 && Distance>.001?Fade(Distance):0.;
        const FVector A=Sample(Distance),B=Sample(Distance-Pitch);
        const FVector Tangent=Sample(Distance+.02)-Sample(Distance-.02);
        Place(Clips[I],A,Tangent,Visibility);
        Place(Bridges[I],(A+B)*.5,A-B,Visibility);
    }
    const double Lead=Feed*Pitch+TabLead;
    const FVector TabOffset=Mounted(Tab,Follow).GetLocation()-Origin-Forward*TabLead;
    Place(Tab,Sample(Lead)+TabOffset,Sample(Lead+.02)-Sample(Lead-.02),!Active?1.:Fade(Lead));
    // Its __NewBelt material section supplies the exact new-belt visibility
    // window. It follows the existing new first-round track, not the receiver.
    if (Pose.IsValidIndex(NewTab)) Pose[NewTab]=Mounted(NewTab,Active && bReloading?NewTip:INDEX_NONE);
    ExitCover.Apply(Mesh,Pose,Tab,NewTab,Clips,OldVisible,NewVisible,Active && !bInspection);
}
