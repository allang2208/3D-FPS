#include "M24Attachments.h"
#include "SniperSuppressorAssets.h"
#include "M24AttachmentCoordinates.h"
#include "M24OpticCoordinates.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace M24Attachments
{
void SetBoltMaterial(USkeletalMeshComponent* Host,const FString& Key)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return;
    const auto* Mesh=Host->GetSkeletalMeshAsset();
    if(!Mesh->GetPathName().StartsWith(TEXT("/Game/Weapons/M24/")))return;
    const int32 Slot=Host->GetMaterialIndex(TEXT("M24_Body"));
    if(!Mesh->GetMaterials().IsValidIndex(Slot))return;
    UMaterialInterface* Desired=Key==CarbonBolt?LoadObject<UMaterialInterface>(nullptr,CarbonBoltMaterial):Mesh->GetMaterials()[Slot].MaterialInterface.Get();
    if(!Desired)return;
    auto* Current=Host->GetMaterial(Slot);
    if(auto* Dynamic=Cast<UMaterialInstanceDynamic>(Current))Current=Dynamic->Parent;
    if(Current!=Desired)Host->SetMaterial(Slot,Desired);
}
bool IsSharedOptic(const FString& Key)
{
    return Key==TEXT("holographic")||Key==TEXT("panoramic_red_dot")||Key==TEXT("prism_scope_2x")
        ||Key==TEXT("lpvo_1_6x")||Key==TEXT("eoth_holographic")||Key==TEXT("kv_scope_4x")||Key==TEXT("thermal_scope");
}
bool IsOptic(const FString& Key){return Key==Scope||Key==IronSight||IsSharedOptic(Key);}
bool IsRearGrip(const FString& Key)
{
    return Key==TEXT("phantom_reargrip")||Key==TEXT("stable_antislip_reargrip")||Key==TEXT("balanced_reargrip");
}
FString MovingOpticPart(const FString& Key)
{return Key==TEXT("lpvo_1_6x")?TEXT("lpvo_ring"):Key==TEXT("thermal_scope")?TEXT("thermal_selector"):FString();}
FString MeshPath(const FString& Key)
{
    if(Key==SniperSuppressorAssets::Zhiming)return SniperSuppressorAssets::ZhimingMesh;
    if(Key==TEXT("m24_rail_seat_native")||Key==TEXT("m24_rail_seat_advanced"))
        return TEXT("/Game/Weapons/M24/RailSeats20261106/Meshes/SM_M24_")+Key;
    if(Key==AdvancedAction)return TEXT("/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_")+Key;
    if(IsRearGrip(Key))return TEXT("/Game/Weapons/M24/RearGrip20261029/Meshes/SM_M24_")+Key;
    const bool Shared=IsSharedOptic(Key)||Key==TEXT("lpvo_ring")||Key==TEXT("thermal_selector");
    return (Shared?TEXT("/Game/Weapons/M24/CommonOptics20261028/Meshes/SM_M24_"):
        Key==IronSight?TEXT("/Game/Weapons/M24/MotionPolish20261027/SM_M24_"):
        Key==ExtendedMagazine?TEXT("/Game/Weapons/M24/MotionMagazine20261027/SM_M24_"):
        TEXT("/Game/Weapons/M24/Surface20261027/SM_M24_"))+Key;
}
float EyeDistanceCM(const FString& Key,float FactoryEyeDistanceCM)
{
    if(Key==IronSight)return IronEyeDistanceCM;
    return FactoryEyeDistanceCM+(IsSharedOptic(Key)?M24OpticCoordinates::OcularForwardCM(Key):0.f);
}
bool IsPart(const FString& Key)
{return IsOptic(Key)||Key==Suppressor||Key==SniperSuppressorAssets::Zhiming||Key==CheekRest||Key==ExtendedMagazine||IsRearGrip(Key)||Key==AdvancedAction
    ||Key==TEXT("m24_rail_seat_native")||Key==TEXT("m24_rail_seat_advanced");}
void FactoryChassisSections(USkeletalMeshComponent* Host,bool Visible)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return;
    const auto* Mesh=Host->GetSkeletalMeshAsset();
    if(const auto* Render=Mesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(!Mesh->GetMaterials().IsValidIndex(M))continue;
                const FName Slot=Mesh->GetMaterials()[M].MaterialSlotName;
                // The retained factory buttstock is independent of the front
                // replacement, including meshes split by the retired full kit.
                if(Slot==TEXT("M24_FactoryChassis"))Host->ShowMaterialSection(M,S,true,L);
                else if(Slot==TEXT("M24_FactoryFront")||Slot==TEXT("M24_FactoryRearSeat"))Host->ShowMaterialSection(M,S,Visible,L);
            }
}
void FactoryMagazineSections(USkeletalMeshComponent* Host,bool Visible)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return;
    const auto* Mesh=Host->GetSkeletalMeshAsset();
    if(const auto* Render=Mesh->GetResourceForRendering())
        for(int32 L=0;L<Render->LODRenderData.Num();++L)
            for(int32 S=0;S<Render->LODRenderData[L].RenderSections.Num();++S)
            {
                const int32 M=Render->LODRenderData[L].RenderSections[S].MaterialIndex;
                if(Mesh->GetMaterials().IsValidIndex(M)&&Mesh->GetMaterials()[M].MaterialSlotName==TEXT("M24_Magazine5"))
                    Host->ShowMaterialSection(M,S,Visible,L);
            }
}
namespace
{
FTransform Reference(const USkeletalMeshComponent* Host,const TCHAR* Name)
{
    FTransform Result=FTransform::Identity;
    const auto& Ref=Host->GetSkeletalMeshAsset()->GetRefSkeleton();
    for(int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE;I=Ref.GetParentIndex(I))
        Result=Result*Ref.GetRefBonePose()[I];
    return Result;
}
}
FTransform Mount(const USkeletalMeshComponent* Host)
{
    if(!Host||!Host->GetSkeletalMeshAsset())return FTransform::Identity;
    using namespace M24AttachmentCoordinates;
    const FVector Rear=Reference(Host,TEXT("WPN_RearSight")).GetLocation();
    const FVector Front=Reference(Host,TEXT("WPN_FrontSight")).GetLocation();
    const FVector Mag=Reference(Host,TEXT("WPN_SOCKET_Magazine")).GetLocation();
    const FQuat Source=FRotationMatrix::MakeFromXZ(SightFront-SightRear,SightRear-Magazine).ToQuat();
    const FQuat Target=FRotationMatrix::MakeFromXZ(Front-Rear,Rear-Mag).ToQuat();
    const FQuat Rotation=Target*Source.Inverse();
    const float Scale=(Front-Rear).Size()/(SightFront-SightRear).Size();
    const FTransform InComponent(Rotation,Rear-Rotation.RotateVector(SightRear*Scale),FVector(Scale));
    return InComponent.GetRelativeTransform(Reference(Host,TEXT("WPN_root")));
}
FVector BareMuzzle(const USkeletalMeshComponent* Host)
{
    return Host->GetSocketTransform(TEXT("WPN_root")).TransformPosition(
        Mount(Host).TransformPosition(M24AttachmentCoordinates::BareMuzzle));
}
UStaticMeshComponent* Configure(AActor* Owner,USkeletalMeshComponent* Host,
    UStaticMeshComponent* Existing,const FString& Key,bool Enabled)
{
    if(!Enabled||!IsPart(Key))
    {if(Existing){Existing->DestroyComponent();}return nullptr;}
    auto* Asset=LoadObject<UStaticMesh>(nullptr,*MeshPath(Key));
    if(!Asset||!Host||!Host->GetSkeletalMeshAsset())return Existing;
    if(!Existing)
    {
        Existing=NewObject<UStaticMeshComponent>(Owner);
        Existing->SetupAttachment(Host,TEXT("WPN_root"));
        Existing->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Existing->SetCastShadow(false);Existing->bReceivesDecals=false;
        Existing->SetVisibility(Host->IsVisible());
        Existing->SetHiddenInGame(Host->bHiddenInGame);
        Existing->RegisterComponent();
    }
    const bool Magazine=Key==ExtendedMagazine;
    Existing->AttachToComponent(Host,FAttachmentTransformRules::KeepRelativeTransform,Magazine?TEXT("WPN_Magazine"):TEXT("WPN_root"));
    if(Existing->GetStaticMesh()!=Asset)Existing->EmptyOverrideMaterials();
    // Shared optics remain in their original +X-forward centimetre frame.
    // Native M24 assemblies are already baked into the source -Y-forward frame.
    FTransform Mounted=Mount(Host);
    if(IsSharedOptic(Key))Mounted=M24OpticCoordinates::InSource(Key)*Mounted;
    else if(Key==SniperSuppressorAssets::Zhiming)
        Mounted=FTransform(FRotator(0,-90,0),M24AttachmentCoordinates::BareMuzzle)*Mounted;
    const FTransform Relative=Magazine?(Mounted*Reference(Host,TEXT("WPN_root"))).GetRelativeTransform(Reference(Host,TEXT("WPN_Magazine"))):Mounted;
    Existing->SetStaticMesh(Asset);Existing->SetRelativeTransform(Relative);
    Existing->SetOnlyOwnerSee(Host->bOnlyOwnerSee);
    Existing->SetFirstPersonPrimitiveType(Host->FirstPersonPrimitiveType);
    Existing->SetVisibility(Host->IsVisible());
    Existing->SetHiddenInGame(Host->bHiddenInGame);
    return Existing;
}
}
