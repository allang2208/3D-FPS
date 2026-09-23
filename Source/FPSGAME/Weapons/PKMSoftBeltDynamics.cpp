#include "PKMSoftBeltDynamics.h"
#include "PKMLowpolyWeaponAssets.h"
#include "Engine/World.h"

namespace
{
double Ramp(double X) { X=FMath::Clamp(X,0.,1.); return X*X*(3.-2.*X); }
}

void FPKMSoftChain::Solve(const TArray<FVector>& Guide, const FTransform& Component,
    double Now, double Gravity, int32 PinnedStart, bool PinEnd, double Strength,
    double Corridor, TArray<FVector>& Result)
{
    Result=Guide;
    if (Guide.Num()<3 || Strength<=.001) { Reset(); return; }
    TArray<FVector> Target;
    for (const FVector& P:Guide) Target.Add(Component.TransformPosition(P));
    const int32 Count=Target.Num();
    const double Elapsed=Now-LastTime;
    if (LastTime<0. || Elapsed<0. || Elapsed>.12 || Positions.Num()!=Count ||
        FVector::DistSquared(Target[0],PreviousGuide[0])>6400.)
    {
        Positions=PreviousGuide=Target;
        Velocities.Init(FVector::ZeroVector,Count);
        Lengths.Reset();
        for (int32 I=1;I<Count;++I) Lengths.Add(FVector::Distance(Target[I-1],Target[I]));
        LastTime=Now;
        return;
    }
    const auto Pinned=[&](int32 I) { return I<PinnedStart || (PinEnd && I==Count-1); };
    if (Elapsed>UE_SMALL_NUMBER)
    {
        const int32 Steps=FMath::Max(1,FMath::CeilToInt(Elapsed*240.));
        const double Dt=Elapsed/Steps;
        TArray<FVector> Goals, Before;
        Goals.SetNumUninitialized(Count);
        for (int32 Step=0;Step<Steps;++Step)
        {
            for (int32 I=0;I<Count;++I)
                Goals[I]=FMath::Lerp(PreviousGuide[I],Target[I],double(Step+1)/Steps);
            Before=Positions;
            for (int32 I=0;I<Count;++I)
            {
                if (Pinned(I)) { Positions[I]=Goals[I]; continue; }
                // Loose positional guidance keeps the chain on its authored
                // side of the receiver while gravity and inertia bend it.
                Velocities[I]*=FMath::Exp(-3.6*Dt);
                Velocities[I]+=(FVector(0,0,Gravity*.65)*Strength+
                    (Goals[I]-Positions[I])*42.)*Dt;
                Positions[I]+=Velocities[I]*Dt;
            }
            for (int32 Iteration=0;Iteration<20;++Iteration)
            {
                for (int32 I=0;I<Count;++I)
                {
                    if (Pinned(I)) { Positions[I]=Goals[I]; continue; }
                    // Taper the free corridor at both contact points. Only the
                    // unsupported span gets centimetres of lateral freedom.
                    const double U=double(I)/double(Count-1);
                    const double Freedom=PinEnd ? .2+.8*FMath::Sin(UE_PI*U) : U;
                    Positions[I]=Goals[I]+(Positions[I]-Goals[I]).GetClampedToMaxSize(Corridor*Freedom*Strength);
                }
                // Alternate sweep order so neither pinned end dominates.
                for (int32 J=0;J<Count-1;++J)
                {
                    const int32 I=Iteration%2 ? Count-2-J : J;
                    const double WA=Pinned(I)?0.:1., WB=Pinned(I+1)?0.:1.;
                    const FVector Delta=Positions[I+1]-Positions[I];
                    const double Distance=Delta.Size();
                    if (WA+WB==0. || Distance<UE_SMALL_NUMBER) continue;
                    const FVector Correction=Delta*((Distance-Lengths[I])/(Distance*(WA+WB)));
                    Positions[I]+=Correction*WA; Positions[I+1]-=Correction*WB;
                }
            }
            for (int32 I=0;I<Count;++I)
            {
                if (Pinned(I)) Positions[I]=Goals[I];
                Velocities[I]=(Positions[I]-Before[I])/Dt;
            }
        }
        PreviousGuide=Target; LastTime=Now;
    }
    for (int32 I=0;I<Count;++I) Result[I]=Component.InverseTransformPosition(Positions[I]);
}

void FPKMSoftBeltDynamics::Apply(USkeletalMeshComponent& Mesh, TArray<FTransform>& Pose,
    bool Reloading, bool Empty, float SourceTime, bool OldVisible, bool NewVisible)
{
    auto* Asset=Mesh.GetSkeletalMeshAsset();
    const auto* World=Mesh.GetWorld();
    if (!Asset || !World) return;
    const auto& Ref=Asset->GetRefSkeleton();
    if (SourceMesh.Get()!=Asset || BoneCount!=Ref.GetNum())
    {
        SourceMesh=Asset; BoneCount=Ref.GetNum();
        for (int32 Side=0;Side<2;++Side)
        {
            Rounds[Side].Reset(); Links[Side].Reset(); Chains[Side].Reset();
            const TCHAR* Prefix=Side?TEXT("New_"):TEXT("");
            // Belt08: point 0 is the finger contact, point 8 the box mouth.
            for (int32 I=0;I<=8;++I)
                Rounds[Side].Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%sPKM_Belt_%02d"),Prefix,I))));
            for (int32 I=0;I<8;++I)
                Links[Side].Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%sPKM_Belt_Link_%02d"),Prefix,I))));
        }
    }
    for (int32 Side=0;Side<2;++Side)
    {
        const float Start=Side?PKMLowpolyWeaponAssets::ReloadEventTime(3.55f,Empty):1.34f;
        const float Settle=PKMLowpolyWeaponAssets::ReloadEventTime(4.82f,Empty);
        const double Strength=Ramp((SourceTime-Start)/.22)*
            (Side?1.-Ramp((SourceTime-Settle)/.28):1.);
        if (!Reloading || !(Side?NewVisible:OldVisible) || (!Side && Empty) || Strength<=.001)
        { Chains[Side].Reset(); continue; }
        TArray<FVector> Guide, Solved;
        for (int32 Index:Rounds[Side]) if (Pose.IsValidIndex(Index)) Guide.Add(Pose[Index].GetLocation());
        if (Guide.Num()!=9) continue;
        Chains[Side].Solve(Guide,Mesh.GetComponentTransform(),World->GetTimeSeconds(),
            World->GetGravityZ(),1,true,Strength,2.4,Solved);
        for (int32 I=1;I<8;++I)
        {
            auto& Bone=Pose[Rounds[Side][I]];
            const FQuat Turn=FQuat::FindBetweenNormals((Guide[I+1]-Guide[I-1]).GetSafeNormal(),
                (Solved[I+1]-Solved[I-1]).GetSafeNormal());
            Bone.SetLocation(Solved[I]);
            Bone.SetRotation((Turn*Bone.GetRotation()).GetNormalized());
        }
        // End cartridge transforms remain exact hand/box contacts; bridge
        // bones articulate freely between them and the solved inner rounds.
        for (int32 I=0;I<8;++I)
        {
            if (!Pose.IsValidIndex(Links[Side][I])) continue;
            auto& Bone=Pose[Links[Side][I]];
            const FQuat Turn=FQuat::FindBetweenNormals((Guide[I+1]-Guide[I]).GetSafeNormal(),
                (Solved[I+1]-Solved[I]).GetSafeNormal());
            const FVector Offset=Bone.GetLocation()-(Guide[I+1]+Guide[I])*.5;
            Bone.SetLocation((Solved[I+1]+Solved[I])*.5+Turn.RotateVector(Offset));
            Bone.SetRotation((Turn*Bone.GetRotation()).GetNormalized());
        }
    }
}
