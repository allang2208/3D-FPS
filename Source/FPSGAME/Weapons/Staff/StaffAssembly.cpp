#include "StaffAssembly.h"
#include "../../UI/ColdSteelInventoryTypes.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
namespace
{
const TCHAR* Slots[]={TEXT("head_crystal"),TEXT("crown"),TEXT("shaft_rune"),TEXT("grip_lining"),TEXT("tail_charm"),TEXT("mana_line")};
FString Path(const FColdSteelItem& I,const TCHAR* Slot){return ColdSteelInventory::Text(I,*(TEXT("staff_part_")+FString(Slot)+TEXT("_mesh")));}
}
void ColdSteelStaffAssembly::Gather(const FColdSteelItem& I,TArray<FSoftObjectPath>& P)
{
    const auto Body=ColdSteelInventory::Text(I,TEXT("staff_body_mesh"));if(!Body.IsEmpty())P.AddUnique(FSoftObjectPath(Body));
    for(const auto* Slot:Slots){const auto S=Path(I,Slot);if(!S.IsEmpty())P.AddUnique(FSoftObjectPath(S));}
}
void ColdSteelStaffAssembly::Clear(UStaticMeshComponent* Root)
{
    if(!Root)return;const auto Children=Root->GetAttachChildren();
    for(USceneComponent* C:Children)if(C->ComponentHasTag(TEXT("StaffPart")))C->DestroyComponent();
}
TArray<UStaticMeshComponent*> ColdSteelStaffAssembly::Components(UStaticMeshComponent* Root)
{
    TArray<UStaticMeshComponent*> Result;if(!Root)return Result;Result.Add(Root);
    for(USceneComponent* C:Root->GetAttachChildren())if(C->ComponentHasTag(TEXT("StaffPart")))if(auto* M=Cast<UStaticMeshComponent>(C))Result.Add(M);
    return Result;
}
FBox ColdSteelStaffAssembly::Bounds(UStaticMeshComponent* Root)
{
    FBox B(ForceInit);for(auto* C:Components(Root))if(C->GetStaticMesh())B+=C->GetStaticMesh()->GetBoundingBox();return B;
}
bool ColdSteelStaffAssembly::Apply(UStaticMeshComponent* Root,const FColdSteelItem& I)
{
    if(!Root)return false;TArray<FSoftObjectPath> Paths;Gather(I,Paths);
    for(const auto& P:Paths)if(!Cast<UStaticMesh>(P.ResolveObject()))return false;
    auto* Body=Cast<UStaticMesh>(FSoftObjectPath(ColdSteelInventory::Text(I,TEXT("staff_body_mesh"))).ResolveObject());if(!Body)return false;
    Clear(Root);Root->ComponentTags.AddUnique(TEXT("StaffAssembly"));Root->SetStaticMesh(Body);Root->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Root->SetCanEverAffectNavigation(false);
    for(const auto* Slot:Slots)
    {
        const FString P=Path(I,Slot);if(P.IsEmpty())continue;
        auto* C=NewObject<UStaticMeshComponent>(Root,NAME_None,RF_Transient);C->ComponentTags.Add(TEXT("StaffPart"));
        C->SetupAttachment(Root);C->SetStaticMesh(Cast<UStaticMesh>(FSoftObjectPath(P).ResolveObject()));
        C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetCanEverAffectNavigation(false);
        C->SetOnlyOwnerSee(Root->bOnlyOwnerSee);C->SetOwnerNoSee(Root->bOwnerNoSee);C->SetCastShadow(Root->CastShadow);
        C->RegisterComponentWithWorld(Root->GetWorld());
    }
    return true;
}
