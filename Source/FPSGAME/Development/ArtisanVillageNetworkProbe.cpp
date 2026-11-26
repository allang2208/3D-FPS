// Opt-in, multi-process regression for the village actors, their stock and personal lessons.
#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "VillageNetworkAudit.h"
#include "../WorldGeneration/SmithYardLamp.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/PointLightComponent.h"
#include "DynamicRHI.h"
#include "RenderTimer.h"
#include "../Weapons/EagleTalonGuardComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../WorldGeneration/SmithYardFurnace.h"
#include "../Multiplayer/ColdSteelSharedInventorySubsystem.h"
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
#include "../UI/ColdSteelSceneContainer.h"
#include "../UI/ColdSteelContainerSearchSubsystem.h"
#include "../Movement/FPSFurnitureRestComponent.h"
#include "../FPSGAMECharacter.h"
#include "UObject/UnrealType.h"
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
                if (Name == TEXT("SM_TavernCookHearth"))
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
               Keepers == 1 && Herbalists == 1 && Bakers == 1;
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
    int64 SmithStartingOre = 0;
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
        if(FParse::Param(FCommandLine::Get(),TEXT("ArtisanShopScene")))
            R->SetNumberField(TEXT("process_working_set_mib"),FPlatformMemory::GetStats().UsedPhysical/(1024.*1024.));
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
                                    FName(TEXT("herbalist")), FName(TEXT("windmill")), FName(TEXT("bakery")), FName(TEXT("gunshop"))})
            {
                const bool OK = H.UnlockVillagePlan(Plan, Reason);
                Record(TEXT("repair-") + Plan.ToString(), OK, Reason.ToString());
            }
            const auto* Saved = Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_World"), 0));
            constexpr uint8 ExpectedPlans = UTemperateHillsSave::CarpenterPlan | UTemperateHillsSave::TavernPlan |
                                            UTemperateHillsSave::HerbalistPlan | UTemperateHillsSave::WindmillPlan;
            Record(TEXT("saved-shops"), Saved && Saved->bVillageBlacksmithRepaired && Saved->bVillageBakeryRepaired && Saved->bVillageGunshopRepaired &&
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
                 S.Smith->GetMesh()->GetSkeletalMeshAsset() && S.Smith->GetMesh()->GetAnimInstance() &&
                 S.Smith->CanTradeWith(PC->GetPawn()) && !S.Smith->Stock().IsEmpty() &&
                 !S.Carpenter->Stock().IsEmpty())
        {
            Record(TEXT("restored"),
                   S.FacingOppositeShops() && H.IsVillageBlacksmithRepaired() && H.IsVillageCarpenterRepaired() &&
                   H.IsTavernRepaired() && H.IsHerbalistRepaired() && H.IsBakeryRepaired() && H.IsGunshopRepaired(),
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
            const auto PriceOfTool=[&](AVillageArtisanMerchant& Merchant,FName Id)
            {
                const auto* Offer=Merchant.Stock().FindByPredicate([Id](const auto& Entry){return Entry.Definition==Id;});
                FColdSteelItem Item;
                return Offer&&Merchant.MakeStockItem(*M,*Offer,Item)?ColdSteelInventory::Number(Item,TEXT("price"),0.):0.;
            };
            const double PickPrice=PriceOfTool(*S.Smith,TEXT("tool_pickaxe")),AxePrice=PriceOfTool(*S.Carpenter,TEXT("tool_axe"));
            Record(TEXT("tool-prices"),PickPrice>0.&&AxePrice>0.,FString::Printf(TEXT("pick=%.0f axe=%.0f"),PickPrice,AxePrice));
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
                 S.Carpenter->GetMesh()->GetSkeletalMeshAsset() && S.Carpenter->GetMesh()->GetAnimInstance() &&
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
    #include "SmithLessonSceneProbe.inl"

    bool ShopScene(UWorld* W, ATemperateHillsWorld& H, const FSite& Site)
    {
        AColdSteelSceneContainer* Chest=nullptr;
        for(TActorIterator<AColdSteelSceneContainer> It(W);It;++It)
            if(It->ContainerId==TEXT("HillsVillage.Plot04.JoinersChest")){Chest=*It;break;}
        auto* Local=W->GetFirstPlayerController();
        if(!Chest||!Local||!Local->GetPawn())return true;
        auto* Search=W->GetSubsystem<UColdSteelContainerSearchSubsystem>();
        const bool Restored=H.IsVillageCarpenterRepaired()&&H.IsVillageBlacksmithRepaired()&&
            H.IsHerbalistRepaired()&&H.IsTavernRepaired()&&H.IsBakeryRepaired()&&H.IsGunshopRepaired()&&
            Site.bKitchen&&!Site.bRuin&&Site.Stools==11&&Chest->IsAvailableForSearch();
        int32 LoadedParts=0;
        if(Site.Carpenter)
        {
            TInlineComponentArray<USkeletalMeshComponent*> Parts(Site.Carpenter);
            for(const auto* Part:Parts)if(Part->GetSkeletalMeshAsset())++LoadedParts;
        }
        const bool Dressed=Site.Carpenter&&Site.Carpenter->GetMesh()->GetSkeletalMeshAsset();
        const FVector Center=Chest->GetActorLocation(), Aim=Center+FVector(0,0,70);
        const FVector Far=Center+FVector(40000,0,1500);
        auto MoveNear=[&](APlayerController* PC)
        {
            for(double Yaw:{0.,90.,180.,270.,45.,135.,225.,315.})
            {
                VillageNetAudit::Place(PC,Center+FVector(110,0,0).RotateAngleAxis(Yaw,FVector::UpVector)+FVector(0,0,94),Aim);
                if(Search->CanAccess(PC->GetPawn(),Chest))return true;
            }
            return false;
        };
        Last=FString::Printf(TEXT("shop step=%d ready=%d restored=%d chest=%d carpenters=%d loaded_parts=%d fraction=%.2f distance_cm=%.0f"),
            Step,H.bReady,Restored,Chest->IsAvailableForSearch(),Site.Carpenters,LoadedParts,Chest->GetDoorOpenFraction(),FVector::Dist(Local->GetPawn()->GetActorLocation(),Center));
        if(Role==TEXT("rejoin"))
        {
            if(Restored&&Chest->GetDoorOpenFraction()<.01f){Record(TEXT("late-layout"),true,Last);return false;}
            return true;
        }
        if(Role==TEXT("owner"))
        {
            auto* PS=Local->GetPlayerState<AColdSteelPlayerState>();
            if(!PS)return true;
            if(Step==0&&!H.IsVillageCarpenterRepaired()&&Site.bRuin)
            {Record(TEXT("ruined"),!Chest->IsAvailableForSearch(),Last);Advance();}
            else if(Step==1&&Restored&&Dressed&&Has(TEXT("server.at-chest"))&&Search->CanAccess(Local->GetPawn(),Chest))
            {
                if(PS->RequestInventoryAction(EColdSteelInventoryAction::ContainerOpen,FString(),Chest))
                {Record(TEXT("open-request"),true,Chest->StorageKey());Advance();}
            }
            else if(Step==2&&Has(TEXT("server.two-viewers"))&&Chest->GetDoorOpenFraction()>.99f)
            {Search->CloseLocal(Local,Chest);Record(TEXT("remote-closed"),true,Last);Advance();}
            else if(Step==3&&Has(TEXT("server.host-away"))&&Dressed&&Chest->GetDoorOpenFraction()<.01f)
            {Record(TEXT("guest-still-near"),true,Last);Advance();}
            else if(Step==4&&Has(TEXT("server.both-away"))&&LoadedParts==0&&FVector::DistSquared(Local->GetPawn()->GetActorLocation(),Center)>FMath::Square(30000.))
            {Record(TEXT("guest-released"),true,Last);Advance();}
            else if(Step==5&&Has(TEXT("server.return"))&&Dressed&&Restored&&Search->CanAccess(Local->GetPawn(),Chest))
            {
                Record(TEXT("chest-draw-distance"),Chest->Body&&Chest->Door&&
                    Chest->Body->LDMaxDrawDistance==5500.f&&Chest->Door->LDMaxDrawDistance==5500.f,Last);
                Record(TEXT("returned"),true,Last);return false;
            }
            return true;
        }
        APlayerController* Guest=nullptr;
        for(auto It=W->GetPlayerControllerIterator();It;++It)
            if(It->Get()&&!It->Get()->IsLocalController()){Guest=It->Get();break;}
        if(Step==6&&Has(TEXT("owner.returned")))Advance();
        if(Step==7&&!Guest){Record(TEXT("disconnected"),!Search->HasViewers(Chest),Last);Advance();}
        if(Step==8&&Has(TEXT("rejoin.late-layout"))){Record(TEXT("done"),Restored,Last);return false;}
        if(!Guest||!Guest->GetPawn())return true;
        if(Step==0&&Has(TEXT("owner.ruined"))&&Site.bSmithStation&&Site.bCarpenterStation)
        {
            Record(TEXT("ruined"),!Chest->IsAvailableForSearch(),Last);
            if(auto* Driver=W->GetNetDriver())
            {
#if DO_ENABLE_NET_TEST
                const auto& Sim=Driver->PacketSimulationSettings;
                Record(TEXT("transport"),Sim.PktLag==60&&Sim.PktLoss==2,FString::Printf(TEXT("lag=%d loss=%d"),Sim.PktLag,Sim.PktLoss));
#endif
            }
            FText Reason;
            for(const FName Plan:{FName(TEXT("blacksmith")),FName(TEXT("carpenter")),FName(TEXT("tavern")),FName(TEXT("herbalist")),FName(TEXT("windmill")),FName(TEXT("bakery")),FName(TEXT("gunshop"))})
            {
                const bool Repaired=H.UnlockVillagePlan(Plan,Reason);
                Record(TEXT("repair-")+Plan.ToString(),Repaired,Reason.ToString());
            }
            Advance();
        }
        else if(Step==1&&Restored&&H.bReady&&MoveNear(Guest))
        {Record(TEXT("at-chest"),true,Site.Details());Advance();}
        else if(Step==2&&Search->IsActive(Guest,Chest)&&MoveNear(Local))
        {
            Search->Begin(Local,Chest);
            Record(TEXT("two-viewers"),Search->IsActive(Local,Chest)&&Search->IsActive(Guest,Chest),Last);Advance();
        }
        else if(Step==3&&Has(TEXT("owner.remote-closed"))&&!Search->IsActive(Guest,Chest))
        {
            Record(TEXT("other-viewer-keeps-open"),Search->IsActive(Local,Chest)&&Chest->GetDoorOpenFraction()>.99f,Last);
            Search->CloseLocal(Local,Chest);VillageNetAudit::Place(Local,Far,Aim);
            Record(TEXT("host-away"),true,Last);Advance();
        }
        else if(Step==4&&Has(TEXT("owner.guest-still-near"))&&Dressed)
        {
            Record(TEXT("remote-keeps-host-pose"),true,Last);
            VillageNetAudit::Place(Guest,Far+FVector(0,300,0),Aim);
            Record(TEXT("both-away"),true,Last);Advance();
        }
        else if(Step==5&&Has(TEXT("owner.guest-released"))&&Site.Carpenter&&LoadedParts==0&&!Search->HasViewers(Chest))
        {
            Record(TEXT("host-released"),Chest->GetDoorOpenFraction()<.01f,Last);
            if(MoveNear(Guest)){Record(TEXT("return"),true,Last);Advance();}
        }
        return true;
    }
    bool Pew(UWorld* W,ATemperateHillsWorld& H)
    {
        auto* Local=W->GetFirstPlayerController();
        if(!Local||!Local->GetPawn()||!H.bReady)return true;
        const auto RestOf=[](APlayerController* PC)
        {return PC&&PC->GetPawn()?PC->GetPawn()->FindComponentByClass<UFPSFurnitureRestComponent>():nullptr;};
        auto* Rest=RestOf(Local);if(!Rest)return true;
        auto SendUse=[](UFPSFurnitureRestComponent& Component)
        {Component.ProcessEvent(Component.FindFunctionChecked(TEXT("ServerInteract")),nullptr);};
        // Headless peers omit cosmetic player bodies; use the production reliable request
        // after focus. Authority still checks the actual view, reach, movement, floor and slot.
        int32 Idles=0,Standing=0;
        TSet<int32> Slots;
        const auto* Field=FindFProperty<FStructProperty>(Rest->GetClass(),TEXT("State"));
        if(!Field){Record(TEXT("rest-state"),false,TEXT("missing replicated State"));return false;}
        for(TActorIterator<AFPSGAMECharacter> It(W);It;++It)
        {
            const auto* C=It->FindComponentByClass<UFPSFurnitureRestComponent>();
            if(!C||!It->GetPlayerState())continue;
            const auto& State=*Field->ContainerPtrToValuePtr<FFurnitureRestState>(C);
            if(State.Phase==0){++Standing;continue;}
            if(State.Kind==TEXT("ChapelPew")&&State.Phase==3){++Idles;Slots.Add(State.SlotIndex);}
        }
        Last=FString::Printf(TEXT("step=%d seated=%d distinct=%d standing=%d local=%d"),Step,Idles,Slots.Num(),Standing,Rest->IsResting());
        if(Role==TEXT("owner"))
        {
            if(Step==0&&Has(TEXT("server.aimed"))&&Rest->UpdateFocus(true).Contains(TEXT("教堂长椅")))
            {SendUse(*Rest);Record(TEXT("guest-use"),true,Last);Advance();}
            else if(Step==1&&Idles==2&&Slots.Num()==2&&Rest->IsResting())
            {Record(TEXT("two-slots"),true,Last);Advance();}
            else if(Step==2&&Has(TEXT("server.leave"))){Rest->RequestLeave();Advance();}
            else if(Step==3&&Standing==2&&!Rest->IsResting())
            {Record(TEXT("both-standing"),true,Last);return false;}
            return true;
        }
        if(Step==0)
        {
            APlayerController* Guest=nullptr;
            for(auto It=W->GetPlayerControllerIterator();It;++It)
                if(It->Get()&&!It->Get()->IsLocalController())Guest=It->Get();
            if(!RestOf(Guest))return true;
            const auto& ChapelLot=H.GetVillageSite().ChapelLot();
            const FVector2D At=ChapelLot.World(FTemperateChapelSite::RestPew.X*ChapelLot.AssemblyScale,FTemperateChapelSite::RestPew.Y*ChapelLot.AssemblyScale);
            TInlineComponentArray<UInstancedStaticMeshComponent*> Groups(&H);
            for(auto* Group:Groups)
            {
                if(!Group->GetStaticMesh()||Group->GetStaticMesh()->GetFName()!=TEXT("SM_ChapelPew"))continue;
                for(int32 I=0;I<Group->GetInstanceCount();++I)
                {
                    FTransform T;
                    if(!Group->GetInstanceTransform(I,T,true)||FVector2D::Distance(FVector2D(T.GetLocation()),At)>100.)continue;
                    auto Aim=[&](APlayerController* PC,double Y)
                    {
                        const FVector Focus=T.TransformPosition(FVector(-8,Y,43.6488));
                        const FVector Feet=T.TransformPosition(FVector(-95,Y,0));
                        FHitResult Floor;
                        if(!W->LineTraceSingleByChannel(Floor,Feet+FVector(0,0,80),Feet-FVector(0,0,140),ECC_Visibility))return false;
                        auto* Pawn=Cast<AFPSGAMECharacter>(PC->GetPawn());if(!Pawn)return false;
                        VillageNetAudit::Place(PC,Floor.ImpactPoint+FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()+2.),Focus,true);
                        return true;
                    };
                    if(!Aim(Local,-70.)||!Aim(Guest,70.))return true;
                    if(!Rest->UpdateFocus(true).Contains(TEXT("教堂长椅")))return true;
                    SendUse(*Rest);
                    if(!Rest->IsResting())return true;
                    Record(TEXT("aimed"),true,FString::Printf(TEXT("outdoor instance=%d %s"),I,*T.GetLocation().ToString()));
                    Advance();return true;
                }
            }
        }
        else if(Step==1&&Has(TEXT("owner.two-slots"))&&Idles==2&&Slots.Num()==2)
        {Record(TEXT("two-slots"),true,Last);Rest->RequestLeave();Record(TEXT("leave"),true,Last);Advance();}
        else if(Step==2&&Has(TEXT("owner.both-standing"))&&Standing==2)
        {Record(TEXT("done"),true,Last);return false;}
        return true;
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
        const bool RenderedStartup=Step==0&&FParse::Param(FCommandLine::Get(),TEXT("RenderOffScreen"));
        const double Timeout=RenderedStartup?2400.:(Step==0||Role==TEXT("server")?850.:240.);
        if (FPlatformTime::Seconds() - Since > Timeout)
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
        if(FParse::Param(FCommandLine::Get(),TEXT("SmithLessonScene")))return SmithLessonScene(W,*H,Site);
        if(FParse::Param(FCommandLine::Get(),TEXT("ArtisanShopScene")))return ShopScene(W,*H,Site);
        if(FParse::Param(FCommandLine::Get(),TEXT("ArtisanPew")))return Pew(W,*H);
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
