// Opt-in, multi-process regression for the village actors, their stock and personal lessons.
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "VillageNetworkAudit.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "../WorldGeneration/HillsCarpenterWorkshop.h"
#include "../Building/VoxelBuildWorld.h"
#include "../NPC/VillageArtisanMerchant.h"
#include "../NPC/VillageTavernKeeper.h"
#include "../NPC/VillageHerbalist.h"
#include "../NPC/VillageBaker.h"
#include "../NPC/ArtisanWoundedAnimInstance.h"
#include "../NPC/ArtisanDefenseComponent.h"
#include "../Monsters/NurseZombie.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Engine/DamageEvents.h"
#include "Kismet/GameplayStatics.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelShopModel.h"
#include "../FPSGAMEPlayerController.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../Tasks/BlacksmithApprenticeship.h"
#include "../Tasks/CarpenterApprenticeship.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/NetDriver.h"
#include "EngineUtils.h"
#include "Engine/Engine.h"
#include "Containers/Ticker.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

namespace ArtisanVillageProbe
{
struct FSite
{
    AVillageArtisanMerchant *Smith = nullptr;
    AVillageArtisanMerchant *Carpenter = nullptr;
    AVillageTavernKeeper* TavernKeeper = nullptr;
    AVillageBaker* Baker = nullptr;
    AHillsBlacksmith* SmithShop = nullptr;
    AHillsCarpenterWorkshop* CarpenterShop = nullptr;
    int32 Smiths = 0, Carpenters = 0, Stools = 0, Utensils = 0;
    int32 Keepers = 0, Herbalists = 0, Bakers = 0, Dressed = 0;
    bool bRuin = false, bKitchen = false, bSmithStation = false, bCarpenterStation = false;

    explicit FSite(UWorld *World)
    {
        auto CountDressed = [this](const AActor& Resident)
        {
            TInlineComponentArray<USkeletalMeshComponent*> Parts(&Resident);
            for (const auto* Part : Parts)
                if (Part && Part->IsVisible() && Part->GetSkeletalMeshAsset() && Part->GetAnimInstance())
                {
                    ++Dressed;
                    break;
                }
        };
        for (TActorIterator<AVillageTavernKeeper> It(World); It; ++It) { TavernKeeper = *It; ++Keepers; CountDressed(**It); }
        for (TActorIterator<AVillageHerbalist> It(World); It; ++It) { ++Herbalists; CountDressed(**It); }
        for (TActorIterator<AVillageBaker> It(World); It; ++It) { Baker = *It; ++Bakers; CountDressed(**It); }
        for (TActorIterator<AHillsBlacksmith> It(World); It; ++It)
        {
            SmithShop = *It;
            bSmithStation = It->StationMesh && Cast<AVoxelBuildWorld>(It->GetOwner());
        }
        for (TActorIterator<AHillsCarpenterWorkshop> It(World); It; ++It)
        {
            CarpenterShop = *It;
            bCarpenterStation = It->StationMesh && Cast<AVoxelBuildWorld>(It->GetOwner());
        }
        for (TActorIterator<AVillageArtisanMerchant> It(World); It; ++It)
        {
            CountDressed(**It);
            if (It->IsCarpenterMerchant())
            {
                Carpenter = *It;
                ++Carpenters;
            }
            else
            {
                Smith = *It;
                ++Smiths;
            }
        }
        for (TActorIterator<AActor> It(World); It; ++It)
        {
            if (!It->ActorHasTag(TEXT("VillageTavern.Interior")))
                continue;
            TInlineComponentArray<UStaticMeshComponent *> Parts(*It);
            for (auto *Part : Parts)
            {
                UStaticMesh *Mesh = Part->GetStaticMesh();
                if (!Mesh)
                    continue;
                const FName Name = Mesh->GetFName();
                const auto *Batch = Cast<UInstancedStaticMeshComponent>(Part);
                const int32 N = Batch ? Batch->GetInstanceCount() : 1;
                if (Name == TEXT("SM_TavernKitchenScreenRuined"))
                    bRuin = Part->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block;
                if (Name == TEXT("SM_TavernKitchenScreen"))
                    bKitchen = Part->GetCollisionResponseToChannel(ECC_Pawn) == ECR_Block;
                if (Name == TEXT("SM_TavernStool"))
                    Stools += N;
                if (Name == TEXT("SM_TavernChopsticks"))
                    Utensils += N;
            }
        }
    }
    bool Restored() const
    {
        return bKitchen && !bRuin && Stools == 11 && Smiths == 1 && Carpenters == 1 &&
               Keepers == 1 && Herbalists == 1 && Bakers == 1 && Dressed == 5;
    }
    bool Empty() const { return Smiths + Carpenters + Keepers + Herbalists + Bakers == 0; }
    bool FacingOppositeShops() const
    {
        auto Faces = [](const AActor* Resident, const AActor* Shop)
        {
            return Resident && Shop && FVector::DotProduct(Resident->GetActorForwardVector(),
                (Shop->GetActorLocation() - Resident->GetActorLocation()).GetSafeNormal2D()) > .985;
        };
        return Faces(Smith, CarpenterShop) && Faces(Carpenter, SmithShop);
    }
    FString Details() const
    {
        return FString::Printf(
            TEXT("smiths=%d carpenters=%d keepers=%d herbalists=%d bakers=%d dressed=%d ruined=%d kitchen=%d stools=%d chopstickPairs=%d stations=%d/%d"),
            Smiths, Carpenters, Keepers, Herbalists, Bakers, Dressed, bRuin, bKitchen, Stools, Utensils, bSmithStation, bCarpenterStation);
    }
};

struct FRun
{
    FString Folder, Role;
    int32 Step = 0;
    double Since = FPlatformTime::Seconds(), NextStatus = 0.;
    bool bFailed = false;
    FString Last;
    FGuid Lot, OwnerIdentity;
    double HoldAt = 0.;
    TWeakObjectPtr<ANurseZombie> GuardTarget;
    int32 GuardKills = 0;
    double FirstWatchAt = 0.;
    FTransform WorkPose;
    FVector AidHome = FVector::ZeroVector;
    TWeakObjectPtr<APlayerController> FirstCustomer;
    int64 Balance = 0, Price = 0;
    int32 Pickaxes = 0;
    bool Has(const FString &Name) const
    {
        return IFileManager::Get().FileExists(*(Folder / (Name + TEXT(".json"))));
    }
    void Record(const FString &Name, bool OK, const FString &Detail)
    {
        auto R = MakeShared<FJsonObject>();
        R->SetStringField(TEXT("peer"), Role);
        R->SetStringField(TEXT("case"), Name);
        R->SetBoolField(TEXT("passed"), OK);
        R->SetStringField(TEXT("detail"), Detail);
        FString Json;
        FJsonSerializer::Serialize(R, TJsonWriterFactory<>::Create(&Json));
        FString Path = Folder / (Role + TEXT(".") + Name + TEXT(".json"));
        FFileHelper::SaveStringToFile(Json, *(Path + TEXT(".tmp")),
                                      FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        IFileManager::Get().Move(*Path, *(Path + TEXT(".tmp")));
        UE_LOG(LogTemp, Display, TEXT("ARTISAN_NET %s %s %d %s"), *Role, *Name, OK, *Detail);
        bFailed |= !OK;
    }
    void Advance()
    {
        ++Step;
        Since = FPlatformTime::Seconds();
    }
    bool Finish()
    {
        Record(TEXT("done"), !bFailed, FString::FromInt(Step));
        if (Role != TEXT("server") && !bFailed)
        {
            const FString Ack = Role == TEXT("owner") ? TEXT("personal-carpenter") : Role + TEXT("-authority");
            const FString AckPath = Folder / (TEXT("server.") + Ack + TEXT(".json"));
            FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([AckPath](float) {
                                                     if (!IFileManager::Get().FileExists(*AckPath))
                                                         return true;
                                                     FPlatformMisc::RequestExit(false);
                                                     return false;
                                                 }),
                                                 1.f);
        }
        return false;
    }
    static int64 CountItem(const UColdSteelStatusModel &M, const FString &Def)
    {
        int64 Count = 0;
        for (const auto &I : M.Items())
            if (I.Definition == Def)
                Count += I.Count;
        return Count;
    }
    static bool Position(APlayerController *PC, AVillageArtisanMerchant *Artisan)
    {
        if (!PC || !PC->GetPawn() || !Artisan)
            return false;
        for (float Angle : {0.f, 90.f, -90.f, 180.f, 45.f, -45.f})
        {
            const FVector Base = Artisan->GetActorLocation();
            const FVector P =
                Base + Artisan->GetActorForwardVector().RotateAngleAxis(Angle, FVector::UpVector) * 115.;
            VillageNetAudit::Place(PC, P, Base + FVector(0, 0, 45));
            if (Artisan->CanTradeWith(PC->GetPawn()))
                return true;
        }
        return false;
    }
    bool SpawnGuardTarget(AVillageArtisanMerchant& Guard)
    {
        auto* World = Guard.GetWorld();
        auto* Type = LoadClass<ANurseZombie>(nullptr, TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
        if (!Type) return false;
        const FVector Center = Guard.GetActorLocation();
        const float Range = Guard.IsCarpenterMerchant() ? 380.f : 104.f;
        FCollisionQueryParams Query(SCENE_QUERY_STAT(VillageGuardFixture), false, &Guard);
        for (float Angle : {0.f, 45.f, -45.f, 90.f, -90.f, 180.f})
        {
            const FVector Axis = Guard.GetActorForwardVector().RotateAngleAxis(Angle, FVector::UpVector);
            const FVector Point = Center + Axis * Range;
            if (World->LineTraceTestByChannel(Center, Point, ECC_Visibility, Query) ||
                World->OverlapBlockingTestByChannel(Point, FQuat::Identity, ECC_Pawn,
                    FCollisionShape::MakeCapsule(31.f, 69.f), Query)) continue;
            const FTransform Pose((-Axis).Rotation(), Point);
            auto* Target = World->SpawnActorDeferred<ANurseZombie>(Type, Pose, nullptr, nullptr,
                ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
            if (!Target) continue;
            Target->MaxHealth = 1.f;
            Target->AutoPossessAI = EAutoPossessAI::Disabled;
            Target->FinishSpawning(Pose);
            Target->GetCharacterMovement()->DisableMovement();
            GuardTarget = Target;
            return true;
        }
        return false;
    }
    bool Server(UWorld *W, ATemperateHillsWorld &H, const FSite &Site)
    {
        APlayerController *PC = nullptr;
        for (auto It = W->GetPlayerControllerIterator(); It; ++It)
            if (It->Get() && !It->Get()->IsLocalController())
            {
                PC = It->Get();
                break;
            }
        auto *M = VillageNetAudit::Model(PC);
        if (PC && PC->GetPawn())
            PC->GetPawn()->SetCanBeDamaged(false);
        if (Step == 0 && Has(TEXT("owner.ruined")) && Site.bSmithStation && Site.bCarpenterStation && PC &&
            PC->GetPawn() && M && M->ProfileView().NetworkProfileId.IsValid())
        {
            Record(TEXT("ruined"), Site.bRuin && Site.Empty(), Site.Details());
#if DO_ENABLE_NET_TEST
            if (const auto *Driver = W->GetNetDriver())
            {
                const auto Settings = Driver->PacketSimulationSettings;
                Record(
                    TEXT("transport"), Settings.PktLag == 60 && Settings.PktLoss == 2,
                    FString::Printf(TEXT("listen-server UDP lag=%d loss=%d"), Settings.PktLag, Settings.PktLoss));
            }
#endif
            FText Reason;
            for (const FName Plan : {FName(TEXT("blacksmith")), FName(TEXT("carpenter")), FName(TEXT("tavern")),
                                    FName(TEXT("herbalist")), FName(TEXT("windmill")), FName(TEXT("bakery"))})
            {
                const bool OK = H.UnlockVillagePlan(Plan, Reason);
                Record(TEXT("repair-") + Plan.ToString(), OK, Reason.ToString());
            }
            const auto* Saved = Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"), 0));
            constexpr uint8 ExpectedPlans = UTemperateHillsSave::CarpenterPlan | UTemperateHillsSave::TavernPlan |
                                            UTemperateHillsSave::HerbalistPlan | UTemperateHillsSave::WindmillPlan;
            Record(TEXT("saved-shops"), Saved && Saved->bVillageBlacksmithRepaired && Saved->bVillageBakeryRepaired &&
                   (Saved->SavedVillagePlans() & ExpectedPlans) == ExpectedPlans &&
                   Saved->VillagePlanVersion == UTemperateHillsSave::CurrentVillagePlanVersion,
                   Saved ? Saved->WorldId.ToString() : TEXT("world slot missing"));
            if (bFailed)
                return Finish();
            OwnerIdentity = M->ProfileView().NetworkProfileId;
            FirstCustomer = PC;
            Advance();
        }
        if (Step == 1 && Site.Restored() && PC && PC->GetPawn())
        {
            if (Site.Utensils == 0)
                return true;
            Record(TEXT("host-layout"), true, Site.Details());
            Record(TEXT("shop-facing"), Site.FacingOppositeShops(), TEXT("both idle residents face the opposite workshop"));
            for (AActor* Speaker : {static_cast<AActor*>(Site.TavernKeeper), static_cast<AActor*>(Site.Baker)})
            {
                const FTransform Frame = Speaker->GetActorTransform();
                const FVector Face = Frame.TransformPosition(FVector(0., 0., 152.));
                VillageNetAudit::Place(PC, Frame.TransformPosition(FVector(215., 0., 92.)), Face);
                const bool FromGuest = ResidentConversation::CanReach(PC->GetPawn(), Speaker) &&
                                       ColdSteelWorldInteraction::IsFocused(PC->GetPawn(), Speaker);
                VillageNetAudit::Place(PC, Frame.TransformPosition(FVector(-65., 0., 92.)), Face);
                Record(TEXT("counter-") + Speaker->GetClass()->GetName(), FromGuest &&
                       !ResidentConversation::CanReach(PC->GetPawn(), Speaker),
                       FString::Printf(TEXT("customer focus and reach=%d"), FromGuest));
            }
            if (FParse::Param(FCommandLine::Get(), TEXT("ArtisanGuardOnly")))
            {
                Step = 10;
                Since = FPlatformTime::Seconds();
            }
            else if (Position(PC, Site.Smith))
            {
                Record(TEXT("at-smith"), true, Site.Details());
                Advance();
            }
        }
        if (Step == 2 && Has(TEXT("owner.purchase")) && M && PC && Site.Carpenter)
        {
            Record(TEXT("personal-smith"),
                   BlacksmithApprenticeship::Stage(M->ProfileView()) !=
                           BlacksmithApprenticeship::EStage::NotStarted &&
                       CountItem(*M, TEXT("tool_pickaxe")) > 0,
                   M->ProfileView().NetworkProfileId.ToString());
            if (Position(PC, Site.Carpenter))
            {
                Record(TEXT("at-carpenter"), true, Site.Details());
                Advance();
            }
        }
        if (Step == 3 && Has(TEXT("owner.carpenter")) && M)
        {
            auto* Enemy = W->SpawnActor<AActor>();
            if (!Enemy || !Site.Smith || !PC || !PC->GetPawn()) return true;
            AidHome = Site.Smith->GetActorLocation();
            FCollisionQueryParams FloorQuery(SCENE_QUERY_STAT(ArtisanAidFloor), false, Site.Smith);
            const float HalfHeight = Site.Smith->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
            for (float Angle : {0.f, 45.f, -45.f, 90.f, -90.f, 180.f})
            {
                const FVector Point = AidHome + Site.Smith->GetActorForwardVector().RotateAngleAxis(Angle, FVector::UpVector) * 100.;
                FHitResult Floor;
                if (W->LineTraceSingleByChannel(Floor, Point, Point - FVector::UpVector * (HalfHeight + 30.f), ECC_Visibility, FloorQuery) &&
                    Site.Smith->GetCharacterMovement()->IsWalkable(Floor) && FMath::Abs(Floor.Location.Z + HalfHeight - AidHome.Z) < 12.f &&
                    Site.Smith->TeleportTo(Floor.Location + FVector::UpVector * (HalfHeight + 2.f), Site.Smith->GetActorRotation())) break;
            }
            Record(TEXT("knockdown-away-from-work"), FVector::Dist2D(Site.Smith->GetActorLocation(), AidHome) > 65.,
                   (Site.Smith->GetActorLocation() - AidHome).ToCompactString());
            Enemy->Tags.Add(TEXT("Enemy"));
            const float Damage = Site.Smith->TakeDamage(100000.f, FDamageEvent(), nullptr, Enemy);
            Enemy->Destroy();
            Record(TEXT("monster-knockdown"), Damage > 0.f && ResidentConversation::IsSpeakerDowned(Site.Smith),
                   FString::Printf(TEXT("effective damage %.1f"), Damage));
            const FVector Base = Site.Smith->GetActorLocation();
            for (float Angle : {0.f, 90.f, -90.f, 180.f})
            {
                VillageNetAudit::Place(PC, Base + Site.Smith->GetActorForwardVector().RotateAngleAxis(Angle, FVector::UpVector) * 120.,
                                      Base + FVector(0., 0., -44.));
                if (ColdSteelWorldInteraction::IsFocused(PC->GetPawn(), Site.Smith)) break;
            }
            Record(TEXT("aim-kneeling"), ColdSteelWorldInteraction::IsFocused(PC->GetPawn(), Site.Smith) &&
                   !Site.Smith->CanTradeWith(PC->GetPawn()), Site.Smith->GetName());
            if (auto *Home = W->GetFirstPlayerController(); Home && Home->IsLocalController())
            {
                if (auto *HostModel = VillageNetAudit::Model(Home))
                    Record(TEXT("host-isolation"),
                           BlacksmithApprenticeship::Stage(HostModel->ProfileView()) ==
                                   BlacksmithApprenticeship::EStage::NotStarted &&
                               CarpenterApprenticeship::Stage(HostModel->ProfileView()) ==
                                   CarpenterApprenticeship::EStage::NotStarted,
                           HostModel->ProfileView().NetworkProfileId.ToString());
            }
            Advance();
        }
        auto* Aid = PC ? PC->FindComponentByClass<UChapelDialogueComponent>() : nullptr;
        if (Step >= 4 && Step <= 6 && PC && PC->GetPawn() && Site.Smith)
        {
            FVector Eye; FRotator Aim;
            ColdSteelWorldInteraction::GetReachViewPoint(PC, Eye, Aim);
            Last = FString::Printf(TEXT("aid=%u focused=%s blocked=%d eye=%s aim=%s target=%s"),
                Aid ? Aid->AuthorityAidSerial : 0, *GetNameSafe(ColdSteelWorldInteraction::TraceTarget(PC)),
                AFPSGAMEPlayerController::BlocksOngoingActions(PC), *Eye.ToCompactString(), *Aim.ToCompactString(),
                *Site.Smith->GetActorLocation().ToCompactString());
            if (FPlatformTime::Seconds() - Since > 30. && Has(TEXT("owner.kneeling")))
            {
                Record(TEXT("aid-timeout"), false, Last);
                return Finish();
            }
        }
        if (Step == 4 && Aid && Aid->AuthorityAidSerial == 1)
        {
            Record(TEXT("aid-start"), Aid->AuthorityAidTarget.Get() == Site.Smith, TEXT("remote begin accepted"));
            Advance();
        }
        if (Step == 5 && Aid && Aid->AuthorityAidSerial == 0)
        {
            Record(TEXT("aid-cancel"), ResidentConversation::IsSpeakerDowned(Site.Smith), TEXT("still down after release"));
            Advance();
        }
        if (Step == 6 && Aid && Aid->AuthorityAidSerial == 2)
        {
            Record(TEXT("aid-restart"), Aid->AuthorityAidTarget.Get() == Site.Smith, TEXT("second remote hold accepted"));
            Advance();
        }
        if (Step == 7 && Site.Smith && Site.Smith->FindComponentByClass<UArtisanDefenseComponent>()->IsAtWork() &&
            !ResidentConversation::IsSpeakerDowned(Site.Smith) &&
            !Has(TEXT("server.resumed-work")) && Position(PC, Site.Smith))
        {
            Record(TEXT("resumed-work"), FVector::Dist2D(Site.Smith->GetActorLocation(), AidHome) < 12.,
                   (Site.Smith->GetActorLocation() - AidHome).ToCompactString());
        }
        if (Step == 7 && Has(TEXT("owner.recovered")) && M)
        {
            Record(TEXT("personal-carpenter"),
                   CarpenterApprenticeship::Stage(M->ProfileView()) != CarpenterApprenticeship::EStage::NotStarted &&
                   Site.Smith && !ResidentConversation::IsSpeakerDowned(Site.Smith) && !Site.Smith->IsDefending(),
                   M->ProfileView().NetworkProfileId.ToString());
            Advance();
        }
        if (Step >= 8 && Step <= 9)
        {
            const bool Returning = Step == 9;
            const FString Joining = Returning ? TEXT("rejoin") : TEXT("visitor");
            if (!Has(Joining + TEXT(".profile")))
                return true;
            for (auto It = W->GetPlayerControllerIterator(); It; ++It)
            {
                auto *Remote = It->Get();
                if (!Remote || Remote->IsLocalController() || Remote == FirstCustomer.Get() || !Remote->GetPawn())
                    continue;
                auto *Profile = VillageNetAudit::Model(Remote);
                if (!Profile)
                    continue;
                const auto &State = Profile->ProfileView();
                if (!State.NetworkProfileId.IsValid() || (State.NetworkProfileId == OwnerIdentity) != Returning)
                    continue;
                const bool HasSmith =
                    BlacksmithApprenticeship::Stage(State) != BlacksmithApprenticeship::EStage::NotStarted;
                const bool HasCarpenter =
                    CarpenterApprenticeship::Stage(State) != CarpenterApprenticeship::EStage::NotStarted;
                Record(Joining + TEXT("-authority"),
                       HasSmith == Returning && HasCarpenter == Returning &&
                           (!Returning || CountItem(*Profile, TEXT("tool_pickaxe")) > 0),
                       State.NetworkProfileId.ToString());
                Advance();
                break;
            }
        }
        if (Step >= 10 && Step <= 15)
        {
            const bool Bow = Step >= 13;
            auto* Guard = Bow ? Site.Carpenter : Site.Smith;
            auto* Defense = Guard ? Guard->FindComponentByClass<UArtisanDefenseComponent>() : nullptr;
            if (!Defense) return true;
            const FString Weapon = Bow ? TEXT("bow") : TEXT("hammer");
            const int32 Phase = (Step - 10) % 3;
            if (Phase == 0)
            {
                // Across-street sight lines overlap. Attribute each weapon sample to
                // the guard under test instead of letting the other merchant shoot first.
                if (auto* Other = Bow ? Site.Smith : Site.Carpenter)
                    if (auto* OtherDefense = Other->FindComponentByClass<UArtisanDefenseComponent>())
                        OtherDefense->SetComponentTickEnabled(false);
                Defense->SetComponentTickEnabled(true);
                GuardKills = 0;
                WorkPose = Guard->GetActorTransform();
                Record(Weapon + TEXT("-target"), SpawnGuardTarget(*Guard), TEXT("stationary nurse blueprint, 1 base HP"));
                if (bFailed) return Finish();
                Advance();
            }
            else if (Phase == 1 && GuardTarget.IsValid() && GuardTarget->Health <= 0.f && Defense->IsKeepingWatch())
            {
                ++GuardKills;
                Record(Weapon + (GuardKills == 1 ? TEXT("-kill-and-watch") : TEXT("-reacquired-and-killed")),
                       Guard->GetController() && GuardTarget->LastHitBy == Guard->GetController(),
                       FString::Printf(TEXT("attacker=%s expected=%s"), *GetNameSafe(GuardTarget->LastHitBy.Get()),
                           *GetNameSafe(Guard->GetController())));
                if (GuardKills == 1)
                {
                    Record(Weapon + TEXT("-watch-target"), SpawnGuardTarget(*Guard), TEXT("second monster arrived during watch"));
                    if (bFailed) return Finish();
                    return true;
                }
                FirstWatchAt = W->GetTimeSeconds();
                Advance();
            }
            else if (Phase == 1 && GuardKills == 1 && Defense->IsAtWork())
            {
                Record(Weapon + TEXT("-premature-return"), false, TEXT("guard returned with second monster in range"));
                return Finish();
            }
            else if (Phase == 2 && Defense->IsAtWork())
            {
                const double Seconds = W->GetTimeSeconds() - FirstWatchAt;
                Record(Weapon + TEXT("-return"), Seconds >= 2.8 &&
                       FVector::Dist2D(Guard->GetActorLocation(), WorkPose.GetLocation()) < 12. &&
                       FMath::Abs(FMath::FindDeltaAngleDegrees(Guard->GetActorRotation().Yaw, WorkPose.Rotator().Yaw)) < 4.,
                       FString::Printf(TEXT("time from observed watch to restored station %.2f s"), Seconds));
                if (Bow || bFailed) return Finish();
                Advance();
            }
            else if (FPlatformTime::Seconds() - Since > 45.)
            {
                Record(Weapon + TEXT("-timeout"), false, FString::Printf(TEXT("phase=%d hp=%.2f alerted=%d watch=%d"),
                       Phase, GuardTarget.IsValid() ? GuardTarget->Health : -1.f, Defense->IsAlerted(), Defense->IsKeepingWatch()));
                return Finish();
            }
        }
        return true;
    }
    bool Client(UWorld *W, ATemperateHillsWorld &H, const FSite &S)
    {
        const auto *PC = W->GetFirstPlayerController();
        if (!PC || !PC->GetPawn() || !PC->IsLocalController())
            return true;
        auto *D = PC->FindComponentByClass<UChapelDialogueComponent>();
        auto *M = W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
        auto *Shop = W->GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
        if (!D || !M || !Shop || !M->ProfileView().NetworkProfileId.IsValid())
            return true;
        if (Role != TEXT("owner"))
        {
            if (!H.IsTavernRepaired() || !S.Restored() || S.Utensils < 1 || S.Smith->Stock().IsEmpty() ||
                S.Carpenter->Stock().IsEmpty())
                return true;
            const bool Known = Role == TEXT("rejoin");
            if (Known && (D->SmithTrainingStage() == 0 || D->CarpenterTrainingStage() == 0))
                return true;
            Record(TEXT("late-layout"), true, S.Details());
            Record(TEXT("profile"),
                   (D->SmithTrainingStage() > 0) == Known && (D->CarpenterTrainingStage() > 0) == Known &&
                       (!Known || CountItem(*M, TEXT("tool_pickaxe")) > 0),
                   M->ProfileView().NetworkProfileId.ToString());
            return Finish();
        }
        if (Step == 0 && S.bRuin)
        {
            Record(TEXT("ruined"), !H.IsTavernRepaired() && S.Empty(), S.Details());
            Advance();
        }
        else if (Step == 1 && Has(TEXT("server.at-smith")) && S.Restored() && S.Utensils > 0 &&
                 S.Smith->CanTradeWith(PC->GetPawn()) && !S.Smith->Stock().IsEmpty() &&
                 !S.Carpenter->Stock().IsEmpty())
        {
            Record(TEXT("restored"),
                   S.FacingOppositeShops() && H.IsVillageBlacksmithRepaired() && H.IsVillageCarpenterRepaired() &&
                   H.IsTavernRepaired() && H.IsHerbalistRepaired() && H.IsBakeryRepaired(),
                   S.Details());
            bool HasStaff = false, HasPick = false, HasBow = false, HasAxe = false, CarpStaff = false,
                 Quality = true;
            for (const auto &Offer : S.Smith->Stock())
            {
                HasStaff |= Offer.Definition.ToString().Contains(TEXT("staff"));
                HasPick |= Offer.Definition == TEXT("tool_pickaxe");
                Quality &= Offer.QualityPercent >= -25 && Offer.QualityPercent <= 5;
            }
            for (const auto &Offer : S.Carpenter->Stock())
            {
                const FString Id = Offer.Definition.ToString();
                HasBow |= Id.Contains(TEXT("bow"));
                HasAxe |= Id.Contains(TEXT("axe"));
                CarpStaff |= Id.Contains(TEXT("staff"));
            }
            Record(TEXT("stock"), !HasStaff && HasPick && HasBow && HasAxe && CarpStaff && Quality,
                   FString::Printf(TEXT("smith=%d carpenter=%d"), S.Smith->Stock().Num(),
                                   S.Carpenter->Stock().Num()));
            D->OpenArtisan(S.Smith);
            Advance();
        }
        else if (Step == 2 && D->IsOpen() && !D->IsPending())
        {
            Record(TEXT("smith-talk"), D->IsBlacksmith(), D->Message);
            D->RequestSmithTraining();
            Advance();
        }
        else if (Step == 3 && D->SmithTrainingStage() > 0 && !D->IsPending())
        {
            Record(TEXT("smith-materials"), !D->CanCollectTrainingSupplies(), D->Message);
            D->TradeWithArtisan();
            Advance();
        }
        else if (Step == 4 && Shop->IsOpen() && S.Smith)
        {
            const auto *Offer = S.Smith->Stock().FindByPredicate(
                [](const auto &O) { return O.Definition == TEXT("tool_pickaxe"); });
            if (!Offer)
                return true;
            Price = Shop->BuyPrice(TEXT("tool_pickaxe"));
            Balance = M->SoulBalance();
            Pickaxes = CountItem(*M, TEXT("tool_pickaxe"));
            if (Balance < Price)
                return true;
            Lot = Offer->Lot;
            Record(TEXT("purchase-request"), Shop->Buy(Lot.ToString(EGuidFormats::Digits), 1),
                   Shop->ResultMessage());
            Advance();
        }
        else if (Step == 5 && CountItem(*M, TEXT("tool_pickaxe")) == Pickaxes + 1 && S.Smith)
        {
            if (S.Smith->Stock().ContainsByPredicate([this](const auto &O) { return O.Lot == Lot; }))
                return true;
            Record(TEXT("purchase"), Price > 0 && M->SoulBalance() == Balance - Price, Shop->ResultMessage());
            if (const auto *Controller = Cast<AFPSGAMEPlayerController>(PC))
                if (auto *HUD = Controller->GetColdSteelHUD())
                    HUD->HandlePanelShortcut(EKeys::Tab);
            Advance();
        }
        else if (Step == 6 && Has(TEXT("server.at-carpenter")) && S.Carpenter &&
                 S.Carpenter->CanTradeWith(PC->GetPawn()))
        {
            D->OpenArtisan(S.Carpenter);
            if (D->IsOpen() || D->IsPending())
                Advance();
        }
        else if (Step == 7 && D->IsOpen() && !D->IsPending())
        {
            Record(TEXT("carpenter-talk"), D->IsCarpenter(), D->Message);
            D->RequestCarpenterTraining();
            Advance();
        }
        else if (Step == 8 && D->CarpenterTrainingStage() > 0 && !D->IsPending())
        {
            Record(TEXT("carpenter"), !D->CanCollectTrainingSupplies(), D->Message);
            D->Close();
            Advance();
        }
        else if (Step == 9 && Has(TEXT("server.aim-kneeling")) && S.Smith &&
                 ResidentConversation::IsSpeakerDowned(S.Smith) && ColdSteelWorldInteraction::IsFocused(PC->GetPawn(), S.Smith))
        {
            const auto* Pose = S.Smith->GetMesh()->GetAnimInstance();
            Record(TEXT("kneeling"), Cast<UArtisanWoundedAnimInstance>(Pose) && !S.Smith->CanTradeWith(PC->GetPawn()),
                   GetNameSafe(Pose));
            D->ServerBeginFirstAid(1, S.Smith);
            Advance();
        }
        else if (Step == 10 && Has(TEXT("server.aid-start")))
        {
            D->ServerEndFirstAid(1, false);
            Advance();
        }
        else if (Step == 11 && Has(TEXT("server.aid-cancel")))
        {
            D->ServerBeginFirstAid(2, S.Smith);
            HoldAt = W->GetTimeSeconds();
            Advance();
        }
        else if (Step == 12 && Has(TEXT("server.aid-restart")) && W->GetTimeSeconds() - HoldAt >= 3.1)
        {
            D->ServerEndFirstAid(2, true);
            Advance();
        }
        else if (Step == 13 && Has(TEXT("server.resumed-work")) && S.Smith && S.Smith->CanTradeWith(PC->GetPawn()))
        {
            D->OpenArtisan(S.Smith);
            Advance();
        }
        else if (Step == 14 && D->IsOpen() && !D->IsPending())
        {
            Record(TEXT("recovered"), D->IsBlacksmith() && !ResidentConversation::IsSpeakerDowned(S.Smith), D->Message);
            D->Close();
            return Finish();
        }
        Last = S.Details() + FString::Printf(TEXT(" talk=%d pending=%d wallet=%lld smith=%d carpenter=%d msg=%s"),
                                             D->IsOpen(), D->IsPending(), M->SoulBalance(),
                                             D->SmithTrainingStage(), D->CarpenterTrainingStage(), *D->Message);
        return !bFailed || Finish();
    }
    bool Tick(float)
    {
        UWorld *W = nullptr;
        for (const auto &C : GEngine->GetWorldContexts())
            if (C.World() && C.World()->HasBegunPlay() &&
                C.World()->GetNetMode() == (Role == TEXT("server") ? NM_ListenServer : NM_Client))
            {
                W = C.World();
                break;
            }
        if (FPlatformTime::Seconds() - Since > ((Step == 0 || Role == TEXT("server")) ? 850. : 240.))
        {
            Record(TEXT("timeout"), false, FString::Printf(TEXT("step=%d %s"), Step, *Last));
            return Finish();
        }
        if (!W)
            return true;
        auto *H = VillageNetAudit::FindHills(W);
        if (!H || !H->GetVillageSite().bPlaced)
        {
            if (FPlatformTime::Seconds() > NextStatus)
            {
                UE_LOG(LogTemp, Display, TEXT("ARTISAN_WAIT %s waiting for village world %s"), *Role,
                       *W->GetName());
                NextStatus = FPlatformTime::Seconds() + 30.;
            }
            return true;
        }
        FSite Site(W);
        if (FPlatformTime::Seconds() > NextStatus)
        {
            UE_LOG(LogTemp, Display, TEXT("ARTISAN_WAIT %s step=%d %s %s"), *Role, Step, *Site.Details(), *Last);
            NextStatus = FPlatformTime::Seconds() + 20.;
        }
        return Role == TEXT("server") ? Server(W, *H, Site) : Client(W, *H, Site);
    }
};

FAutoConsoleCommand Cmd(TEXT("fps.Test.ArtisanVillageNet"),
                        TEXT("Run the opt-in village regression on this peer."),
                        FConsoleCommandDelegate::CreateLambda([] {
                            auto R = MakeShared<FRun>();
                            if (!FParse::Param(FCommandLine::Get(), TEXT("ArtisanVillageTest")) ||
                                !FParse::Value(FCommandLine::Get(), TEXT("ArtisanEvidence="), R->Folder) ||
                                !FParse::Value(FCommandLine::Get(), TEXT("ArtisanRole="), R->Role))
                                return;
                            FTSTicker::GetCoreTicker().AddTicker(
                                FTickerDelegate::CreateLambda([R](float Delta) { return R->Tick(Delta); }), 1.f);
                        }));
} // namespace ArtisanVillageProbe
#endif
