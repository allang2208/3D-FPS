#include "ResidentConversation.h"
#include "VillageArtisanMerchant.h"
#include "VillageBaker.h"
#include "ChapelNun.h"
#include "VillageHerbalist.h"
#include "VillageMasterArtisan.h"
#include "VillageMillKeeper.h"
#include "../Movement/StableHorseMarket.h"
#include "GameFramework/Character.h"
#include "../WorldGeneration/VillageGunshopServices.h"
#include "VillageTavernKeeper.h"
#include "ResidentTurnAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

void ResidentConversation::SetLocalFacing(AActor* Speaker, APlayerController* Viewer)
{
    if (!IsValid(Speaker) || Speaker->GetNetMode()==NM_DedicatedServer ||
        (Viewer && (!Viewer->IsLocalController() || Viewer->GetWorld()!=Speaker->GetWorld()))) return;
    if (auto* Artisan=Cast<AVillageArtisanMerchant>(Speaker)) Artisan->SetLocalConversation(Viewer);
    else if (auto* Nun=Cast<AChapelNun>(Speaker)) Nun->SetLocalConversation(Viewer);
    else if (auto* Baker=Cast<AVillageBaker>(Speaker)) Baker->SetLocalConversation(Viewer);
    else if (auto* Master=Cast<AVillageMasterArtisan>(Speaker)) Master->SetLocalConversation(Viewer);
    else if (auto* Miller=Cast<AVillageMillKeeper>(Speaker)) Miller->SetLocalConversation(Viewer);
    else if (auto* Keeper=Cast<AVillageTavernKeeper>(Speaker)) Keeper->SetLocalConversation(Viewer);
    else if (auto* Herbalist=Cast<AVillageHerbalist>(Speaker)) Herbalist->SetLocalConversation(Viewer);
    else if (auto* Gunshop=Cast<AVillageGunshopCounter>(Speaker)) Gunshop->SetLocalConversation(Viewer);
    else if (StableHorseMarket::IsSeller(Speaker))
    {
        // The placed resident is an authored Character blueprint with a looping single-node idle.
        auto* Resident=Cast<ACharacter>(Speaker);
        auto* Body=Resident ? Resident->GetMesh() : nullptr;
        if (!Body) return;
        if (auto* Turn=Cast<UResidentTurnAnimInstance>(Body->GetAnimInstance()))
            Turn->ConversationPlayer=Viewer;
        else if (Viewer)
        {
            auto* Single=Body->GetSingleNodeInstance();
            auto* Idle=Single ? Cast<UAnimSequence>(Single->GetCurrentAsset()) : nullptr;
            if (!Idle) return;
            Body->AnimationData.PopulateFrom(Single);
            Body->SetAnimInstanceClass(UResidentTurnAnimInstance::StaticClass());
            if (auto* NewInstance=Cast<UResidentTurnAnimInstance>(Body->GetAnimInstance()))
                NewInstance->ConversationPlayer=Viewer;
        }
    }
}

bool ResidentConversation::IsSpeakerDowned(const AActor* Speaker)
{
    const auto* Vitals = IsValid(Speaker) ? Speaker->FindComponentByClass<UVillageArtisanVitalsComponent>() : nullptr;
    return Vitals && Vitals->IsDowned();
}

bool ResidentConversation::CanReach(const APawn* Pawn, const AActor* Speaker)
{
    if (!IsValid(Pawn) || !IsValid(Speaker) || Pawn->GetWorld() != Speaker->GetWorld() || IsSpeakerDowned(Speaker)) return false;
    if (const auto* Counter = Cast<AVillageGunshopCounter>(Speaker); Counter && !Counter->IsOpen()) return false;

    if (const auto* Artisan = Cast<AVillageArtisanMerchant>(Speaker); Artisan && Artisan->IsDefending()) return false;
    FVector TalkPoint;
    if (const auto* Keeper = Cast<AVillageTavernKeeper>(Speaker))
    {
        if (!Keeper->GetCounterTalkPoint(*Pawn, TalkPoint)) return false;
    }
    else if (const auto* Baker = Cast<AVillageBaker>(Speaker))
    {
        if (!Baker->GetCounterTalkPoint(*Pawn, TalkPoint)) return false;
    }
    else
    {
        const auto* Capsule = Speaker->FindComponentByClass<UCapsuleComponent>();
        const FVector Center = Capsule ? Capsule->GetComponentLocation() : Speaker->GetActorLocation();
        if (FVector::DistSquared(Pawn->GetActorLocation(), Center) > FMath::Square(380.f)) return false;
        TalkPoint = Center + FVector(0, 0, 45);
    }

    const auto* PC = Cast<APlayerController>(Pawn->GetController());
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!PC || PC->GetPawn() != Pawn || !Health || Health->IsDead()) return false;

    FVector Eye;
    FRotator View;
    ColdSteelWorldInteraction::GetReachViewPoint(PC, Eye, View);
    FHitResult Hit;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(ResidentConversation), false, Pawn);
    return !Pawn->GetWorld()->LineTraceSingleByChannel(Hit, Eye, TalkPoint, ECC_Visibility, Query)
        || Hit.GetActor() == Speaker;
}

void FResidentConversationFacing::SetLocalPlayer(APlayerController* Player)
{
    if (Player && !Player->IsLocalController()) return;
    LocalPlayer = Player;
    if (auto* Instance=Animation.Get()) Instance->ConversationPlayer=LocalPlayer;
}

void FResidentConversationFacing::StartIdle(USkeletalMeshComponent& Body, UAnimSequence& Idle, float StartSeconds)
{
    Body.AnimationData.AnimToPlay=&Idle;
    Body.AnimationData.SavedPosition=StartSeconds;
    Body.SetAnimInstanceClass(UResidentTurnAnimInstance::StaticClass());
    Animation=CastChecked<UResidentTurnAnimInstance>(Body.GetAnimInstance());
    Animation->ConversationPlayer=LocalPlayer;
}
