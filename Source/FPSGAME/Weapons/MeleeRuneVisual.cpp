#include "MeleeRuneVisual.h"
#include "FrostSwordRunes.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Serialization/JsonSerializer.h"

namespace
{
bool IsNativeGold(UMaterialInterface* Material)
{
    const auto* Base=Material?Material->GetBaseMaterial():nullptr;
    return Base&&Base->GetName()==TEXT("M_AzureRunesword_NativeGold");
}

UMaterialInterface* FactoryMaterial(UMeshComponent* Mesh,int32 Slot)
{
    if(const auto* Static=Cast<UStaticMeshComponent>(Mesh))
        if(UStaticMesh* Asset=Static->GetStaticMesh())return Asset->GetMaterial(Slot);
    if(const auto* Skeletal=Cast<USkeletalMeshComponent>(Mesh))
        if(auto* Asset=Skeletal->GetSkeletalMeshAsset())
            if(Asset->GetMaterials().IsValidIndex(Slot))return Asset->GetMaterials()[Slot].MaterialInterface;
    return LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/M_AzureRunesword"));
}
}

FString ColdSteelMeleeRune::Selected(const FColdSteelItem& Item)
{
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return {};
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    if(Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))(*Parts)->TryGetStringField(TEXT("blade_2"),Rune);
    return ColdSteelFrostRunes::Upgrade(Item.Definition,Rune);
}

void ColdSteelMeleeRune::Apply(UMeshComponent* Mesh,const FString& Rune,const FString& Definition)
{
    if(!Mesh)return;
    const bool bFrost=Definition==ColdSteelFrostRunes::Definition;
    const FString EquippedRune=ColdSteelFrostRunes::Upgrade(Definition,Rune);
    const bool bInnate=bFrost&&(EquippedRune.IsEmpty()||EquippedRune==TEXT("false"));
    const FString VisualRune=bInnate?TEXT("erosion_rune"):EquippedRune;
    const bool bGolden=VisualRune==TEXT("golden_glow_rune");
    const bool bSpirit=bFrost&&VisualRune==ColdSteelFrostRunes::SpiritBurst;
    const bool bWild=Definition==TEXT("ue_highland_claymore")&&VisualRune==TEXT("wild_rune");
    const int32 Mode=bWild?5:bSpirit?4:bGolden?3:VisualRune==TEXT("resonance_rune")?0:VisualRune==TEXT("erosion_rune")?1:VisualRune==TEXT("conduction_rune")?2:-1;
    auto IsOurs=[](UMaterialInterface* M){auto* Base=M?M->GetBaseMaterial():nullptr;return Base&&(Base->GetName().StartsWith(TEXT("M_SilverRuneSurface"))||Base->GetName()==TEXT("M_SilverRuneSurfaceV2"));};
    for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
    {
        auto* Current=Mesh->GetOverlayMaterial(true,Slot);
        auto* Base=Mesh->GetMaterial(Slot);
        const FString BaseName=Base&&Base->GetBaseMaterial()?Base->GetBaseMaterial()->GetName():FString();
        if(BaseName==TEXT("M_HighlandClaymoreSurface"))
        {
            // Recolor native ink on its original UVs alongside the selected rune.
            auto* HighlandMID=Cast<UMaterialInstanceDynamic>(Base);
            if(!HighlandMID){HighlandMID=UMaterialInstanceDynamic::Create(Base,Mesh);Mesh->SetMaterial(Slot,HighlandMID);}
            HighlandMID->SetScalarParameterValue(TEXT("NativeGold"),0.f);
            HighlandMID->SetScalarParameterValue(TEXT("NativeWild"),bWild?1.f:0.f);
        }
        const bool NativeSword=Definition==TEXT("ue_rune_sword")||
            (Definition.IsEmpty()&&BaseName.Contains(TEXT("AzureRunesword")));
        const bool UseNativeGold=bGolden&&NativeSword&&BaseName.Contains(TEXT("AzureRunesword"));
        if(UseNativeGold)
        {
            // The cut guard contains the lowest native blade glyphs. It needs its
            // own UV0 mask so unrelated guard UV islands never inherit blade ink.
            if(IsOurs(Current))Mesh->SetOverlayMaterial(nullptr,true,Slot);
            auto* NativeMID=IsNativeGold(Base)?Cast<UMaterialInstanceDynamic>(Base):nullptr;
            if(!NativeMID)
            {
                auto* Native=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold"));
                if(!Native)continue;
                NativeMID=UMaterialInstanceDynamic::Create(Native,Mesh);
                Mesh->SetMaterial(Slot,NativeMID);
            }
            NativeMID->SetScalarParameterValue(TEXT("GoldAmount"),1.f);
            const bool GuardRoot=Mesh->ComponentHasTag(TEXT("SwordSlot=guard"));
            auto* Ink=LoadObject<UTexture>(nullptr,GuardRoot?
                TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/T_RuneSword_GuardNativeMask"):
                TEXT("/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/T_RuneSword_NativeMask"));
            if(Ink)NativeMID->SetTextureParameterValue(TEXT("NativeRuneMask"),Ink);
            continue;
        }
        if(IsNativeGold(Base))
        {
            Base=FactoryMaterial(Mesh,Slot);
            Mesh->SetMaterial(Slot,Base);
        }
        // A transient MID has an arbitrary object name; classify its source material.
        const FString Name=Base?Base->GetBaseMaterial()->GetName():FString();
        const bool Blade=Name.Contains(TEXT("FrostCrystalSword"))||Name.Contains(TEXT("AzureRunesword"))||Name==TEXT("M_HighlandClaymoreSurface");
        if(Mode<0||!Blade){if(IsOurs(Current))Mesh->SetOverlayMaterial(nullptr,true,Slot);continue;}
        auto* MID=IsOurs(Current)?Cast<UMaterialInstanceDynamic>(Current):nullptr;
        const FString DesiredBase=bWild?TEXT("M_SilverRuneSurface_HighlandWild"):bSpirit?TEXT("M_SilverRuneSurface_FrostSpirit"):TEXT("M_SilverRuneSurfaceV2");
        if(MID&&MID->GetBaseMaterial()->GetName()!=DesiredBase)MID=nullptr;
        if(!MID)
        {
            auto* Material=LoadObject<UMaterialInterface>(nullptr,bWild?
                TEXT("/Game/Weapons/HighlandClaymore20260922/WildRune/M_SilverRuneSurface_HighlandWild"):bSpirit?
                TEXT("/Game/Weapons/FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit"):
                TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2"));
            if(!Material)return;
            MID=UMaterialInstanceDynamic::Create(Material,Mesh);Mesh->SetOverlayMaterial(MID,true,Slot);
        }
        MID->SetScalarParameterValue(TEXT("GoldenTint"),bGolden?1.f:0.f);
        MID->SetScalarParameterValue(TEXT("BaseBrightness"),bInnate?.65f:.85f);
        MID->SetScalarParameterValue(TEXT("GlowStrength"),bInnate?.75f:1.25f);
        if(MID->K2_GetScalarParameterValue(TEXT("RuneMode"))!=Mode||!MID->K2_GetTextureParameterValue(TEXT("RuneTexture")))
        {
            // Other swords retain their existing projected rune appearance.
            FString MaskName=bSpirit?TEXT("erosion_rune"):VisualRune;
            if(bGolden)
            {
                MaskName=TEXT("resonance_rune");
            }
            const FString TexturePath=bWild?TEXT("/Game/Weapons/HighlandClaymore20260922/WildRune/T_Mask_wild_rune"):
                TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_")+MaskName;
            auto* Texture=LoadObject<UTexture>(nullptr,*TexturePath);
            if(!Texture&&bGolden)Texture=LoadObject<UTexture>(nullptr,TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_resonance_rune"));
            MID->SetTextureParameterValue(TEXT("RuneTexture"),Texture);
            MID->SetScalarParameterValue(TEXT("RuneMode"),Mode);
        }
    }
    UpdatePose(Mesh);
}

bool ColdSteelMeleeRune::UpdatePose(UMeshComponent* Mesh,double PreviewTime)
{
    if(!Mesh)return false;
    bool Active=false;
    for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
    {
        if(auto* Native=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(Slot));Native&&IsNativeGold(Native))
        {
            Native->SetScalarParameterValue(TEXT("PreviewTime"),PreviewTime);
            Active=true;
        }
        auto* MID=Cast<UMaterialInstanceDynamic>(Mesh->GetOverlayMaterial(true,Slot));
        if(!MID||!MID->GetBaseMaterial()->GetName().StartsWith(TEXT("M_SilverRuneSurface")))continue;
        Active=true;
        // The current skinned frame also works with GPU skin cache. The shader
        // uses component-space positions and normals, without new UVs or bones.
        FVector Origin=FVector::ZeroVector,Axis=FVector::UpVector;
        if(const auto* Skinned=Cast<USkeletalMeshComponent>(Mesh))
        {
            const FVector Base=Skinned->GetSocketTransform(TEXT("Blade_Base"),RTS_Component).GetLocation();
            const FVector Tip=Skinned->GetSocketTransform(TEXT("Blade_Tip"),RTS_Component).GetLocation();
            Axis=(Tip-Base).GetSafeNormal();Origin=Base-Axis*3.;
        }
        MID->SetVectorParameterValue(TEXT("BladeOrigin"),FLinearColor(Origin.X,Origin.Y,Origin.Z,0));
        MID->SetVectorParameterValue(TEXT("BladeAxis"),FLinearColor(Axis.X,Axis.Y,Axis.Z,0));
        MID->SetScalarParameterValue(TEXT("PreviewTime"),PreviewTime);
        // 金色强化：呼吸闪光由材质端按 GoldenTint 增强，每帧保持同步。
        MID->SetScalarParameterValue(TEXT("GoldenTint"),FMath::IsNearlyEqual(MID->K2_GetScalarParameterValue(TEXT("RuneMode")),3.f)?1.f:0.f);
    }
    return Active;
}
