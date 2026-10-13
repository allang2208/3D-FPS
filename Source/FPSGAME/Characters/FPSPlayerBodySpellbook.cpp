#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"

void UFPSPlayerBodyComponent::UpdateFloatingBook(const FFPSBodyMotionSample& Sample,float Alpha)
{
    if(GetNetMode()==NM_DedicatedServer||!Character.IsValid()||!GetBodyMesh())return;
    static const FSoftObjectPath MeshPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/PagesV1/Meshes/SK_Spellbook_Alchemy_16Pages.SK_Spellbook_Alchemy_16Pages"));
    if(Sample.FloatingBook&&!WorldFloatingBook)
    {
        auto* Mesh=Cast<USkeletalMesh>(MeshPath.ResolveObject());
        if(!Mesh)
        {
            if(!FloatingBookLoad)FloatingBookLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(MeshPath);
            return; // the next body tick consumes the latest sample after loading
        }
        WorldFloatingBook=NewObject<UFPSBodyWeaponMeshComponent>(Character.Get(),TEXT("BodyFloatingSpellbook"));
        Character->AddInstanceComponent(WorldFloatingBook);
        WorldFloatingBook->SetupAttachment(GetBodyMesh());
        WorldFloatingBook->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        WorldFloatingBook->SetCanEverAffectNavigation(false);
        WorldFloatingBook->SetSkeletalMesh(Mesh);
        WorldFloatingBook->SetVisibility(false);
        WorldFloatingBook->RegisterComponent();
        WorldFloatingBook->SetComponentTickEnabled(false);
    }
    if(!WorldFloatingBook)return;
    const bool Show=Sample.FloatingBook&&!FPSPlayerBodyWorldBodyHidden()
        &&Sample.BookPose.Num()==WorldFloatingBook->GetSkeletalMeshAsset()->GetRefSkeleton().GetNum();
    FPSBodyEquipment::ApplyOwnerVisibilityFlags(WorldFloatingBook,false,!IsThirdPersonViewEnabled());
    FPSBodyEquipment::ApplyShadowFlags(WorldFloatingBook,Show&&ShouldWorldBodyCastShadow());
    if(Show)
    {
        const bool Snap=!WorldFloatingBook->IsVisible()||SmoothedBookPose.Num()!=Sample.BookPose.Num();
        SmoothedBookFrame.Blend(SmoothedBookFrame,Sample.BookFrame,Snap?1.f:Alpha);
        if(Snap)SmoothedBookPose=Sample.BookPose;
        else for(int32 I=0;I<Sample.BookPose.Num();++I)SmoothedBookPose[I].Blend(SmoothedBookPose[I],Sample.BookPose[I],Alpha);
        WorldFloatingBook->SetRelativeTransform(SmoothedBookFrame);
        WorldFloatingBook->PublishMechanicalPose(SmoothedBookPose);
    }
    if(WorldFloatingBook->IsVisible()!=Show)WorldFloatingBook->SetVisibility(Show);
}
