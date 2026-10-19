#include "FPSBodyRuneVisual.h"
#include "FPSPlayerBodyTypes.h"
#include "../Weapons/MeleeRuneVisual.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Weapons/FrostSwordRunes.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"

namespace
{
UMaterialInstanceDynamic* RuneMaterial(UMaterialInterface* Material)
{
    auto* MID=Cast<UMaterialInstanceDynamic>(Material);
    const auto* Base=MID?MID->GetBaseMaterial():nullptr;
    if(!Base)return nullptr;
    const FString Name=Base->GetName();
    return (Name.StartsWith(TEXT("M_SilverRuneSurface"))||Name.StartsWith(TEXT("M_TangDaoBladeRuneSurface"))||
        Name.StartsWith(TEXT("M_XuanChiBladeRuneSurface"))||Name==TEXT("M_AzureRunesword_NativeGold"))?MID:nullptr;
}
}

void FPSBodyRuneVisual::Capture(UStaticMeshComponent* Source,const FColdSteelItem* Item,FFPSBodyAttachment& Out)
{
    if(!Source||!Item||(!ColdSteelInventory::IsTwoHandedSword(*Item)&&!ColdSteelInventory::IsTwoHandedBlunt(*Item)))return;
    Out.bChixiaoBlade=Source->ComponentTags.Contains(FName(TEXT("SwordSlot=blade_1")))&&ColdSteelModularSword::UsesChixiaoDoubleHeavy(*Item);
    Out.bZhufengBlade=Source->ComponentTags.Contains(FName(TEXT("SwordSlot=blade_1")))&&ColdSteelModularSword::UsesZhufengWhirlwind(*Item);
    if(Out.bChixiaoBlade||Out.bZhufengBlade)
    {
        // Blade-specific trails also work with no rune material installed.
        Out.BeiweiBladeBase=ColdSteelModularSword::BladePoint(*Item,false);
        Out.BeiweiBladeTip=ColdSteelModularSword::BladePoint(*Item,true);
    }
    for(int32 Slot=0;Slot<Source->GetNumMaterials();++Slot)
    {
        auto* MID=RuneMaterial(Source->GetOverlayMaterial(true,Slot));
        if(!MID)MID=RuneMaterial(Source->GetMaterial(Slot));
        if(!MID)continue;
        const bool NativeGold=MID->GetBaseMaterial()->GetName()==TEXT("M_AzureRunesword_NativeGold");
        if(!NativeGold&&MID->K2_GetScalarParameterValue(TEXT("RuneMode"))<0.f)continue;
        Out.RuneDefinition=Item->Definition;Out.RuneId=ColdSteelMeleeRune::Selected(*Item);
        if(Out.RuneDefinition==ColdSteelFrostRunes::Zhanmadao&&Out.RuneId==ColdSteelFrostRunes::Beiwei)
        {
            Out.BeiweiBladeBase=ColdSteelModularSword::BladePoint(*Item,false);
            Out.BeiweiBladeTip=ColdSteelModularSword::BladePoint(*Item,true);
        }
        for(FName Tag:Source->ComponentTags)
            if(Tag.ToString().StartsWith(TEXT("SwordSlot="))){Out.RuneSlot=Tag;break;}
        const auto D=MID->K2_GetVectorParameterValue(TEXT("Dimensions"));
        if(D.R>0.f&&D.G>0.f&&D.B>0.f)Out.RuneDimensions=FVector(D.R,D.G,D.B);
        return;
    }
}

void FPSBodyRuneVisual::Apply(UStaticMeshComponent* Mesh,const FFPSBodyAttachment& Description)
{
    if(!Mesh||Description.RuneDefinition.IsEmpty())return;
    if(!Description.RuneSlot.IsNone())Mesh->ComponentTags.AddUnique(Description.RuneSlot);
    ColdSteelMeleeRune::Apply(Mesh,Description.RuneId,Description.RuneDefinition);
    const auto& D=Description.RuneDimensions;
    for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
    {
        if(auto* MID=RuneMaterial(Mesh->GetOverlayMaterial(true,Slot)))
            MID->SetVectorParameterValue(TEXT("Dimensions"),FLinearColor(D.X,D.Y,D.Z,0));
        if(auto* MID=RuneMaterial(Mesh->GetMaterial(Slot)))
            MID->SetVectorParameterValue(TEXT("Dimensions"),FLinearColor(D.X,D.Y,D.Z,0));
    }
}

FString FPSBodyRuneVisual::Key(const FFPSBodyAttachment& Description)
{
    return Description.RuneDefinition.IsEmpty()&&!Description.bChixiaoBlade&&!Description.bZhufengBlade?FString():TEXT("|rune:")+Description.RuneDefinition+
        TEXT(":")+Description.RuneId+TEXT(":")+Description.RuneSlot.ToString()+TEXT(":")+Description.RuneDimensions.ToString()+
        TEXT(":")+Description.BeiweiBladeBase.ToString()+TEXT(":")+Description.BeiweiBladeTip.ToString()+
        (Description.bChixiaoBlade?TEXT(":chixiao"):TEXT(""))+(Description.bZhufengBlade?TEXT(":zhufeng"):TEXT(""));
}
