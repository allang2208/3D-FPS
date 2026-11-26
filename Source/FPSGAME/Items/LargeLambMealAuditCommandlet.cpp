#include "LargeLambMealAuditCommandlet.h"
#include "FPSPotionUseComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSWeatherManager.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelSmeltingWidget.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Survival/FPSSurvivalComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Building/SmeltingSystem.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPalette.h"
#include "../Building/ColdSteelCampfire.h"
#include "../Skills/FPSCastingMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/Button.h"
#include "Components/Border.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Materials/Material.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 ULargeLambMealAuditCommandlet::Main(const FString& Params)
{
    FString UserDir;
    if(!FParse::Value(FCommandLine::Get(),TEXT("UserDir="),UserDir)||
       !FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()).Contains(TEXT("LargeLamb20261014/TestRuns/")))
    {UE_LOG(LogTemp,Error,TEXT("LargeLambMealAudit requires its isolated UserDir"));return 2;}
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("LargeLambAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(Original+TEXT(" -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("LargeLambMealAudit"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    World->GetWorldSettings()->MaxUndilatedFrameTime=1.f;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);R->SetStringField(TEXT("detail"),Detail);
        Rows.Add(MakeShared<FJsonValueObject>(R));if(!OK)++Failed;
        UE_LOG(LogTemp,Display,TEXT("LARGE_LAMB_AUDIT %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Near=[](double A,double B){return FMath::Abs(A-B)<.002;};
    auto* Player=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetPlayerState(World->SpawnActor<APlayerState>());
    PC->SetAsLocalPlayerController();PC->Possess(Player);
    Player->DispatchBeginPlay();
    auto* Survival=Player->FindComponentByClass<UFPSSurvivalComponent>();
    auto* Health=Player->FindComponentByClass<UFPSCombatHealthComponent>();
    auto* Potion=Player->FindComponentByClass<UFPSPotionUseComponent>();
    Model->CurrentPawn=Player;
    auto Seed=Model->Snapshot();Seed.Items.Reset();Seed.ActiveProductionTool.Reset();Seed.ActiveWeaponSlot=6;
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Seed.QuickBindings)Binding={};
    Seed.StaminaVersion=1;Seed.Stamina=37;Seed.StaminaRecoveryDelay=60;Seed.Survival={};
    Seed.Survival.MaxHunger=120;Seed.Survival.Hunger=10;Seed.Survival.Hydration=83;Seed.Survival.Sanity=74;
    Health->Health=Health->MaxHealth;Seed.Health=Health->Health;
    auto Put=[&](FColdSteelProfile& P,const TCHAR* Id){auto I=Model->CreateItem(Id);const FString Key=I.InstanceId;Check(ColdSteelInventory::Insert(P.Items,I),FString(TEXT("fixture insert "))+Id);return Key;};
    const FString Raw=Put(Seed,TEXT("raw_large_lamb"));Put(Seed,TEXT("wood"));
    Check(Model->CommitState(Seed),TEXT("isolated profile seeded"),Model->ResultMessage());
    Check(Player->HasActorBegunPlay()&&Near(Survival->GetState().Hunger,10)&&Near(Survival->GetState().MaxHunger,120),TEXT("initialized pawn receives production profile publication"));
    Check(!Model->UseConsumableAtContact(Raw,true)&&Model->FindItem(Raw),TEXT("raw cannot be consumed"));
    auto* Cooking=GI->GetSubsystem<UColdSteelSmeltingSystem>();
    const auto* Recipe=Cooking->Find(TEXT("roast_large_lamb"));
    Check(Recipe&&Recipe->bCampfire&&Recipe->InputCount==1&&Recipe->OutputCount==1&&Near(Recipe->Seconds,60),TEXT("catalog 1 raw to 1 cooked in 60s"));
    auto* Building=World->SpawnActor<AVoxelBuildWorld>();
    // Cooking does not depend on the unrelated visual/material palette. Use a
    // transient minimal palette; all recipes, journals and transactions are real.
    auto* Palette=NewObject<UVoxelBuildPalette>(Building);
    auto& Material=Palette->Materials.AddDefaulted_GetRef();Material.Id=TEXT("wood");Material.Surface=UMaterial::GetDefaultMaterial(MD_Surface);
    auto& Definition=Palette->Components.AddDefaulted_GetRef();Definition.Id=TEXT("campfire");
    Definition.ActorClass=AColdSteelCampfire::StaticClass();Definition.Footprint=FIntVector(5,5,4);
    const bool BuildingReady=Building->Initialize(Profile,Palette);
    Check(BuildingReady,TEXT("isolated cooking world initialized with transient palette"),Building->Message);
    const FIntVector Cell(0,0,0);auto& Fire=Building->Prefabs.AddDefaulted_GetRef();Fire.Id=TEXT("campfire");Fire.Cell=Cell;Fire.InstanceId=FGuid::NewGuid();
    FString Reason;
    Check(Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,0,NAME_None,1,Reason),TEXT("real fuel transaction"),Reason);
    Check(Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,1,TEXT("roast_large_lamb"),1,Reason),TEXT("real cooking input transaction"),Reason);
    Check(!Model->FindItem(Raw),TEXT("raw removed exactly once"));
    auto* Job=Building->FindSmeltingMutable(Cell);
    if(Job)
    {
        const int64 Now=FDateTime::UtcNow().GetTicks();
        Building->SetFuel(Cell,90);Building->SetFurnaceFireTicks(Cell,Now-59*ETimespan::TicksPerSecond);Job->BurnStartTicks=Now-59*ETimespan::TicksPerSecond;
        Cooking->SettleCampfire(Building,Cell);
        Check(Job->Products.IsEmpty()&&Job->ProgressSeconds>=59&&Job->ProgressSeconds<60,TEXT("59s produces no early food"));
        Building->SetFurnaceFireTicks(Cell,FDateTime::UtcNow().GetTicks()-2*ETimespan::TicksPerSecond);
        Job->BurnStartTicks=Building->FurnaceFireTicks(Cell);Cooking->SettleCampfire(Building,Cell);
        Check(Job->Products.Num()==1&&Job->Products[0].Item==TEXT("roasted_large_lamb")&&Job->Products[0].Count==1,TEXT("crossing 60s produces exactly one"));
        Cooking->SettleCampfire(Building,Cell);Check(Job->Products.Num()==1&&Job->Products[0].Count==1,TEXT("repeat settle does not duplicate"));
        Check(Cooking->ExecuteCampfire(Building,Cell,Model,nullptr,2,NAME_None,1,Reason),TEXT("real collect transaction"),Reason);
    }
    else Check(false,TEXT("cooking job exists"));
    // Explicit campfire completion review. All writes remain in the guarded UserDir.
    // Preserve the cooked meal that the existing contact/effect cases use below.
    const auto MealProfile=Model->Snapshot();
    const TCHAR* CampfireRecipes[]={TEXT("roast_chicken_leg"),TEXT("roast_lamb_ribs"),TEXT("roast_sausage"),TEXT("roast_large_lamb")};
    for(int32 Index=0;Index<4;++Index)
    {
        const auto* R=Cooking->Find(CampfireRecipes[Index]);
        if(!R){Check(false,FString(TEXT("missing campfire recipe "))+CampfireRecipes[Index]);continue;}
        const FString Label=R->Id.ToString()+TEXT(": ");
        const FIntVector TestCell(20+Index*10,0,0);
        auto& Record=Building->Prefabs.AddDefaulted_GetRef();Record.Id=TEXT("campfire");Record.Cell=TestCell;Record.InstanceId=FGuid::NewGuid();
        auto TestProfile=MealProfile;TestProfile.Items.Reset();
        const bool Seeded=ColdSteelInventory::Insert(TestProfile.Items,Model->CreateItem(R->Input,R->InputCount))
            &&ColdSteelInventory::Insert(TestProfile.Items,Model->CreateItem(TEXT("wood"),2))&&Model->CommitState(TestProfile);
        Check(Seeded,Label+TEXT("ingredients seeded"));
        Check(Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,0,NAME_None,1,Reason)
            &&Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,1,R->Id,1,Reason),Label+TEXT("fuel and input transactions"),Reason);
        auto* Active=Building->FindSmeltingMutable(TestCell);
        if(!Active){Check(false,Label+TEXT("active job exists"));continue;}
        const double Half=R->Seconds*.5;
        const double StartedProgress=Active->ProgressSeconds;
        const int64 Earlier=FDateTime::UtcNow().GetTicks()-600*ETimespan::TicksPerSecond;
        Building->SetFuel(TestCell,Half);Building->SetFurnaceFireTicks(TestCell,Earlier);Active->BurnStartTicks=Earlier;
        Cooking->SettleCampfire(Building,TestCell);
        const FString BurnDetail=FString::Printf(TEXT("initial=%.6f progress=%.6f budget=%.6f fuel=%.6f"),StartedProgress,Active->ProgressSeconds,Half,Building->FuelAt(TestCell));
        Check(Near(Building->FuelAt(TestCell),0)&&Near(Active->ProgressSeconds,StartedProgress+Half)&&Active->Products.IsEmpty(),Label+TEXT("offline burn stops exactly when fuel runs out"),BurnDetail);
        Cooking->SettleCampfire(Building,TestCell);
        Check(Near(Active->ProgressSeconds,StartedProgress+Half)&&Active->Products.IsEmpty(),Label+TEXT("no fuel preserves unfinished progress"));
        Check(Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,0,NAME_None,1,Reason),Label+TEXT("refuel resumes existing job"),Reason);
        const int64 Resume=FDateTime::UtcNow().GetTicks()-FMath::RoundToInt64((R->Seconds-Half+.1)*ETimespan::TicksPerSecond);
        Building->SetFurnaceFireTicks(TestCell,Resume);Active->BurnStartTicks=Resume;
        Cooking->SettleCampfire(Building,TestCell);Cooking->SettleCampfire(Building,TestCell);
        Check(Active->Recipe.IsNone()&&Active->Products.Num()==1&&Active->Products[0].Item==R->Output
            &&Active->Products[0].Count==R->OutputCount,Label+TEXT("resume produces exactly once"));
        if(Index==3)
        {
            const auto BeforeFull=Model->Snapshot();auto Full=BeforeFull;Full.Items.Reset();
            for(int32 N=0;N<512;++N)
            {auto Trial=Full.Items;if(!ColdSteelInventory::Insert(Trial,Model->CreateItem(TEXT("raw_sausage"))))break;Full.Items=MoveTemp(Trial);}
            Check(Model->CommitState(Full),Label+TEXT("full backpack fixture saved"));
            const int64 Revision=Model->Snapshot().CampfireInventoryRevision;
            Check(!Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,2,NAME_None,1,Reason)
                &&Active->Products.Num()==1&&Active->Products[0].Count==R->OutputCount
                &&Model->Snapshot().CampfireInventoryRevision==Revision,Label+TEXT("full backpack retains public product without a transaction"));
            Check(Model->CommitState(BeforeFull),Label+TEXT("backpack space restored"));
        }
        Check(Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,2,NAME_None,1,Reason)
            &&Model->CountMaterial(R->Output)==R->OutputCount,Label+TEXT("collect credits actual inventory"),Reason);
        Check(!Cooking->ExecuteCampfire(Building,TestCell,Model,nullptr,2,NAME_None,1,Reason)
            &&Model->CountMaterial(R->Output)==R->OutputCount,Label+TEXT("repeat collect cannot duplicate food"));
    }
    {
        const FIntVector QueueCell(70,0,0);
        auto& Record=Building->Prefabs.AddDefaulted_GetRef();Record.Id=TEXT("campfire");Record.Cell=QueueCell;Record.InstanceId=FGuid::NewGuid();
        auto QueueProfile=MealProfile;QueueProfile.Items.Reset();bool Seeded=true;
        for(int32 N=0;N<12;++N)Seeded&=ColdSteelInventory::Insert(QueueProfile.Items,Model->CreateItem(TEXT("raw_sausage")));
        Check(Seeded&&Model->CommitState(QueueProfile),TEXT("queue fixture seeded"));
        bool Queued=true;
        for(int32 N=0;N<9;++N)Queued&=Cooking->ExecuteCampfire(Building,QueueCell,Model,nullptr,1,TEXT("roast_sausage"),1,Reason);
        Check(Queued&&Building->FindSmelting(QueueCell)&&Building->FindSmelting(QueueCell)->Queue.Num()==8,TEXT("one active order plus eight waiting orders"));
        const int64 BeforeReject=Model->CountMaterial(TEXT("raw_sausage"));
        Check(!Cooking->ExecuteCampfire(Building,QueueCell,Model,nullptr,1,TEXT("roast_sausage"),1,Reason)
            &&Model->CountMaterial(TEXT("raw_sausage"))==BeforeReject,TEXT("full queue rejects without taking ingredients"));
        auto* Reloaded=World->SpawnActor<AVoxelBuildWorld>();
        const bool ReloadOK=Building->FlushCampfirePersistence()&&Reloaded->Initialize(Profile,Palette);
        const auto* ReloadedJob=Reloaded->FindSmelting(QueueCell);
        Check(ReloadOK&&ReloadedJob&&ReloadedJob->Recipe==TEXT("roast_sausage")&&ReloadedJob->Queue.Num()==8,
            TEXT("building save reload preserves active and queued orders"));
        Reloaded->Destroy();
        Check(Cooking->ExecuteCampfire(Building,QueueCell,Model,nullptr,3,NAME_None,1,Reason)
            &&Model->CountMaterial(TEXT("raw_sausage"))==12,TEXT("validated teardown returns every unfinished ingredient"),Reason);
    }
    Check(Model->CommitState(MealProfile),TEXT("meal fixture restored after campfire transaction cases"));
    if(!FParse::Param(FCommandLine::Get(),TEXT("SkipCampfireWidget")))
    {
        auto* Panel=CreateWidget<UColdSteelSmeltingWidget>(GI);auto* ViewFire=World->SpawnActor<AColdSteelCampfire>();
        // Headless fixtures have no LocalPlayer, so UUserWidget may defer this hook.
        if(Panel&&!Panel->CollectButton)Panel->NativeOnInitialized();
        Check(Panel!=nullptr,TEXT("campfire widget initializes without a viewport"));
        if(Panel)
        {
            Panel->SetCampfire(ViewFire);Panel->SelectRecipe(TEXT("roast_chicken_leg"));
            Check(Panel->Batch==0&&Panel->BatchText->GetText().ToString().Contains(TEXT("最多 0"))&&!Panel->StartButton->GetIsEnabled(),
                TEXT("empty ingredients show zero available portions and disable enqueue"));
            auto WithRaw=MealProfile;ColdSteelInventory::Insert(WithRaw.Items,Model->CreateItem(TEXT("raw_chicken_leg")));
            Check(Model->CommitState(WithRaw),TEXT("panel ingredient fixture added"));Panel->RefreshCampfireJob();
            Check(Panel->Batch==1,TEXT("adding ingredients restores one selected portion"));
            Check(Model->CommitState(MealProfile),TEXT("panel ingredient fixture removed"));Panel->RefreshCampfireJob();
            Check(Panel->Batch==0&&!Panel->BatchPlus->GetIsEnabled(),TEXT("removing last ingredient clears stale batch"));
            auto& Snapshot=const_cast<FCampfireSharedState&>(ViewFire->SharedState());
            auto& Product=Snapshot.Products.AddDefaulted_GetRef();Product.Item=TEXT("roasted_chicken_leg");Product.Count=1;
            Panel->RefreshCampfireJob();
            Check(Panel->CollectGlow->GetVisibility()==ESlateVisibility::SelfHitTestInvisible,TEXT("collection glow keeps child button hit testing enabled"));
            const FIntVector FurnaceCell(80,0,0);
            auto& Furnace=Building->Prefabs.AddDefaulted_GetRef();Furnace.Id=VoxelSmeltingFurnaceId;
            Furnace.Cell=FurnaceCell;Furnace.InstanceId=FGuid::NewGuid();
            const auto* FurnaceRecipe=Cooking->Catalog().FindByPredicate([](const auto& R){return !R.bCampfire;});
            if(FurnaceRecipe)
            {
                auto& Finished=Building->SmeltingJobs.AddDefaulted_GetRef();Finished.Cell=FurnaceCell;Finished.Recipe=FurnaceRecipe->Id;
                Finished.BatchCount=1;Finished.ProgressSeconds=FurnaceRecipe->Seconds;
            }
            Panel->SetFurnace(Building,FurnaceCell);
            Check(FurnaceRecipe&&!Panel->bCampfire&&Panel->CollectButton->GetIsEnabled()
                &&Panel->CollectButton->GetVisibility()==ESlateVisibility::Visible,TEXT("completed furnace remains collectible after switching from campfire"));
        }
        ViewFire->Destroy();
    }
    FString Cooked;for(const auto& I:Model->Snapshot().Items)if(I.Definition==TEXT("roasted_large_lamb"))Cooked=I.InstanceId;
    Check(!Cooked.IsEmpty(),TEXT("cooked item in inventory"));
    FPotionUseMotion Motion;Motion.Load(false,TEXT("roasted_large_lamb"));
    Check(Near(Motion.Duration,6)&&Near(Motion.Contact,4.65),TEXT("native motion reads 6s / 4.65s"));
    // The fixture skips visual setup, but drives the real component's contact gate,
    // cancellation and transaction. The pawn has begun play; no viewport or user map is involved.
    Potion->Bottle=NewObject<UStaticMeshComponent>(Player);Potion->Liquid=NewObject<UStaticMeshComponent>(Player);Potion->Stopper=NewObject<UStaticMeshComponent>(Player);
    Potion->FallbackHands=NewObject<UFPSCastingMeshComponent>(Player);
    auto Arm=[&](const FString& Id,float Age){Potion->UsingItem=Id;Potion->Motion=Motion;Potion->StartTime=World->GetTimeSeconds()-Age;
        Potion->bActive=Potion->bFood=true;Potion->bCommitted=Potion->bDiscarded=false;Potion->bSwallowStarted=true;};
    const float BaseMaximum=Model->MaxStamina(),BaseRate=Model->StaminaRecoveryRate();
    Arm(Cooked,4.64f);Potion->bStowOffhand=true;
    Check(Motion.bTwoHanded&&Potion->HandlePrimaryPress(),TEXT("two-hand meal consumes cancel press before contact"));
    Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(Potion->IsActive()&&!Potion->bCommitted&&Model->FindItem(Cooked)&&Near(Survival->LargeLambMealRemaining(),0),
        TEXT("early raise neither settles nor releases attack ownership"));
    Potion->StartTime=World->GetTimeSeconds()-Motion.Duration-.27f;Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(!Potion->IsActive()&&Potion->HandlePrimaryRelease()&&Model->FindItem(Cooked),TEXT("cancel release after full return cannot attack"));
    Arm(Cooked,4.64f);Potion->TickComponent(.01f,LEVELTICK_All,nullptr);Potion->Cancel();
    Check(Model->FindItem(Cooked)&&Near(Survival->LargeLambMealRemaining(),0)&&Near(Model->Stamina(),37),TEXT("pre-contact cancel preserves item, stamina and buff"));
    Arm(Cooked,4.651f);Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    auto Used=Model->Snapshot();
    Check(!Model->FindItem(Cooked)&&Near(Used.Survival.Hunger,70),TEXT("real contact consumes once and restores 50 percent current max hunger"));
    Check(Near(Used.Survival.Hydration,83)&&Near(Used.Survival.Sanity,74),TEXT("water and SAN unchanged"));
    Check(Near(Survival->LargeLambMealRemaining(),600)&&Near(Model->MaxStamina(),BaseMaximum*1.1)&&Near(Model->StaminaRecoveryRate(),BaseRate*1.05),TEXT("600s buff changes maximum and recovery"));
    Check(Near(Model->Stamina(),37),TEXT("activation does not grant current stamina"));
    const auto Tiles=UStatusEffectsComponent::GetOrCreate(Player)->Snapshot();
    const auto* Tile=Tiles.FindByPredicate([](const auto& E){return E.Type==TEXT("largeLambMeal");});
    Check(Tile&&Tile->Name==TEXT("大份烤羊排")&&Near(Tile->Duration,600)&&Near(Tile->Remaining,600),TEXT("HUD adapter publishes exact name and duration"));
    Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(Near(Model->Snapshot().Survival.Hunger,70)&&Near(Survival->LargeLambMealRemaining(),600),TEXT("duplicate contact tick cannot apply twice"));
    Potion->bStowOffhand=true;
    Check(Potion->HandlePrimaryPress(),TEXT("post-contact click is owned by the meal"));
    Potion->StartTime=World->GetTimeSeconds()-6.27;Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(!Potion->IsActive()&&Potion->HandlePrimaryRelease()&&!Model->FindItem(Cooked)&&Near(Model->Snapshot().Survival.Hunger,70),
        TEXT("post-contact cancel keeps one settlement and completes raise"));
    // The natural end must also keep both triggers reserved through the raise.
    Arm(Cooked,6.001f);Potion->bCommitted=true;Potion->bStowOffhand=true;
    Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(Potion->IsActive()&&UFPSPotionUseComponent::BlocksWeaponAttack(Player),TEXT("natural finish reserves both hands during raise"));
    Potion->StartTime=World->GetTimeSeconds()-6.27f;Potion->TickComponent(.01f,LEVELTICK_All,nullptr);
    Check(!UFPSPotionUseComponent::BlocksWeaponAttack(Player),TEXT("natural raise releases attack ownership"));
    auto Advance=[&](int32 Seconds){for(int32 I=0;I<Seconds;++I)World->Tick(LEVELTICK_TimeOnly,1.f);};
    Advance(120);Check(Near(Survival->LargeLambMealRemaining(),480),TEXT("server gameplay clock advances remaining time"));
    Model->SyncRuntime();auto Again=Model->Snapshot();Again.Survival.Hunger=Again.Survival.MaxHunger;const FString Second=Put(Again,TEXT("roasted_large_lamb"));
    Check(Model->CommitState(Again),TEXT("repeat fixture saved"));
    Check(Model->UseConsumableAtContact(Second,true),TEXT("full hunger permits buff refresh"));
    Check(Near(Survival->LargeLambMealRemaining(),600)&&Near(Model->MaxStamina(),BaseMaximum*1.1)&&Near(Model->Stamina(),37),TEXT("refresh is 600s, no maximum or current stamina stacking"));
    auto Combined=Model->Snapshot();Combined.Survival=Survival->GetState();const FString Sausage=Put(Combined,TEXT("roasted_sausage"));
    Check(Model->CommitState(Combined)&&Model->UseConsumableAtContact(Sausage,true)&&Near(Survival->SausageRecoveryRemaining(),600),TEXT("real sausage contact grants 600 second effect"));
    Check(Near(Model->FoodStaminaRecoveryMultiplier(),1.1025),TEXT("distinct food sources multiply once"));
    Model->SyncRuntime();Check(Model->CommitState(Model->Snapshot())&&Model->ReloadProfile(),TEXT("remaining effect saves and reloads in isolated profile"));
    Check(Survival->LargeLambMealRemaining()>599&&Near(Model->MaxStamina(),BaseMaximum*1.1),TEXT("reload retains one effect"));
    auto Staggered=Survival->GetState();Staggered.SausageRecoverySeconds=120;Staggered.LargeLambMealSeconds=600;Survival->RestoreState(Staggered);
    Model->Current.Stamina=BaseMaximum*1.1f;Model->Current.StaminaRecoveryDelay=60;
    Advance(121);Model->TickStamina(.01f,Player);
    Check(Near(Survival->SausageRecoveryRemaining(),0)&&Survival->LargeLambMealRemaining()>478&&Near(Model->MaxStamina(),BaseMaximum*1.1)&&Near(Model->StaminaRecoveryRate(),BaseRate*1.05),TEXT("sausage expires first: lamb maximum and one recovery factor remain"));
    Advance(480);Model->TickStamina(.01f,Player);
    Check(Near(Survival->LargeLambMealRemaining(),0)&&Near(Model->MaxStamina(),BaseMaximum)&&Near(Model->Stamina(),BaseMaximum),TEXT("expiry restores base maximum and clamps current stamina"));
    Check(Near(Model->StaminaRecoveryRate(),BaseRate),TEXT("expiry restores recovery without drift"));
    Staggered=Survival->GetState();Staggered.SausageRecoverySeconds=600;Staggered.LargeLambMealSeconds=120;Survival->RestoreState(Staggered);
    Model->Current.Stamina=BaseMaximum*1.1f;Model->Current.StaminaRecoveryDelay=60;
    Advance(121);Model->TickStamina(.01f,Player);
    Check(Near(Survival->LargeLambMealRemaining(),0)&&Survival->SausageRecoveryRemaining()>478&&Near(Model->MaxStamina(),BaseMaximum)&&Near(Model->Stamina(),BaseMaximum)&&Near(Model->StaminaRecoveryRate(),BaseRate*1.05),TEXT("lamb expires first: maximum clamps while sausage recovery remains"));
    Advance(480);Model->TickStamina(.01f,Player);
    Check(Near(Model->MaxStamina(),BaseMaximum)&&Near(Model->StaminaRecoveryRate(),BaseRate),TEXT("both expiry orders restore baseline without drift"));
    auto Fail=Model->Snapshot();Fail.Survival=Survival->GetState();const FString FailId=Put(Fail,TEXT("roasted_large_lamb"));
    Check(Model->CommitState(Fail),TEXT("failed-save fixture saved"));Model->AuditFailNextSave=true;
    Check(!Model->UseConsumableAtContact(FailId,true)&&Model->FindItem(FailId)&&Near(Survival->LargeLambMealRemaining(),0),TEXT("failed save grants no buff and loses no food"));
    Check(Model->UseConsumableAtContact(FailId,true),TEXT("retry after isolated save failure succeeds"));
    Model->Current.Health=0;Health->Health=0;
    auto* Respawn=World->SpawnActor<AFPSGAMECharacter>();PC->Possess(Respawn);Respawn->DispatchBeginPlay();Model->AttachPawn(Respawn);
    const auto Respawned=Model->Snapshot();
    Check(Near(Respawned.Survival.LargeLambMealSeconds,0)&&Near(Model->MaxStamina(),BaseMaximum)&&Near(Model->Stamina(),BaseMaximum),TEXT("death respawn clears food and restores unbuffed maximum"));
    // The following uses the real server component at its normal 4 Hz cadence,
    // with a controlled healthy pawn and no automatic actor ticks or user map.
    auto* Daily=Respawn->FindComponentByClass<UFPSSurvivalComponent>();
    auto* DailyHealth=Respawn->FindComponentByClass<UFPSCombatHealthComponent>();
    DailyHealth->Health=DailyHealth->MaxHealth;
    Check(Respawn->HasAuthority()&&Respawn->IsPlayerControlled()&&!World->IsPaused()&&!DailyHealth->IsDead(),TEXT("daily fixture is an alive authoritative player with PlayerState"));
    const float DaySeconds=GetDefault<AFPSWeatherManager>()->RealSecondsPerGameDay;
    Check(Near(DaySeconds,2160)&&Near(Daily->HungerPerSecond*DaySeconds,100)&&Near(Daily->HydrationPerSecond*DaySeconds,200),TEXT("normal day consumes 100 hunger and 200 water: water lasts 1080 seconds"));
    auto Fresh=[&](){DailyHealth->Health=DailyHealth->MaxHealth;Daily->RestoreState(FFPSSurvivalState{});};
    auto Consume=[&](int32 Steps){for(int32 I=0;I<Steps;++I)Daily->TickComponent(.25f,LEVELTICK_All,nullptr);};
    Fresh();Consume(4319);
    Check(Daily->GetState().Hydration>0,TEXT("water remains positive one tick before 18 minutes"));
    Consume(1);
    Check(FMath::Abs(Daily->GetState().Hunger-50)<.01&&Daily->GetState().Hydration==0&&Near(DailyHealth->Health,DailyHealth->MaxHealth),TEXT("18 minutes exhausts water and leaves 50 hunger without early deprivation damage"),FString::Printf(TEXT("hunger=%.6f water=%.6f"),Daily->GetState().Hunger,Daily->GetState().Hydration));
    Daily->RestoreResources(0,100,0); // Keep the hunger-day observation alive after half-day thirst.
    Consume(4319);
    Check(Daily->GetState().Hunger>0&&Daily->GetState().Hydration>0,TEXT("hunger and refilled water remain positive one tick before a day"));
    Consume(1);
    Check(Daily->GetState().Hunger==0&&Daily->GetState().Hydration==0&&Near(DailyHealth->Health,DailyHealth->MaxHealth),TEXT("36 minutes exhausts hunger and the second water fill without early starvation damage"),FString::Printf(TEXT("hunger=%.6f water=%.6f"),Daily->GetState().Hunger,Daily->GetState().Hydration));
    Fresh();auto Blessed=Daily->GetState();Blessed.FountainBlessingSeconds=720;Daily->RestoreState(Blessed);Consume(400);
    Check(Near(Daily->GetState().FountainBlessingSeconds,620)&&FMath::Abs(Daily->GetState().Hunger-(100-100*Daily->HungerPerSecond*.9))<.01&&FMath::Abs(Daily->GetState().Hydration-(100-100*Daily->HydrationPerSecond*.9))<.01,TEXT("non-food fountain duration and 0.9 consumption multiplier preserved for both resources"));
    Fresh();auto Depleted=Daily->GetState();Depleted.Sanity=0;Daily->RestoreState(Depleted);Consume(400);
    Check(FMath::Abs(Daily->GetState().Hunger-(100-100*Daily->HungerPerSecond*2))<.01&&FMath::Abs(Daily->GetState().Hydration-(100-100*Daily->HydrationPerSecond*2))<.01,TEXT("SAN depletion still doubles both natural rates"));
    Fresh();auto* WarmFire=World->SpawnActor<AColdSteelCampfire>(Respawn->GetActorLocation()-FVector(0,0,90),FRotator::ZeroRotator);WarmFire->SetFuelSeconds(600);
    Check(Near(AColdSteelCampfire::ConsumptionMultiplierAt(Respawn),.5),TEXT("real campfire spatial query supplies one half multiplier"));
    Consume(400);
    Check(FMath::Abs(Daily->GetState().Hunger-(100-100*Daily->HungerPerSecond*.5))<.01&&FMath::Abs(Daily->GetState().Hydration-(100-100*Daily->HydrationPerSecond*.5))<.01,TEXT("campfire halves both new natural rates while water remains twice hunger"));
    WarmFire->Destroy();
    Check(Near(AColdSteelCampfire::ConsumptionMultiplierAt(Respawn),1),TEXT("destroying campfire clears reduction immediately"));
    Model->CurrentPawn.Reset();
    // DispatchBeginPlay was explicit in this uninitialized test world. UE's
    // RouteEndPlay skips actor EndPlay unless bActorInitialized is set, so end
    // any remaining manually begun components while their timer world exists.
    TArray<AActor*> BegunActors;for(TActorIterator<AActor> It(World);It;++It)if(It->HasActorBegunPlay())BegunActors.Add(*It);
    int32 StillBegun=0;
    for(auto* Actor:BegunActors)if(IsValid(Actor))
    {
        Actor->RouteEndPlay(EEndPlayReason::Quit);
        TInlineComponentArray<UActorComponent*> Components;Actor->GetComponents(Components);
        for(auto* Component:Components)if(Component->HasBegunPlay())Component->EndPlay(EEndPlayReason::Quit);
        for(const auto* Component:Components)if(Component->HasBegunPlay())++StillBegun;
    }
    Check(StillBegun==0,TEXT("fixture ends all manually begun components before world teardown"));
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("cases"),Rows);Report->SetNumberField(TEXT("passed"),Rows.Num()-Failed);Report->SetNumberField(TEXT("failed"),Failed);
    Report->SetStringField(TEXT("profile"),Model->ProfileSlot());Report->SetStringField(TEXT("saved_dir"),FPaths::ProjectSavedDir());
    Report->SetStringField(TEXT("scope"),TEXT("headless native production-path fixture; clocks advanced; no rendered hand/PIE/network transport test"));
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectSavedDir()/TEXT("large-lamb-runtime.json")));
    Building->Destroy();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    UE_LOG(LogTemp,Display,TEXT("LARGE_LAMB_AUDIT_RESULT passed=%d failed=%d"),Rows.Num()-Failed,Failed);return Failed?1:0;
}
