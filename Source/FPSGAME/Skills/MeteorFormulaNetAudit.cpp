#include "SkillNetworkAuditCommandlet.h"
#include "FPSFireMagicComponent.h"
#include "FPSFireballComponent.h"
#include "FPSMeteorStrike.h"
#include "MeteorAssets.h"
#include "MeteorGround.h"
#include "FireMagicArea.h"
#include "PlayerSkillPreparation.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 USkillNetworkAuditCommandlet::RunMeteorFormulaNetAudit(const FString& Params)
{
    const FString Original=FCommandLine::Get();
    const FString Slot=TEXT("SkillNetworkAudit_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("SkillNetworkAudit -ColdSteelProfile=")+Slot));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("MeteorFormulaNetAudit"));
    auto* World=GI->GetWorld();auto* Host=GI->GetSubsystem<UColdSteelStatusModel>();
    if(!World||!Host||!Host->IsAudit()||Host->ProfileSlot()!=TEXT("ColdSteel_")+Slot)return 2;
    int32 Failures=0;TArray<TSharedPtr<FJsonValue>> Rows,Levels;
    const auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("case"),Name);Row->SetBoolField(TEXT("passed"),OK);Row->SetStringField(TEXT("detail"),Detail);
        Rows.Add(MakeShared<FJsonValueObject>(Row));Failures+=!OK;
        UE_LOG(LogTemp,Display,TEXT("METEOR_FORMULA_NET %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Seed=Host->Snapshot();Seed.Items.Reset();Seed.ActiveWeaponSlot=6;Seed.ActiveProductionTool.Reset();
    Seed.DungeonRun={};Seed.MeteorCooldown=0;Seed.Mana=10000;Seed.NetworkProfileId=FGuid::NewGuid();
    for(auto& Skill:Seed.Skills){Skill.Value.Level=1;Skill.Value.Experience=0;}
    auto Staff=Host->CreateItem(TEXT("ue_apprentice_staff"));Staff.Place=1;Staff.Cell=6;Seed.Items={Staff};Host->Current=Seed;
    auto* Model=Host->CreateShadowModel(Seed);
    auto* PC=World->SpawnActor<ASkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>(FVector(0,0,100),FRotator::ZeroRotator);
    PS->SetOwner(PC);PC->SetPlayerState(PS);PC->Possess(Pawn);Pawn->SetPlayerState(PS);PS->ShadowModel=Model;
    Pawn->NetShadowProfile=Model;Model->CurrentPawn=Pawn;
    Model->Current.Mana=Model->Derived(TEXT("maxMp"));
    auto* Fire=Pawn->FindComponentByClass<UFPSFireMagicComponent>();
    Pawn->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    auto* HP=Pawn->FindComponentByClass<UFPSCombatHealthComponent>();HP->Health=HP->MaxHealth;
    for(int32 L=1;L<=20;++L)
    {
        const auto S=Model->FireMagicStats(TEXT("meteor"),L);const float K=L-1;
        const float Multiplier=Model->MagicImplementMultiplier();
        const float Direct=FMath::FloorToFloat(FMath::FloorToFloat(80.f+10.f*K+S.MagicAttack*(20.f+1.2f*K))*Multiplier);
        const float Field=FMath::FloorToFloat(FMath::FloorToFloat(10.f+K+S.MagicAttack*(1.3f+.09f*K))*Multiplier);
        Check(FMath::IsNearlyEqual(S.Damage,Direct,.01f)&&FMath::IsNearlyEqual(S.AuraDamage,Field,.01f),FString::Printf(TEXT("level %d damage contract"),L));
        Check(FMath::IsNearlyEqual(S.Radius,630.f+22.5f*L)&&FMath::IsNearlyEqual(S.AuraRadius,540.f+18.f*L),FString::Printf(TEXT("level %d radius contract"),L));
        auto R=MakeShared<FJsonObject>();R->SetNumberField(TEXT("level"),L);R->SetNumberField(TEXT("magic_attack"),S.MagicAttack);
        R->SetNumberField(TEXT("impact"),S.Damage);R->SetNumberField(TEXT("field_tick"),S.AuraDamage);
        R->SetNumberField(TEXT("radius_cm"),S.Radius);R->SetNumberField(TEXT("field_radius_cm"),S.AuraRadius);
        R->SetNumberField(TEXT("duration"),S.Duration);R->SetNumberField(TEXT("ticks"),FMath::FloorToInt(S.Duration/S.TickSeconds));Levels.Add(MakeShared<FJsonValueObject>(R));
    }
    TArray<FSoftObjectPath> Paths;PlayerSkillAssets::Gather(TEXT("meteor"),Seed,Paths);
    const auto Load=UAssetManager::GetStreamableManager().RequestSyncLoad(Paths);
    for(const auto& Path:Paths)Check(Path.ResolveObject()!=nullptr,TEXT("runtime asset resolves"),Path.ToString());
    Fire->ResolveMeteorAssets();Check(Fire->bMeteorAssetsReady&&Fire->MeteorAimMaterial,TEXT("current manifest passes cast readiness"));
    const auto Box=[&](FVector At,FVector Extent,FRotator Rotation=FRotator::ZeroRotator)
    {
        auto* Actor=World->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(Actor);Actor->AddInstanceComponent(B);Actor->SetRootComponent(B);
        B->SetBoxExtent(Extent);B->SetCollisionEnabled(ECollisionEnabled::QueryOnly);B->SetCollisionResponseToAllChannels(ECR_Block);
        B->RegisterComponent();Actor->SetActorLocationAndRotation(At,Rotation);return Actor;
    };
    auto* Floor=Box(FVector(0,0,-20),FVector(6000,6000,20));
    const auto Spell=Model->FireMagicStats(TEXT("meteor"));
    FVector Point(Spell.Range+15.f,0,0),Normal=FVector::UpVector;FString Failure;
    Check(!MeteorGround::Validate(Pawn,Spell.Range,Point,Normal,true,Failure),TEXT("server rejects former extra 15 percent range"));
    Point=FVector(400,0,160);Check(!MeteorGround::Validate(Pawn,Spell.Range,Point,Normal,false,Failure),TEXT("hovering locked target rejected"));
    Point=FVector(400,0,0);Normal=FVector::UpVector;
    Check(MeteorGround::Validate(Pawn,Spell.Range,Point,Normal,true,Failure),TEXT("visible real ground accepted for lock"));
    FColdSteelNetCastRequest Request;Request.SourcePawn=Pawn;Request.SkillId=TEXT("meteor");Request.Sequence=Request.CastId=100;
    Request.AimPoint=Point;Request.AimNormal=Normal;
    const float ManaBefore=Model->Snapshot().Mana;PS->ExecuteCastRequest(Request);
    Check(PS->PendingCastSkill==TEXT("meteor")&&FMath::IsNearlyEqual(Model->Snapshot().Mana,ManaBefore-Spell.ManaCost),TEXT("authority prepare charges once and stores target"));
    auto* Wall=Box(FVector(180,0,130),FVector(15,350,130));
    auto Locked=Point;auto LockedNormal=Normal;
    Check(!MeteorGround::Validate(Pawn,Spell.Range,Locked,LockedNormal,true,Failure)
        &&MeteorGround::Validate(Pawn,Spell.Range,Locked,LockedNormal,false,Failure),TEXT("new obstruction blocks a new lock but not a confirmed lock"));
    Request.Phase=1;Request.Sequence=101;Request.AimPoint=FVector(900,500,0);PS->ExecuteCastRequest(Request);PS->ExecuteCastRequest(Request);
    TArray<AFPSMeteorStrike*> Strikes;for(TActorIterator<AFPSMeteorStrike> It(World);It;++It)if(!It->IsActorBeingDestroyed())Strikes.Add(*It);
    Check(Strikes.Num()==1&&Strikes[0]->Destination.Equals(Point,1.f)&&PS->PendingCastSkill.IsNone(),TEXT("release uses server locked point; duplicate creates no second meteor"));
    Check(FMath::IsNearlyEqual(Model->Snapshot().Mana,ManaBefore-Spell.ManaCost),TEXT("duplicate release cannot refund accepted cast"));
    for(auto* Strike:Strikes)Strike->FinishForRemoval();Wall->Destroy();
    Model->Current.MeteorCooldown=0;Model->Current.Mana=ManaBefore;Request.Phase=0;Request.Sequence=Request.CastId=200;Request.AimPoint=Point;
    PS->ExecuteCastRequest(Request);const float Paid=Model->Snapshot().Mana;
    Request.Phase=2;Request.CastId=199;PS->ExecuteCastRequest(Request);
    Check(PS->PendingCastSkill==TEXT("meteor")&&Model->Snapshot().Mana==Paid,TEXT("stale cancel cannot touch next reservation"));
    Request.CastId=200;PS->ExecuteCastRequest(Request);PS->ExecuteCastRequest(Request);
    Check(FMath::IsNearlyEqual(Model->Snapshot().Mana,ManaBefore)&&Model->FireMagicCooldown(TEXT("meteor"))==0,TEXT("matching cancellation refunds only actual payment once"));
    Request.Phase=0;Request.Sequence=Request.CastId=300;Request.AimPoint=FVector(Spell.Range+100,0,0);
    const float BeforeInvalid=Model->Snapshot().Mana;PS->ExecuteCastRequest(Request);
    Check(PS->PendingCastSkill.IsNone()&&Model->Snapshot().Mana==BeforeInvalid,TEXT("invalid prepare spends no authority mana"));

    // Actual target inclusion and foot-based falloff inputs on a 45 degree plane.
    auto* Enemy=World->SpawnActor<ANurseZombie>(FVector(0,0,100),FRotator::ZeroRotator);Enemy->Health=Enemy->MaxHealth=100000;
    Enemy->Knockdown=nullptr;Enemy->GetCapsuleComponent()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    const FVector SlopeNormal(0,-.70710678,.70710678),Tangent(0,.70710678,.70710678),Center(0,2500,200);
    auto PlaceFeet=[&](const FVector& Feet,float HalfHeight){Enemy->GetCapsuleComponent()->SetCapsuleHalfHeight(HalfHeight);Enemy->SetActorLocation(Feet+FVector(0,0,HalfHeight));};
    const FVector Mid=Center+Tangent*Spell.Radius*.5;
    PlaceFeet(Mid,95);const FVector ShortFoot=FireMagic::GroundPoint(Enemy);PlaceFeet(Mid,180);const FVector TallFoot=FireMagic::GroundPoint(Enemy);
    Check(ShortFoot.Equals(TallFoot,.01f)&&FMath::IsNearlyEqual(float(FVector::VectorPlaneProject(TallFoot-Center,SlopeNormal).Size()/Spell.Radius),.5f,.001f),TEXT("slope falloff uses same foot position for different heights"));
    Check(FireMagic::GroundTargets(Pawn,Center,SlopeNormal,Spell.Radius).Contains(Enemy),TEXT("slope midpoint within footprint is hittable"));
    PlaceFeet(Center+Tangent*(Spell.Radius+100),95);
    Check(!FireMagic::GroundTargets(Pawn,Center,SlopeNormal,Spell.Radius).Contains(Enemy),TEXT("beyond slope radius and body margin excluded"));
    PlaceFeet(Center+SlopeNormal*110,95);
    Check(!FireMagic::GroundTargets(Pawn,Center,SlopeNormal,Spell.Radius).Contains(Enemy),TEXT("other ground layer outside 100 cm band excluded"));
    PlaceFeet(FVector(400,0,0),95);
    Enemy->Tags.Add(TEXT("Friendly"));
    Check(!FireMagic::GroundTargets(Pawn,FVector::ZeroVector,FVector::UpVector,Spell.Radius).Contains(Enemy),TEXT("friendly unit inside footprint takes no area hit"));
    Enemy->Tags.Remove(TEXT("Friendly"));
    auto* Cover=Box(FVector(180,0,180),FVector(20,400,180));
    Check(!FireMagic::GroundTargets(Pawn,FVector::ZeroVector,FVector::UpVector,Spell.Radius).Contains(Enemy),TEXT("solid wall blocks impact and field exposure"));
    Cover->Destroy();
    Check(FireMagic::GroundTargets(Pawn,FVector::ZeroVector,FVector::UpVector,Spell.Radius).Contains(Enemy),TEXT("removing cover restores target exposure"));
    Enemy->Destroy();

    const int32 HitXP=Model->FireMagicDefinition(TEXT("meteor")).FireMagic.HitExperience;
    for(bool Death:{false,true})
    {
        const int32 BeforeXP=Model->FireMagicProgress(TEXT("meteor")).Experience;
        const int32 HostXP=Host->FireMagicProgress(TEXT("meteor")).Experience;
        auto* Removed=World->SpawnActor<AFPSMeteorStrike>();Removed->InitializeStrike(Pawn,Spell,Point,Normal);Removed->Rewards.Hits=1;
        if(Death){HP->Health=0;Removed->Tick(0.f);HP->Health=HP->MaxHealth;}
        else Removed->EndPlay(EEndPlayReason::Destroyed); // Isolated world does not dispatch BeginPlay.
        Removed->FinishForRemoval();Removed->SettleRewards();
        Check(Model->FireMagicProgress(TEXT("meteor")).Experience==BeforeXP+HitXP
            &&Host->FireMagicProgress(TEXT("meteor")).Experience==HostXP,
            Death?TEXT("caster death settles guest training exactly once"):TEXT("direct removal settles guest training exactly once"));
    }

    // Real decal/MID alignment; presentation follows the selected surface each frame.
    auto* LocalPC=World->SpawnActor<APlayerController>();LocalPC->SetAsLocalPlayerController();LocalPC->Possess(Pawn);
    Host->Current=Seed;Host->CurrentPawn=Pawn;Pawn->SetActorLocation(FVector(4500,0,400));
    auto* Slope=Box(FVector(4500,0,220),FVector(600,600,20),FRotator(0,0,45));
    auto* Camera=Pawn->FindComponentByClass<UCameraComponent>();Camera->SetWorldLocation(FVector(4500,0,700));Camera->SetWorldRotation(FRotator(-90,0,0));
    Fire->SetMeteorAimPreview(true);
    Check(Fire->bMeteorPreviewValid&&Fire->MeteorAimDecal&&Fire->MeteorAimMID,TEXT("slope preview resolves real surface"));
    if(Fire->MeteorAimDecal&&Fire->MeteorAimMID)
    {
        Check(Fire->MeteorAimMID->K2_GetVectorParameterValue(TEXT("SurfaceNormal")).Equals(FLinearColor(Fire->LockedNormal),.001f)
            &&Fire->MeteorAimDecal->GetForwardVector().Equals(-Fire->LockedNormal,.001f),TEXT("preview shader and projector use damage surface normal"));
        Check(Fire->MeteorAimMID->K2_GetScalarParameterValue(TEXT("ImpactRadius"))==Spell.Radius
            &&Fire->MeteorAimMID->K2_GetScalarParameterValue(TEXT("FieldRadius"))==Spell.AuraRadius,TEXT("both preview radii equal authority snapshot"));
        int32 Updates=0;for(int32 I=0;I<20;++I){const FVector Before=Fire->LockedPoint;Camera->SetWorldLocation(FVector(4500+I*2,0,700));Fire->TickComponent(1.f/144,LEVELTICK_All,&Fire->PrimaryComponentTick);Updates+=!Before.Equals(Fire->LockedPoint,.01f);}
        Check(Updates>=19,TEXT("surface fix retains per-frame dragging"),FString::FromInt(Updates));
    }
    Fire->SetMeteorAimPreview(false);Slope->Destroy();Floor->Destroy();
    const auto SetPaidMeteor=[&](uint32 Id)
    {
        Host->Current=Seed;Host->Current.Mana=20.f;
        Host->Current.MeteorCooldown=Host->Current.MeteorCooldownDuration=30.f;
        Fire->MeteorLocalCastId=Id;Fire->MeteorResolvedCastId=0;Fire->MeteorPendingRefund=10.f;
        Fire->bMeteorAwaitingResult=true;Fire->CommittedSkill=NAME_None;
    };
    SetPaidMeteor(501);Fire->NetMeteorCastResult(1,7,501);Fire->NetMeteorCastResult(1,7,501);
    Check(Host->Snapshot().Mana==30.f&&Host->FireMagicCooldown(TEXT("meteor"))==0.f&&!Fire->bMeteorAwaitingResult,
        TEXT("duplicate reject receipts refund exact local payment once"));
    SetPaidMeteor(502);Fire->NetMeteorCastResult(1,7,501);
    Check(Host->Snapshot().Mana==20.f&&Fire->bMeteorAwaitingResult,TEXT("old receipt cannot alter a newer local cast"));
    Fire->NetMeteorCastResult(1,0,502);Fire->NetMeteorCastResult(1,7,502);
    Check(Host->Snapshot().Mana==20.f&&!Fire->bMeteorAwaitingResult,TEXT("accepted receipt cannot later become a refund"));
    SetPaidMeteor(503);Fire->CommittedSkill=TEXT("meteor");
    Pawn->FindComponentByClass<UFPSFireballComponent>()->RecordGesturePayment(30.f,20.f,true);
    Fire->CancelPending();Fire->NetMeteorCastResult(0,6,503);
    Check(Host->Snapshot().Mana==30.f&&Host->FireMagicCooldown(TEXT("meteor"))==0.f,TEXT("gesture cancel plus delayed rejection refunds once"));
    auto Root=MakeShared<FJsonObject>();Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failures"),Failures);
    Root->SetBoolField(TEXT("real_network_transport"),false);Root->SetBoolField(TEXT("rendered"),false);Root->SetArrayField(TEXT("results"),Rows);Root->SetArrayField(TEXT("levels"),Levels);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(FPaths::ProjectDir()/TEXT("SourceAssets/MeteorFormulaNetAudit20261022/native-result.json")));
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*Original);
    return Failures?1:0;
}
