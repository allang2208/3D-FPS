#include "FPSPlayerBodyComponent.h"
#include "FPSBodyWeaponMeshComponent.h"
#include "../FPSGAMECharacter.h"
#include "Engine/AssetManager.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "Components/DynamicMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "../Weapons/Spellbook/SpellbookGoldGeometry.h"
#include "../Weapons/Spellbook/SpellbookBookOrientation.h"

void UFPSPlayerBodyComponent::ClearFloatingBook()
{
    if(FloatingBookLoad)FloatingBookLoad->CancelHandle();FloatingBookLoad.Reset();
    if(FloatingBookGoldLoad)FloatingBookGoldLoad->CancelHandle();FloatingBookGoldLoad.Reset();
    if(WorldBookGold){WorldBookGold->DestroyComponent();WorldBookGold=nullptr;}WorldBookGoldMaterial=nullptr;
    if(WorldFloatingBook){WorldFloatingBook->DestroyComponent();WorldFloatingBook=nullptr;}
    SmoothedBookPose.Reset();
}

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
    if(Show&&!WorldBookGold)
    {
        static const FSoftObjectPath GoldPath(TEXT("/Game/Weapons/SpellbookEvildeer20261009/Effects/M_Spellbook_GoldOrbit.M_Spellbook_GoldOrbit"));
        auto* Material=Cast<UMaterialInterface>(GoldPath.ResolveObject());
        if(!Material)
        {
            if(!FloatingBookGoldLoad)FloatingBookGoldLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(GoldPath);
        }
        else
        {
            WorldBookGold=NewObject<UDynamicMeshComponent>(Character.Get(),TEXT("BodySpellbookGoldOrbits"));
            Character->AddInstanceComponent(WorldBookGold);WorldBookGold->SetupAttachment(WorldFloatingBook);
            WorldBookGold->SetRelativeTransform(SpellbookBookOrientation::ReadingSurface());
            WorldBookGold->SetCollisionEnabled(ECollisionEnabled::NoCollision);WorldBookGold->SetGenerateOverlapEvents(false);
            WorldBookGold->SetCanEverAffectNavigation(false);WorldBookGold->SetCastShadow(false);
            WorldBookGold->bReceivesDecals=false;WorldBookGold->SetVisibility(false);WorldBookGold->RegisterComponent();
            WorldBookGold->SetComponentTickEnabled(false);WorldBookGold->SetMesh(SpellbookGoldGeometry::Build());
            WorldBookGoldMaterial=UMaterialInstanceDynamic::Create(Material,this);WorldBookGold->SetMaterial(0,WorldBookGoldMaterial);
        }
    }
    if(WorldBookGold)
    {
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(WorldBookGold,false,!IsThirdPersonViewEnabled());
        const bool Glow=Show&&Sample.BookGold.X>UE_SMALL_NUMBER;
        if(WorldBookGold->IsVisible()!=Glow)WorldBookGold->SetVisibility(Glow);
        if(Glow&&WorldBookGoldMaterial)
        {
            const float Age=Sample.BookGold.Y+FMath::Clamp(ServerClock()-DisplayState.PresentationSampledAt,0.f,.12f);
            WorldBookGoldMaterial->SetScalarParameterValue(TEXT("GoldAge"),Age);
            WorldBookGoldMaterial->SetScalarParameterValue(TEXT("Fade"),Sample.BookGold.X);
            WorldBookGoldMaterial->SetScalarParameterValue(TEXT("PageActivity"),Sample.BookGold.Z);
        }
    }
}
