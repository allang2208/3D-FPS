#include "MeleeRuneVisual.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "Components/MeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Texture.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/Material.h"
#include "Serialization/JsonSerializer.h"

FString ColdSteelMeleeRune::Selected(const FColdSteelItem& Item)
{
    TSharedPtr<FJsonObject> Data;
    if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data)||!Data)return {};
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Rune;
    if(Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))(*Parts)->TryGetStringField(TEXT("blade_2"),Rune);
    return Rune;
}

void ColdSteelMeleeRune::Apply(UMeshComponent* Mesh,const FString& Rune)
{
    if(!Mesh)return;
    const int32 Mode=Rune==TEXT("resonance_rune")?0:Rune==TEXT("erosion_rune")?1:Rune==TEXT("conduction_rune")?2:-1;
    auto IsOurs=[](UMaterialInterface* M){return M&&M->GetBaseMaterial()->GetName().StartsWith(TEXT("M_SilverRuneSurface"));};
    for(int32 Slot=0;Slot<Mesh->GetNumMaterials();++Slot)
    {
        auto* Current=Mesh->GetOverlayMaterial(true,Slot);
        auto* Base=Mesh->GetMaterial(Slot);
        // A transient MID has an arbitrary object name; classify its source material.
        const FString Name=Base?Base->GetBaseMaterial()->GetName():FString();
        const bool Blade=Name.Contains(TEXT("FrostCrystalSword"))||Name.Contains(TEXT("AzureRunesword"));
        if(Mode<0||!Blade){if(IsOurs(Current))Mesh->SetOverlayMaterial(nullptr,true,Slot);continue;}
        auto* MID=IsOurs(Current)&&Current->GetBaseMaterial()->GetName()==TEXT("M_SilverRuneSurfaceV2")?Cast<UMaterialInstanceDynamic>(Current):nullptr;
        if(!MID)
        {
            auto* Material=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2"));
            if(!Material)return;
            MID=UMaterialInstanceDynamic::Create(Material,Mesh);Mesh->SetOverlayMaterial(MID,true,Slot);
        }
        if(MID->K2_GetScalarParameterValue(TEXT("RuneMode"))!=Mode||!MID->K2_GetTextureParameterValue(TEXT("RuneTexture")))
        {
            auto* Texture=LoadObject<UTexture>(nullptr,*(TEXT("/Game/Weapons/MeleeRunes20260915/SurfaceV2/T_Mask_")+Rune));
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
    }
    return Active;
}
