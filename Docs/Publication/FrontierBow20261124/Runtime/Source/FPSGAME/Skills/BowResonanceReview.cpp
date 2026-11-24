#include "BowSkillTrainingAuditCommandlet.h"
#include "ColdSteelSkillRules.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowCadenceComponent.h"
#include "../Weapons/Bow/BowMountainEchoComponent.h"
#include "../Weapons/Bow/CadenceString.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Bow/BowPartReceipt.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "../Multiplayer/ColdSteelProfileTransfer.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "../Props/FPSPracticeTarget.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"

namespace
{
// Time the production game-thread path with warm assets. No viewport/GPU time is included.
TSharedPtr<FJsonObject> MeasureAuroraUpdates(AActor* Emitter,int32 Lanes)
{
    LoadObject<UStaticMesh>(nullptr,AuroraBeamVisual::Cylinder);
    LoadObject<UStaticMesh>(nullptr,AuroraBeamVisual::Sphere);
    LoadObject<UMaterialInterface>(nullptr,AuroraBeamVisual::MaterialPath);
    auto* World=Emitter->GetWorld();
    TArray<double> Samples;
    int32 PeakInstances=0;
    constexpr double Step=1./60.;
    for(int32 Run=0;Run<8;++Run)
    {
        auto* Effect=AAuroraBeamVisual::Open(Emitter,FVector::ZeroVector);
        if(!Effect)break;
        const double Start=AuroraBeamVisual::Clock(World);
        for(int32 Frame=1;Frame<=42;++Frame)
        {
            World->TimeSeconds+=Step;
            const double Now=AuroraBeamVisual::Clock(World);
            const double Begin=FPlatformTime::Seconds();
            if(Frame<=20)for(int32 Lane=0;Lane<Lanes;++Lane)
            {
                const FVector From(0,120.*Lane,500.),Tip=From+FVector(Frame*125.,0,-Frame*10.);
                const float Scale=Lanes==1?1.f:.72f;
                if(Frame<20)Effect->Trace(Lane,From,Start,Tip,Now,Scale);
                else
                {
                    FAuroraBeamContact Hit;Hit.Point=Tip;Hit.At=Now;
                    Effect->Finish(Lane,From,Start,Hit,Scale);
                }
            }
            if(Frame==20)Effect->Release();
            Effect->Tick(Step);
            const double Elapsed=(FPlatformTime::Seconds()-Begin)*1000.;
            if(Run>0)Samples.Add(Elapsed);
            TInlineComponentArray<UInstancedStaticMeshComponent*> Meshes(Effect);
            int32 Instances=0;for(const auto* Mesh:Meshes)Instances+=Mesh->GetInstanceCount();
            PeakInstances=FMath::Max(PeakInstances,Instances);
        }
        Effect->Destroy();
    }
    Samples.Sort();
    auto Result=MakeShared<FJsonObject>();
    Result->SetNumberField(TEXT("lanes"),Lanes);Result->SetNumberField(TEXT("samples"),Samples.Num());
    Result->SetNumberField(TEXT("peak_allocated_instances"),PeakInstances);
    if(!Samples.IsEmpty())
    {
        Result->SetNumberField(TEXT("p50_ms"),Samples[Samples.Num()/2]);
        Result->SetNumberField(TEXT("p95_ms"),Samples[FMath::CeilToInt(Samples.Num()*.95)-1]);
    }
    return Result;
}
}

int32 UBowSkillTrainingAuditCommandlet::RunBowResonanceReview(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Profile=TEXT("BowSkillAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("BowSkillTrainingAudit -ColdSteelProfile=")+Profile));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("BowResonanceReview"));
    auto* W=GI->GetWorld();auto* M=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!W||!M||!M->IsAudit()||M->ProfileSlot()!=TEXT("ColdSteel_")+Profile)return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    auto Check=[&](bool OK,const FString& Name)
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
        Rows.Add(MakeShared<FJsonValueObject>(R));Failed+=!OK;
        UE_LOG(LogTemp,Display,TEXT("BOW_RESONANCE_REVIEW %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name);
    };
    auto Install=[](FColdSteelItem& Item,const TCHAR* Option)
    {
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("string"),Option);
        Data->SetObjectField(TEXT("gunsmith_parts"),Parts);FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
    };
    auto Seed=M->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();Seed.DungeonRun={};
    for(auto& B:Seed.QuickBindings)B={};Seed.Stamina=100;Seed.Mana=100;
    auto Item=M->CreateItem(CadenceString::Weapon);Item.Place=1;Item.Cell=6;Install(Item,CadenceString::Option);Seed.Items.Add(Item);
    const FString Ammo=M->AmmoDefinitionFor(Item);Seed.AmmoPouch.FindOrAdd(Ammo)=100;
    Check(M->CommitState(Seed),TEXT("isolated profile seed"));
    auto* Host=W->SpawnActor<AFPSGAMECharacter>();auto* PC=W->SpawnActor<APlayerController>();PC->SetAsLocalPlayerController();
    auto* HPS=W->SpawnActor<AColdSteelPlayerState>();HPS->SetOwner(PC);PC->SetPlayerState(HPS);PC->Possess(Host);Host->SetPlayerState(HPS);M->CurrentPawn=Host;
    auto Guest=Seed;Guest.NetworkProfileId=FGuid::NewGuid();auto* S=M->CreateShadowModel(Guest);
    auto* Remote=W->SpawnActor<AFPSGAMECharacter>(FVector(3000,0,500),FRotator::ZeroRotator);
    auto* RPC=W->SpawnActor<ABowSkillAuditRemoteController>();auto* PS=W->SpawnActor<AColdSteelPlayerState>();
    PS->SetOwner(RPC);PS->ShadowModel=S;PS->SlotName=TEXT("ColdSteel_")+Profile+TEXT("_Guest");RPC->SetPlayerState(PS);RPC->Possess(Remote);
    Remote->SetPlayerState(PS);Remote->NetShadowProfile=S;S->CurrentPawn=Remote;
    for(auto* P:{Host,Remote}){auto* HP=P->FindComponentByClass<UFPSCombatHealthComponent>();HP->Health=HP->MaxHealth;}
    for(int32 I=0;I<40;++I)W->Tick(LEVELTICK_TimeOnly,.1f);
    Check(ColdSteelAuthority::ForPawn(Host)==M&&ColdSteelAuthority::ForPawn(Remote)==S,TEXT("host and guest use distinct authority models"));
    auto* HC=Host->FindComponentByClass<UBowCadenceComponent>();auto* C=Remote->FindComponentByClass<UBowCadenceComponent>();
    HC->RefreshEquipment(M);C->RefreshEquipment(S);
    const double Passive=ColdSteelWeaponStats::BowDrawSpeedBonus(&Item,S);
    auto Base=ColdSteelWeaponStats::DamageParts(Item,S,69);
    for(int32 Count=1;Count<=5;++Count)
    {
        C->CommitRelease(Item.InstanceId,true);
        Check(C->Charges()==Count&&HC->Charges()==0,FString::Printf(TEXT("guest cadence stack %d does not affect host"),Count));
        Check(FMath::IsNearlyEqual(ColdSteelWeaponStats::BowDrawSpeedBonus(&Item,S)-Passive,Count*double(CadenceString::SpeedPerStack),1.e-5),TEXT("stack speed added once"));
    }
    const auto Full=ColdSteelWeaponStats::DamageParts(Item,S,69);
    Check(FMath::IsNearlyEqual(Full.BasePhysical,Base.BasePhysical*1.2,1.e-4)&&FMath::IsNearlyEqual(Full.AddedPhysical,Base.AddedPhysical*1.2,1.e-4)
        &&Full.BaseMagic==Base.BaseMagic&&Full.AddedMagic==Base.AddedMagic,TEXT("full cadence scales physical only"));
    Check(C->SpreadMultiplier()==.5f,TEXT("full cadence halves hip spread"));
    const uint32 Rev=C->State.Revision;C->CommitRelease(Item.InstanceId,true);
    Check(C->Charges()==5&&C->State.Revision>Rev,TEXT("maximum stack refresh retains cap and pulse revision"));
    const auto Views=UStatusEffectsComponent::GetOrCreate(Remote)->Snapshot();
    Check(Views.ContainsByPredicate([](const FStatusEffectView& V){return V.Type==CadenceString::Status&&V.Stacks==5;}),TEXT("buff snapshot exposes five stacks"));
    C->CommitRelease(Item.InstanceId,false);Check(C->Charges()==5,TEXT("full cadence treats committed release outside timing window as rhythm"));
    C->CommitRelease(Item.InstanceId,true);C->State.EndServerTime=W->GetTimeSeconds()-.1;
    Check(C->Charges()==0&&C->SpeedBonus()==0.f,TEXT("expired cadence stops bonuses before next tick"));
    C->CommitRelease(Item.InstanceId,true);const auto NewPawn=Remote->FindComponentByClass<UFPSCombatHealthComponent>();NewPawn->Health=0;
    C->TickComponent(.1f,LEVELTICK_All,nullptr);Check(C->State.Stacks==0,TEXT("death clears cadence"));NewPawn->Health=NewPawn->MaxHealth;
    C->CommitRelease(Item.InstanceId,true);S->Current.ActiveWeaponSlot=0;C->RefreshEquipment(S);
    Check(C->State.Instance.IsEmpty()&&C->State.Stacks==0,TEXT("unequip clears cadence identity"));S->Current.ActiveWeaponSlot=6;C->RefreshEquipment(S);

    // Real authority release entry, including delayed/stale draw identities.
    const FGuid Old=FGuid::NewGuid(),Current=FGuid::NewGuid();
    PS->ServerSetBowDraw_Implementation(Remote,Item.InstanceId,true,0.f,Current);
    PS->ServerSetBowDraw_Implementation(Remote,Item.InstanceId,false,0.f,Old);
    Check(PS->IsBowDrawActive(Remote)&&PS->BowDrawId==Current,TEXT("old cancel preserves current server draw"));
    FColdSteelInventoryRequest R;R.Pawn=Remote;R.Item=Item.InstanceId;R.Charge=1.f;R.BowDrawId=Old;
    R.Eye=Remote->GetPawnViewLocation();R.Origin=R.Eye;R.Direction=Remote->GetBaseAimRotation().Vector();FString Reason;
    Check(!PS->ExecuteBowShot(R,S,Reason)&&PS->BowDrawId==Current,TEXT("old release cannot consume a newer draw"));
    R.BowDrawId=Current;const float Release=PS->BowDrawSeconds+.05f;PS->BowDrawStartedAt=W->GetTimeSeconds()-Release;
    R.BowReleaseElapsed=R.BowChargeElapsed=Release;PS->LastBowShotAt=-100.;const int32 Before=S->PouchCount(Ammo);
    Check(PS->ExecuteBowShot(R,S,Reason)&&C->Charges()==1&&PS->bBowPerfectSpeedBonus,TEXT("authority perfect shot earns cadence and next-arrow speed"));
    Check(S->PouchCount(Ammo)==Before-1&&M->PouchCount(Ammo)==100,TEXT("guest shot spends only guest ammunition"));
    Check(!PS->ExecuteBowShot(R,S,Reason)&&C->Charges()==1&&S->PouchCount(Ammo)==Before-1,TEXT("duplicate shot cannot add a stack or spend again"));
    PS->BowPerfectPawn=Host;PS->RefreshBowPerfectOwner();Check(!PS->bBowPerfectSpeedBonus,TEXT("respawn/pawn replacement invalidates pending speed"));
    PS->bBowPerfectSpeedBonus=true;PS->BowPerfectPawn=Remote;PS->BowPerfectWeapon=Item.InstanceId;
    S->Current.ActiveWeaponSlot=0;PS->TickBowDrawAuthority();Check(!PS->bBowPerfectSpeedBonus,TEXT("switching weapon clears server perfect bonus even while idle"));S->Current.ActiveWeaponSlot=6;

    // Exercise receipt application out of order, without claiming socket transport.
    auto* B=Host->FindComponentByClass<UBowWeaponComponent>();B->Character=Host;B->InstanceId=Item.InstanceId;
    B->Stage=EBowStage::Drawing;B->Elapsed=.7f;B->DrawSeconds=.6f;B->ActiveDrawId=Current;
    B->ConfirmNetworkDraw(Item.InstanceId,Old,2.f,false);Check(B->DrawSeconds==.6f,TEXT("old draw acknowledgement is ignored"));
    B->ConfirmNetworkDraw(Item.InstanceId,Current,1.f,true);
    Check(B->DrawSeconds==1.f&&B->DrawElapsed()==.7f&&B->Stage==EBowStage::Drawing&&B->HasPerfectDrawSpeedBonus(),TEXT("authority duration and bonus correct prediction without resetting elapsed"));
    B->LastReleasedDrawId=Current;B->bPerfectSpeedPending=true;
    B->ConfirmNetworkRelease(Item.InstanceId,Old,true,false,false);Check(B->bPerfectSpeedPending,TEXT("old shot receipt cannot clear later prediction"));
    B->ConfirmNetworkRelease(Item.InstanceId,Current,true,false,false);Check(!B->bPerfectSpeedPending,TEXT("successful non-perfect authority result corrects false positive prediction"));
    B->Stage=EBowStage::Release;B->ConfirmNetworkRelease(Item.InstanceId,Current,false,true,false);
    Check(B->bPerfectSpeedPending&&!B->bLastPerfectRelease,TEXT("rejected shot preserves earned speed without showing successful release"));
    PS->bBowPerfectSpeedBonus=true;PS->BowPerfectPawn=Remote;PS->BowPerfectWeapon=Item.InstanceId;
    PS->ResetBowPerfectSpeedBonus();Check(!PS->bBowPerfectSpeedBonus&&PS->BowPerfectWeapon.IsEmpty(),TEXT("committed rain clears authority next-arrow bonus"));
    B->LastReleasedDrawId.Invalidate();B->bPerfectSpeedPending=false;
    B->ConfirmNetworkRelease(Item.InstanceId,Current,true,true,false);
    Check(!B->bPerfectSpeedPending,TEXT("pre-rain release receipt cannot restore a retired prediction"));
    auto* Reply=NewObject<UColdSteelInventoryReply>();Reply->Sequence=17;Reply->bBowPerfect=true;Reply->bBowPiercing=true;
    TArray<uint8> Blob;auto* Decoded=NewObject<UColdSteelInventoryReply>();
    Check(ColdSteelProfileTransfer::SaveToBlob(Reply,Blob)&&ColdSteelProfileTransfer::BlobToSaveObject(Blob,Decoded)
        &&Decoded->bBowPerfect&&Decoded->bBowPiercing&&Decoded->Sequence==17,TEXT("release flags survive actual receipt serialization"));

    // Same production hit path for a training target and a living enemy.
    Install(S->Current.Items[0],MountainEchoString::Option);auto* E=Remote->FindComponentByClass<UBowMountainEchoComponent>();
    E->RefreshEquipment(S);C->RefreshEquipment(S);
    auto* Target=W->SpawnActor<AFPSPracticeTarget>(FVector(10000,0,500),FRotator::ZeroRotator);
    auto* Monster=W->SpawnActor<ANurseZombie>(FVector(12000,0,500),FRotator::ZeroRotator);Monster->Knockdown=nullptr;Monster->Health=Monster->MaxHealth=10000;
    auto Fire=[&](AActor* Victim,float Charge)
    {
        FActorSpawnParameters Spawn;Spawn.Owner=Remote;Spawn.Instigator=Remote;
        auto* A=W->SpawnActor<ABowArrow>(FVector(9000,0,500),FRotator::ZeroRotator,Spawn);
        A->Configure(10,9800,520,30000,ColdSteelSkills::Snapshot(Remote,S->ActiveBow(),true),nullptr,nullptr,.3f,76,TEXT(""),false,8);
        E->CommitArrow(A,Item.InstanceId,Charge,Remote->GetPawnViewLocation());
        if(Victim)
        {
            auto* Primitive=Victim->FindComponentByClass<UPrimitiveComponent>();
            FHitResult Hit(Victim,Primitive,Victim->GetActorLocation(),FVector(-1,0,0));A->ApplyHit(Hit);A->ApplyHit(Hit);
        }
        return A;
    };
    Fire(Target,.7f)->Destroy();Check(E->ChargesFor(Item.InstanceId)==0,TEXT("partial draw on target does not earn mountain echo"));
    Fire(Target,1.f)->Destroy();Check(E->ChargesFor(Item.InstanceId)==1,TEXT("full target hit adds exactly one charge"));
    Fire(Monster,1.f)->Destroy();Check(E->ChargesFor(Item.InstanceId)==2,TEXT("living enemy hit adds exactly one charge"));
    Fire(Target,1.f)->Destroy();Check(E->ChargesFor(Item.InstanceId)==3,TEXT("third full hit lights all mountains"));
    auto* OriginalArrow=Fire(nullptr,1.f);int32 Echoes=0;ABowArrow* Echo=nullptr;
    for(TActorIterator<ABowArrow> It(W);It;++It)if(It->Presentation.bMountainEcho&&!It->IsActorBeingDestroyed()){++Echoes;Echo=*It;}
    Check(E->ChargesFor(Item.InstanceId)==0&&Echoes==1&&Echo&&Echo->bEchoPending,TEXT("next full shot consumes three charges and creates exactly one delayed echo"));
    if(Echo)
    {
        FHitResult Hit(Target,Target->FindComponentByClass<UPrimitiveComponent>(),Target->GetActorLocation(),FVector(-1,0,0));
        OriginalArrow->ApplyHit(Hit);Echo->ApplyHit(Hit);
        Check(E->ChargesFor(Item.InstanceId)==0&&Echo->MountainContact.bHit,TEXT("echo contact never recharges and retains replicated impact snapshot"));
        Check(!Echo->bRecoverable&&Echo->Presentation.Element==EArrowElement::None,TEXT("echo grants neither ammo nor elemental proc"));
    }
    E->Stacks=2;E->ExpiresAt=W->GetTimeSeconds()-.1;
    Check(E->ChargesFor(Item.InstanceId)==0,TEXT("mountain HUD expires from server clock without waiting for clear notification"));
    const uint32 Epoch=E->Epoch;S->Current.ActiveWeaponSlot=0;E->RefreshEquipment(S);E->ConfirmHit(Epoch);
    Check(E->Stacks==0,TEXT("arrow from a previous equipment epoch cannot recharge"));

    const auto* Catalog=GI->GetSubsystem<UGunsmithSystem>();
    for(const TCHAR* Definition:{TEXT("bow_dark"),TEXT("bow_woodsteel"),TEXT("bow_frontier_compound")})
    {
        auto Stock=S->CreateItem(Definition);Stock.Place=1;Stock.Cell=6;
        S->Current.ActiveWeaponSlot=6;S->Current.Items={Stock};
        const double StockRate=ColdSteelBow::ArrowRainStaminaPerSecond(*S);
        for(const auto Grip:{TEXT("waxed_linen"),TEXT("slim_leather_grip")})
        {
            auto Modified=Stock;
            TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Modified.Data),Data);
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("grip"),Grip);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
            Modified.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Modified.Data));
            S->Current.Items={Modified};
            const double Ratio=FString(Grip)==TEXT("waxed_linen")?.9:1.1;
            Check(StockRate>0.&&FMath::IsNearlyEqual(ColdSteelBow::ArrowRainStaminaPerSecond(*S),StockRate*Ratio,1.e-4),
                FString::Printf(TEXT("%s arrow rain upkeep follows %s"),Definition,Grip));
        }
        Check(Catalog&&BowPartReceipt::CanMerge(*Catalog,Definition,TEXT("string"),TEXT("false"),MountainEchoString::Option)
            &&BowPartReceipt::CanMerge(*Catalog,Definition,TEXT("string"),CadenceString::Option,TEXT("false")),
            FString::Printf(TEXT("%s shared string install and remove eligible for ordered receipts"),Definition));
    }
    Check(Catalog&&BowPartReceipt::CanMerge(*Catalog,TEXT("bow_frontier_compound"),TEXT("riser"),TEXT("frontier_aurora"),TEXT("frontier_eclipse"))
        &&!BowPartReceipt::CanMerge(*Catalog,TEXT("bow_dark"),TEXT("riser"),TEXT("false"),TEXT("frontier_aurora"))
        &&!BowPartReceipt::CanMerge(*Catalog,TEXT("bow_woodsteel"),TEXT("riser"),TEXT("woodcrafted_heavy"),TEXT("false")),
        TEXT("legendary swap stays on compatible bow and excludes retired paid parts"));

    W->InitializeActorsForPlay(FURL());
    const FVector Origin(50000,0,1500);
    auto* Source=W->SpawnActor<AFPSPracticeTarget>(Origin,FRotator::ZeroRotator);
    auto* Near=W->SpawnActor<AFPSPracticeTarget>(Origin+FVector(700,0,0),FRotator::ZeroRotator);
    auto* Far=W->SpawnActor<AFPSPracticeTarget>(Origin+FVector(1250,0,0),FRotator::ZeroRotator);
    for(auto* Prop:{Near,Far})
    {
        auto* Shape=NewObject<UBoxComponent>(Prop);Prop->AddInstanceComponent(Shape);
        Shape->SetupAttachment(Prop->GetRootComponent());Shape->SetBoxExtent(FVector(25.));
        Shape->SetCollisionProfileName(TEXT("BlockAll"));Shape->RegisterComponent();
    }
    for(int32 Index=0;Index<12;++Index)
    {
        FEclipseBowShot Shot;Shot.Shooter=Remote;FEclipseBowImpact Contact(&Shot,Source);
        Contact.Confirm(1.f);Contact.Confirm(1.f);
        Check(FMath::IsNearlyEqual(UEclipseBowMark::DamageMultiplier(Source),1.+.03*FMath::Min(10,Index+1)),
            FString::Printf(TEXT("eclipse unique shot and cap %d"),Index+1));
    }
    W->TimeSeconds+=8.f;
    FEclipseBowImpact::OnDeath(Source);
    Check(FMath::IsNearlyEqual(UEclipseBowMark::DamageMultiplier(Source),1.)&&FMath::IsNearlyEqual(UEclipseBowMark::DamageMultiplier(Near),1.30)
        &&FMath::IsNearlyEqual(UEclipseBowMark::DamageMultiplier(Far),1.),TEXT("eclipse propagates live layers within ten metres"));
    W->TimeSeconds+=3.f;
    Check(UEclipseBowMark::DamageMultiplier(Near)>1.,TEXT("eclipse spread has a refreshed lifetime"));
    W->TimeSeconds+=8.f;
    Check(UEclipseBowMark::DamageMultiplier(Near)==1.,TEXT("eclipse expires together on the shared clock"));

    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failed"),Failed);
    if(FParse::Param(*Params,TEXT("AuroraCost")))
    {
        Root->SetObjectField(TEXT("single_beam_cpu"),MeasureAuroraUpdates(Remote,1));
        Root->SetObjectField(TEXT("32_beam_rain_cpu"),MeasureAuroraUpdates(Remote,32));
    }
    Root->SetBoolField(TEXT("actual_socket_transport"),false);Root->SetBoolField(TEXT("gameplay_map_started"),false);
    Root->SetBoolField(TEXT("visual_or_audio_acceptance"),false);Root->SetArrayField(TEXT("results"),Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));FString Dir;
    FParse::Value(*Params,TEXT("ReportDir="),Dir);if(Dir.IsEmpty())Dir=FPaths::ProjectSavedDir()/TEXT("BowResonanceReview20261028");
    IFileManager::Get().MakeDirectory(*Dir,true);FFileHelper::SaveStringToFile(Json,*(Dir/TEXT("native-checks.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("BOW_RESONANCE_REVIEW_DONE checks=%d failed=%d"),Rows.Num(),Failed);
    TArray<AActor*> Actors;for(TActorIterator<AActor> It(W);It;++It)Actors.Add(*It);for(auto* A:Actors)if(IsValid(A))A->Destroy();
    GI->Shutdown();GEngine->DestroyWorldContext(W);W->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failed?1:0;
}
