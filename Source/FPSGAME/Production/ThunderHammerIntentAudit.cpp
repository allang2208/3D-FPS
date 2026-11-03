#include "WarhammerModificationAuditCommandlet.h"
#include "ProductionToolComponent.h"
#include "ThunderHammerCallIntent.h"
#include "ThunderHammerThrown.h"
#include "ThunderHammerThrow.h"
#include "../Weapons/ModularSwordVisual.h"
#include "../FPSGAMECharacter.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Serialization/JsonSerializer.h"

int32 UWarhammerModificationAuditCommandlet::AuditJiLeiIntent(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_JiLeiIntent_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("WarhammerModificationAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("JiLeiIntentWorld"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit())return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows;
    const auto Check=[&](bool OK,const FString& Name)
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("JILEI_INTENT %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.Stamina=150;Seed.Mana=100;Seed.bSprintExhausted=false;
    auto Hammer=Host->CreateItem(TEXT("ue_thunder_god_hammer"));Hammer.Place=1;Hammer.Cell=6;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Hammer.Data),Data);
    auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("head_mount"),TEXT("ji_lei_seat"));
    Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Hammer.Data.Reset();
    FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Hammer.Data));Seed.Items.Add(Hammer);
    auto* Guest=Host->CreateShadowModel(Seed);
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<AWarhammerAuditRemoteController>();
    auto* PS=World->SpawnActor<AColdSteelPlayerState>();PC->PlayerState=PS;PC->Possess(Pawn);PS->ShadowModel=Guest;Guest->AttachPawn(Pawn);
    Pawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health=100;
    auto* Tool=Pawn->FindComponentByClass<UProductionToolComponent>();Tool->Character=Pawn;Tool->Kind=TEXT("warhammer");
    const auto Begin=[&](uint32 Id,float Mana)
    {
        Tool->CancelUse();Tool->BluntServerReadyAt=0.;auto P=Seed;P.Mana=Mana;Guest->AdoptNetMirror(P);
        Tool->ServerBeginBluntCharge_Implementation(Id);
        Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-1.;
    };
    Begin(1,100);
    Check(Tool->bBluntServerCharging&&!Tool->IsThunderCalling(),TEXT("server waits for hold confirmation despite delayed release"));
    Tool->TickThunderCall(.1f);
    Check(!Tool->bThunderCallCharging&&!Tool->OwnsThunderCallResources(),TEXT("pending tap has no remote FX or resource ownership"));
    const float BeforePendingTick=Guest->Stamina();Guest->TickRuntime(.1f,Pawn);
    Check(Guest->Stamina()>=FMath::Min(BeforePendingTick,Guest->MaxStamina())&&Guest->Mana()>=FMath::Min(100.f,float(Guest->Derived(TEXT("maxMp")))),TEXT("profile tick does not debit generic heavy charge during pending tap"));
    const float PendingMana=Guest->Mana();
    Tool->ServerBeginBluntAttack_Implementation(1,true,false);
    Check(Tool->BluntLastServerRequestId==1&&Guest->Stamina()<FMath::Min(150.f,Guest->MaxStamina())&&Guest->Mana()==PendingMana,TEXT("delayed tap commits ordinary stamina only"));
    const float AfterTap=Guest->Stamina();Tool->BluntServerReadyAt=0.;
    Tool->ServerBeginBluntAttack_Implementation(1,false,false);
    Check(Guest->Stamina()==AfterTap,TEXT("repeated ordinary RPC cannot debit stamina twice"));
    Begin(2,0);Check(Tool->bBluntServerCharging,TEXT("zero mana permits pending tap"));
    Tool->ServerBeginBluntAttack_Implementation(2,true,false);
    Check(Tool->BluntLastServerRequestId==2&&Guest->Stamina()<150&&Guest->Mana()==0,TEXT("zero mana ordinary attack accepted"));
    Begin(3,0);Tool->ServerConfirmThunderCall_Implementation(3);
    Check(!Tool->bBluntServerCharging&&!Tool->bThunderCallHoldConfirmed,TEXT("zero mana rejects only confirmed hold"));
    Begin(4,100);Tool->ServerConfirmThunderCall_Implementation(3);
    Check(!Tool->IsThunderCalling()&&Tool->bBluntServerCharging,TEXT("stale confirmation cannot activate next input"));
    Tool->ServerBeginBluntCharge_Implementation(3);Tool->ServerReleaseThunderCall_Implementation(3,FVector::ZeroVector);
    Check(Tool->bBluntServerCharging&&Tool->BluntServerAttackId==4,TEXT("stale begin and release cannot replace or cancel next input"));
    Tool->ServerConfirmThunderCall_Implementation(4);Tool->TickThunderCall(.1f);
    Check(Tool->IsThunderCalling()&&Tool->bThunderCallCharging,TEXT("matching confirmation activates charge"));
    Tool->ServerBeginBluntAttack_Implementation(4,true,false);
    Check(!Tool->bBluntServerCharging&&!Tool->bThunderCallCharging&&Guest->Stamina()==150,TEXT("confirmed hold cannot splice into ordinary attack"));
    Begin(5,100);Tool->ServerConfirmThunderCall_Implementation(5);Tool->TickThunderCall(.1f);
    Tool->ServerCancelBluntAttack_Implementation(5);Tool->ServerConfirmThunderCall_Implementation(5);
    Check(!Tool->IsThunderCalling()&&!Tool->bThunderCallCharging&&!Tool->bThunderCallHoldConfirmed,TEXT("cancel remains terminal after late confirmation"));
    Begin(6,100);Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-100.;
    Tool->ServerConfirmThunderCall_Implementation(6);
    Tool->ServerReleaseThunderCall_Implementation(6,FVector(1000,0,0));
    Check(Tool->BluntLastServerRequestId!=6&&!Tool->bBluntServerCharging,TEXT("late confirmation cannot bypass full active charge time"));
    Begin(7,100);Tool->ServerConfirmThunderCall_Implementation(7);
    Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds+.1;
    Tool->ServerReleaseThunderCall_Implementation(7,FVector(1000,0,0));
    Check(Tool->bBluntServerCharging&&Tool->BluntLastServerRequestId!=7&&World->GetTimerManager().TimerExists(Tool->BluntContactTimer),TEXT("jittered full release waits for authority deadline without early strike"));
    Tool->ServerCancelBluntAttack_Implementation(7);
    Check(!Tool->bBluntServerCharging&&!World->GetTimerManager().TimerExists(Tool->BluntContactTimer),TEXT("cancel removes deferred full release"));
    Begin(8,100);Tool->ServerConfirmThunderCall_Implementation(8);
    Tool->BluntServerChargeStartedAt=World->GetTimeSeconds()-Tool->BluntChargeSeconds+.4;
    Tool->ServerReleaseThunderCall_Implementation(8,FVector(1000,0,0));
    Check(!Tool->bBluntServerCharging&&!World->GetTimerManager().TimerExists(Tool->BluntContactTimer)&&Tool->BluntLastServerRequestId!=8,TEXT("substantially undercharged release remains rejected"));
    Tool->CancelUse();
    // Compare actual saved head vertices against the planted ground plane,
    // including slopes; a replicated recipe alone cannot prove ground contact.
    for(const TCHAR* Head:{TEXT("factory"),TEXT("heavy_forged"),TEXT("flanged_breaker"),TEXT("light_drum"),TEXT("pointed_hammer")})
    {
        auto GroundHammer=Hammer;Parts->SetStringField(TEXT("head_mount"),TEXT("guan_lei_seat"));Parts->SetStringField(TEXT("hammer_heads"),Head);
        GroundHammer.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&GroundHammer.Data));
        for(const FVector Normal:{FVector::UpVector,FVector(.2f,.3f,1.f).GetSafeNormal()})
        {
            FActorSpawnParameters Spawn;Spawn.Owner=Pawn;auto* Thrown=World->SpawnActor<AThunderHammerThrown>(Spawn);
            Thrown->Weapon=GroundHammer;Thrown->Velocity=FVector(100,0,-40);
            FHitResult Hit;Hit.ImpactPoint=FVector(1000,0,0);Hit.ImpactNormal=Normal;Thrown->Land(Hit);
            float MinDistance=BIG_NUMBER;
            for(const auto& Part:ColdSteelModularSword::DescribeGeometry(GroundHammer))if(Part.Slot==TEXT("hammer_heads"))
                if(const auto* Mesh=LoadObject<UStaticMesh>(nullptr,*Part.Mesh))if(const auto* Render=Mesh->GetRenderData();Render&&!Render->LODResources.IsEmpty())
                {
                    const auto& Buffer=Render->LODResources[0].VertexBuffers.PositionVertexBuffer;
                    for(uint32 V=0;V<Buffer.GetNumVertices();++V)
                    {
                        const FVector LocalPoint=Part.RelativeTransform.TransformPosition(FVector(Buffer.VertexPosition(V)))-FVector(0,0,ThunderHammerThrow::CenterZ);
                        const FVector WorldPoint=Thrown->GetActorLocation()+Thrown->GroundRotation.RotateVector(LocalPoint);
                        MinDistance=FMath::Min(MinDistance,float(FVector::DotProduct(WorldPoint-Hit.ImpactPoint,Normal)));
                    }
                }
            Check(FMath::IsNearlyEqual(MinDistance,-ThunderHammerThrow::GroundEmbedCM,.12f),FString::Printf(TEXT("saved head %s embeds on %s ground (%.3f cm)"),Head,Normal==FVector::UpVector?TEXT("flat"):TEXT("sloped"),MinDistance));
            Thrown->Destroy();
        }
    }
    // Possession must retire the dead snapshot before initial pawn replication.
    auto Dead=Guest->Snapshot();Dead.Health=0.f;Guest->AdoptNetMirror(Dead);
    Pawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health=0.f;
    auto* Reborn=World->SpawnActor<AFPSGAMECharacter>();PC->UnPossess();PC->Possess(Reborn);
    Check(Guest->RuntimePawn()==Reborn,TEXT("remote possession immediately binds new pawn to its shadow profile"));
    Check(Guest->Snapshot().Health>0.f,TEXT("new life clears dead profile before first replication"));
    Check(Pawn->FindComponentByClass<UFPSCombatHealthComponent>()->Health==0.f,TEXT("respawn binding never revives previous pawn"));
    Reborn->Destroy();Pawn->Destroy();PC->Destroy();PS->Destroy();

    // Exercise actual local press/release methods with a dummy mesh readiness
    // fixture. This does not render or validate hand-bone contact.
    auto* Local=World->SpawnActor<AFPSGAMECharacter>();auto* LocalPC=World->SpawnActor<APlayerController>();
    auto* LocalPS=World->SpawnActor<AColdSteelPlayerState>();LocalPS->SetOwner(LocalPC);LocalPC->SetPlayerState(LocalPS);
    LocalPC->SetAsLocalPlayerController();LocalPC->Possess(Local);Local->SetPlayerState(LocalPS);Local->bInventoryWeaponReady=false;
    Host->AdoptNetMirror(Seed);Host->AttachPawn(Local);
    Local->FindComponentByClass<UFPSCombatHealthComponent>()->Health=100;
    auto* LocalTool=Local->FindComponentByClass<UProductionToolComponent>();LocalTool->Character=Local;
    LocalTool->Kind=TEXT("warhammer");LocalTool->EquippedId=Hammer.InstanceId;LocalTool->bUsesArms=false;
    LocalTool->ToolMesh=NewObject<UStaticMeshComponent>(Local);
    LocalTool->ToolMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));
    LocalTool->Elapsed=LocalTool->EquipElapsed=-1.f;
    auto Zero=Seed;Zero.Mana=0;Host->AdoptNetMirror(Zero);
    LocalTool->BeginPrimaryAttack();
    Check(LocalTool->bBluntCharging&&!LocalTool->IsThunderCalling(),TEXT("local zero mana press stays tap pending"));
    LocalTool->ReleasePrimaryAttack();
    Check(LocalTool->Elapsed>=0.f&&!LocalTool->bBluntHeavy&&!LocalTool->bBluntReturningCharge&&Host->Stamina()<150,TEXT("local zero mana tap attacks without lowering hand"));
    LocalTool->CancelUse();Host->AdoptNetMirror(Seed);LocalTool->BeginPrimaryAttack();
    LocalTool->BluntChargeStartedAt=World->GetTimeSeconds()-.5;
    LocalTool->TickThunderCall(.1f);LocalTool->ReleasePrimaryAttack();
    Check(LocalTool->Elapsed<0.f&&!LocalTool->bBluntCharging&&!LocalTool->bThunderCallCharging,TEXT("local underfull hold cancels without normal attack"));
    LocalTool->CancelUse();Local->Destroy();LocalPC->Destroy();LocalPS->Destroy();
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("checks"),Rows);Report->SetNumberField(TEXT("failures"),Failures);
    Report->SetNumberField(TEXT("count"),Rows.Num());Report->SetBoolField(TEXT("real_network_transport_tested"),false);
    Report->SetStringField(TEXT("isolated_profile"),Slot);Report->SetBoolField(TEXT("rendered"),false);
    FString Out;FParse::Value(*Params,TEXT("Out="),Out);FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    const bool Saved=FFileHelper::SaveStringToFile(Json,*Out);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures||!Saved?1:0;
}
