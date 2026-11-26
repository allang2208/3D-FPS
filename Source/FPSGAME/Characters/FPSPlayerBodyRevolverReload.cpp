#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/DanWesson715WeaponAssets.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Engine/World.h"

namespace FPSBodyRevolver
{
FTransform Rigid(FTransform Frame){Frame.SetScale3D(FVector::OneVector);return Frame;}
float Ease(float Begin,float End,float Time){return FMath::SmoothStep(Begin,End,Time);}
void Show(UStaticMeshComponent* Part,bool Visible,float Opacity=1.f)
{
    if(!Part)return;
    if(Part->IsVisible()!=Visible)Part->SetVisibility(Visible);
    if(Part->bHiddenInGame==Visible)Part->SetHiddenInGame(!Visible);
    Part->SetCustomPrimitiveDataFloat(0,Opacity);
}
}

void UFPSPlayerBodyComponent::PrepareRevolverReload(FFPSBodyMotionBinding& Binding)
{
    using namespace FPSBodyRevolver;
    auto* Weapon=Binding.Mesh.Get();
    if(!Weapon||!Binding.Definition.bGunRevolver)return;
    auto& Reload=Binding.Revolver;
    const auto& Skeleton=Weapon->GetSkeletalMeshAsset()->GetRefSkeleton();
    Reload.Cylinder=Skeleton.FindBoneIndex(TEXT("WPN_Cylinder"));
    const int32 HandBone=Skeleton.FindBoneIndex(Binding.Definition.GripBone);
    if(Reload.Cylinder==INDEX_NONE||HandBone==INDEX_NONE||Binding.NativeWeaponRoot==INDEX_NONE)return;
    const bool RSH=Binding.Definition.GunDefinition==TEXT("ue_rsh12");
    const int32 Capacity=RSH?5:6;
    const FString Prefix=FString::Printf(TEXT("/Game/Weapons/DualRevolverReload20261022/SM_%s_%s_"),
        RSH?TEXT("RSH12"):TEXT("DW715"),Binding.Definition.AttachHand?TEXT("l"):TEXT("r"));
    const auto Load=[&](const FString& Suffix)->UStaticMesh*
    {
        auto* Asset=LoadObject<UStaticMesh>(nullptr,*(Prefix+Suffix));
        if(Asset)WorldRevolverAssets.AddUnique(Asset);
        return Asset;
    };
    const auto Create=[&](UStaticMesh* Asset)->UStaticMeshComponent*
    {
        auto* Part=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        Part->ComponentTags.Add(TEXT("FPSRevolverReloadProp"));
        GetOwner()->AddInstanceComponent(Part);Part->SetStaticMesh(Asset);Part->SetupAttachment(Weapon);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->bReceivesDecals=false;
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(Part,false,!IsThirdPersonViewEnabled());
        Part->SetVisibility(false);Part->SetHiddenInGame(true);Part->RegisterComponent();
        WorldParts.Add(Part);WorldEquipmentHands.Add(Part,Binding.Definition.AttachHand);
        return Part;
    };
    Reload.GunInHand=Binding.FrozenPose[Binding.NativeWeaponRoot].GetRelativeTransform(FPSBodyRevolver::Rigid(Binding.FrozenPose[HandBone]));
    const FTransform FrozenCylinder=FPSBodyRevolver::Rigid(Binding.FrozenPose[Reload.Cylinder]);
    for(int32 Chamber=0;Chamber<Capacity;++Chamber)
    {
        const int32 Case=Skeleton.FindBoneIndex(*FString::Printf(TEXT("WPN_Case_%d"),Chamber));
        const int32 Round=Skeleton.FindBoneIndex(*FString::Printf(TEXT("WPN_Round_%d"),Chamber));
        auto* CaseAsset=Load(FString::Printf(TEXT("Case_%d"),Chamber));
        auto* LiveAsset=Load(FString::Printf(TEXT("Live_%d"),Chamber));
        const auto* Travel=LiveAsset?LiveAsset->FindSocket(TEXT("InsertTravel")):nullptr;
        if(Case==INDEX_NONE||Round==INDEX_NONE||!CaseAsset||!Travel)return;
        Reload.Cases.Add(Case);Reload.Rounds.Add(Round);Reload.CaseAssets.Add(CaseAsset);Reload.LiveAssets.Add(LiveAsset);
        Reload.CaseInCylinder.Add(Binding.FrozenPose[Case].GetRelativeTransform(FrozenCylinder));
        Reload.RoundInCase.Add(Binding.FrozenPose[Round].GetRelativeTransform(FPSBodyRevolver::Rigid(Binding.FrozenPose[Case])));
        Reload.InsertTravel.Add(Travel->RelativeLocation);Reload.IncomingRounds.Add(Create(LiveAsset));
    }
    auto* LoaderAsset=Load(TEXT("Loader"));
    const auto* LoaderSeat=LoaderAsset?LoaderAsset->FindSocket(TEXT("SeatInCylinder")):nullptr;
    if(!LoaderSeat)return;
    Reload.Loader=Create(LoaderAsset);
    Reload.LoaderInCylinder=FTransform(LoaderSeat->RelativeRotation,LoaderSeat->RelativeLocation);
    const int32 LoaderBone=Skeleton.FindBoneIndex(TEXT("WPN_Loader"));
    for(int32 Bone:Binding.Definition.MotionBones)
    {
        if(Skeleton.GetBoneName(Bone).ToString().StartsWith(TEXT("WPN_")))Reload.Mechanisms.Add(Bone);
        if(Bone==LoaderBone||(LoaderBone!=INDEX_NONE&&Skeleton.BoneIsChildOf(Bone,LoaderBone)))Reload.LoaderBones.Add(Bone);
    }
    Reload.bPrepared=true;
}

void UFPSPlayerBodyComponent::UpdateRevolverReload(FFPSBodyMotionBinding& Binding,TArray<FTransform>& Pose,bool bVisible,float Delta)
{
    using namespace FPSBodyRevolver;
    using namespace DanWesson715WeaponAssets;
    auto& Reload=Binding.Revolver;
    const auto HideProps=[&]()
    {
        for(const auto& Part:Reload.IncomingRounds)Show(Part.Get(),false);
        Show(Reload.Loader.Get(),false);
    };
    if(!Reload.bPrepared)return;
    const auto& Hand=Binding.Definition.AttachHand==0?DisplayState.RightHand:DisplayState.LeftHand;
    const bool Active=DisplayState.bDual&&Hand.bReloading&&Hand.ReloadSourceLength>0.f;
    Reload.HoldWeight=FMath::FInterpConstantTo(Reload.HoldWeight,Active?1.f:0.f,Delta,10.f);
    if(!DisplayState.bDual)Reload.HoldWeight=0.f;
    if(Reload.HoldWeight<=0.f){HideProps();Reload.StartedAt=-100.f;return;}
    const int32 Gun=Binding.NativeWeaponRoot;
    const FTransform OriginalGun=FPSBodyRevolver::Rigid(Pose[Gun]);
    FTransform StableGun;StableGun.Blend(OriginalGun,FPSBodyRevolver::Rigid(Reload.GunInHand),Reload.HoldWeight);
    // Preserve native crane/cylinder/trigger transforms relative to the gun;
    // only remove the camera-framed gun throw relative to the holding palm.
    for(int32 Bone:Reload.Mechanisms)Pose[Bone]=Pose[Bone].GetRelativeTransform(OriginalGun)*StableGun;
    Reload.PresentedParts.SetNum(Binding.Smoothed.Parts.Num(),EAllowShrinking::No);
    for(int32 PartIndex=0;PartIndex<Binding.Smoothed.Parts.Num();++PartIndex)
        Reload.PresentedParts[PartIndex]=Binding.Smoothed.Parts[PartIndex].GetRelativeTransform(OriginalGun)*StableGun;
    for(int32 Bone:Reload.LoaderBones)Pose[Bone].SetScale3D(FVector::ZeroVector);
    if(auto* Prop=Binding.ReloadProp.Get()){Prop->SetVisibility(false);Prop->SetHiddenInGame(true);}
    if(!Active){HideProps();Reload.StartedAt=-100.f;return;}

    const float Time=Hand.Progress*Hand.ReloadSourceLength;
    const float LoaderScale=3.85f/NormalReload;
    const bool RSH=Binding.Definition.GunDefinition==TEXT("ue_rsh12");
    const float EjectTime=Hand.bSpeedloaderReload?Eject*LoaderScale:Hand.ReloadStart==0?(RSH?Eject:EmptyCaseClear):Open+.06f;
    if(!FMath::IsNearlyEqual(Reload.StartedAt,Hand.ReloadStartedAt,.01f))
    {
        Reload.StartedAt=Hand.ReloadStartedAt;
        Reload.InitialLive=Hand.LiveRounds;Reload.InitialCases=Hand.Cartridges;
        Reload.bDiscardLive=Hand.bDiscardReloadRounds;
        Reload.bDropArmed=Time<EjectTime;Reload.bDropped=false;Reload.bLoaderReleased=false;
    }
    const FTransform Cylinder=FPSBodyRevolver::Rigid(Pose[Reload.Cylinder]);
    const int32 Capacity=Reload.Cases.Num();
    if(Time>=EjectTime&&!Reload.bDropped)
    {
        Reload.bDropped=true;
        const bool DrawDrop=bVisible&&Character.IsValid()&&(!Character->IsLocallyControlled()||IsThirdPersonViewEnabled());
        if(Reload.bDropArmed&&DrawDrop&&GetNetMode()!=NM_DedicatedServer)
        {
            const int32 First=Reload.bDiscardLive?0:Reload.InitialLive;
            for(int32 Chamber=First;Chamber<FMath::Min(Capacity,Reload.InitialCases);++Chamber)
            {
                FTransform Frame=FPSBodyRevolver::Rigid(Reload.CaseInCylinder[Chamber]*Cylinder);
                const FVector Direction=Frame.GetRotation().RotateVector(Reload.InsertTravel[Chamber].GetSafeNormal());
                Frame.AddToTranslation(Frame.GetRotation().RotateVector(Reload.InsertTravel[Chamber]));
                auto* Weapon=Binding.Mesh.Get();
                DropRevolverCase(Chamber<Reload.InitialLive?Reload.LiveAssets[Chamber].Get():Reload.CaseAssets[Chamber].Get(),
                    Frame*Weapon->GetComponentTransform(),Weapon->GetComponentQuat().RotateVector(Direction));
            }
        }
    }
    const float LoaderSeatTime=Seat*LoaderScale;
    const bool WaitingForDiscardedReload=Reload.bDiscardLive&&Time>=EjectTime&&Time<
        (Hand.bSpeedloaderReload?LoaderSeatTime:SingleSeatTime(0,Hand.ReloadStart==0));
    const int32 Loaded=WaitingForDiscardedReload?0:Hand.LiveRounds;
    for(int32 Chamber=0;Chamber<Capacity;++Chamber)
    {
        const FTransform Seated=Reload.CaseInCylinder[Chamber]*Cylinder;
        FTransform OldCartridge=Seated;
        const int32 FirstEjected=Reload.bDiscardLive?0:Reload.InitialLive;
        if(Time<EjectTime&&Chamber>=FirstEjected&&Chamber<Reload.InitialCases)
            OldCartridge.AddToTranslation(Seated.GetRotation().RotateVector(Reload.InsertTravel[Chamber])*
                Ease(FMath::Max(Open,EjectTime-.20f),EjectTime,Time));
        Pose[Reload.Cases[Chamber]]=OldCartridge;
        Pose[Reload.Rounds[Chamber]]=Reload.RoundInCase[Chamber]*FPSBodyRevolver::Rigid(OldCartridge);
        const int32 CasesVisible=Time<EjectTime?Reload.InitialCases:Loaded;
        if(Chamber>=CasesVisible)Pose[Reload.Cases[Chamber]].SetScale3D(FVector::ZeroVector);
        if(Chamber>=Loaded)Pose[Reload.Rounds[Chamber]].SetScale3D(FVector::ZeroVector);
        auto* Part=Reload.IncomingRounds[Chamber].Get();
        const int32 LoadingIndex=Chamber-(Hand.bSpeedloaderReload?0:Hand.ReloadStart);
        if(LoadingIndex<0||LoadingIndex>=Hand.ReloadCount){Show(Part,false);continue;}
        const float Contact=Hand.bSpeedloaderReload?LoaderSeatTime:SingleSeatTime(LoadingIndex,Hand.ReloadStart==0);
        const float Appear=Hand.bSpeedloaderReload?RoundsVisible*LoaderScale:Contact-.48f;
        if(Time<Appear||Time>=Contact){Show(Part,false);continue;}
        FTransform Incoming=FPSBodyRevolver::Rigid(Seated);
        Incoming.AddToTranslation(Incoming.GetRotation().RotateVector(Reload.InsertTravel[Chamber])*(1.f-Ease(Appear,Contact,Time)));
        if(Part)
        {
            Part->SetRelativeTransform(Incoming);Show(Part,bVisible,Ease(Appear,Appear+.08f,Time));
            FPSBodyEquipment::ApplyShadowFlags(Part,bVisible&&ShouldWorldBodyCastShadow());
        }
    }
    if(Hand.bSpeedloaderReload)
    {
        const float Appear=RoundsVisible*LoaderScale,Withdraw=2.68f*LoaderScale,End=3.02f*LoaderScale;
        FTransform LoaderFrame=Reload.LoaderInCylinder*Cylinder;
        const FVector Extraction=(Reload.CaseInCylinder[0]*Cylinder).GetRotation().RotateVector(Reload.InsertTravel[0]);
        if(Time<LoaderSeatTime)LoaderFrame.AddToTranslation(Extraction*(1.f-Ease(Appear,LoaderSeatTime,Time)));
        else
        {
            if(!Reload.bLoaderReleased)
            {
                Reload.ReleasedLoaderInGun=LoaderFrame.GetRelativeTransform(StableGun);
                Reload.bLoaderReleased=true;
            }
            // Once disengaged, follow the stable gun rather than the closing
            // cylinder. Withdraw in one straight line, then dither away.
            LoaderFrame=Reload.ReleasedLoaderInGun*StableGun;
            const FVector Back=LoaderFrame.GetRotation().RotateVector(Reload.LoaderInCylinder.GetRotation().UnrotateVector(
                Reload.CaseInCylinder[0].GetRotation().RotateVector(Reload.InsertTravel[0].GetSafeNormal())));
            LoaderFrame.AddToTranslation(Back*4.f*Ease(LoaderSeatTime,Withdraw,Time));
        }
        if(auto* Part=Reload.Loader.Get())
        {
            Part->SetRelativeTransform(LoaderFrame);
            Show(Part,bVisible&&Time>=Appear&&Time<End,Ease(Appear,Appear+.08f,Time)*(1.f-Ease(Withdraw,End,Time)));
            FPSBodyEquipment::ApplyShadowFlags(Part,Part->IsVisible()&&ShouldWorldBodyCastShadow());
        }
    }
    else Show(Reload.Loader.Get(),false);
}

void UFPSPlayerBodyComponent::DropRevolverCase(UStaticMesh* Geometry,const FTransform& Frame,const FVector& Direction)
{
    if(!Geometry)return;
    DroppedRevolverCases.RemoveAll([](const auto& Actor){return !Actor.IsValid();});
    if(DroppedRevolverCases.Num()>=48){DroppedRevolverCases[0]->Destroy();DroppedRevolverCases.RemoveAt(0);}
    const FBox Box=Geometry->GetBoundingBox();const FVector Center=Frame.TransformPosition(Box.GetCenter());
    FActorSpawnParameters Parameters;Parameters.Owner=GetOwner();Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Dropped=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),Center,Frame.Rotator(),Parameters);
    if(!Dropped)return;
    auto* Physics=NewObject<UBoxComponent>(Dropped,TEXT("RevolverCaseBody"));Dropped->SetRootComponent(Physics);
    Physics->SetBoxExtent((Box.GetExtent()*Frame.GetScale3D().GetAbs()).ComponentMax(FVector(.15f)));
    Physics->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Physics->SetCollisionObjectType(ECC_PhysicsBody);
    Physics->SetCollisionResponseToAllChannels(ECR_Ignore);Physics->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
    Physics->SetGenerateOverlapEvents(false);Physics->BodyInstance.bUseCCD=true;
    Physics->RegisterComponent();Physics->SetWorldLocationAndRotation(Center,Frame.GetRotation());
    auto* Visual=NewObject<UStaticMeshComponent>(Dropped,TEXT("RevolverCase"));Visual->SetStaticMesh(Geometry);
    Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);Visual->SetupAttachment(Physics);Visual->RegisterComponent();Visual->SetWorldTransform(Frame);
    Visual->SetCustomPrimitiveDataFloat(0,1.f);
    Physics->SetSimulatePhysics(true);Physics->SetMassOverrideInKg(NAME_None,.025f,true);
    Physics->SetPhysicsLinearVelocity(GetOwner()->GetVelocity()+Direction*20.f+FVector(0,0,-20.f));
    Physics->SetPhysicsAngularVelocityInDegrees(GetOwner()->GetActorRightVector()*25.f);
    Dropped->SetLifeSpan(6.f);DroppedRevolverCases.Add(Dropped);
}
