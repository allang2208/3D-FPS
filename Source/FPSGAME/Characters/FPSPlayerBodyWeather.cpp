#include "FPSPlayerBodyComponent.h"
#include "../FPSGAMECharacter.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"

void UFPSPlayerBodyComponent::GetWeatherWeaponMeshes(TArray<FFPSWeatherWeaponMesh>& Out,bool bWorldOnly) const
{
    Out.Reset();
    const auto Add=[&](UMeshComponent* Mesh,uint8 Hand,const FString& Instance)
    {
        if(!Mesh||Instance.IsEmpty()||Mesh->GetFName()==TEXT("StaffV7Arms")
            ||Mesh->GetFName()==TEXT("RuneSwordRift")||Mesh->ComponentHasTag(TEXT("ModularOutfit")))return;
        if(!Out.ContainsByPredicate([Mesh](const auto& Entry){return Entry.Mesh==Mesh;}))
            Out.Add({Mesh,Hand,Instance});
    };
    TArray<USceneComponent*> Children;
    const auto AddBranch=[&](UMeshComponent* Root,uint8 Hand,const FString& Instance)
    {
        if(!Root)return;
        Add(Root,Hand,Instance);
        Children.Reset();Root->GetChildrenComponents(true,Children);
        for(auto* Child:Children)Add(Cast<UMeshComponent>(Child),Hand,Instance);
    };
    if(!bWorldOnly&&Character.IsValid()&&(GetNetMode()==NM_Standalone||Character->IsLocallyControlled()))
    {
        for(const auto& Weapon:LocalWeapons)
        {
            const uint8 Hand=FMath::Min<uint8>(Weapon.AttachHand,1);
            const FString& Instance=Weapon.ItemInstance;
            // Sources cover dual pistols, the staff assembly and tools as well as
            // the rifle. Do not infer a hand from a viewmodel's component name.
            AddBranch(Weapon.Source.Get(),Hand,Instance);
            AddBranch(Weapon.StaticSource.Get(),Hand,Instance);
            Add(Weapon.ReloadPropSource.Get(),Hand,Instance);
            for(const auto& Part:Weapon.SourceParts)Add(Part.Get(),Hand,Instance);
        }
    }
    for(const auto& Pair:WorldEquipmentHands)
        AddBranch(Cast<UMeshComponent>(Pair.Key.Get()),Pair.Value,WorldWeatherInstances[FMath::Min<int32>(Pair.Value,1)]);
}
