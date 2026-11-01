#include "ThunderHammerRecallAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerThrow.h"
#include "../Skills/FPSMagicPreview.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/NurseZombie.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "WarhammerShockwave.h"
#include "ThunderHammerRunes.h"
#include "ThunderHammerPommel.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/LineBatchComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/TextureRenderTarget2D.h"
#include "RenderingThread.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/IConsoleManager.h"

int32 UThunderHammerRecallAuditCommandlet::Main(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("ThunderRecallAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("ThunderHammerRecallAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ThunderRecallAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Model||!Model->IsAudit()||Model->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
#if UE_SUPPORT_FOR_ACTOR_TICK_DISABLE
    World->EnableActorTickAndUserCallbacks(true);
#endif
    int32 Failed=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool Pass,const FString& Name,double Value=0.)
    {auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("check"),Name);R->SetBoolField(TEXT("pass"),Pass);R->SetNumberField(TEXT("value"),Value);Rows.Add(MakeShared<FJsonValueObject>(R));Failed+=!Pass;UE_LOG(LogTemp,Display,TEXT("THUNDER_RECALL %s %s %.6f"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name,Value);};
    auto Item=Model->CreateItem(TEXT("ue_thunder_god_hammer"));Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("head_mount"),TEXT("guan_lei_seat"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    auto Seed=Model->Snapshot();Seed.Items={Item};Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.Stamina=100;Model->AdoptNetMirror(Seed);
    IConsoleManager::Get().FindConsoleVariable(TEXT("s.StreamableDelegateDelayFrames"))->Set(0);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<AThunderRecallAuditController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);Model->AttachPawn(Pawn);
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->InitializeLocalTool();
    if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
    Check(Tool->HasReadyPresentation()&&Tool->Motions.FindRef(TEXT("ThunderCatch"))&&Tool->Motions.FindRef(TEXT("ThunderRecallReady")),TEXT("native clips and modular presentation loaded"));
    if(!Tool->HasReadyPresentation()){GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return 2;}
    Tool->EquipElapsed=-1.f;Tool->Elapsed=-1.f;Tool->SampleMotion(TEXT("Idle"),0.f);
    if(FParse::Param(*Params,TEXT("WeaponSwitchOnly")))
    {
        auto Other=Model->CreateItem(TEXT("ue_m1911"));Other.Place=1;Other.Cell=9;
        Seed.Items={Item,Other};Model->AdoptNetMirror(Seed);
        const auto Switch=[&](int32 SlotIndex)
        {
            Seed.ActiveWeaponSlot=SlotIndex;Model->AdoptNetMirror(Seed);
            Tool->RefreshHeldTool();
            if(Tool->LoadHandle)Tool->LoadHandle->WaitUntilComplete();
        };
        FActorSpawnParameters Spawn;Spawn.Owner=Pawn;Spawn.Instigator=Pawn;
        Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        for(uint8 Phase:{uint8(0),uint8(1)})
        {
            auto* Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(1000,0,36),FRotator::ZeroRotator,Spawn);
            Hammer->Weapon=Item;Hammer->Phase=Phase;Hammer->OwnerCheck=1.f;
            Hammer->PostInitializeComponents();Hammer->DispatchBeginPlay();
            Tool->ThrownHammer=Hammer;Tool->ThunderAwayInstance=Item.InstanceId;
            for(int32 Round=0;Round<2;++Round)
            {
                Switch(9);
                Check(!Tool->IsThunderHammerAway()&&!Tool->HandleThunderPrimary(),TEXT("other weapon does not intercept primary input for recall"));
                Check(IsValid(Hammer)&&Tool->ThrownHammer==Hammer&&Tool->ThunderAwayInstance==Item.InstanceId,TEXT("switch preserves actual thrown weapon instance"));
                Switch(6);
                Check(Tool->HasReadyPresentation()&&Tool->IsThunderHammerAway(),TEXT("switch back restores the thrown instance's presentation"));
                Check(!Tool->IsEquipping(),TEXT("switch back does not enter a draw that cannot finish"));
            }
            // Late network state or a pre-fix loaded draw must also retire.
            Tool->EquipElapsed=0.f;Tool->UpdateHandPresentation(.016f);
            Check(!Tool->IsEquipping(),TEXT("late away state retires an already started draw"));
            if(Phase==0)
            {
                Tool->BeginPrimaryAttack();
                Check(!Hammer->IsReturning()&&!Tool->bThunderRecallPending,TEXT("outbound hammer cannot recall before landing"));
                Hammer->Phase=1;
            }
            const auto Catch=Tool->Motions.FindRef(TEXT("ThunderCatch"));Tool->Motions.Remove(TEXT("ThunderCatch"));
            Tool->BeginPrimaryAttack();
            Check(Hammer->IsGrounded()&&!Tool->bThunderRecallPending,TEXT("wait for reloaded hand presentation before recall"));
            Tool->Motions.Add(TEXT("ThunderCatch"),Catch);
            Tool->BeginPrimaryAttack();
            Check(Hammer->IsReturning()&&Tool->bThunderRecallPending,TEXT("primary attack recalls the same hammer after switch back"));
            Switch(9);
            Check(!Tool->bThunderRecallPending&&Tool->ThunderReachAge<0.f&&Hammer->IsReturning(),TEXT("switch away clears only hand pose while return continues"));
            Switch(6);Tool->UpdateHandPresentation(.016f);
            Check(!Tool->IsEquipping()&&Tool->ThunderReachAge>=0.f&&Tool->bThunderRecallPending,TEXT("switch back during return resumes receiving pose and catch receipt"));
            Hammer->Phase=3;Hammer->CaughtAt=Hammer->Clock()-.11;
            Tool->TickComponent(0.f,LEVELTICK_All,nullptr);Hammer->Tick(0.f);
            Check(Hammer->IsActorBeingDestroyed()&&!Tool->ThrownHammer&&Tool->ThunderAwayInstance.IsEmpty(),TEXT("catch retires projectile and clears away state"));
            Tool->ThunderCatchStartedAt=Tool->RuneboundClock()-.61;Tool->PresentThunderCatch(0.f);
            Check(Tool->ThunderCatchAge<0.f&&!Tool->IsEquipping(),TEXT("catch finishes without leaving an action lock"));
        }
        auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("failed"),Failed);Result->SetArrayField(TEXT("checks"),Rows);
        Result->SetBoolField(TEXT("user_profile_modified"),false);Result->SetBoolField(TEXT("visual_tested"),false);
        FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));
        FString Out=FPaths::ProjectSavedDir()/TEXT("ThunderHammerSwitchAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
        FFileHelper::SaveStringToFile(Text,*Out);
        Tool->CancelUse();PC->UnPossess();Pawn->Destroy();PC->Destroy();
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
        return Failed?1:0;
    }
    // Explicitly requested preview diagnosis, isolated from recall/damage tests.
    if(FParse::Param(*Params,TEXT("PreviewOnly")))
    {
        Pawn->SetActorLocation(FVector(10000,20000,100));
        PC->SetControlRotation(FRotator::ZeroRotator);
        Pawn->FindComponentByClass<UCameraComponent>()->SetWorldRotation(FRotator::ZeroRotator);
        auto* Ground=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Ground);
        Ground->AddInstanceComponent(Box);Ground->SetRootComponent(Box);Box->SetBoxExtent(FVector(5000,5000,20));
        Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Block);
        Box->RegisterComponent();Ground->SetActorLocation(FVector(10000,20000,-20));
        Tool->BeginPrimaryAttack();
        Check(Tool->bBluntCharging&&Tool->bThunderThrowSeat,TEXT("preview charge starts with installed seat"));
        Tool->BluntChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds-.01;
        Tool->TickThunderThrow(.06f);
        auto Result=MakeShared<FJsonObject>();
        Result->SetNumberField(TEXT("charge_fraction"),Tool->HeavyChargeFraction());
        Result->SetBoolField(TEXT("can_use"),Tool->CanUse());
        Result->SetNumberField(TEXT("stamina"),Model->Stamina());
        Result->SetNumberField(TEXT("release_cost"),Tool->ToolStats.HeavyReleaseStaminaCost);
        Result->SetNumberField(TEXT("path_points"),Tool->ThunderPreviewPoints.Num());
        if(auto* Lines=Tool->ThunderPreview.Get())
        {
            Lines->UpdateBounds();
            Result->SetNumberField(TEXT("drawn_lines"),Lines->BatchedLines.Num());
            Result->SetBoolField(TEXT("registered"),Lines->IsRegistered());
            Result->SetBoolField(TEXT("visible"),Lines->IsVisible());
            Result->SetBoolField(TEXT("hidden_in_game"),Lines->bHiddenInGame);
            Result->SetBoolField(TEXT("owner_hidden"),Pawn->IsHidden());
            Result->SetBoolField(TEXT("owner_no_see"),Lines->bOwnerNoSee);
            Result->SetBoolField(TEXT("only_owner_see"),Lines->bOnlyOwnerSee);
            Result->SetBoolField(TEXT("use_editor_compositing"),Lines->bUseEditorCompositing);
            Result->SetStringField(TEXT("bounds_origin"),Lines->Bounds.Origin.ToString());
            Result->SetStringField(TEXT("bounds_extent"),Lines->Bounds.BoxExtent.ToString());
            Check(!Lines->BatchedLines.IsEmpty(),TEXT("fully charged preview produces line segments"));
        }
        else Check(false,TEXT("fully charged preview creates line component"));
        if(!Tool->ThunderPreviewPoints.IsEmpty())
        {
            Result->SetStringField(TEXT("path_start"),Tool->ThunderPreviewPoints[0].ToString());
            Result->SetStringField(TEXT("path_end"),Tool->ThunderPreviewPoints.Last().ToString());
        }
        Result->SetStringField(TEXT("camera"),Pawn->FindComponentByClass<UCameraComponent>()->GetComponentLocation().ToString());
        if(FParse::Param(*Params,TEXT("PreviewRender"))&&Tool->ThunderPreview)
        {
            auto* Capture=NewObject<USceneCaptureComponent2D>(Pawn);Pawn->AddInstanceComponent(Capture);
            Capture->bCaptureEveryFrame=false;Capture->bCaptureOnMovement=false;
            Capture->CaptureSource=ESceneCaptureSource::SCS_FinalColorLDR;Capture->FOVAngle=90.f;
            auto* Target=NewObject<UTextureRenderTarget2D>(Capture);Target->ClearColor=FLinearColor::Black;
            Target->InitCustomFormat(960,540,PF_B8G8R8A8,false);Target->UpdateResourceImmediate(true);Capture->TextureTarget=Target;
            Capture->RegisterComponent();Capture->SetWorldLocation(Pawn->FindComponentByClass<UCameraComponent>()->GetComponentLocation());
            Capture->SetWorldRotation(FRotator::ZeroRotator);
            Capture->ShowFlags.SetAtmosphere(false);Capture->ShowFlags.SetFog(false);Capture->ShowFlags.SetAntiAliasing(false);
            Capture->ShowFlags.SetPostProcessing(false);Capture->ShowFlags.SetCompositeDebugPrimitives(true);
            Capture->PrimitiveRenderMode=ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
            Capture->ShowOnlyComponent(Tool->ThunderPreview);
            World->SendAllEndOfFrameUpdates();FlushRenderingCommands();
            Capture->CaptureScene();FlushRenderingCommands();
            TArray<FColor> Pixels;Target->GameThread_GetRenderTargetResource()->ReadPixels(Pixels);
            int32 Red=0;for(const auto& Pixel:Pixels)if(Pixel.R>30&&Pixel.R>Pixel.G*2&&Pixel.R>Pixel.B*2)++Red;
            Result->SetNumberField(TEXT("rendered_red_pixels"),Red);
            Check(Red>10,TEXT("trajectory renders red pixels in game scene capture"),Red);
            Capture->DestroyComponent();
        }
        // The same real trajectory collapses to a short segment near a ledge.
        // Exercise its production draw path, not a replica of the fade formula.
        Ground->SetActorLocation(FVector(10000,20000,114));
        Tool->TickThunderThrow(.06f);
        const auto HasVisibleLines=[&]()
        {
            return Tool->ThunderPreview&&Tool->ThunderPreview->BatchedLines.ContainsByPredicate(
                [](const FBatchedLine& L){return L.Color.A>.05f&&FVector::DistSquared(L.Start,L.End)>1.;});
        };
        Check(HasVisibleLines(),TEXT("nearby landing retains visible aim geometry"));
        Result->SetNumberField(TEXT("near_path_points"),Tool->ThunderPreviewPoints.Num());
        TObjectPtr<ULineBatchComponent> LegacyNear;
        FPSMagicPreview::BeginRefresh(LegacyNear,Ground);
        FPSMagicPreview::DrawPath(LegacyNear,Tool->ThunderPreviewPoints);
        int32 LegacyVisible=0;for(const auto& L:LegacyNear->BatchedLines)if(L.Color.A>.05f)++LegacyVisible;
        Result->SetNumberField(TEXT("legacy_near_visible_segments"),LegacyVisible);
        LegacyNear->DestroyComponent();
        Ground->SetActorLocation(FVector(10000,20000,-20));
        PC->SetControlRotation(FRotator(-90,0,0));Pawn->FindComponentByClass<UCameraComponent>()->SetWorldRotation(FRotator(-90,0,0));
        Tool->TickThunderThrow(.06f);
        const FBox DownBounds=Tool->ThunderPreview->CalcBounds(FTransform::Identity).GetBox();
        Check(HasVisibleLines()&&DownBounds.GetSize().Y>30.,TEXT("vertical aim has a visible landing marker"),DownBounds.GetSize().Y);
        Tool->BluntChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds*.5;
        Tool->TickThunderThrow(.06f);
        Check(Tool->ThunderPreview->BatchedLines.IsEmpty(),TEXT("partial charge has no throw indicator"));
        Tool->BluntChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds-.01;
        auto LowStamina=Model->Snapshot();LowStamina.Stamina=1;Model->AdoptNetMirror(LowStamina);
        Tool->TickThunderThrow(.06f);
        Check(Tool->ThunderPreview->BatchedLines.IsEmpty(),TEXT("insufficient release stamina hides indicator"));
        LowStamina.Stamina=100;Model->AdoptNetMirror(LowStamina);Tool->TickThunderThrow(.06f);
        Check(HasVisibleLines(),TEXT("ready charge restores indicator"));
        Tool->CancelUse();
        Check(Tool->ThunderPreview->BatchedLines.IsEmpty(),TEXT("cancel clears indicator immediately"));
        Tool->bThunderThrowSeat=false;Tool->bBluntCharging=true;Tool->TickThunderThrow(.06f);
        Check(Tool->ThunderPreview->BatchedLines.IsEmpty(),TEXT("factory hammer does not show throw indicator"));
        Result->SetNumberField(TEXT("failed"),Failed);Result->SetArrayField(TEXT("checks"),Rows);
        FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));
        FString Out=FPaths::ProjectSavedDir()/TEXT("ThunderHammerPreviewAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
        FFileHelper::SaveStringToFile(Text,*Out);
        Tool->CancelUse();Ground->Destroy();PC->UnPossess();Pawn->Destroy();PC->Destroy();
        GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
        return Failed?1:0;
    }
    FActorSpawnParameters Spawn;Spawn.Owner=Pawn;Spawn.Instigator=Pawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    // Execute the production path at four frame rates, three ranges, and a moving/turning owner.
    for(int32 FPS:{15,30,60,120})for(float Distance:{200.f,1500.f,5000.f})for(bool Moving:{false,true})
    {
        Pawn->SetActorLocation(FVector::ZeroVector);Pawn->SetActorRotation(FRotator::ZeroRotator);PC->SetControlRotation(FRotator::ZeroRotator);
        Tool->CurrentMotion=nullptr;
        auto* Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(Distance,0,36),FRotator::ZeroRotator,Spawn);
        Hammer->Weapon=Item;Hammer->Phase=1;Hammer->Recall();
        Check(Hammer->RecallShot.DamagePanel.BaseMagic==0.&&Hammer->RecallShot.DamagePanel.AddedMagic==0.,TEXT("return snapshot contains physical damage only"));
        Hammer->RecallShot.DamagePanel={};const float Delta=1.f/FPS;float Age=0.f;
        while(Hammer->Phase==2&&Age<5.f)
        {
            Age+=Delta;Hammer->RecallAt=Hammer->Clock()-Age;
            if(Moving){Pawn->SetActorLocation(FVector(0,600.f*Age,0));PC->SetControlRotation(FRotator(0,120.f*Age,0));Pawn->SetActorRotation(PC->GetControlRotation());}
            Hammer->AdvanceRecall(Delta);
        }
        const FString Label=FString::Printf(TEXT("%dfps %.0fcm %s"),FPS,Distance,Moving?TEXT("moving_turning"):TEXT("stationary"));
        const auto Hand=ThunderHammerThrow::CatchFrame(Pawn);
        Check(Hammer->Phase==3&&FVector::Distance(Hammer->GetActorLocation(),Hand.GetLocation())<.02,TEXT("reaches actual hand ")+Label,Age);
        // Distance-dependent speed is intentional: all ranges share one arrival deadline.
        Check(FMath::Abs(Hammer->RecallDuration-1.f)<.001f&&Age>=1.f-.001f&&Age<=1.f+Delta+.001f,
            TEXT("fixed one-second recall ")+Label,Age);
        Check(FMath::RadiansToDegrees(Hammer->RecallRotation().AngularDistance(Hand.GetRotation()))<.01,TEXT("whole-turn orientation closes at palm ")+Label);
        Hammer->Destroy();
    }
    Pawn->SetActorLocation(FVector::ZeroVector);Pawn->SetActorRotation(FRotator::ZeroRotator);PC->SetControlRotation(FRotator::ZeroRotator);
    auto* Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(1000,0,36),FRotator::ZeroRotator,Spawn);
    Hammer->Weapon=Item;Hammer->Phase=1;Hammer->Recall();Hammer->RecallShot.CriticalChance=0;
    FActorSpawnParameters EnemySpawn;EnemySpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    EnemySpawn.CustomPreSpawnInitialization=[](AActor* A){CastChecked<ACharacter>(A)->AutoPossessAI=EAutoPossessAI::Disabled;};
    auto* Target=World->SpawnActor<ANurseZombie>(FVector(500,0,0),FRotator::ZeroRotator,EnemySpawn);Target->Health=Target->MaxHealth=100000.f;
    const float Before=Target->Health;Hammer->HitRecallSegment(FVector(250,0,60),FVector(750,0,60));const float Once=Target->Health;
    Hammer->HitRecallSegment(FVector(750,0,60),FVector(250,0,60));
    Check(Once<Before&&Target->Health==Once&&Hammer->RecallHits.Num()==1,TEXT("repeated path hurts each target once"),Before-Once);
    Target->Tags.Add(TEXT("Companion"));Hammer->RecallHits.Reset();
    Hammer->HitRecallSegment(FVector(250,0,60),FVector(750,0,60));
    Check(Target->Health==Once&&Hammer->RecallHits.IsEmpty(),TEXT("recall excludes companion before hit receipt"));
    auto* Wave=World->SpawnActor<AWarhammerShockwave>(FVector(500,0,0),FRotator::ZeroRotator,Spawn);
    Wave->Setup(Hammer->RecallShot,300.f,1.5f,100.f);
    Check(Target->Health==Once,TEXT("native lightning and physical heavy exclude companion"));Wave->Destroy();
    auto* Far=World->SpawnActor<AThunderHammerThrown>(FVector(6100,0,36),FRotator::ZeroRotator,Spawn);
    Far->Weapon=Item;Far->Phase=1;Far->Recall();
    Check(Far->RecallShot.DamagePanel.Total()==0.,TEXT("over sixty metres recall has no damage or hit procs"));Far->Destroy();
    auto* Lost=World->SpawnActor<AThunderHammerThrown>(FVector(0,0,World->GetWorldSettings()->KillZ-100.f),FRotator::ZeroRotator,Spawn);
    Lost->Weapon=Item;Lost->Phase=0;Lost->OwnerCheck=1.f;Lost->PostInitializeComponents();Lost->DispatchBeginPlay();
    Tool->ThrownHammer=Lost;Tool->ThunderAwayInstance=Item.InstanceId;Lost->Tick(.016f);
    Check(Lost->IsActorBeingDestroyed()&&Tool->ThunderAwayInstance.IsEmpty(),TEXT("void flight retires representation and restores equipment"));
    Target->Tags.Remove(TEXT("Companion"));
    auto RuneItem=Item;auto RuneData=Data;auto RuneParts=Parts;
    const auto SetRune=[&](const TCHAR* Rune,const TCHAR* Pommel)
    {
        RuneParts->SetStringField(TEXT("rune"),Rune);RuneParts->SetStringField(TEXT("pommel"),Pommel);
        RuneItem.Data.Reset();FJsonSerializer::Serialize(RuneData.ToSharedRef(),TJsonWriterFactory<>::Create(&RuneItem.Data));
    };
    auto Spell=Model->LightningStats();const float OriginalStun=Spell.OverloadStun;
    SetRune(ThunderHammerRunes::Thunder,TEXT(""));ThunderHammerRunes::Configure(Spell,&RuneItem);
    Check(Spell.RuneElectrifyChance==.5f&&!Spell.bEchoRune,TEXT("LeiMing configures one fifty-percent contact roll"));
    SetRune(ThunderHammerRunes::Echo,ThunderHammerPommel::LeiXi);ThunderHammerRunes::Configure(Spell,&RuneItem);
    ThunderHammerRunes::Configure(Spell,&RuneItem);
    Check(FMath::IsNearlyEqual(Spell.OverloadStun,OriginalStun+.25f)&&Spell.OverloadRetainedStacks==2&&Spell.OverloadStacks==5,
        TEXT("Echo threshold five retains two and adds quarter-second once"));
    auto RuneShot=Hammer->RecallShot;RuneShot.HammerLightning=Spell;
    auto* Status=UCombatStatusFormula::GetOrAdd(Target);
    ThunderHammerRunes::ApplyStacks(Pawn,Target,RuneShot,2);
    Check(Status->ElectrifiedCount()==2&&!Status->IsStunned(),TEXT("two native stacks alone do not overload"));
    ThunderHammerRunes::ApplyStacks(Pawn,Target,RuneShot,3);
    Check(Status->ElectrifiedCount()==2&&Status->IsStunned(),TEXT("fifth stack overload stuns and Echo retains two"));
    Status->TickComponent(OriginalStun+.24f,LEVELTICK_All,nullptr);
    Check(Status->IsStunned(),TEXT("Echo stun lasts original plus quarter second"));
    Status->TickComponent(.02f,LEVELTICK_All,nullptr);
    Check(!Status->IsStunned(),TEXT("Echo stun expires at extended duration"));
    auto* OwnerStatus=UCombatStatusFormula::GetOrAdd(Pawn);
    ThunderHammerPommel::ConfirmElectricDamage(Pawn,Spell,0.f);
    Check(OwnerStatus->MagicInspirationAttackSpeed()==1.f,TEXT("zero electric damage cannot grant inspiration"));
    ThunderHammerPommel::ConfirmElectricDamage(Pawn,Spell,10.f);
    Check(OwnerStatus->MagicInspirationAttackSpeed()==1.25f,TEXT("LeiXi grants existing inspiration buff"));
    OwnerStatus->TickComponent(9.f,LEVELTICK_All,nullptr);ThunderHammerPommel::ConfirmElectricDamage(Pawn,Spell,10.f);
    OwnerStatus->TickComponent(2.f,LEVELTICK_All,nullptr);
    Check(OwnerStatus->MagicInspirationAttackSpeed()==1.25f,TEXT("repeat electric hit refreshes duration without stacking"));
    OwnerStatus->TickComponent(8.1f,LEVELTICK_All,nullptr);
    Check(OwnerStatus->MagicInspirationAttackSpeed()==1.f,TEXT("inspiration expires ten seconds after latest hit"));
    ThunderHammerRunes::Configure(Spell,&Item);
    Check(Spell.RuneElectrifyChance==0.f&&!Spell.bEchoRune&&!Spell.bLeiXiPommel&&FMath::IsNearlyEqual(Spell.OverloadStun,OriginalStun),TEXT("rebinding factory removes exclusive modifiers"));
    Target->Destroy();
    Tool->ThrownHammer=Hammer;Tool->ThunderAwayInstance=Item.InstanceId;Tool->bThunderRecallPending=true;
    Tool->PresentThunderCatch(1.f);FTransform Ready;Check(Tool->GetThunderCatchFrame(Ready),TEXT("extended palm supplies live contact frame"));
    Hammer->Phase=3;Hammer->CaughtAt=Hammer->Clock()-.11;Hammer->OwnerCheck=1.f;
    // The fixture world is intentionally not playing. RouteEndPlay requires
    // both component initialization and BeginPlay, just as a real spawn does.
    Hammer->PostInitializeComponents();Hammer->DispatchBeginPlay();
    Tool->TickComponent(0.f,LEVELTICK_All,nullptr);const auto FrameBefore=ThunderHammerThrow::CatchFrame(Pawn,Hammer->CatchAge());
    Check(!Tool->ToolMesh->IsVisible(),TEXT("held mesh hidden while flying assembly occupies hand"));
    Hammer->Tick(0.f);
    Check(Hammer->IsActorBeingDestroyed(),TEXT("projectile retires at authored attach time"),Hammer->CatchAge());
    Check(!Tool->IsThunderHammerAway()&&Tool->ThunderCatchAge>=.1f,TEXT("authority catch hands off during recovery"),Tool->ThunderCatchAge);
    Check(Tool->ToolMesh->IsVisible(),TEXT("held mesh visible on same frame as projectile retirement"));
    FTransform After;Tool->GetThunderCatchFrame(After);
    Check(FVector::Distance(FrameBefore.GetLocation(),After.GetLocation())<.02,TEXT("assembly handoff keeps identical contact frame"));
    Tool->ThunderCatchStartedAt=Tool->RuneboundClock()-.61;Tool->PresentThunderCatch(0.f);
    Check(Tool->ThunderCatchAge<0.f,TEXT("catch recovery finishes and releases action lock"));
    const auto StoredSeed=Model->Snapshot();
    for(int32 Scenario=0;Scenario<4;++Scenario)
    {
        Model->AdoptNetMirror(StoredSeed);
        auto* Health=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();Health->Health=100;
        auto* Grounded=World->SpawnActor<AThunderHammerThrown>(FVector(1000,0,36),FRotator::ZeroRotator,Spawn);
        Grounded->Weapon=Item;Grounded->Phase=1;Grounded->StartedAt=Grounded->Clock()-3600.;Grounded->PostInitializeComponents();Grounded->DispatchBeginPlay();
        Tool->ThrownHammer=Grounded;Tool->ThunderAwayInstance=Item.InstanceId;
        Grounded->Tick(.21f);
        Check(!Grounded->IsActorBeingDestroyed()&&Grounded->IsGrounded(),TEXT("ground hammer persists without a recall timeout"));
        auto Changed=StoredSeed;
        if(Scenario==0){for(auto& I:Changed.Items)if(I.InstanceId==Item.InstanceId){I.Place=0;I.Cell=0;}}
        if(Scenario==1)Changed.Items.RemoveAll([&](const auto& I){return I.InstanceId==Item.InstanceId;});
        if(Scenario<2){Model->AdoptNetMirror(Changed);Tool->CommitThunderEquipmentChange(Changed);}
        else if(Scenario==2){Health->Health=0;Grounded->Tick(.21f);}
        else Grounded->EndPlay(EEndPlayReason::LevelTransition);
        Check(!Tool->ThrownHammer&&Tool->ThunderAwayInstance.IsEmpty(),FString::Printf(TEXT("cleanup clears equipment state scenario %d (bag/removed/death/level end)"),Scenario));
        if(!Grounded->IsActorBeingDestroyed())Grounded->Destroy();
    }
    Model->AdoptNetMirror(StoredSeed);
    auto Result=MakeShared<FJsonObject>();Result->SetNumberField(TEXT("failed"),Failed);Result->SetArrayField(TEXT("checks"),Rows);
    FString Text;FJsonSerializer::Serialize(Result,TJsonWriterFactory<>::Create(&Text));
    FString Out=FPaths::ProjectSavedDir()/TEXT("ThunderHammerRecallAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FFileHelper::SaveStringToFile(Text,*Out);
    PC->UnPossess();Pawn->Destroy();PC->Destroy();GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);return Failed?1:0;
}
