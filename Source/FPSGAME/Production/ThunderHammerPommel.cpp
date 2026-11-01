#include "ThunderHammerPommel.h"
#include "ThunderHammerTuning.h"
#include "../Skills/LightningTypes.h"
#include "../UI/ColdSteelItemReadCache.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../UI/ColdSteelStatusModel.h"
#include "GameFramework/Pawn.h"
#include "../Weapons/ModularSwordVisual.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"

void ThunderHammerPommel::Configure(FLightningCast& Spell,const FColdSteelItem* Item)
{
    Spell.bLeiXiPommel=false;
    if(!Item||Item->Definition!=ThunderHammer::Definition)return;
    const auto Data=ColdSteelItemData::Read(Item->Data);
    const TSharedPtr<FJsonObject>* Parts=nullptr;FString Pommel;
    if(Data&&Data->TryGetObjectField(TEXT("gunsmith_parts"),Parts))
        (*Parts)->TryGetStringField(TEXT("pommel"),Pommel);
    Spell.bLeiXiPommel=Pommel==LeiXi;
}

void ThunderHammerPommel::ConfirmElectricDamage(AActor* Source,const FLightningCast& Spell,float AppliedDamage)
{
    if(!Spell.bLeiXiPommel||AppliedDamage<=0.f||!IsValid(Source)||!Source->HasAuthority())return;
    auto* Pawn=Cast<APawn>(Source);if(!Pawn||!Pawn->IsPlayerControlled())return;
    const auto* Health=Source->FindComponentByClass<UFPSCombatHealthComponent>();
    if(Health&&Health->IsDead())return;
    auto* Status=UCombatStatusFormula::GetOrAdd(Source);
    const bool AlreadyActive=Status->MagicInspirationAttackSpeed()>1.f;
    Status->GrantMagicInspiration(); // Existing server-owned 10s timer, one stack.
    // Repeated AoE targets refresh the timer without rebuilding the whole HUD.
    if(!AlreadyActive)if(auto* Model=ColdSteelAuthority::ForPawn(Pawn))Model->OnChanged.Broadcast();
}

UMaterialInstanceDynamic* ThunderHammerPommel::BindVisual(UStaticMeshComponent* Root)
{
    for(auto* Part:ColdSteelModularSword::Components(Root))
        for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
            if(auto* Material=Part->GetMaterial(Slot);Material&&Material->GetBaseMaterial()->GetFName()==TEXT("M_LeiXi_StormCore"))
                return Part->CreateAndSetMaterialInstanceDynamic(Slot);
    return nullptr;
}

void ThunderHammerPommel::UpdateVisual(AActor* Holder,UMaterialInstanceDynamic* Core,bool& WasActive)
{
    if(!Holder||!Core)return;
    const auto* Status=Holder->FindComponentByClass<UCombatStatusFormula>();
    const bool Active=Status&&Status->MagicInspirationAttackSpeed()>1.f;
    if(Active!=WasActive){WasActive=Active;Core->SetScalarParameterValue(TEXT("LeiXiActive"),Active?1.f:0.f);}
}

void ThunderHammerPommel::RefreshWorldCore(AActor* Holder,UStaticMeshComponent* Part)
{
    if(!Holder||!Part)return;
    for(int32 Slot=0;Slot<Part->GetNumMaterials();++Slot)
    {
        auto* Material=Part->GetMaterial(Slot);
        if(!Material||!Material->GetBaseMaterial()||Material->GetBaseMaterial()->GetFName()!=TEXT("M_LeiXi_StormCore"))continue;
        auto* Core=Cast<UMaterialInstanceDynamic>(Material);
        if(!Core)Core=Part->CreateDynamicMaterialInstance(Slot);
        if(!Core)continue;
        bool Active=Core->K2_GetScalarParameterValue(TEXT("LeiXiActive"))>.5f;
        UpdateVisual(Holder,Core,Active);
    }
}
