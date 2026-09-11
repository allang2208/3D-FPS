#include "ColdSteelPickup.h"
#include "ColdSteelUIStyle.h"
#include "Components/StaticMeshComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "GameFramework/PlayerController.h"
#include "Engine/StaticMesh.h"
void AColdSteelPickup::BuildLootGlow(const FColdSteelItem& Item)
{
    FString Rarity=ColdSteelInventory::Text(Item,TEXT("rarity"));if(Rarity.IsEmpty())Rarity=ColdSteelInventory::Text(Item,TEXT("grade"));if(Rarity.IsEmpty())Rarity=TEXT("common");
    FLinearColor Color=ColdSteelUI::RarityColor(Rarity);
    if(Rarity==TEXT("common"))Color=FLinearColor(.8f,.87f,1.f);
    else{auto HSV=Color.LinearRGBToHSV();HSV.G=FMath::Max(HSV.G,.95f);HSV.B=1.f;Color=HSV.HSVToLinearRGB();}
    const float Height=Rarity==TEXT("legendary")?180.f:Rarity==TEXT("mythic")?170.f:Rarity==TEXT("epic")?150.f:Rarity==TEXT("rare")?130.f:Rarity==TEXT("uncommon")?110.f:90.f;
    auto* BeamMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Items/LootFX/M_LootBeam.M_LootBeam"));
    auto* CenterMaterial=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Items/LootFX/M_LootCenter.M_LootCenter"));
    auto* Plane=LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Plane.Plane"));
    if(!BeamMaterial||!CenterMaterial||!Plane){UE_LOG(LogTemp,Error,TEXT("LootGlow: missing materials or plane"));return;}
    LootBeam->SetStaticMesh(Plane);
    auto* BeamMID=UMaterialInstanceDynamic::Create(BeamMaterial,this);BeamMID->SetVectorParameterValue(TEXT("LootColor"),Color);BeamMID->SetScalarParameterValue(TEXT("Intensity"),7.f);LootBeam->SetMaterial(0,BeamMID);
    LootBeam->SetRelativeLocation(FVector(0,0,Height*.5f));LootBeam->SetRelativeScale3D(FVector(Height/100.f,.18f,1.f));LootBeam->SetRelativeRotation(FRotator(90,0,0));LootBeam->SetVisibility(true);
    auto* CenterMID=UMaterialInstanceDynamic::Create(CenterMaterial,this);CenterMID->SetVectorParameterValue(TEXT("LootColor"),Color);CenterMID->SetScalarParameterValue(TEXT("Intensity"),5.f);
    LootCenter->Elements.Empty();LootCenter->AddElement(CenterMID,nullptr,false,20.f,20.f,nullptr);LootCenter->SetVisibility(true);
    UE_LOG(LogTemp,Display,TEXT("LootGlow: %s rarity=%s height=%.0f color=%s"),*Item.Definition,*Rarity,Height,*Color.ToString());
}
void AColdSteelPickup::FaceLootBeam(const APlayerController* PC)
{
    if(!PC||!LootBeam->IsVisible())return;
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);
    // Only yaw faces the viewer: local X stays world-up even when the item rolls.
    LootBeam->SetWorldRotation(FRotator(90.f,(Eye-GetActorLocation()).Rotation().Yaw,0.f));
}
