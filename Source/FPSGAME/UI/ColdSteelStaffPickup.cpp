#include "ColdSteelPickup.h"
#include "../Weapons/Staff/StaffAssembly.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"

bool AColdSteelPickup::BuildStaff(const FColdSteelItem& Item)
{
    if(!ColdSteelStaff::IsStaff(Item))return false;
    const auto Recipe=ColdSteelStaff::Resolve(Item);TArray<FSoftObjectPath> Paths;ColdSteelStaffAssembly::Gather(Recipe,Paths);
    if(StaffLoad)StaffLoad->CancelHandle();Mesh->SetStaticMesh(nullptr);
    // A lightweight physical envelope is available while its particular recipe streams.
    Body->SetBoxExtent(FVector(8,8,80));Mesh->SetRelativeScale3D(FVector(1));
    const FString Identity=Item.InstanceId;
    StaffLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,FStreamableDelegate::CreateWeakLambda(this,[this,Identity,Recipe]()
    {
        if(ItemId!=Identity||!ColdSteelStaffAssembly::Apply(Mesh,Recipe))return;
        const FBox B=ColdSteelStaffAssembly::Bounds(Mesh);Mesh->SetRelativeLocation(-B.GetCenter());
        Body->SetBoxExtent(B.GetExtent().ComponentMax(FVector(1)));Mesh->SetVisibility(true,true);
    }));
    return true;
}
