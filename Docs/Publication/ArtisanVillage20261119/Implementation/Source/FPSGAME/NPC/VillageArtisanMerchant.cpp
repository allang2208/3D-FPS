#include "VillageArtisanMerchant.h"
#include "../Building/ForgingQuality.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

AVillageArtisanMerchant::AVillageArtisanMerchant()
{
    bReplicates = true;
    SetReplicateMovement(true);
    bUseControllerRotationYaw = false;
    Tags.AddUnique(TEXT("Friendly"));
    auto* Capsule = GetCapsuleComponent();
    Capsule->InitCapsuleSize(31.f, CapsuleHalfHeight);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetCanEverAffectNavigation(false);
    Body = GetMesh();
    Body->SetRelativeLocationAndRotation(FVector(0, 0, -CapsuleHalfHeight), FRotator(0, FResidentConversationFacing::RestYaw, 0));
    GetCharacterMovement()->NavAgentProps.bCanCrouch = false;
}

void AVillageArtisanMerchant::SetLocalConversation(APlayerController* Player)
{
    if (GetNetMode() != NM_DedicatedServer) ConversationFacing.SetLocalPlayer(Player);
}

const TCHAR* AVillageArtisanMerchant::TradeMode(bool bSale) const
{
    if (bCarpenter) return bSale ? TEXT("carpenter.sell") : TEXT("carpenter.buy");
    return bSale ? TEXT("blacksmith.sell") : TEXT("blacksmith.buy");
}

bool AVillageArtisanMerchant::SellsDefinition(const FString& Id, const FString& Data) const
{
    if (Id == (bCarpenter ? TEXT("tool_axe") : TEXT("tool_pickaxe"))) return true;
    if (bCarpenter)
    {
        if (!Data.Contains(TEXT("\"bow\"")) && !Data.Contains(TEXT("\"weapon_bow\""))
            && !Data.Contains(TEXT("\"staff\""))) return false;
        if (Id != ColdSteelStaff::CanonicalDefinition(Id)) return false;
    }
    else if (!Data.Contains(TEXT("\"weapon_melee\""))) return false;

    FColdSteelItem Item;
    Item.Data = Data;
    return bCarpenter ? ColdSteelInventory::IsBow(Item) || ColdSteelInventory::IsStaff(Item)
                      : ColdSteelInventory::HasMeleeCategory(Item);
}

void AVillageArtisanMerchant::Restock(FVillageArtisanOffer& Offer) const
{
    Offer.Lot = FGuid::NewGuid();
    Offer.QualityPercent = !bCarpenter && Offer.Definition != TEXT("tool_pickaxe")
        ? FMath::RandRange(ColdSteelForgeQuality::SmithMinPercent, ColdSteelForgeQuality::SmithMaxPercent) : 0;
}

bool AVillageArtisanMerchant::MakeStockItem(const UColdSteelStatusModel& Profile, const FVillageArtisanOffer& Offer, FColdSteelItem& Out) const
{
    Out = Profile.CreateItem(Offer.Definition.ToString());
    if (!Offer.Lot.IsValid() || Out.Data.IsEmpty()) return false;
    Out.InstanceId = Offer.Lot.ToString(EGuidFormats::Digits);
    // The carpenter sells catalogue-grade equipment. Woodworking bonuses come from a paid workpiece.
    return bCarpenter || Offer.Definition == TEXT("tool_pickaxe")
        || ColdSteelForgeQuality::ApplyBlacksmithOffer(Out, Offer.QualityPercent);
}

void AVillageArtisanMerchant::BeginPlay()
{
    Super::BeginPlay();
    if (!HasAuthority()) return;
    const auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if (!Profile) return;
    for (const auto& Pair : Profile->ItemDefinitions())
    {
        if (!SellsDefinition(Pair.Key, Pair.Value)) continue;
        auto& Offer = Offers.AddDefaulted_GetRef();
        Offer.Definition = FName(*Pair.Key);
        Restock(Offer);
    }
    Offers.Sort([](const auto& A, const auto& B){ return A.Definition.LexicalLess(B.Definition); });
}

bool AVillageArtisanMerchant::CanTradeWith(const APawn* Pawn) const
{
    return ResidentConversation::CanReach(Pawn, this);
}

void AVillageArtisanMerchant::RestockSoldLot(const FGuid& Lot)
{
    if (!HasAuthority()) return;
    if (auto* Offer = Offers.FindByPredicate([&](const auto& Entry){ return Entry.Lot == Lot; }))
    {
        Restock(*Offer);
        ForceNetUpdate();
        OnStockChanged.Broadcast();
    }
}

void AVillageArtisanMerchant::OnRep_Offers() { OnStockChanged.Broadcast(); }

void AVillageArtisanMerchant::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AVillageArtisanMerchant, Offers);
}
