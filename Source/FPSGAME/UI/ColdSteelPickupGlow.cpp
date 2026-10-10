#include "ColdSteelPickup.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelItemRarity.h"
#include "Components/StaticMeshComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StaticMesh.h"
void AColdSteelPickup::BuildLootGlow(const FColdSteelItem& Item)
{
    // Both progression systems share the established white/green/blue/purple/
    // gold/red palette and its world-space saturation adjustment.
    const auto LootColorForRarity=[](const FString& Key)
    {
        if(Key==TEXT("common"))return FLinearColor(.8f,.87f,1.f);
        auto HSV=ColdSteelUI::RarityColor(Key).LinearRGBToHSV();
        HSV.G=FMath::Max(HSV.G,.95f);HSV.B=1.f;
        return HSV.HSVToLinearRGB();
    };
    const bool Equipment=ColdSteelItemRarity::IsEquipment(Item);
    const int32 Enhancement=Equipment?FMath::Max(0,int32(ColdSteelInventory::Number(Item,TEXT("enhanceLevel")))):0;
    FString Rarity;
    FLinearColor Color=ColdSteelUI::Accent;
    float Height=90.f,BeamIntensity=7.f,CenterIntensity=5.f;
    if(Equipment)
    {
        // Only numeric enhancement controls equipment loot beams. Tool material
        // levels, crafting quality and enchantments are separate progression.
        struct FEnhancementLootTier
        {
            int32 MinimumLevel;
            const TCHAR* ColorKey;
            float Height,BeamIntensity,CenterIntensity;
        };
        const FEnhancementLootTier Tiers[]={
            {0,TEXT("common"),90.f,7.f,5.f},
            {1,TEXT("uncommon"),105.f,7.4f,5.2f},
            {4,TEXT("rare"),120.f,7.8f,5.4f},
            {7,TEXT("epic"),135.f,8.2f,5.6f},
            {10,TEXT("mythic"),150.f,8.6f,5.8f},
            {13,TEXT("legendary"),165.f,9.f,6.f}
        };
        const FEnhancementLootTier* Selected=&Tiers[0];
        for(const auto& Tier:Tiers)
        {
            if(Enhancement<Tier.MinimumLevel)break;
            Selected=&Tier;
        }
        // Color keys are palette references, never an equipment rarity value.
        Color=LootColorForRarity(Selected->ColorKey);Height=Selected->Height;
        BeamIntensity=Selected->BeamIntensity;CenterIntensity=Selected->CenterIntensity;
    }
    else
    {
        Rarity=ColdSteelInventory::Text(Item,TEXT("rarity"));if(Rarity.IsEmpty())Rarity=ColdSteelInventory::Text(Item,TEXT("grade"));if(Rarity.IsEmpty())Rarity=TEXT("common");
        Color=LootColorForRarity(Rarity);
        Height=Rarity==TEXT("legendary")?180.f:Rarity==TEXT("mythic")?170.f:Rarity==TEXT("epic")?150.f:Rarity==TEXT("rare")?130.f:Rarity==TEXT("uncommon")?110.f:90.f;
    }
    auto* BeamMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Items/LootFX/M_LootBeam.M_LootBeam"));
    auto* CenterMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter"));
    auto* Plane=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    if(!BeamMaterial||!CenterMaterial||!Plane){UE_LOG(LogTemp,Error,TEXT("LootGlow: missing materials or plane"));return;}
    LootBeam->SetStaticMesh(Plane);
    auto* BeamMID=UMaterialInstanceDynamic::Create(BeamMaterial,this);BeamMID->SetVectorParameterValue(TEXT("LootColor"),Color);BeamMID->SetScalarParameterValue(TEXT("Intensity"),BeamIntensity);LootBeam->SetMaterial(0,BeamMID);
    LootBeam->SetRelativeLocation(FVector(0,0,Height*.5f));LootBeam->SetRelativeScale3D(FVector(Height/100.f,.18f,1.f));LootBeam->SetRelativeRotation(FRotator(90,0,0));LootBeam->SetVisibility(true);
    auto* CenterMID=UMaterialInstanceDynamic::Create(CenterMaterial,this);CenterMID->SetVectorParameterValue(TEXT("LootColor"),Color);CenterMID->SetScalarParameterValue(TEXT("Intensity"),CenterIntensity);
    LootCenter->Elements.Empty();LootCenter->AddElement(CenterMID,nullptr,false,20.f,20.f,nullptr);LootCenter->SetVisibility(true);
    UE_LOG(LogTemp,Display,TEXT("LootGlow: %s enhance=%d rarity=%s height=%.0f color=%s"),*Item.Definition,Enhancement,Equipment?TEXT("none"):*Rarity,Height,*Color.ToString());
}
void AColdSteelPickup::FaceLootBeam(const APlayerController* PC)
{
    if(!PC||!LootBeam->IsVisible())return;
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    // Only yaw faces the viewer: local X stays world-up even when the item rolls.
    LootBeam->SetWorldRotation(FRotator(90.f,(Eye-GetActorLocation()).Rotation().Yaw,0.f));
}
