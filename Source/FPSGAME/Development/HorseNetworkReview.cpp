#if !UE_BUILD_SHIPPING && !UE_BUILD_TEST
#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../Movement/StableHorseMarket.h"
#include "../Movement/StableHorseGear.h"
#include "../NPC/ResidentTurnAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelShopModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelInventoryRequestTypes.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Components/CapsuleComponent.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/NetDriver.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameModeBase.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"

// Opt-in, isolated listen server and guest. Files synchronize the test steps only;
// game state crosses the normal player controller, inventory and horse actor channels.
struct FHorseNetworkReview
{
    FString Dir,Role,Detail;int Phase=0;bool Floor=false,Staged=false,Injured=false;
    float BeforeImpact=0.f;
    TWeakObjectPtr<AActor> Vendor;FGuid Lot;
    double Start=FPlatformTime::Seconds(),NextLog=0.,Retry=0.;
    int64 InitialSouls=0,Price=0;float StartHealth=0,StartStamina=0;
    void Mark(FString Key,FString Value=TEXT("ok")) const
    {
        const FString Path=Dir/(Role+TEXT(".")+Key);
        FFileHelper::SaveStringToFile(Value,*(Path+TEXT(".tmp")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        IFileManager::Get().Move(*Path,*(Path+TEXT(".tmp")),true);
    }
    bool Has(const TCHAR* Key) const {return IFileManager::Get().FileExists(*(Dir/Key));}
    FString Read(const TCHAR* Key) const {FString V;FFileHelper::LoadFileToString(V,*(Dir/Key));return V;}
    bool Fail(FString Why){Mark(TEXT("failed"),Why);FPlatformMisc::RequestExit(false);return false;}
    void MakeFloor(UWorld* W)
    {
        if(W->GetNetMode()==NM_ListenServer)
        {
            auto* A=W->SpawnActor<AStaticMeshActor>();
            auto* B=A->GetStaticMeshComponent();B->SetMobility(EComponentMobility::Movable);
            A->SetReplicates(true);A->SetReplicateMovement(true);A->bAlwaysRelevant=true;
            B->SetIsReplicated(true);B->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
            B->SetCollisionProfileName(TEXT("BlockAll"));
            A->SetActorTransform(FTransform(FRotator::ZeroRotator,FVector(0,0,-32),FVector(400,400,.64)));
            A->ForceNetUpdate();
        }
        Floor=true;
    }
    // Exercise real owner requests, including an item sent to the wrong slot.
    // Keep the original IDs to detect a duplicate, lost or substituted instance on reconnect.
    int32 GearStep=0;
    bool CheckGear(APlayerController* PC,UColdSteelStatusModel& M,const FStableMountRecord& Horse)
    {
        auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();
        if(!PS || PS->InventoryRequestPending())return false;
        const int32 Step=GearStep;
        const int32 Slot=Step==0 || Step>=5?0:Step-1;
        const FString Def=StableHorseGear::Definitions[Slot];
        const auto* InBag=M.Items().FindByPredicate([&](const auto& I){return I.Definition==Def && I.Place==0;});
        const auto* Worn=StableHorseGear::At(Horse,Slot);
        const bool Remove=Step==5;
        if(Step==1 && (Worn || !InBag)){Fail(TEXT("incorrect slot changed gear ownership"));return false;}
        if(Step>=2 && Step<=5 && Horse.Equipment.Num()!=Step-1)return false;
        if(Step==6 && (Worn || !InBag))return false;
        if(Step==7)
        {
            if(Horse.Equipment.Num()!=4)return false;
            for(const auto& I:Horse.Equipment)
                if(M.FindItem(I.InstanceId) || Read(*(TEXT("guest.gear_")+I.Definition))!=I.InstanceId)
                {Fail(TEXT("invalid equipped instance after transfers"));return false;}
            if(!Has(TEXT("guest.gear")))Mark(TEXT("gear"),TEXT("wrong slot, equip four, remove, re-equip; same instance IDs"));
            return true;
        }
        const auto* Item=Remove?Worn:InBag;
        if(!Item)return false;
        if(Step>=1 && Step<=4)Mark(TEXT("gear_")+Def,Item->InstanceId);
        FColdSteelInventoryRequest Req;
        Req.Action=EColdSteelInventoryAction::MountGear;Req.MountId=Horse.HorseId;Req.Item=Item->InstanceId;
        Req.Cell=Step==0?1:Slot;Req.Mode=Remove?TEXT("remove"):TEXT("equip");
        if(PS->RequestInventoryAction(Req))++GearStep;
        return false;
    }
    bool Host(UWorld* W,APlayerController* PC)
    {
        if(!Has(TEXT("host.ready")))
        {
            Mark(TEXT("ready"));
#if DO_ENABLE_NET_TEST
            const auto& Net=W->GetNetDriver()->PacketSimulationSettings;
            Mark(TEXT("transport"),FString::Printf(TEXT("lag=%d loss=%d"),Net.PktLag,Net.PktLoss));
#endif
        }
        APlayerController* Guest=nullptr;
        for(auto It=W->GetPlayerControllerIterator();It;++It)
        {
            auto* C=It->Get();if(!C)continue;
            if(!C->GetPawn()&&W->GetAuthGameMode())W->GetAuthGameMode()->RestartPlayerAtTransform(C,FTransform(FVector(250,100,100)));
            if(!C->IsLocalController())Guest=C;
        }
        if(!Guest)
        {
            if(Has(TEXT("guest.done"))&&!Has(TEXT("host.left")))Mark(TEXT("left"));
            return true;
        }
        auto* PS=Guest->GetPlayerState<AColdSteelPlayerState>();auto* Model=VillageNetAudit::Model(Guest);
        auto* P=Cast<AFPSGAMECharacter>(Guest->GetPawn());if(!PS||!PS->IsGuestInitialized()||!Model||!P||!PC->GetPawn())return true;
        auto* R=P->FindComponentByClass<UHorseRiderComponent>();auto* H=R?R->GetOwnedHorse():nullptr;
        if(!Staged)
        {
            auto* C=LoadClass<ACharacter>(nullptr,TEXT("/Game/WorldGeneration/TemperateHills/VillageStable/StablemasterMeshyR3/BP_Stablemaster.BP_Stablemaster_C"));
            if(!C)return Fail(TEXT("stablemaster class"));
            Vendor=W->SpawnActor<ACharacter>(C,FVector(0,0,86),FRotator::ZeroRotator);
            if(!Vendor.IsValid()||!StableHorseMarket::IsSeller(Vendor.Get()))return Fail(TEXT("stablemaster spawn"));
            if(!TActorIterator<AFPSWeatherManager>(W))W->SpawnActor<AFPSWeatherManager>();
            VillageNetAudit::Place(PC,FVector(1000,900,100),FVector(0,0,100),true);
            VillageNetAudit::Place(Guest,FVector(135,0,100),Vendor->GetActorLocation(),true);
            if(Model->SoulBalance()<9000)return Fail(TEXT("isolated guest wallet not admitted"));
            Mark(TEXT("market"),Model->ProfileView().NetworkProfileId.ToString());Staged=true;
        }
        if(!Has(TEXT("host.side"))&&H && H->Visit()==EStableHorseVisit::Present && H->GetLeader()==P)
        {
            if(!Model->ProfileView().MountRoster.Find(H->Identity()) || VillageNetAudit::Model(PC)->ProfileView().MountRoster.Find(H->Identity()))
                return Fail(TEXT("ownership isolation"));
            const auto* Record=Model->ProfileView().MountRoster.Find(H->Identity());
            auto* VendorPose=Cast<UResidentTurnAnimInstance>(CastChecked<ACharacter>(Vendor.Get())->GetMesh()->GetAnimInstance());
            if(VendorPose && VendorPose->ConversationPlayer.IsValid())return Fail(TEXT("guest stole host gaze"));
            Mark(TEXT("viewer"),TEXT("host pose independent of guest"));
            if(Record->Equipment.Num()!=4)return Fail(TEXT("host gear after equip"));
            const int64 PreviousPlayer=Model->ProfileView().Experience, PreviousHorse=Record->Experience;
            if(!Model->GainExperience(53))return Fail(TEXT("guest authority XP commit"));
            Record=Model->ProfileView().MountRoster.Find(H->Identity());
            const int64 Earned=Model->ProfileView().Experience-PreviousPlayer;
            if(Earned<=0 || !Record || Record->Experience-PreviousHorse!=Earned)return Fail(TEXT("shared XP mismatch"));
            Mark(TEXT("xp"),FString::Printf(TEXT("%lld"),Record->Experience));
            H->SetLeader(nullptr);H->Halt();
            VillageNetAudit::Place(Guest,H->GetActorLocation()+H->GetActorRightVector()*115,FVector(H->GetActorLocation()+FVector(0,0,15)),true);
            Mark(TEXT("side"),H->Identity().ToString());
        }
        if(H && H->GetRider()==P && R->IsSeated(P) && !Injured && H->GetVelocity().Size2D()>340)
        {
            StartHealth=H->GetHealth();auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();
            auto* Enemy=W->SpawnActor<AActor>();Enemy->Tags.Add(TEXT("Enemy"));
            const float Old=HP->Health;UGameplayStatics::ApplyDamage(P,24,nullptr,Enemy,nullptr);
            const float Loss=Old-HP->Health;
            if(Loss<=0||!FMath::IsNearlyEqual(Loss,StartHealth-H->GetHealth(),.05f))return Fail(TEXT("mounted damage mismatch"));
            Mark(TEXT("damage"),FString::Printf(TEXT("rider=%.2f horse=%.2f"),Loss,StartHealth-H->GetHealth()));
            Injured=true;
        }
        if(H&&H->InJump()&&!Has(TEXT("host.jump")))Mark(TEXT("jump"));
        if(H && !H->GetRider() && H->Visit()==EStableHorseVisit::Departing && !Has(TEXT("host.depart")))Mark(TEXT("depart"));
        if(Has(TEXT("host.left")) && !Has(TEXT("host.returned")))
        {
            VillageNetAudit::Place(Guest,FVector(850,400,100),FVector(0,0,100),true);
            Mark(TEXT("returned"),Model->ProfileView().NetworkProfileId.ToString());
        }
        if(Has(TEXT("rejoin.recalled")) && H && !Has(TEXT("host.wounded")) && H->Visit()==EStableHorseVisit::Present)
        {
            auto* Enemy=W->SpawnActor<AActor>();Enemy->Tags.Add(TEXT("Enemy"));
            UGameplayStatics::ApplyDamage(H,H->GetHealth()-3.f,nullptr,Enemy,nullptr);
            if(!FMath::IsNearlyEqual(H->GetHealth(),3.f,.1f))return Fail(TEXT("wounding the unmounted horse"));
            H->SetLeader(nullptr);H->Halt();
            VillageNetAudit::Place(Guest,H->GetActorLocation()+H->GetActorRightVector()*115,H->GetActorLocation()+FVector(0,0,15),true);
            Mark(TEXT("wounded"));
        }
        if(Has(TEXT("rejoin.remounted")) && H && R->IsSeated(P) && !Has(TEXT("host.retreat")))
        {
            auto* Enemy=W->SpawnActor<AActor>();Enemy->Tags.Add(TEXT("Enemy"));
            UGameplayStatics::ApplyDamage(H,24.f,nullptr,Enemy,nullptr);
            BeforeImpact=P->FindComponentByClass<UFPSCombatHealthComponent>()->Health;
            if(!H->IsRetreating()||BeforeImpact<=0.f)return Fail(TEXT("horse-origin hit or retreat"));
            UE_LOG(LogTemp,Display,TEXT("HORSE_REVIEW_WAIT_FOR_IMPACT"));
            Mark(TEXT("retreat"));
        }
        if(Has(TEXT("host.retreat"))&&!Has(TEXT("host.fall"))&&!R->Active())
        {
            const float After=P->FindComponentByClass<UFPSCombatHealthComponent>()->Health;
            if(After<BeforeImpact-.1f)
            {
                // Natural HP recovery continues during the rear and fall. The runner reads the combat
                // receipt bracketed by these markers for the exact health immediately before impact.
                UE_LOG(LogTemp,Display,TEXT("HORSE_REVIEW_IMPACT_OBSERVED"));
                Mark(TEXT("fall"),FString::Printf(TEXT("post_hit=%.2f post_impact=%.2f"),BeforeImpact,After));
            }
        }
        if(Has(TEXT("host.left"))&&Has(TEXT("rejoin.done")))
        {
            FGuid Saved;FGuid::Parse(Read(TEXT("guest.done")),Saved);
            if(!Model->ProfileView().MountRoster.Find(Saved)||Model->ProfileView().MountRoster.Deployed!=Saved)return Fail(TEXT("rejoin server roster"));
            if(!Has(TEXT("host.done")))Mark(TEXT("done"));
        }
        return true;
    }
    bool Tick(float)
    {
        const double Now=FPlatformTime::Seconds();
        if(Role==TEXT("rejoin") && Has(TEXT("rejoin.done")) && Has(TEXT("host.done")))
        {Mark(TEXT("ack"));FPlatformMisc::RequestExit(false);return false;}
        if(Role==TEXT("host") && Has(TEXT("rejoin.ack")))
        {FPlatformMisc::RequestExit(false);return false;}
        if(Now-Start>360.)return Fail(FString::Printf(TEXT("timeout phase=%d %s"),Phase,*Detail));
        UWorld* W=nullptr;const bool IsHost=Role==TEXT("host");
        const auto NetMode=Role==TEXT("seed")?NM_Standalone:(IsHost?NM_ListenServer:NM_Client);
        for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->HasBegunPlay()&&C.World()->GetNetMode()==NetMode){W=C.World();break;}
        if(!W)return true;
        if(Role==TEXT("seed"))
        {
            auto* Model=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
            if(!Model||!Model->ProfileView().NetworkProfileId.IsValid())return true;
            if(!Model->AddItem(TEXT("hp_potion"),1)||!Model->GrantSouls(9000))return Fail(Model->ResultMessage());
            for(const auto* Def:StableHorseGear::Definitions)if(!Model->AddItem(Def,1))return Fail(TEXT("could not seed tack"));
            Mark(TEXT("done"),FString::Printf(TEXT("%lld"),Model->SoulBalance()));FPlatformMisc::RequestExit(false);return false;
        }
        if(!Floor)MakeFloor(W);
        auto* PC=W->GetFirstPlayerController();if(!PC)return true;
        if(IsHost)return Host(W,PC);
        auto* P=Cast<AFPSGAMECharacter>(PC->GetPawn());if(!P)return true;
        auto* R=P->FindComponentByClass<UHorseRiderComponent>();auto* M=VillageNetAudit::Model(PC);
        if(!R||!M||!M->ProfileView().NetworkProfileId.IsValid())return true;
        const auto& Book=M->ProfileView().MountRoster;auto* H=R->GetOwnedHorse();
        if(Role==TEXT("rejoin"))
        {
            FGuid Saved;FGuid::Parse(Read(TEXT("guest.done")),Saved);
            const auto* Record=Book.Find(Saved);
            if(Now>=NextLog)
            {
                NextLog=Now+4.;
                UE_LOG(LogTemp,Display,TEXT("Horse rejoin phase=%d id=%s roster=%d deployed=%s horse=%s seated=%d hp=%.1f position=%s"),
                    Phase,*M->ProfileView().NetworkProfileId.ToString(),Book.Horses.Num(),*Book.Deployed.ToString(),*GetNameSafe(H),int(R->IsSeated(P)),Record?Record->Health:-1.f,*P->GetActorLocation().ToString());
            }
            if(!Record||Book.Deployed!=Saved||M->ProfileView().NetworkProfileId.ToString()!=Read(TEXT("host.market"))||!Has(TEXT("host.returned")))return true;
            const auto CallHorse=[&]{R->ServerToggleMount(P->GetPawnViewLocation(),PC->GetControlRotation(),75);};
            if(Phase==0 && P->GetCharacterMovement()->IsMovingOnGround()){
                if(Record->Equipment.Num()!=4 || Record->Experience!=FCString::Atoi64(*Read(TEXT("host.xp"))))return true;
                for(const auto& Item:Record->Equipment)if(M->FindItem(Item.InstanceId) ||
                    Read(*(TEXT("guest.gear_")+Item.Definition))!=Item.InstanceId)return Fail(TEXT("rejoin gear identity"));
                Mark(TEXT("inventory"),TEXT("four original pieces, no backpack duplicates, retained XP"));
                CallHorse();Retry=Now+5.;++Phase;}
            else if(Phase==1&&!IsValid(H)&&Now>=Retry){CallHorse();Retry=Now+5.;}
            else if(Phase==1&&H&&H->Identity()==Saved&&H->Visit()==EStableHorseVisit::Present)
            {Mark(TEXT("recalled"));++Phase;}
            else if(Phase==2&&H&&Has(TEXT("host.wounded"))&&Now>=Retry)
            {
                if(R->IsSeated(P)&&H->GetRider()==P){Mark(TEXT("remounted"));++Phase;}
                else if(!R->Active())
                {
                    PC->SetControlRotation((H->GetActorLocation()+FVector(0,0,15)-P->GetMeleeAimTransform().GetLocation()).Rotation());
                    R->ServerUse(H,true);Retry=Now+.6;
                }
            }
            else if(Phase==3&&Record->Health<=0.f&&Record->Cooling(FDateTime::UtcNow().GetTicks())&&!IsValid(H)&&Has(TEXT("host.fall")))
            {
                const auto* Stack=M->Items().FindByPredicate([](const FColdSteelItem& I){return I.Definition==TEXT("hp_potion")&&I.Count>0;});
                if(!Stack)return Fail(TEXT("missing seeded potion"));
                auto* PS=P->GetPlayerState<AColdSteelPlayerState>();if(!PS)return true;
                FColdSteelInventoryRequest Request;Request.Action=EColdSteelInventoryAction::MountPotion;Request.MountId=Saved;Request.Item=Stack->InstanceId;
                if(PS->RequestInventoryAction(Request))++Phase;
            }
            else if(Phase==4&&Record->Health>0.f)
            {
                const double Left=FTimespan(Record->RecallAfterUtc-FDateTime::UtcNow().GetTicks()).GetTotalSeconds();
                if(Left<=0. || Left>60.)return Fail(TEXT("invalid escape deadline"));
                Mark(TEXT("potion"),FString::Printf(TEXT("health=%.2f remaining=%.2fs"),Record->Health,Left));
                CallHorse();++Phase;
            }
            else if(Phase==5)
            {
                if(IsValid(H))return Fail(TEXT("early recall bypassed cooldown"));
                if(!Record->Cooling(FDateTime::UtcNow().GetTicks())){CallHorse();Retry=Now+5.;++Phase;}
            }
            else if(Phase==6&&!IsValid(H)&&Now>=Retry){CallHorse();Retry=Now+5.;}
            else if(Phase==6 && H && H->Identity()==Saved && H->Visit()==EStableHorseVisit::Present)
            {
                if(H->GetHealth()<=0.f)return Fail(TEXT("recall lost healed condition"));
                if(!Has(TEXT("rejoin.done")))Mark(TEXT("done"),Saved.ToString());
            }
            return true;
        }
        auto* Shop=W->GetGameInstance()->GetSubsystem<UColdSteelShopModel>();
        if(Now>=NextLog)
        {
            Detail=FString::Printf(TEXT("phase=%d souls=%lld horses=%d horse=%s visit=%d rider=%s mode=%d shop=%s"),Phase,M->SoulBalance(),Book.Horses.Num(),*GetNameSafe(H),H?int(H->Visit()):-1,H?*GetNameSafe(H->GetRider()):TEXT("-"),int(P->GetCharacterMovement()->MovementMode.GetValue()),*Shop->ResultMessage());
            UE_LOG(LogTemp,Display,TEXT("HORSE_REVIEW %s"),*Detail);NextLog=Now+5.;
        }
        if(Phase==0&&Has(TEXT("host.market"))&&M->SoulBalance()>=9000)
        {
            for(TActorIterator<ACharacter> It(W);It;++It)if(StableHorseMarket::IsSeller(*It)){Vendor=*It;break;}
            if(!Vendor.IsValid() || !Shop->BeginStableSession(Vendor.Get()) || Shop->HorseOffers().Num()!=4)return true;
            const auto Offer=Shop->HorseOffers()[0];Lot=Offer.Horse.HorseId;Price=Offer.Price;InitialSouls=M->SoulBalance();
            if(!Shop->BuyHorse(Lot))return Fail(Shop->ResultMessage());++Phase;
        }
        else if(Phase==1 && Book.Find(Lot) && M->SoulBalance()==InitialSouls-Price)
        {
            if(Book.Horses.Num()!=1||Book.Deployed!=Lot)return Fail(TEXT("duplicate or incorrect deployment"));
            if(!CheckGear(PC,*M,*Book.Find(Lot)))return true;
            auto* Seller=CastChecked<ACharacter>(Vendor.Get());
            auto* Turn=Cast<UResidentTurnAnimInstance>(Seller->GetMesh()->GetAnimInstance());
            if(!Turn || Turn->ConversationPlayer.Get()!=PC)return Fail(TEXT("guest stablemaster did not acquire local viewer"));
            Mark(TEXT("purchase"),Lot.ToString());Shop->EndSession();
            if(Turn->ConversationPlayer.IsValid())return Fail(TEXT("guest vendor retained target after closing"));
            Mark(TEXT("gaze"),TEXT("guest shop opens and releases the native local gaze target"));
            R->ServerToggleMount(P->GetPawnViewLocation(),PC->GetControlRotation(),75);++Phase;
        }
        else if(Phase==2 && H && Has(TEXT("host.side")) && H->Visit()==EStableHorseVisit::Present && Now>=Retry)
        {
            PC->SetControlRotation((H->GetActorLocation()+FVector(0,0,15)-P->GetMeleeAimTransform().GetLocation()).Rotation());
            if(R->IsSeated(P))
            {
                if(H->GetRider()!=P)return true;
                if(!H->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(P) || !P->GetCapsuleComponent()->GetMoveIgnoreActors().Contains(H))return Fail(TEXT("asymmetric client capsule collision"));
                StartHealth=H->GetHealth();StartStamina=H->GetStamina();Mark(TEXT("seat"));R->ServerDrive(H,100,0,true);++Phase;
            }
            else if(!R->Active()){R->ServerUse(H,true);Retry=Now+.5;}
        }
        else if(Phase==3&&H&&H->GetHealth()<StartHealth&&H->GetStamina()<StartStamina && H->GetCharacterMovement()->GetWalkableFloorAngle()>59.9f && Has(TEXT("host.damage")))
        {Mark(TEXT("canter"),FString::Printf(TEXT("speed=%.1f stamina=%.1f"),H->GetVelocity().Size2D(),H->GetStamina()));R->ServerHorseJump(H);++Phase;}
        else if(Phase==4&&H&&H->InJump()){Mark(TEXT("jump"));R->ServerDrive(H,0,0,false);++Phase;}
        else if(Phase==5&&H&&!H->InJump()&&H->GetVelocity().Size2D()<10 && Has(TEXT("host.jump")) && Now>=Retry)
        {R->ServerDrive(H,-100,0,false);Phase=20;}
        else if(Phase==20 && H && FVector::DotProduct(H->GetVelocity(),H->GetActorForwardVector())<-30.f)
        {Mark(TEXT("reverse"),FString::SanitizeFloat(FVector::DotProduct(H->GetVelocity(),H->GetActorForwardVector())));R->ServerDrive(H,0,0,false);Phase=21;}
        else if(Phase==21 && H && H->GetVelocity().Size2D()<10 && Now>=Retry)
        {
            if(!R->Active()){Mark(TEXT("dismount"));R->ServerToggleMount(P->GetPawnViewLocation(),PC->GetControlRotation(),75);Phase=6;}
            else if(R->IsSeated(P)){R->ServerUse(H,true);Retry=Now+.6;}
        }
        else if(Phase==6&&!IsValid(H)&&Has(TEXT("host.depart")) && Book.Find(Lot))
        {Mark(TEXT("done"),Lot.ToString());FPlatformMisc::RequestExit(false);return false;}
        return true;
    }
};
static FAutoConsoleCommand HorseReviewCmd(TEXT("fps.Test.HorseNetwork"),TEXT("Run isolated horse network review"),
    FConsoleCommandDelegate::CreateLambda([]{
        auto Run=MakeShared<FHorseNetworkReview>();
        if(!FParse::Param(FCommandLine::Get(),TEXT("HorseNetworkReview"))||
            !FParse::Value(FCommandLine::Get(),TEXT("HorseEvidence="),Run->Dir)||
            !FParse::Value(FCommandLine::Get(),TEXT("HorseRole="),Run->Role))return;
        FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run](float D){return Run->Tick(D);}),.08f);
    }));
#endif
