#include "WarhammerNetworkAuditCommandlet.h"
#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "ThunderHammerTuning.h"
#include "ThunderHammerStaticField.h"
#include "ThunderHammerCoil.h"
#include "ThunderHammerRunes.h"
#include "ThunderHammerZhenTing.h"
#include "ThunderHammerThrown.h"
#include "WarhammerShockwave.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Weapons/FPSMeleeLightningComponent.h"
#include "../Weapons/RuneSwordMeshComponent.h"
#include "../Weapons/WeaponGripProfile.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/NetDriver.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 UWarhammerNetworkAuditCommandlet::AuditConductiveGrips(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Conductive_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ConductiveGripAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit())return 2;
    World->InitializeActorsForPlay(FURL());
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("CONDUCTIVE_GRIP %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    const auto Pump=[&](float Seconds){++GFrameCounter;World->GetTimerManager().Tick(Seconds);};Pump(.001f);
    auto* FloorActor=World->SpawnActor<AActor>();auto* Floor=NewObject<UBoxComponent>(FloorActor);
    FloorActor->AddInstanceComponent(Floor);FloorActor->SetRootComponent(Floor);Floor->SetBoxExtent(FVector(6000,6000,20));
    Floor->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Floor->SetCollisionResponseToAllChannels(ECR_Block);
    Floor->RegisterComponent();FloorActor->SetActorLocation(FVector(0,0,-20));
    auto Item=Host->CreateItem(ThunderHammer::Definition);Item.Place=1;Item.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
    auto Seed=Host->Snapshot();Seed.Items={Item};Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.Stamina=150;Seed.Mana=200;
    Seed.Skills.FindOrAdd(Host->LightningDefinition().Id).Level=1;
    const auto Equip=[&](UColdSteelStatusModel* Model,const TCHAR* Grip,const TCHAR* Seat=TEXT(""))
    {
        Parts->SetStringField(TEXT("grip"),Grip);Parts->SetStringField(TEXT("head_mount"),Seat);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        Seed.Items={Item};Model->AdoptNetMirror(Seed);
    };
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(-500,0,100),FRotator::ZeroRotator);
    auto* PC=World->SpawnActor<APlayerController>();auto* HostPS=World->SpawnActor<AColdSteelPlayerState>();
    HostPS->SetOwner(PC);PC->SetPlayerState(HostPS);PC->SetAsLocalPlayerController();PC->Possess(Pawn);Pawn->SetPlayerState(HostPS);Host->AttachPawn(Pawn);
    // No full inventory equip tick runs in this fixture. Retire the constructor's
    // default rifle and supply the PlayerState required by UE 5.8 IsPlayerControlled.
    Pawn->bInventoryWeaponReady=false;
    Check(Pawn->IsPlayerControlled()&&Pawn->IsLocallyControlled(),TEXT("local fixture has player identity and hammer equipment"));
    Pawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health=100;
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;Tool->Kind=TEXT("warhammer");
    Tool->EquippedId=Item.InstanceId;Tool->bUsesArms=false;
    Tool->ToolMesh=NewObject<UStaticMeshComponent>(Pawn);Tool->ToolMesh->SetStaticMesh(NewObject<UStaticMesh>());
    auto* Lightning=Pawn->FindComponentByClass<UFPSMeleeLightningComponent>();
    const auto ResetLocal=[&](const TCHAR* Grip,bool Heavy,const TCHAR* Seat=TEXT(""))
    {
        Equip(Host,Grip,Seat);Tool->CancelUse();Tool->Elapsed=Tool->EquipElapsed=-1.f;Tool->bBluntCharging=false;
        Tool->bBluntReturningCharge=false;Tool->bBluntReleaseCharge=Heavy;Tool->bBluntHeavy=Heavy;Tool->bBluntSprintAttack=false;
        Tool->BluntServerReadyAt=0.;Lightning->Waves.Reset();
    };
    ResetLocal(ThunderHammerCoil::Grip,true);const auto Base=ColdSteelTool::Evaluate(Item,Host);
    Tool->BeginUse();Check(Lightning->Waves.Num()==1,FString::Printf(TEXT("standalone heavy releases exactly one coil bolt (actual %d, throw %d, call %d)"),Lightning->Waves.Num(),Tool->bThunderThrowSeat,Tool->bThunderCallSeat));
    Check(Tool->AxeStrike.bHammerCoil&&FMath::IsNearlyEqual(Tool->AxeStrike.HammerCoilLightning.Damage,Host->LightningStats(10,false).Damage),TEXT("coil minimum level is ten"));
    ResetLocal(ThunderHammerCoil::Grip,false);Tool->BeginUse();Check(Lightning->Waves.IsEmpty(),TEXT("ordinary swing cannot release heavy coil proc"));
    Equip(Host,TEXT(""));const auto Factory=ColdSteelTool::Evaluate(Item,Host);
    Check(FMath::IsNearlyEqual(Base.RateScale/Factory.RateScale,1.1,.001),TEXT("coil passive attack speed plus ten percent"));
    Check(FMath::IsNearlyEqual(Base.HeavyChargeSeconds*1.15,Factory.HeavyChargeSeconds,.001),TEXT("coil passive charge speed plus fifteen percent"));
    Equip(Host,ThunderHammerStaticField::Grip);const auto Field=ColdSteelTool::Evaluate(Item,Host);
    Check(FMath::IsNearlyEqual(Field.PhysicalAttack-Factory.PhysicalAttack,5.,.001),TEXT("static field passive physical attack plus five"));
    Check(FMath::IsNearlyEqual(Field.HeavyChargeSeconds*1.15,Factory.HeavyChargeSeconds,.001),TEXT("static field passive charge speed plus fifteen percent"));

    // Real engine listen-server branch, but deliberately no socket/remote peer.
    auto* Driver=NewObject<UNetDriver>(World,LoadClass<UNetDriver>(nullptr,TEXT("/Script/OnlineSubsystemUtils.IpNetDriver")));
    const bool WasClient=GIsClient;GIsClient=true;Driver->SetWorld(World);World->SetNetDriver(Driver);
    Check(World->GetNetMode()==NM_ListenServer,TEXT("listen-server execution mode"));
    uint32 Attack=100;
    ResetLocal(ThunderHammerCoil::Grip,true);Tool->BluntAttackId=++Attack;Tool->ServerBeginBluntCharge_Implementation(Attack);
    Tool->BluntServerChargeStartedAt=-100.;Tool->BeginUse();
    Check(Lightning->Waves.Num()==1,FString::Printf(TEXT("listen host prediction and authority release only one coil bolt (actual %d, throw %d, call %d)"),Lightning->Waves.Num(),Tool->bThunderThrowSeat,Tool->bThunderCallSeat));
    Tool->ServerBeginBluntAttack_Implementation(Attack,true,false);
    Check(Lightning->Waves.Num()==1,TEXT("duplicate charged release cannot repeat coil proc"));
    ResetLocal(ThunderHammerCoil::Grip,true);Tool->BluntAttackId=++Attack;Tool->bBluntServerCharging=false;Tool->BeginUse();
    Check(Lightning->Waves.IsEmpty(),TEXT("rejected host release cannot proc from prediction"));
    FActorSpawnParameters EnemySpawn;EnemySpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    EnemySpawn.CustomPreSpawnInitialization=[](AActor* A){CastChecked<ACharacter>(A)->AutoPossessAI=EAutoPossessAI::Disabled;};
    auto* Target=World->SpawnActor<ANurseZombie>(FVector(500,0,100),FRotator::ZeroRotator,EnemySpawn);
    Target->Health=Target->MaxHealth=100000.f;
    ResetLocal(ThunderHammerStaticField::Grip,true);Tool->BluntAttackId=++Attack;Tool->ServerBeginBluntCharge_Implementation(Attack);
    Tool->BluntServerChargeStartedAt=-100.;Tool->BeginUse();
    auto* Status=UCombatStatusFormula::GetOrAdd(Target);
    Check(Status->ElectrifiedCount()==2,TEXT("listen host adds two stacks once, not four"));
    Check(!UFPSMeleeLightningComponent::IsEnemy(Pawn,Pawn),TEXT("static field excludes owner"));
    Target->Destroy();Tool->CancelUse();

    auto* Guest=Host->CreateShadowModel(Seed);auto* GuestPC=World->SpawnActor<AWarhammerAuditRemoteController>();
    auto* GuestPS=World->SpawnActor<AColdSteelPlayerState>();auto* GuestPawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,1000,100),FRotator::ZeroRotator);
    GuestPS->SetOwner(GuestPC);GuestPS->ShadowModel=Guest;GuestPC->SetPlayerState(GuestPS);GuestPC->Possess(GuestPawn);GuestPawn->SetPlayerState(GuestPS);
    GuestPawn->NetShadowProfile=Guest;Guest->AttachPawn(GuestPawn);GuestPawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health=100;
    auto* GuestTool=GuestPawn->FindComponentByClass<UProductionToolComponent>();GuestTool->Character=GuestPawn;GuestTool->Kind=TEXT("warhammer");GuestTool->EquippedId=Item.InstanceId;
    auto* GuestLightning=GuestPawn->FindComponentByClass<UFPSMeleeLightningComponent>();
    Seed.Skills.FindOrAdd(Host->LightningDefinition().Id).Level=17;Equip(Guest,ThunderHammerCoil::Grip);
    const auto HostBefore=Host->Snapshot();GuestTool->ServerBeginBluntCharge_Implementation(++Attack);GuestTool->BluntServerChargeStartedAt=-100.;
    GuestTool->ServerBeginBluntAttack_Implementation(Attack,true,false);
    Check(ColdSteelAuthority::ForPawn(GuestPawn)==Guest,TEXT("remote authority resolves guest shadow profile"));
    Check(GuestLightning->Waves.Num()==1,TEXT("guest heavy queues one authoritative bolt"));
    Check(Guest->LightningProgress().Level==17&&FMath::IsNearlyEqual(GuestTool->AxeStrike.HammerCoilLightning.Damage,Guest->LightningStats(17,false).Damage),TEXT("guest coil uses own level seventeen damage snapshot"));
    Check(Host->Stamina()==HostBefore.Stamina&&Host->Mana()==HostBefore.Mana,TEXT("guest heavy does not spend host resources"));
    Check(Guest->Mana()==Seed.Mana&&Guest->LightningCooldown()==Seed.LightningCooldown,TEXT("coil does not spend active lightning mana or cooldown"));
    GuestTool->CancelUse();

    FActorSpawnParameters Spawn;Spawn.Owner=GuestPawn;Spawn.Instigator=GuestPawn;Spawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    const auto ShotFor=[&](const TCHAR* Grip,const TCHAR* Seat)
    {
        Equip(Guest,Grip,Seat);auto Shot=ColdSteelSkills::Snapshot(GuestPawn,&Item);
        ThunderHammerStaticField::Commit(Shot,&Item);ThunderHammerCoil::Commit(Shot,&Item,Guest);return Shot;
    };
    for(const TCHAR* Grip:{ThunderHammerCoil::Grip,ThunderHammerStaticField::Grip})
    {
        const bool Coil=FString(Grip)==ThunderHammerCoil::Grip;const FString Label=Coil?TEXT("coil"):TEXT("static field");
        auto Shot=ShotFor(Grip,TEXT("guan_lei_seat"));
        auto* Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(0,1000,100),FRotator::ZeroRotator,Spawn);
        Hammer->Launch(Item,Shot,50.f);
        auto Active=[&](){return World->GetTimerManager().IsTimerActive(Coil?Hammer->CoilTimer:Hammer->StaticFieldTimer);};
        Check(Active(),Label+TEXT(" thrown periodic timer starts"));
        Check(FMath::IsNearlyEqual(World->GetTimerManager().GetTimerRate(Coil?Hammer->CoilTimer:Hammer->StaticFieldTimer),Coil?6.f:3.f),Label+TEXT(" periodic interval matches specification"));
        auto Switched=Guest->Snapshot();Switched.ActiveWeaponSlot=9;Guest->AdoptNetMirror(Switched);
        if(Coil)Hammer->PulseCoil();else Hammer->PulseStaticField();
        Check(Active(),Label+TEXT(" stays active across weapon switching while equipped"));
        Equip(Guest,TEXT(""),TEXT("guan_lei_seat"));
        if(Coil)Hammer->PulseCoil();else Hammer->PulseStaticField();
        Check(!Active(),Label+TEXT(" stops after grip removal"));Hammer->Destroy();
        Shot=ShotFor(Grip,TEXT("guan_lei_seat"));Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(0,1000,100),FRotator::ZeroRotator,Spawn);
        Hammer->Launch(Item,Shot,50.f);Hammer->Phase=1;Hammer->Recall();
        Check(Hammer->IsReturning()&&!Active(),Label+TEXT(" stops as recall starts"));Hammer->Destroy();
        Shot=ShotFor(Grip,TEXT("guan_lei_seat"));Hammer=World->SpawnActor<AThunderHammerThrown>(FVector(0,1000,100),FRotator::ZeroRotator,Spawn);
        Hammer->Launch(Item,Shot,50.f);auto Removed=Guest->Snapshot();Removed.Items[0].Place=0;Guest->AdoptNetMirror(Removed);
        if(Coil)Hammer->PulseCoil();else Hammer->PulseStaticField();
        Check(!Active(),Label+TEXT(" stops when weapon leaves equipment"));Hammer->Destroy();
    }
    GuestLightning->Waves.Reset();auto CallShot=ShotFor(ThunderHammerCoil::Grip,TEXT("ji_lei_seat"));
    CallShot.ZhenTingForward=FVector::ForwardVector;
    auto* Wave=World->SpawnActor<AWarhammerShockwave>(FVector(0,1000,8),FRotator::ZeroRotator,Spawn);
    Wave->Setup(CallShot,300.f,1.5f,50.f,true);
    Check(GuestLightning->Waves.Num()==2,TEXT("JiLei origin queues two coil bolts"));
    Pump(.26f);Check(GuestLightning->Waves.Num()==4,TEXT("first extra strike queues two bolts at 0.25s"));
    Pump(.25f);Check(GuestLightning->Waves.Num()==6,TEXT("second extra strike queues two bolts at 0.50s"));
    Pump(.25f);Check(GuestLightning->Waves.Num()==8,TEXT("third extra strike queues two bolts at 0.75s"));
    Check(GuestLightning->Waves.ContainsByPredicate([](const auto& W){return FMath::IsNearlyEqual(W.Chain->Radius,1000.f);}),TEXT("JiLei coil target radius is ten metres"));
    GuestLightning->ChainSystem=nullptr;const int32 BeforeArcs=GuestLightning->WorldArcs.Num();
    GuestLightning->ShowArc(FVector(0,0,100),FVector(100,0,100),CallShot.HammerCoilLightning,false);
    Check(GuestLightning->WorldArcs.Num()==BeforeArcs+1,TEXT("authority publishes arc before cosmetic asset load"));

    Parts->SetStringField(TEXT("rune"),ThunderHammerRunes::Echo);
    auto FieldShot=ShotFor(ThunderHammerStaticField::Grip,TEXT("ji_lei_seat"));FieldShot.ZhenTingForward=FVector::ForwardVector;
    TArray<ANurseZombie*> FieldTargets;
    for(int32 I=0;I<4;++I)
    {
        auto* Enemy=World->SpawnActor<ANurseZombie>(FVector(I*600.f,1950,100),FRotator::ZeroRotator,EnemySpawn);
        Enemy->Health=Enemy->MaxHealth=100000.f;FieldTargets.Add(Enemy);
    }
    auto* Outside=World->SpawnActor<ANurseZombie>(FVector(0,2300,100),FRotator::ZeroRotator,EnemySpawn);
    auto* FieldWave=World->SpawnActor<AWarhammerShockwave>(FVector(0,1000,8),FRotator::ZeroRotator,Spawn);
    FieldWave->Setup(FieldShot,300.f,1.5f,50.f,true);
    const auto Overloaded=[&](int32 I)
    {const auto* S=UCombatStatusFormula::GetOrAdd(FieldTargets[I]);return S->IsStunned()&&S->ElectrifiedCount()==2;};
    Check(Overloaded(0),TEXT("JiLei static field adds five stacks and preserves echo overload"));
    Check(!UCombatStatusFormula::GetOrAdd(Outside)->IsStunned(),TEXT("JiLei static field excludes targets outside ten metres"));
    Pump(.26f);Check(Overloaded(1),TEXT("first additional JiLei static field triggers at its own impact"));
    Pump(.25f);Check(Overloaded(2),TEXT("second additional JiLei static field triggers at its own impact"));
    Pump(.25f);Check(Overloaded(3),TEXT("third additional JiLei static field triggers at its own impact"));
    for(auto* Enemy:FieldTargets)Enemy->Destroy();Outside->Destroy();Parts->RemoveField(TEXT("rune"));

    World->SetNetDriver(nullptr);Driver->SetWorld(nullptr);GIsClient=WasClient;
    // The replicated equipment descriptor must carry the same saved grip layer.
    ResetLocal(ThunderHammerCoil::Grip,false);Tool->bUsesArms=true;
    auto* Arms=NewObject<URuneSwordMeshComponent>(Pawn);Tool->Viewmodel=Arms;
    Arms->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*ColdSteelInventory::Text(Item,TEXT("tool_viewmodel"))));
    auto* GripProfile=LoadObject<UWeaponGripProfile>(nullptr,TEXT("/Game/Weapons/ThunderGodHammer20261028/NormalGripFix20261031/DA_ThunderHammer_ConductiveGrip.DA_ThunderHammer_ConductiveGrip"));
    Arms->SetGripProfile(GripProfile);
    auto* Body=Pawn->FindComponentByClass<UFPSPlayerBodyComponent>();Body->Character=Pawn;Body->CaptureEquipment();
    UE_LOG(LogTemp,Display,TEXT("CONDUCTIVE_BODY tool=%d gun=%d loaded=%s mesh=%s count=%d"),Tool->IsEquipped(),Pawn->HasInventoryWeapon(),*GetPathNameSafe(GripProfile),*GetPathNameSafe(Arms->GetSkeletalMeshAsset()),Body->LocalWeapons.Num());
    for(const auto& W:Body->LocalWeapons)UE_LOG(LogTemp,Display,TEXT("CONDUCTIVE_BODY family=%s grip=%s"),*W.PoseFamily.ToString(),*W.GripProfile.ToSoftObjectPath().ToString());
    Check(GripProfile&&Body->LocalWeapons.ContainsByPredicate([&](const auto& W){return W.PoseFamily==TEXT("Tool")&&W.GripProfile.Get()==GripProfile;}),TEXT("body equipment carries conductive left-hand profile"));
    Check(Body->ReplicatedWeapons.ContainsByPredicate([&](const auto& W){return W.PoseFamily==TEXT("Tool")&&W.GripProfile.Get()==GripProfile;}),TEXT("replicated equipment carries conductive left-hand profile"));
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("count"),Rows.Num());Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetBoolField(TEXT("passed"),Failures==0);Report->SetBoolField(TEXT("user_profile_modified"),false);
    Report->SetBoolField(TEXT("real_network_transport_tested"),false);Report->SetBoolField(TEXT("visual_tested"),false);
    FString Out=FPaths::ProjectSavedDir()/TEXT("ConductiveGripAudit.json");FParse::Value(*Params,TEXT("Out="),Out);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures||!Saved?1:0;
}
