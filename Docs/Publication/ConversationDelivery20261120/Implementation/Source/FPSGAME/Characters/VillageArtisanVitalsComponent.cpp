#include "VillageArtisanVitalsComponent.h"

#include "../NPC/VillageArtisanMerchant.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "GameFramework/Controller.h"
#include "Net/UnrealNetwork.h"

namespace
{
    // Equal sixty-point budgets, in the player sheet's STR, DEX, INT, CON, WIS, LUCK order.
    const CoreCombatFormula::Attributes Smith{17, 8, 7, 15, 7, 6};
    const CoreCombatFormula::Attributes Carpenter{9, 16, 11, 10, 8, 6};

    bool IsMonster(const AActor* Source)
    {
        return IsValid(Source) && (Source->ActorHasTag(TEXT("Enemy")) || Source->FindComponentByClass<UMonsterCombatComponent>())
            && !Source->ActorHasTag(TEXT("Friendly")) && !Source->ActorHasTag(TEXT("Wildlife"));
    }
}

UVillageArtisanVitalsComponent::UVillageArtisanVitalsComponent()
{
    SetIsReplicatedByDefault(true);
}

const CoreCombatFormula::Attributes& UVillageArtisanVitalsComponent::Attributes() const
{
    return CastChecked<AVillageArtisanMerchant>(GetOwner())->IsCarpenterMerchant() ? Carpenter : Smith;
}

float UVillageArtisanVitalsComponent::MaxHealth() const
{
    return CoreCombatFormula::Player(Attributes()).MaxHp;
}

float UVillageArtisanVitalsComponent::WeaponDamage() const
{
    const auto& A = Attributes();
    const auto* Resident = CastChecked<AVillageArtisanMerchant>(GetOwner());
    const auto* Game = Resident->GetGameInstance();
    const auto* Catalogue = Game ? Game->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    const double BaseAttack = CoreCombatFormula::Player(A).Atk;
    if (!Catalogue) return BaseAttack;

    const bool bBow = Resident->IsCarpenterMerchant();
    const auto Item = Catalogue->CreateItem(bBow ? TEXT("bow_dark") : TEXT("ue_steel_warhammer"));
    if (bBow)
        return CoreCombatFormula::Round(ColdSteelInventory::Number(Item, TEXT("full_damage"), 69.) +
            BaseAttack * ColdSteelInventory::Number(Item, TEXT("bow_damage_coefficient_scale"), 1.5));

    // Read the unmodified hammer's actual STR/CON scaling without borrowing a local player's equipment.
    const auto* Enhancement = Game->GetSubsystem<UColdSteelEnhancementSystem>();
    const auto Formula = Enhancement ? Enhancement->AttackFormula(Item) : nullptr;
    if (!Formula) return BaseAttack;
    std::vector<CoreCombatFormula::WeaponTerm> Terms;
    for (const auto& Entry : Formula->GetArrayField(TEXT("attrs")))
    {
        const auto Term = Entry->AsObject();
        const FString Key = Term->GetStringField(TEXT("key"));
        const double Value = Key == TEXT("str") ? A.Str : Key == TEXT("con") ? A.Con :
            Key == TEXT("dex") ? A.Dex : Key == TEXT("int") ? A.Int : Key == TEXT("wis") ? A.Wis : A.Luck;
        Terms.push_back({Value, Term->GetNumberField(TEXT("base")), 0});
    }
    return CoreCombatFormula::Weapon(Formula->GetNumberField(TEXT("base")), 0, 0, Terms);
}

void UVillageArtisanVitalsComponent::BeginPlay()
{
    Super::BeginPlay();
    if (GetOwner()->HasAuthority()) Health = MaxHealth();
}

float UVillageArtisanVitalsComponent::ReceiveMonsterDamage(float Amount, const UDamageType* Type, AController* Instigator, AActor* Causer)
{
    if (!GetOwner()->HasAuthority() || IsDowned() || !(Amount > 0.f)) return 0.f;
    if (!IsMonster(Instigator ? Instigator->GetPawn() : nullptr) && !IsMonster(Causer) &&
        !(Causer && (IsMonster(Causer->GetInstigator()) || IsMonster(Causer->GetOwner())))) return 0.f;
    const auto Stats = CoreCombatFormula::Player(Attributes());
    const bool bMagic = CombatFormulaRuntime::IsMagic(Type);
    const float Loss = FMath::Min(Health, float(CoreCombatFormula::Defense(Amount, bMagic ? Stats.Mdef : Stats.Def, bMagic)));
    SetHealth(Health - Loss);
    return Loss;
}

bool UVillageArtisanVitalsComponent::ReviveFromFirstAid(APawn* Rescuer)
{
    if (!GetOwner()->HasAuthority() || !IsDowned() || !IsValid(Rescuer) || !Rescuer->IsPlayerControlled() ||
        Rescuer->GetWorld() != GetWorld()) return false;
    SetHealth(MaxHealth());
    return true;
}

void UVillageArtisanVitalsComponent::SetHealth(float NewHealth)
{
    if (NewHealth == Health) return;
    const float Previous = Health;
    Health = NewHealth;
    OnRep_Health(Previous);
    GetOwner()->ForceNetUpdate();
}

void UVillageArtisanVitalsComponent::OnRep_Health(float Previous)
{
    if ((Previous <= 0.f) != IsDowned())
        CastChecked<AVillageArtisanMerchant>(GetOwner())->OnDownedStateChanged(IsDowned());
}

void UVillageArtisanVitalsComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UVillageArtisanVitalsComponent, Health);
}
