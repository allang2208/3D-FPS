#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodySinglePistolSource.h"
#include "FPSBodyPistolMagazineTiming.h"
#include "../FPSGAMECharacter.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshSocket.h"
#include "Engine/World.h"

namespace FPSBodyMagazine
{
constexpr float WithdrawAt=FPSBodyPistolMagazineTiming::Withdraw,ReleaseAt=FPSBodyPistolMagazineTiming::Release,
    AppearAt=FPSBodyPistolMagazineTiming::Appear,InsertAt=FPSBodyPistolMagazineTiming::Seat;
FTransform Rigid(FTransform Frame){Frame.SetScale3D(FVector::OneVector);return Frame;}
}

void UFPSPlayerBodyComponent::PreparePistolMagazine(FFPSBodyMotionBinding& Binding)
{
    auto* Weapon=Binding.Mesh.Get();
    // Equipment can arrive before the replicated dual-wield state.
    if(!Weapon||!Binding.Definition.bGunPistol||Binding.Definition.bGunRevolver)return;
    const FName Definition=Binding.Definition.GunDefinition;
    const TCHAR* Model=Definition==TEXT("ue_m1911")?TEXT("M1911"):
        Definition==TEXT("ue_g18")?TEXT("G18"):Definition==TEXT("ue_pit_viper2011")?TEXT("PitViper2011"):nullptr;
    if(!Model)return;
    const auto& Skeleton=Weapon->GetSkeletalMeshAsset()->GetRefSkeleton();
    const int32 Magazine=Skeleton.FindBoneIndex(TEXT("WPN_SOCKET_Magazine"));
    if(Magazine==INDEX_NONE)return;
    const FString Path=FString::Printf(TEXT("/Game/Weapons/DualPistolMagazineDrop20261022/SM_%s_Magazine_%s"),
        Model,Binding.Definition.AttachHand?TEXT("l"):TEXT("r"));
    auto* Geometry=LoadObject<UStaticMesh>(nullptr,*Path);
    const auto* Exit=Geometry?Geometry->FindSocket(TEXT("MagazineExit")):nullptr;
    if(!Exit)return;
    WorldPistolMagazineAssets.AddUnique(Geometry);Binding.FactoryMagazine=Geometry;
    Binding.MagazineBone=Magazine;Binding.MagazineExit=Exit->RelativeLocation;
    for(int32 Bone=0;Bone<Skeleton.GetNum();++Bone)
        if(Bone==Magazine||Skeleton.BoneIsChildOf(Bone,Magazine))Binding.MagazineBones.Add(Bone);
    for(int32 PartIndex=0;PartIndex<Binding.Parts.Num();++PartIndex)
    {
        const auto* Part=Binding.Parts[PartIndex].Get();
        if(!Part||!Part->GetStaticMesh())continue;
        const FString Name=Part->GetStaticMesh()->GetName();
        if(Name==TEXT("SM_M1911_ext_mag")||Name==TEXT("SM_G18_ext_mag")||Name==TEXT("SM_G18_Drum50")||
            Name==TEXT("SM_PitViper2011_ext_mag"))
        {
            Binding.MagazinePart=PartIndex;
            // Extend the insertion stroke to clear this attachment's actual
            // tower/body. Bounds are transformed once at equipment creation.
            const FTransform PartInMagazine=Binding.FrozenParts[PartIndex].GetRelativeTransform(
                FPSBodyMagazine::Rigid(Binding.FrozenPose[Magazine]));
            const FBox Box=Part->GetStaticMesh()->GetBoundingBox();
            const FVector Axis=Binding.MagazineExit.GetSafeNormal();
            float Minimum=FLT_MAX,Maximum=-FLT_MAX;
            for(int32 Corner=0;Corner<8;++Corner)
            {
                const FVector Point=PartInMagazine.TransformPosition(FVector(Corner&1?Box.Max.X:Box.Min.X,
                    Corner&2?Box.Max.Y:Box.Min.Y,Corner&4?Box.Max.Z:Box.Min.Z));
                const float Projection=FVector::DotProduct(Point,Axis);
                Minimum=FMath::Min(Minimum,Projection);Maximum=FMath::Max(Maximum,Projection);
            }
            Binding.MagazineExit=Axis*FMath::Max(Binding.MagazineExit.Size(),Maximum-Minimum+2.f);
            break;
        }
    }
}

void UFPSPlayerBodyComponent::UpdatePistolMagazine(FFPSBodyMotionBinding& Binding,TArray<FTransform>& Pose,bool bVisible)
{
    using namespace FPSBodyMagazine;
    const bool WasOverridden=Binding.bMagazineOverride;
    Binding.bMagazineOverride=false;Binding.bMagazineHidden=false;
    const int32 Magazine=Binding.MagazineBone,Gun=Binding.NativeWeaponRoot;
    const bool Single=BodyAnimation&&BodyAnimation->UsesNativeSinglePistolSource();
    if((!DisplayState.bDual&&!Single)||!Pose.IsValidIndex(Magazine)||!Pose.IsValidIndex(Gun))return;
    if(Single)BodyAnimation->SinglePistolContact.MagazineStroke=Binding.MagazineExit.Size();
    const auto& HandState=Binding.Definition.AttachHand==0?DisplayState.RightHand:DisplayState.LeftHand;
    const bool Reloading=HandState.bReloading&&HandState.ReloadSourceLength>0.f;
    if(!Reloading)
    {
        Binding.MagazineReloadStartedAt=-100.f;
        Binding.bMagazineDropArmed=false;Binding.bMagazineDropped=false;
        if(!WasOverridden)return;
    }
    const float SourceSeconds=Reloading?HandState.Progress*HandState.ReloadSourceLength:InsertAt;
    if(Reloading&&!FMath::IsNearlyEqual(HandState.ReloadStartedAt,Binding.MagazineReloadStartedAt,.01f))
    {
        Binding.MagazineReloadStartedAt=HandState.ReloadStartedAt;
        // A newly relevant observer must not manufacture an old drop halfway
        // through a reload. An observed release edge emits exactly once.
        Binding.bMagazineDropArmed=SourceSeconds<ReleaseAt;
        Binding.bMagazineDropped=false;
    }
    Binding.bMagazineOverride=true;
    Binding.bMagazineHidden=SourceSeconds>=ReleaseAt&&SourceSeconds<AppearAt;
    const FTransform FrozenGun=FPSBodyMagazine::Rigid(Binding.FrozenPose[Gun]),CurrentGun=FPSBodyMagazine::Rigid(Pose[Gun]);
    const FTransform Seated=Binding.FrozenPose[Magazine].GetRelativeTransform(FrozenGun)*CurrentGun;
    // A cancelled FPS action can leave its smoothed belt-retrieval pose in
    // the contact buffer. Keep the magazine seated until that buffer returns.
    bool NativeReturned=Pose[Magazine].Equals(Seated,.01f);
    const FVector ExitDirection=Seated.GetRotation().RotateVector(Binding.MagazineExit.GetSafeNormal());
    const float Travel=SourceSeconds<ReleaseAt?3.f*FMath::SmoothStep(WithdrawAt,ReleaseAt,SourceSeconds):
        SourceSeconds<AppearAt?(Single?Binding.MagazineExit.Size():0.f):Binding.MagazineExit.Size()*(1.f-FMath::SmoothStep(AppearAt,InsertAt,SourceSeconds));
    FTransform Presented=Seated;Presented.AddToTranslation(ExitDirection*Travel);
    const FTransform Original=FPSBodyMagazine::Rigid(Pose[Magazine]),Destination=FPSBodyMagazine::Rigid(Presented);
    FTransform OriginalContact=Original,PresentedContact=Destination;
    for(int32 Bone:Binding.MagazineBones)
    {
        // Preserve the native internal cartridge visibility and scale while
        // transporting the whole magazine along its own feed axis.
        Pose[Bone]=Pose[Bone].GetRelativeTransform(Original)*Destination;
        if(Binding.bMagazineHidden)Pose[Bone].SetScale3D(FVector::ZeroVector);
    }
    if(Binding.FrozenParts.IsValidIndex(Binding.MagazinePart))
    {
        Binding.MagazinePartPose=Binding.FrozenParts[Binding.MagazinePart].GetRelativeTransform(FrozenGun)*CurrentGun;
        NativeReturned&=Binding.Smoothed.Parts.IsValidIndex(Binding.MagazinePart)&&
            Binding.Smoothed.Parts[Binding.MagazinePart].Equals(Binding.MagazinePartPose,.01f);
        Binding.MagazinePartPose.AddToTranslation(ExitDirection*Travel);
        if(Binding.Smoothed.Parts.IsValidIndex(Binding.MagazinePart))
        {
            // A drum's authored grip belongs to the actual drum shell. Its
            // live attachment frame can differ from WPN_SOCKET_Magazine.
            OriginalContact=FPSBodyMagazine::Rigid(Binding.Smoothed.Parts[Binding.MagazinePart]);
            PresentedContact=FPSBodyMagazine::Rigid(Binding.MagazinePartPose);
        }
    }
    if(Single&&Reloading&&SmoothedContacts.HasSupportGrip)
    {
        const FTransform Root=FPSBodyMagazine::Rigid(Binding.Smoothed.Root);
        const FTransform HandInMagazine=SmoothedContacts.SupportGrip.GetRelativeTransform(OriginalContact*Root);
        BodyAnimation->SinglePistolContact.Operation=HandInMagazine*PresentedContact*Root;
        BodyAnimation->SinglePistolContact.OperationWeight=
            FMath::SmoothStep(FPSBodyPistolMagazineTiming::HandArrive,AppearAt,SourceSeconds)*
            (1.f-FMath::SmoothStep(InsertAt,FPSBodyPistolMagazineTiming::HandRelease,SourceSeconds));
    }
    if(!Reloading&&NativeReturned)Binding.bMagazineOverride=false;
    if(Reloading&&SourceSeconds>=ReleaseAt&&!Binding.bMagazineDropped)
    {
        Binding.bMagazineDropped=true;
        const bool CanDraw=bVisible&&Character.IsValid()&&(!Character->IsLocallyControlled()||IsThirdPersonViewEnabled());
        if(Binding.bMagazineDropArmed&&SourceSeconds<AppearAt&&CanDraw&&GetNetMode()!=NM_DedicatedServer)
        {
            FTransform Released=FPSBodyMagazine::Rigid(Seated);Released.AddToTranslation(ExitDirection*3.f);
            if(Binding.FrozenParts.IsValidIndex(Binding.MagazinePart))
            {
                Released=Binding.FrozenParts[Binding.MagazinePart].GetRelativeTransform(FrozenGun)*CurrentGun;
                Released.AddToTranslation(ExitDirection*3.f);
            }
            const auto* Weapon=Binding.Mesh.Get();
            DropPistolMagazine(Binding,Released*Weapon->GetComponentTransform(),
                Weapon->GetComponentQuat().RotateVector(ExitDirection));
        }
    }
}

void UFPSPlayerBodyComponent::DropPistolMagazine(FFPSBodyMotionBinding& Binding,const FTransform& MagazineFrame,const FVector& ExitDirection)
{
    auto* Part=Binding.Parts.IsValidIndex(Binding.MagazinePart)?Binding.Parts[Binding.MagazinePart].Get():nullptr;
    UStaticMesh* Geometry=Binding.FactoryMagazine.Get();
    if(Part)Geometry=Part->GetStaticMesh();
    if(!Geometry)return;
    DroppedPistolMagazines.RemoveAll([](const auto& Actor){return !Actor.IsValid();});
    if(DroppedPistolMagazines.Num()>=16)
    {DroppedPistolMagazines[0]->Destroy();DroppedPistolMagazines.RemoveAt(0);}
    const FBox Box=Geometry->GetBoundingBox();
    const FVector Center=MagazineFrame.TransformPosition(Box.GetCenter());
    FActorSpawnParameters Parameters;Parameters.Owner=GetOwner();
    Parameters.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    auto* Dropped=GetWorld()->SpawnActor<AActor>(AActor::StaticClass(),Center,MagazineFrame.Rotator(),Parameters);
    if(!Dropped)return;
    auto* Physics=NewObject<UBoxComponent>(Dropped,TEXT("MagazineDropBody"));Dropped->SetRootComponent(Physics);
    Physics->SetBoxExtent((Box.GetExtent()*MagazineFrame.GetScale3D().GetAbs()).ComponentMax(FVector(.2f)));
    Physics->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);Physics->SetCollisionObjectType(ECC_PhysicsBody);
    Physics->SetCollisionResponseToAllChannels(ECR_Ignore);Physics->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
    Physics->SetGenerateOverlapEvents(false);Physics->BodyInstance.bUseCCD=true;
    Physics->RegisterComponent();Physics->SetWorldLocationAndRotation(Center,MagazineFrame.GetRotation());
    auto* Visual=NewObject<UStaticMeshComponent>(Dropped,TEXT("DroppedMagazine"));
    Visual->SetStaticMesh(Geometry);Visual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Visual->SetCastShadow(true);Visual->SetupAttachment(Physics);Visual->RegisterComponent();Visual->SetWorldTransform(MagazineFrame);
    for(int32 MaterialIndex=0;MaterialIndex<Geometry->GetStaticMaterials().Num();++MaterialIndex)
    {
        auto* Material=Part?Part->GetMaterial(MaterialIndex):nullptr;
        if(!Part)if(const auto* Weapon=Binding.Mesh.Get())
        {
            const FName Slot=Geometry->GetStaticMaterials()[MaterialIndex].MaterialSlotName;
            const int32 NativeIndex=Weapon->GetMaterialIndex(Slot);
            if(NativeIndex!=INDEX_NONE)Material=Weapon->GetMaterial(NativeIndex);
        }
        if(Material)Visual->SetMaterial(MaterialIndex,Material);
    }
    Physics->SetSimulatePhysics(true);Physics->SetMassOverrideInKg(NAME_None,.3f,true);
    Physics->SetPhysicsLinearVelocity(GetOwner()->GetVelocity()+ExitDirection*65.f+FVector(0,0,-20.f));
    Physics->SetPhysicsAngularVelocityInDegrees(GetOwner()->GetActorRightVector()*20.f);
    Dropped->SetLifeSpan(8.f);DroppedPistolMagazines.Add(Dropped);
}
