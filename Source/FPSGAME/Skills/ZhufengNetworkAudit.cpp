#include "SkillNetworkAuditCommandlet.h"
#include "ColdSteelSkillTypes.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/UppercutStaminaReceipt.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordComponent.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../Movement/FPSCharacterMovementComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Characters/FPSBodyRuneVisual.h"
#include "../Characters/FPSPlayerBodyTypes.h"
#include "Components/CapsuleComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

int32 USkillNetworkAuditCommandlet::RunZhufengAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get(),Slot=TEXT("SkillNetworkAudit_Zhufeng_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("ZhufengAuditWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("ZHUFENG_AUDIT %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Hotbar.Init(TEXT(""),4);Seed.HotbarDefinitions.Init(TEXT(""),4);for(auto& Binding:Seed.QuickBindings)Binding={};
    Seed.Stamina=150;Seed.bSprintExhausted=false;Seed.SwordUppercutCooldown=Seed.WhirlwindCooldown=0;
    Seed.UppercutStaminaSpent=0;Seed.DungeonRun={};Seed.NetworkProfileId=FGuid::NewGuid();
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Item=Host->CreateItem(TEXT("ue_zhanmadao"));Item.Place=1;Item.Cell=6;
    const auto SetBlade=[](FColdSteelItem& I,const FString& Blade,const FString& Rune=FString())
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("blade_1"),Blade);
        if(!Rune.IsEmpty())Parts->SetStringField(TEXT("blade_2"),Rune);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));
    };
    auto Factory=Item;SetBlade(Factory,TEXT("false"));SetBlade(Item,TEXT("zhufeng"));Seed.Items={Item};
    auto* Shadow=Host->CreateShadowModel(Seed);
    if(!Shadow){UE_LOG(LogTemp,Error,TEXT("ZHUFENG_AUDIT fixture profile rejected: %s"),*Host->ResultMessage());return 2;}
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,500),FRotator::ZeroRotator);
    PS->SetOwner(PC);PS->ShadowModel=Shadow;PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);
    Pawn->NetShadowProfile=Shadow;Shadow->CurrentPawn=Pawn;Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();Sword->Character=Pawn;Sword->InstanceId=Item.InstanceId;
    auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP->Health=HP->MaxHealth;
    auto* Move=CastChecked<UFPSCharacterMovementComponent>(Pawn->GetCharacterMovement());
    const float HostStamina=Host->Stamina();const auto Base=Shadow->Snapshot();
    const auto Reset=[&]()
    {
        PS->SettleSwordWhirlwind();Shadow->Current=Base;Shadow->CurrentPawn=Pawn;HP->Health=HP->MaxHealth;
        PS->WhirlwindDashReadyUntil=-1.;PS->WhirlwindSprintSeconds=0.f;PS->WhirlwindSprintWeapon=Item.InstanceId;
        Move->ServerMeleeRecoveryUntil=0.;Move->LastServerMeleeSequence=0;Move->bServerMeleeBlocked=false;
        Move->SetMovementMode(MOVE_Walking);Move->bWantsToSprint=false;Move->Velocity=FVector::ZeroVector;
    };
    const auto Charge=[&]()
    {
        Move->SetMovementMode(MOVE_Walking);Move->Velocity=FVector(300,0,0);Move->bWantsToSprint=true;
        PS->TickSwordWhirlwind(Shadow->DashAttackStats().ReadySeconds+.01f);
    };
    Check(Pawn->HasAuthority()&&!Pawn->IsLocallyControlled(),TEXT("fixture uses guest authority and guest shadow"));
    Shadow->Current.Items={Factory};const auto FactoryCast=Shadow->WhirlwindStats();const auto FactoryStats=ColdSteelMelee::Evaluate(Factory,Shadow);
    Shadow->Current.Items={Item};const auto Cast=Shadow->WhirlwindStats();const auto Stats=ColdSteelMelee::Evaluate(Item,Shadow);
    Check(FMath::IsNearlyEqual(Cast.DamageMultiplier,FactoryCast.DamageMultiplier+.5f)&&
        FMath::IsNearlyEqual(Shadow->WhirlwindStats(0).DamageMultiplier,Cast.DamageMultiplier),TEXT("whirlwind uses level-one floor plus additive 0.5"));
    Check(FMath::IsNearlyEqual(Cast.RadiusCM,FactoryCast.RadiusCM*1.2f),TEXT("Zhufeng radius includes 20 percent range"));
    Check(FMath::IsNearlyEqual(Stats.DamageParts.BasePhysical+Stats.DamageParts.AddedPhysical,
        (FactoryStats.DamageParts.BasePhysical+FactoryStats.DamageParts.AddedPhysical)*1.1),TEXT("Zhufeng physical channel gains 10 percent"));
    auto Beiwei=Item;SetBlade(Beiwei,TEXT("zhufeng"),TEXT("beiwei_rune"));Shadow->Current.Items={Beiwei};const auto Gold=Shadow->WhirlwindStats();
    Check(FMath::IsNearlyEqual(Gold.Damage,Cast.Damage*1.5f)&&FMath::IsNearlyEqual(Gold.RadiusCM,Cast.RadiusCM*1.25f),TEXT("Beiwei multiplies the upgraded whirlwind damage and radius once"));
    auto Red=Item;SetBlade(Red,TEXT("chixiao"));const auto RedStats=ColdSteelMelee::Evaluate(Red,Shadow);
    Check(FMath::IsNearlyEqual(RedStats.Modifiers.PhysicalDamage,1.1)&&FMath::IsNearlyEqual(RedStats.Modifiers.AttackSpeed,1.15)&&RedStats.Modifiers.WhirlwindDamageAdd==0,
        TEXT("Chixiao retains physical and speed passives without Zhufeng bonus"));
    Reset();uint32 Serial=0;
    Shadow->Current.Skills.FindChecked(TEXT("whirlwind")).Level=0;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,false,0,FVector::ForwardVector,false);
    Check(!PS->WhirlwindActiveSequence&&Shadow->Stamina()==Base.Stamina,TEXT("manual whirlwind rejects a zero-level request without payment"));
    Shadow->Current.Skills.FindChecked(TEXT("whirlwind")).Level=1;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,11,FVector::ForwardVector,false);
    Check(!PS->WhirlwindActiveSequence,TEXT("Zhufeng rejects unearned sprint readiness"));
    FFPSNetworkMoveData Movement;Movement.MeleeRequest.Sequence=11;Movement.MeleeRequest.Kind=EFPSMeleeMove::Zhufeng;
    Movement.MeleeRequest.Direction=FVector::ForwardVector;Movement.MeleeRequest.Distance=20;
    const FVector BeforePending=Pawn->GetActorLocation();Move->ProcessMeleeNetworkMove(Movement,true);
    Check(Pawn->GetActorLocation().Equals(BeforePending)&&Move->LastServerMeleeSequence==0,TEXT("movement arriving before cast waits without permanently rejecting sequence"));
    Charge();const float Cost=Shadow->WhirlwindStats().StaminaCost;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,11,FVector::ForwardVector,false);
    Check(PS->WhirlwindActiveSequence==Serial&&FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost)&&Shadow->WhirlwindCooldown()>0,
        TEXT("Zhufeng guest commits whirlwind cost and cooldown on authority"));
    Check(Host->Stamina()==HostStamina,TEXT("guest cast does not charge the host"));
    PS->ServerSwordWhirlwind_Implementation(Serial,Pawn,Item.InstanceId,true,11,FVector::ForwardVector,false);
    Check(FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost)&&FMath::IsNearlyEqual(Shadow->Current.UppercutStaminaSpent,double(Cost)),TEXT("duplicate start pays exactly once"));
    Check(Pawn->IsMeleeSkillMovementLocked(),TEXT("authority blocks ordinary locomotion during committed whirlwind"));
    FVector Heading;float Limit=0;
    Check(PS->SwordWhirlwindMove(11,Heading,Limit)&&Limit<PS->WhirlwindMoveSpeed*PS->WhirlwindMoveSeconds,
        TEXT("early movement allowance is elapsed-time bounded"));
    Move->SetMovementMode(MOVE_Falling);Movement.MeleeRequest.Direction=-FVector::ForwardVector;
    const FVector BeforeMove=Pawn->GetActorLocation();Move->ProcessMeleeNetworkMove(Movement,true);
    Check(Pawn->GetActorLocation().X>BeforeMove.X&&FMath::IsNearlyEqual(Pawn->GetActorLocation().Y,BeforeMove.Y),TEXT("accepted cast fixes direction even if a move packet changes it"));
    const FVector AfterMove=Pawn->GetActorLocation();Move->ProcessMeleeNetworkMove(Movement,true);
    Check(Pawn->GetActorLocation().Equals(AfterMove),TEXT("duplicate cumulative move cannot apply displacement twice"));
    Movement.MeleeRequest.Kind=EFPSMeleeMove::Dash;Movement.MeleeRequest.Distance+=20;Move->ProcessMeleeNetworkMove(Movement,true);
    Check(Pawn->GetActorLocation().Equals(AfterMove),TEXT("same move sequence cannot switch attack kind"));
    // Advance only the authority action clock; no world/PIE or render tick is needed.
    PS->WhirlwindStartedAt-=PS->WhirlwindReadySeconds;
    PS->FireTokenBucket=0;PS->LastFireTokenRefillAt=World->GetTimeSeconds();
    TArray<ANurseZombie*> Targets;
    FActorSpawnParameters TargetSpawn;TargetSpawn.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    FColdSteelNetHitReport Hit;Hit.ItemDefinition=Item.Definition;Hit.AttackMeta=0x20;Hit.WhirlwindSerial=Serial;
    Hit.Flags=1<<3;Hit.HitNormal=-FVector::ForwardVector;Hit.ClientFireTime=World->GetTimeSeconds();Hit.ClaimedDamage=10000000;
    int32 Damaged=0;
    for(int32 I=0;I<10;++I)
    {
        const FVector Offset=FRotator(0,I*36.f,0).Vector()*180.f+FVector(0,0,55);
        auto* Target=World->SpawnActor<ANurseZombie>(Pawn->GetActorLocation()+Offset,FRotator::ZeroRotator,TargetSpawn);
        Target->Health=Target->MaxHealth=100000;Targets.Add(Target);
        Hit.Target=Target;Hit.AimOrigin=Pawn->GetPawnViewLocation();Hit.ImpactPoint=Target->GetActorLocation();
        Hit.Direction=(Target->GetActorLocation()-Pawn->GetActorLocation()).GetSafeNormal();
        PS->ServerReportHit_Implementation(Hit);Damaged+=Target->Health<100000;
    }
    Check(Damaged==10&&PS->WhirlwindTargets.Num()==10,TEXT("ten simultaneous AOE targets are not capped by the firearm token bucket"));
    const float LastHP=Targets.Last()->Health;PS->ServerReportHit_Implementation(Hit);
    Check(Targets.Last()->Health==LastHP,TEXT("same target cannot take a second hit in this cast"));
    FColdSteelSkillShot ClaimedShot;ClaimedShot.bMelee=true;
    Check(FMath::IsNearlyEqual(PS->ComputeServerDamage(Pawn,Hit,ClaimedShot,Shadow->Equipped(),1.f),PS->ServerWhirlwindCast.Damage),
        TEXT("client claimed damage cannot override server snapshot"));
    Check(Targets.Last()->Combat->StunSecondsRemaining()>0.f,TEXT("remote whirlwind applies explicit stun on authority"));
    auto* Wall=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall);
    Wall->AddInstanceComponent(Box);Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(10,300,300));
    Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponent();Wall->SetActorLocation(Pawn->GetActorLocation()+FVector(75,0,55));
    auto* Behind=World->SpawnActor<ANurseZombie>(Pawn->GetActorLocation()+FVector(150,0,55),FRotator::ZeroRotator,TargetSpawn);
    auto BlockedHit=Hit;BlockedHit.Target=Behind;BlockedHit.ImpactPoint=Behind->GetActorLocation();
    FString BlockedReason;const FColdSteelItem* Declared=nullptr;
    Check(!PS->ValidateHitReport(BlockedHit,Pawn,BlockedReason,Declared)&&BlockedReason==TEXT("los blocked"),
        TEXT("whirlwind respects static wall occlusion on authority"));
    Wall->Destroy();
    const int32 Hits=PS->WhirlwindHits;
    PS->ServerSwordWhirlwind_Implementation(Serial,Pawn,FString(),false,0,FVector::ForwardVector,true);
    const int32 XP=Shadow->MasteryProgress(TEXT("dashAttack")).Experience;
    const int32 TrainedLevel=Shadow->MasteryProgress(TEXT("dashAttack")).Level;
    const auto& BeforeTraining=Base.Skills.FindChecked(TEXT("dashAttack"));
    Check(Hits==10&&(TrainedLevel>BeforeTraining.Level||XP>BeforeTraining.Experience)&&Shadow->MasteryProgress(TEXT("whirlwind")).Experience==Base.Skills.FindChecked(TEXT("whirlwind")).Experience,
        TEXT("Zhufeng trains dash on accepted authority hits"));
    PS->SettleSwordWhirlwind();Check(Shadow->MasteryProgress(TEXT("dashAttack")).Experience==XP&&Shadow->MasteryProgress(TEXT("dashAttack")).Level==TrainedLevel,TEXT("duplicate finish cannot award training twice"));
    Check(!PS->SwordWhirlwindMove(11,Heading,Limit)&&!Pawn->IsMeleeSkillMovementLocked(),TEXT("finish closes move authorization and locomotion lock"));
    PS->ServerReportHit_Implementation(Hit);Check(Targets.Last()->Health==LastHP,TEXT("late hit after finish is rejected"));
    const float CD=Shadow->WhirlwindCooldown();PS->ServerMartialCooldowns_Implementation(Pawn,999,0,0,0,0,World->GetTimeSeconds());
    Check(Shadow->WhirlwindCooldown()==CD,TEXT("owner cooldown publication cannot clear authority whirlwind cooldown"));
    Charge();PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,12,FVector::ForwardVector,false);
    Check(!PS->WhirlwindActiveSequence&&FMath::IsNearlyEqual(Shadow->Stamina(),Base.Stamina-Cost),TEXT("cooldown rejects repeat cast without spending again"));
    Reset();Charge();Shadow->Current.Stamina=Cost-1;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,13,FVector::ForwardVector,false);
    Check(!PS->WhirlwindActiveSequence&&Shadow->Stamina()==Cost-1,TEXT("insufficient authority stamina rejects cast"));
    Reset();Charge();Shadow->Current.Skills.FindChecked(TEXT("dashAttack")).Level=0;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,14,FVector::ForwardVector,false);
    Check(!PS->WhirlwindActiveSequence,TEXT("Zhufeng cannot bypass dash learning requirement"));
    Reset();Shadow->Current.Skills.FindChecked(TEXT("whirlwind")).Level=1;
    PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,false,0,FVector::ForwardVector,false);
    Check(PS->WhirlwindActiveSequence==Serial&&FMath::IsNearlyEqual(PS->ServerWhirlwindCast.DamageMultiplier,Cast.DamageMultiplier),TEXT("manual learned whirlwind uses the same additive upgrade"));
    Shadow->Current.Items.Reset();PS->TickSwordWhirlwind(0);
    Check(!PS->WhirlwindActiveSequence,TEXT("unequip closes active authority cast"));
    Reset();Charge();PS->ServerSwordWhirlwind_Implementation(++Serial,Pawn,Item.InstanceId,true,15,FVector::ForwardVector,false);
    HP->Health=0;PS->TickSwordWhirlwind(0);Check(!PS->WhirlwindActiveSequence,TEXT("death closes active authority cast"));
    auto Receipt=Base;UppercutStaminaReceipt::Merge(Receipt,Cost);UppercutStaminaReceipt::Merge(Receipt,Cost);
    Check(FMath::IsNearlyEqual(Receipt.Stamina,Base.Stamina-Cost),TEXT("late receipt and mirror share one cumulative payment"));
    UppercutStaminaReceipt::Merge(Receipt,Cost+7);UppercutStaminaReceipt::Merge(Receipt,Cost);
    Check(FMath::IsNearlyEqual(Receipt.Stamina,Base.Stamina-Cost-7),TEXT("interleaved martial charges cannot be reverted by older receipt"));
    auto* Source=NewObject<UStaticMeshComponent>(Pawn);Source->ComponentTags.Add(TEXT("SwordSlot=blade_1"));
    FFPSBodyAttachment CyanPart,FactoryPart;FPSBodyRuneVisual::Capture(Source,&Item,CyanPart);FPSBodyRuneVisual::Capture(Source,&Factory,FactoryPart);
    Check(CyanPart.bZhufengBlade&&!CyanPart.BeiweiBladeBase.Equals(CyanPart.BeiweiBladeTip)&&
        FPSBodyRuneVisual::Key(CyanPart)!=FPSBodyRuneVisual::Key(FactoryPart),TEXT("rune-free Zhufeng captures remote trail endpoints and cache identity"));
    FFPSBodyState State;State.Action=EFPSBodyAction::Whirlwind;State.ActionVariant=TEXT("ZhufengWhirlwind");
    State.bZhufengWhirlwindTrail=true;State.bBeiweiMartial=true;State.ZhufengForwardSpeed=400;State.ZhufengForwardYaw=72;
    TArray<uint8> Bytes;FMemoryWriter Writer(Bytes);FObjectAndNameAsStringProxyArchive Out(Writer,false);
    FFPSBodyState::StaticStruct()->SerializeItem(Out,&State,nullptr);
    FFPSBodyState Restored;FMemoryReader Reader(Bytes);FObjectAndNameAsStringProxyArchive In(Reader,true);
    FFPSBodyState::StaticStruct()->SerializeItem(In,&Restored,nullptr);
    Check(Restored.bZhufengWhirlwindTrail&&Restored.bBeiweiMartial&&Restored.ActionVariant==State.ActionVariant&&
        Restored.ZhufengForwardSpeed==400&&Restored.ZhufengForwardYaw==72,TEXT("body state serialization retains cyan flags and forward gait fields"));
    Check(LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Weapons/Zhanmadao20261018/ZhufengCyanTrailV1/Materials/M_ZhufengSwordTrail.M_ZhufengSwordTrail"))!=nullptr,
        TEXT("published cyan material resolves in native host"));
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);
    Root->SetArrayField(TEXT("results"),Rows);Root->SetBoolField(TEXT("real_network_transport_tested"),false);Root->SetBoolField(TEXT("visual_tested"),false);
    Root->SetBoolField(TEXT("world_begin_play"),World->HasBegunPlay());Root->SetBoolField(TEXT("net_driver_created"),World->GetNetDriver()!=nullptr);
    Root->SetBoolField(TEXT("client_process_started"),false);Root->SetBoolField(TEXT("reflection_archive_roundtrip"),true);
    Root->SetStringField(TEXT("authority_entry"),TEXT("ServerSwordWhirlwind_Implementation / ServerReportHit_Implementation / ProcessMeleeNetworkMove"));
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    const FString Path=FPaths::ProjectSavedDir()/TEXT("ZhufengNetworkReview20261019/authority-result.json");
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Path),true);FFileHelper::SaveStringToFile(Json,*Path);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
