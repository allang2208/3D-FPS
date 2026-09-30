#include "LMG201BeltDynamics.h"
#include "LMG201BeltLayout.h"
#include "LMG201WeaponAssets.h"
#include "Engine/World.h"

namespace
{
float Belt49Ramp(float X) { X=FMath::Clamp(X,0.f,1.f);return X*X*(3.f-2.f*X); }
// Same source-time advance as the current PKM Feed13, adapted to this chain.
constexpr float Belt49FeedBegin=.012f,Belt49FeedDuration=.068f;
FVector Belt49Sample(const TArray<FVector>& Points,double Slot)
{
    const double U=FMath::Clamp(Slot-LMG201BeltLayout::FirstSlot,0.,double(Points.Num()-1));
    const int32 I=FMath::Min(FMath::FloorToInt(U),Points.Num()-2);
    return FMath::Lerp(Points[I],Points[I+1],U-I);
}
}

void FLMG201BeltDynamics::Configure(bool Enabled,bool Reloading,bool Empty,float ReloadSourceTime,
    int32 Rounds,bool Firing,float FireSourceTime,double ShotWorldTime,bool Inspection)
{
    bEnabled=Enabled;bInspection=Inspection;bEmpty=Empty;ReloadTime=ReloadSourceTime;
    if(!Enabled || Inspection)
    {
        bInitialized=bFeedShot=false;Feed=0.f;FireRippleTime=-1.f;FedCells=0;
        bReloading=Reloading;Chains[0].Reset();Chains[1].Reset();return;
    }
    if(!bInitialized || Rounds>PreviousRounds || Reloading!=bReloading)
    {
        FedCells=0;bFeedShot=false;PreviousShot=ShotWorldTime;bInitialized=true;
    }
    else if(!Reloading && Firing && ShotWorldTime!=PreviousShot)
    {
        // The accepted shot clock also covers infinite-ammo presentation.
        // Missed view frames advance by the actual count, without a reverse step.
        FedCells=(FedCells+FMath::Max(1,PreviousRounds-Rounds))%LMG201BeltLayout::CellCount;
        PreviousShot=ShotWorldTime;bFeedShot=true;
    }
    PreviousRounds=Rounds;bReloading=Reloading;
    Feed=float(FedCells);
    if(bFeedShot && Firing && !Reloading)
        Feed-=1.f-Belt49Ramp((FireSourceTime-Belt49FeedBegin)/Belt49FeedDuration);
    FireRippleTime=Firing && !Reloading && FireSourceTime<.1f ? FireSourceTime : -1.f;
}

void FLMG201BeltDynamics::Apply(USkeletalMeshComponent& Mesh,TArray<FTransform>& Pose)
{
    if(!LMG201WeaponAssets::Matches(&Mesh))
    {
        SourceMesh.Reset();bInitialized=bHadOutput=false;Chains[0].Reset();Chains[1].Reset();return;
    }
    auto* Asset=Mesh.GetSkeletalMeshAsset();const auto& Ref=Asset->GetRefSkeleton();
    if(SourceMesh.Get()!=Asset || BoneCount!=Ref.GetNum())
    {
        SourceMesh=Asset;BoneCount=Ref.GetNum();Root=Ref.FindBoneIndex(TEXT("WPN_root"));
        OldSection=NewSection=INDEX_NONE;bIndexedMesh=false;bHadOutput=false;
        for(int32 M=0;M<Asset->GetMaterials().Num();++M)
        {
            const FString Name=Asset->GetMaterials()[M].MaterialSlotName.ToString();
            if(Name==TEXT("M_LMG201_Cloth33__OldBelt_B53_Case")){OldSection=M;bIndexedMesh=true;}
            if(Name==TEXT("M_LMG201_Cloth33__NewBelt_B53_Case"))NewSection=M;
        }
        for(int32 Side=0;Side<2;++Side)
        {
            Bones[Side].Reset();LastInput[Side].Reset();LastOutput[Side].Reset();Chains[Side].Reset();
            for(int32 I=0;I<LMG201BeltLayout::CellCount;++I)
                Bones[Side].Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%sLMG201_Belt_%02d"),Side?TEXT("New_"):TEXT(""),I))));
            for(int32 I=0;I<LMG201BeltLayout::LinkCount;++I)
                Bones[Side].Add(Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%sLMG201_Belt_Link_%02d"),Side?TEXT("New_"):TEXT(""),I))));
        }
    }
    if(!bIndexedMesh || !Pose.IsValidIndex(Root) || Pose.Num()!=BoneCount)return;
    for(int32 Side=0;Side<2;++Side)for(int32 Index:Bones[Side])if(!Pose.IsValidIndex(Index))return;
    // Finalization may run repeatedly on an already finalized pose. Restore
    // only our leaf bones before reapplying, never accumulate last output.
    for(int32 Side=0;Side<2;++Side)
    {
        for(int32 I=0;I<Bones[Side].Num();++I)
            if(bHadOutput && Pose[Bones[Side][I]].Equals(LastOutput[Side][I],1.e-7))Pose[Bones[Side][I]]=LastInput[Side][I];
        LastInput[Side].Reset();
        for(int32 Index:Bones[Side])LastInput[Side].Add(Pose[Index]);
    }
    const auto* World=Mesh.GetWorld();
    const bool Active=bEnabled && !bInspection && World && World->IsGameWorld() && Mesh.IsVisible() && !Mesh.bHiddenInGame;
    if(bLastReloading!=bReloading){Chains[0].Reset();Chains[1].Reset();bLastReloading=bReloading;}
    // Reload clips own the complete chain, including the pouch reservoir and
    // the turn into the receiver. Do not replace those tracks with a rigid tail.
    // The additional return cell never participates in the authored hand-off.
    Pose[Bones[0][10]].SetScale3D(FVector::ZeroVector);
    Pose[Bones[1][10]].SetScale3D(FVector::ZeroVector);
    if(!Active){Chains[0].Reset();Chains[1].Reset();}
    else if(bReloading)
    {
        for(int32 Side=0;Side<2;++Side)
        {
            const int32 Section=Side?NewSection:OldSection;
            const bool Visible=Section!=INDEX_NONE && Mesh.IsMaterialSectionShown(Section,0) && (Side || !bEmpty);
            // Normal-clip seconds; the empty clip's pacing maps through ClothEventTime.
            const auto At=[this](float T){return LMG201WeaponAssets::ClothEventTime(T,bEmpty);};
            const float Strength=Side
                ? Belt49Ramp((ReloadTime-At(4.10f))/(At(4.30f)-At(4.10f)))*(1.f-Belt49Ramp((ReloadTime-At(4.55f))/(At(4.78f)-At(4.55f))))
                : Belt49Ramp((ReloadTime-1.60f)/.18f);
            if(!Visible || Strength<.001f){Chains[Side].Reset();continue;}
            TArray<FVector> Guide,Solved;
            for(int32 I=0;I<LMG201BeltLayout::ReloadContactCount;++I)Guide.Add(Pose[Bones[Side][I]].TransformPosition(Side?LMG201BeltLayout::NewCenters[I]:LMG201BeltLayout::Centers[I]));
            Chains[Side].Solve(Guide,Mesh.GetComponentTransform(),World->GetTimeSeconds(),World->GetGravityZ(),1,true,
                Strength,PKMBeltProfiles::IncomingCorridor,Solved,PKMBeltProfiles::Incoming);
            // Keep both exact animated hand/pouch contacts. Only free cells move.
            for(int32 I=1;I<5;++I)
            {
                auto& Bone=Pose[Bones[Side][I]];
                const FQuat Turn=FQuat::FindBetweenNormals((Guide[I+1]-Guide[I-1]).GetSafeNormal(),(Solved[I+1]-Solved[I-1]).GetSafeNormal());
                Bone.SetLocation(Solved[I]+Turn.RotateVector(Bone.GetLocation()-Guide[I]));
                Bone.SetRotation((Turn*Bone.GetRotation()).GetNormalized());
            }
        }
    }
    else if(OldSection!=INDEX_NONE && Mesh.IsMaterialSectionShown(OldSection,0))
    {
        const FTransform Gun=Pose[Root];TArray<FVector> Guide,Solved;
        for(const FVector& P:LMG201BeltLayout::Guide)Guide.Add(Gun.TransformPosition(P));
        // PKM Feed13: one 0.1 s tug, gated by feed progress, with 0.65/0.45 mm
        // amplitudes and .33 rad per-cell phase. No 201-only ringing tail.
        if(FireRippleTime>=0.f)
        {
            const float U=Belt49Ramp((FireRippleTime-Belt49FeedBegin)/Belt49FeedDuration);
            for(int32 I=1;I<Guide.Num()-1;++I)
            {
                const double Envelope=FMath::Sin(UE_PI*I/(Guide.Num()-1));
                const double Pulse=FMath::Sin(UE_PI*U)*FMath::Sin(2.*UE_PI*FireRippleTime/.1-I*.33)*Envelope;
                Guide[I]+=Gun.GetRotation().RotateVector(FVector(0.,.065*Pulse,.045*Pulse));
            }
        }
        Chains[0].Solve(Guide,Mesh.GetComponentTransform(),World->GetTimeSeconds(),World->GetGravityZ(),1,true,
            1.,PKMBeltProfiles::IncomingCorridor,Solved,PKMBeltProfiles::Incoming);
        Chains[1].Reset();
        for(int32 I=0;I<LMG201BeltLayout::CellCount;++I)
        {
            const double RestSlot=LMG201BeltLayout::SlotByCell[I];
            const double Slot=FMath::Fmod(RestSlot-Feed-LMG201BeltLayout::FirstSlot+2.*LMG201BeltLayout::CellCount,
                double(LMG201BeltLayout::CellCount))+LMG201BeltLayout::FirstSlot;
            const FVector Target=Belt49Sample(Solved,Slot);
            const FVector Tangent=(Belt49Sample(Solved,Slot+.04)-Belt49Sample(Solved,Slot-.04)).GetSafeNormal();
            const FVector OriginalTangent=(Belt49Sample(Guide,RestSlot+.04)-Belt49Sample(Guide,RestSlot-.04)).GetSafeNormal();
            FTransform Bone=LMG201BeltLayout::Idle[I]*Gun;
            const FQuat Turn=FQuat::FindBetweenNormals(OriginalTangent,Tangent);
            const FVector Origin=Bone.TransformPosition(LMG201BeltLayout::Centers[I]);
            Bone.SetLocation(Target+Turn.RotateVector(Bone.GetLocation()-Origin));
            Bone.SetRotation((Turn*Bone.GetRotation()).GetNormalized());
            // Retire only beyond the two receiver cells, not at the exposed mouth.
            const float Visibility=Belt49Ramp(float((Slot-LMG201BeltLayout::FirstSlot)/.4))*(1.f-Belt49Ramp(float((Slot-10.2)/.8)));
            // Scale about the cell centroid, not the inherited legacy bone pivot.
            const FVector CenterOffset=Bone.TransformVector(LMG201BeltLayout::Centers[I]);
            Bone.SetLocation(Target-CenterOffset*Visibility);Bone.SetScale3D(Bone.GetScale3D()*Visibility);
            Pose[Bones[0][I]]=Bone;
        }
    }
    else {Chains[0].Reset();Chains[1].Reset();}
    // Independent steel links are solved from the final cartridge transforms,
    // after both indexing and damping. Never stretch the ammunition meshes.
    const FTransform Gun=Pose[Root];
    const double GunScale=Gun.GetScale3D().GetAbsMax();
    for(int32 Side=0;Side<2;++Side)
    {
        const auto* Centers=Side?LMG201BeltLayout::NewCenters:LMG201BeltLayout::Centers;
        const auto* Axis=Side?LMG201BeltLayout::NewAxis:LMG201BeltLayout::Axis;
        const auto* LinkIdle=Side?LMG201BeltLayout::NewLinkIdle:LMG201BeltLayout::LinkIdle;
        const auto* LinkCenters=Side?LMG201BeltLayout::NewLinkCenters:LMG201BeltLayout::LinkCenters;
        for(int32 K=0;K<LMG201BeltLayout::LinkCount;++K)
        {
            const int32 A=LMG201BeltLayout::LinkA[K],B=LMG201BeltLayout::LinkB[K];
            const FTransform& PA=Pose[Bones[Side][A]];const FTransform& PB=Pose[Bones[Side][B]];
            const FVector CA=PA.TransformPosition(Centers[A]),CB=PB.TransformPosition(Centers[B]);
            const double Distance=FVector::Distance(CA,CB);
            const double Nominal=LMG201BeltLayout::LinkLength[K]*GunScale;
            const double Visibility=FMath::Min(PA.GetScale3D().GetAbsMax(),PB.GetScale3D().GetAbsMax())/FMath::Max(GunScale,1.e-6);
            FTransform Bone=LinkIdle[K]*Gun;
            // Hide the wrap pair while a cell recycles inside the enclosure.
            if(Distance<.001 || Distance>1.7*Nominal || Visibility<.01 || (K==13 && (bReloading || !Active)))
                Bone.SetScale3D(FVector::ZeroVector);
            else
            {
                const FVector Y=(PA.TransformVectorNoScale(Axis[A])+PB.TransformVectorNoScale(Axis[B])).GetSafeNormal();
                const FQuat Desired=FRotationMatrix::MakeFromZY((CB-CA).GetSafeNormal(),Y).ToQuat();
                const FQuat Turn=Desired*(Gun.GetRotation()*LMG201BeltLayout::LinkFrame[K]).Inverse();
                const FVector Center=(CA+CB)*.5,Origin=Bone.TransformPosition(LinkCenters[K]);
                // The last ring edge is authored across the pool boundary; when
                // it becomes adjacent, use the same finite link pitch as its peers.
                const double Ratio=Distance/FMath::Max(Nominal,1.e-6);
                Bone.SetLocation(Center+Turn.RotateVector(Bone.GetLocation()-Origin)*(Ratio*Visibility));
                Bone.SetRotation((Turn*Bone.GetRotation()).GetNormalized());
                Bone.SetScale3D(Bone.GetScale3D()*(Ratio*Visibility));
            }
            Pose[Bones[Side][LMG201BeltLayout::CellCount+K]]=Bone;
        }
    }
    for(int32 Side=0;Side<2;++Side)
    {
        LastOutput[Side].Reset();for(int32 Index:Bones[Side])LastOutput[Side].Add(Pose[Index]);
    }
    bHadOutput=true;
}
