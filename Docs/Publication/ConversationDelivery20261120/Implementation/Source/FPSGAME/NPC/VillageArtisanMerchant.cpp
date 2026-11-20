#include "VillageArtisanMerchant.h"
#include "../UI/ResidentHighlightSubsystem.h"
#include "ArtisanDefenseComponent.h"
#include "ArtisanWoundedAnimInstance.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "AIController.h"
#include "Animation/AnimSequence.h"
#include "../Building/ForgingQuality.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Weapons/Staff/StaffCatalog.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/DamageEvents.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/DamageType.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Net/UnrealNetwork.h"

AVillageArtisanMerchant::AVillageArtisanMerchant()
{
    bReplicates = true;
    SetReplicateMovement(true);
    AIControllerClass = AAIController::StaticClass();
    AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
    bUseControllerRotationYaw = false;
    Tags.AddUnique(TEXT("Friendly"));
    auto* Capsule = GetCapsuleComponent();
    Capsule->InitCapsuleSize(31.f, CapsuleHalfHeight);
    Capsule->SetCollisionProfileName(TEXT("Pawn"));
    Capsule->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    Capsule->SetCanEverAffectNavigation(false);
    // The kneeling torso sits forward of the standing capsule. Aim at the wounded body to help.
    FirstAidTarget = CreateDefaultSubobject<UBoxComponent>(TEXT("KneelingInteractionTarget"));
    FirstAidTarget->SetupAttachment(Capsule);
    FirstAidTarget->InitBoxExtent(FVector(39, 32, 40));
    FirstAidTarget->SetRelativeLocation(FVector(14, 0, 41 - CapsuleHalfHeight));
    FirstAidTarget->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FirstAidTarget->SetCollisionResponseToAllChannels(ECR_Ignore);
    FirstAidTarget->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    FirstAidTarget->SetGenerateOverlapEvents(false);
    FirstAidTarget->SetCanEverAffectNavigation(false);
    Body = GetMesh();
    Body->SetRelativeLocationAndRotation(FVector(0, 0, -CapsuleHalfHeight), FRotator(0, FResidentConversationFacing::RestYaw, 0));
    GetCharacterMovement()->NavAgentProps.bCanCrouch = false;
    GetCharacterMovement()->MaxWalkSpeed = 320.f;
    Vitals = CreateDefaultSubobject<UVillageArtisanVitalsComponent>(TEXT("ArtisanVitals"));
    Defense = CreateDefaultSubobject<UArtisanDefenseComponent>(TEXT("WorkshopDefense"));
}

void AVillageArtisanMerchant::SetLocalConversation(APlayerController* Player)
{
    if (GetNetMode() != NM_DedicatedServer) ConversationFacing.SetLocalPlayer(Vitals->IsDowned() ? nullptr : Player);
}

float AVillageArtisanMerchant::TakeDamage(float Amount, const FDamageEvent& Event, AController* InstigatorController, AActor* Causer)
{
    if (!CanBeDamaged()) return 0.f;
    const UDamageType* Type = Event.DamageTypeClass ? Event.DamageTypeClass->GetDefaultObject<UDamageType>() : GetDefault<UDamageType>();
    const float Loss = Vitals->ReceiveMonsterDamage(Amount, Type, InstigatorController, Causer);
    if (Loss > 0.f) Super::TakeDamage(Loss, Event, InstigatorController, Causer);
    return Loss;
}

void AVillageArtisanMerchant::OnDressed()
{
    StandingIdle = Cast<UAnimSequence>(Body->AnimationData.AnimToPlay);
    Defense->RefreshPresentation();
    if (Vitals->IsDowned()) PlayWoundedPose();
}

void AVillageArtisanMerchant::ResumeWorkPose()
{
    if (!StandingIdle || GetNetMode() == NM_DedicatedServer || Vitals->IsDowned()) return;
    Body->SetRelativeRotation(FRotator(0, FResidentConversationFacing::RestYaw, 0));
    ConversationFacing.StartIdle(*Body, *StandingIdle);
}

void AVillageArtisanMerchant::PlayWoundedPose()
{
    if (!StandingIdle || GetNetMode() == NM_DedicatedServer) return;
    ConversationFacing.SetLocalPlayer(nullptr);
    Body->SetRelativeRotation(FRotator(0, FResidentConversationFacing::RestYaw, 0));
    Body->AnimationData.AnimToPlay = StandingIdle;
    Body->AnimationData.bSavedLooping = true;
    Body->AnimationData.bSavedPlaying = true;
    Body->SetAnimInstanceClass(UArtisanWoundedAnimInstance::StaticClass());
}

void AVillageArtisanMerchant::OnDownedStateChanged(bool bDowned)
{
    GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Visibility, bDowned ? ECR_Ignore : ECR_Block);
    FirstAidTarget->SetCollisionEnabled(bDowned ? ECollisionEnabled::QueryOnly : ECollisionEnabled::NoCollision);
    if (HasAuthority())
    {
        if (bDowned)
        {
            if (auto* AI = Cast<AAIController>(GetController())) AI->StopMovement();
            GetCharacterMovement()->StopMovementImmediately();
            if (GetCharacterMovement()->IsMovingOnGround()) GetCharacterMovement()->DisableMovement();
        }
        else
        {
            GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        }
        Defense->SetDowned(bDowned);
    }
    if (bDowned) PlayWoundedPose();
    else
    {
        ResumeWorkPose();
        Defense->RefreshPresentation();
    }
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
    UResidentHighlightSubsystem::RegisterShopkeeper(*this);
    Defense->OnResumeWork.AddUObject(this, &AVillageArtisanMerchant::ResumeWorkPose);
    if (!HasAuthority()) return;
    Defense->SetAttackDamage(Vitals->WeaponDamage());
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

bool AVillageArtisanMerchant::IsDefending() const
{
    return Defense->IsAlerted();
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
