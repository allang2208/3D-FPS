#include "ColdSteelPickup.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"

bool AColdSteelPickup::BuildProductionTool(const FColdSteelItem& Item)
{
    if (ColdSteelInventory::Text(Item,TEXT("category"))!=TEXT("tool")) return false;
    const FSoftObjectPath Path(ColdSteelInventory::Text(Item,TEXT("tool_mesh")));
    const float Scale=ColdSteelInventory::Number(Item,TEXT("tool_scale"),.65);
    const FString Id=Item.InstanceId;
    Mesh->SetStaticMesh(nullptr);
    ProductionToolLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,
        FStreamableDelegate::CreateWeakLambda(this,[this,Path,Scale,Id]()
        {
            if (Id!=ItemId) return;
            auto* Asset=Cast<UStaticMesh>(Path.ResolveObject()); if (!Asset) return;
            const auto Bounds=Asset->GetBounds();
            Mesh->SetStaticMesh(Asset); Mesh->SetRelativeScale3D(FVector(Scale));
            Mesh->SetRelativeLocation(-Bounds.Origin*Scale);
            Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(2)));
            Body->SetMassOverrideInKg(NAME_None,1.5f);
        }));
    return true;
}
