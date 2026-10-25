#include "BowSkillTrainingAuditCommandlet.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Weapons/Bow/BowStats.h"
#include "../Weapons/Bow/BowWeaponComponent.h"
#include "../Weapons/Bow/BowArrow.h"
#include "../Characters/FPSPlayerBodyComponent.h"
#include "../Characters/FPSQuiverMotion.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

// Explicit commandlet only. Isolated profiles; no player save or asset writes.
int32 UBowSkillTrainingAuditCommandlet::RunQuiverBelt(const FString& Params)
{
    const FString OriginalCommand=FCommandLine::Get();
    const FString ProfileName=TEXT("BowSkillAudit_Quiver_")+FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FCommandLine::Set(*(TEXT("BowSkillTrainingAudit -ColdSteelProfile=")+ProfileName));
    auto* GI=NewObject<UGameInstance>(GEngine);GI->AddToRoot();GI->InitializeStandalone(TEXT("QuiverAuditWorld"));
    auto* World=GI->GetWorld();auto* Model=GI->GetSubsystem<UColdSteelStatusModel>();
    auto* Enhancement=GI->GetSubsystem<UColdSteelEnhancementSystem>();
    if(!World||!Model||!Model->IsAudit())return 2;
    TArray<TSharedPtr<FJsonValue>> Rows;int32 Failed=0;
    auto Check=[&](bool OK,const FString& Name,const FString& Detail=FString())
    {
        auto R=MakeShared<FJsonObject>();R->SetStringField(TEXT("case"),Name);R->SetBoolField(TEXT("passed"),OK);
        R->SetStringField(TEXT("detail"),Detail);Rows.Add(MakeShared<FJsonValueObject>(R));if(!OK)++Failed;
        UE_LOG(LogTemp,Display,TEXT("QUIVER_AUDIT %s %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),*Name,*Detail);
    };
    auto Near=[](double A,double B){return FMath::Abs(A-B)<1.e-5;};
    auto Json=[](const FString& S){TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(S),O);return O;};
    auto SetLevel=[&](FColdSteelItem& I,int32 Level)
    {auto O=Json(I.Data);O->SetNumberField(TEXT("enhanceLevel"),Level);FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));};
    auto Base=Model->Snapshot();Base.Items.Reset();Base.ActiveWeaponSlot=6;Base.ActiveProductionTool.Reset();Base.DungeonRun={};
    Base.Hotbar.Init(TEXT(""),4);Base.HotbarDefinitions.Init(TEXT(""),4);for(auto& B:Base.QuickBindings)B={};
    for(auto& S:Base.Skills){S.Value.Level=1;S.Value.Experience=0;}
    auto Weapon=Model->CreateItem(TEXT("bow_dark"));Weapon.Place=1;Weapon.Cell=6;Base.Items.Add(Weapon);
    auto Belt=Model->CreateItem(TEXT("ue_leather_quiver_belt"));Belt.Place=1;Belt.Cell=10;
    const FString Ammo=Model->AmmoDefinitionFor(Weapon);Base.AmmoPouch.FindOrAdd(Ammo)=100;Base.Stamina=100;
    Model->Current=Base;
    const auto Bare=ColdSteelBow::Evaluate(Weapon,Model);
    const double BareDrawBonus=ColdSteelWeaponStats::BowDrawSpeedBonus(&Weapon,Model);
    auto* Player=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();
    PC->SetAsLocalPlayerController();PC->Possess(Player);
    auto* Bow=Player->FindComponentByClass<UBowWeaponComponent>();
    Bow->InitializePresentation();
    Bow->Character=Player;Bow->InstanceId=Weapon.InstanceId;Bow->ArrowId=Ammo;Bow->bPresentationReady=true;Bow->bUsesArms=false;
    auto* Body=Player->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* Clip=LoadObject<UAnimSequence>(nullptr,*ColdSteelInventory::Text(Weapon,TEXT("bow_nock_animation")));
    Check(Clip!=nullptr,TEXT("native nock animation resolves"));if(Clip)Bow->Animations.Add(TEXT("Nock"),Clip);
    for(int32 Level:{0,1,14,15,16})
    {
        SetLevel(Belt,Level);auto State=Base;State.Items.Add(Belt);Model->Current=State;
        const double N=.50+.02*FMath::Min(Level,15),D=.05+.01*FMath::Min(Level,15);
        const auto Stats=ColdSteelBow::Evaluate(Weapon,Model);
        const double ExpectedDraw=FMath::Max(.3,Bare.Draw*(1.+BareDrawBonus)/(1.+BareDrawBonus+D));
        const FString Tag=FString::Printf(TEXT("level %d"),Level);
        Check(Near(Model->EquipmentBonus(TEXT("bowNockSpeed")),N)&&Near(Model->EquipmentBonus(TEXT("bowDrawSpeed")),D),Tag+TEXT(" equipment bonuses/cap"));
        Check(Near(Stats.Nock,Bare.Nock/(1.+N))&&Near(Stats.Draw,ExpectedDraw),Tag+TEXT(" production timing"));
        Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=false;Bow->BeginNock();
        Check(Bow->Stage==EBowStage::Nocking&&Near(Bow->NockSeconds,Stats.Nock),Tag+TEXT(" manual nock executor"));
        Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=false;Bow->BeginDrawEntry();
        const double Entry=ColdSteelInventory::Number(Weapon,TEXT("bow_draw_entry_seconds"),.2)/(1.+N);
        Check(Bow->Stage==EBowStage::DrawEntry&&Near(Bow->DrawEntrySeconds,Entry),Tag+TEXT(" quick entry executor"));
        Bow->Stage=EBowStage::Release;Bow->bArrowNocked=false;Bow->BeginDrawEntry();
        Check(Bow->bChainEntry&&Near(Bow->DrawEntrySeconds,Entry),Tag+TEXT(" chain entry executor"));
        Bow->SetStage(EBowStage::Drawing,0.f);
        Check(Near(Bow->DrawSeconds,Stats.Draw),Tag+TEXT(" real draw clock"));
    }
    // Equip/unequip without changing the bow instance must affect the next action.
    Model->Current=Base;Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=false;Bow->BeginNock();
    Check(Near(Bow->NockSeconds,Bare.Nock),TEXT("unequip belt resets next nock"));
    const float Started=Bow->NockSeconds;SetLevel(Belt,15);Model->Current.Items.Add(Belt);Bow->ApplyNumbers(&Weapon);
    Check(Near(Bow->NockSeconds,Started),TEXT("in-progress nock keeps its starting clock"));
    Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=false;Bow->BeginNock();
    Check(Near(Bow->NockSeconds,Bare.Nock/1.8),TEXT("same bow picks up newly equipped belt"));
    Bow->Stage=EBowStage::Ready;Bow->bArrowNocked=true;Bow->bNockKeepsDrawPose=false;Bow->BeginDrawEntry();
    Check(Near(Bow->DrawEntrySeconds,ColdSteelInventory::Number(Weapon,TEXT("bow_draw_entry_seconds"),.2)),TEXT("already nocked entry retains its duration"));
    // The remote animation clock must contain BOTH equipment and action haste.
    Bow->Stage=EBowStage::Nocking;Bow->CurrentClip=TEXT("Nock");Bow->Elapsed=0.f;
    for(float Rate:{1.f,2.f})
    {
        Bow->StageActionRate=Rate;FFPSBodyState State;Body->SampleBowState(*Bow,State);
        Check(Clip&&Near(State.BowClipRate,Clip->GetPlayLength()/Bow->NockSeconds*Rate),
            FString::Printf(TEXT("replicated nock rate includes action multiplier %.1f"),Rate));
    }
    Bow->StageActionRate=1.f;
    Check(Enhancement&&Enhancement->Supports(Belt)&&Enhancement->MaxLevel(Belt)==15,TEXT("belt supports enhancement through +15"));
    const auto CappedQuote=Enhancement->Quote(Belt.InstanceId);
    Check(!CappedQuote.Valid&&CappedQuote.Reason==TEXT("已达到强化上限"),TEXT("+15 cannot enhance again"));
    auto Processing=Base;Processing.Souls=1000;SetLevel(Belt,0);Processing.Items.Add(Belt);
    auto Stone=Model->CreateItem(TEXT("enhancement_stone"));Stone.Place=0;Stone.Cell=0;Stone.Count=2;Processing.Items.Add(Stone);
    Model->Current=Processing;
    const auto Quote=Enhancement->Quote(Belt.InstanceId);FString EnhanceReason;
    const bool Enhanced=Quote.Valid&&Enhancement->Apply(Quote,EnhanceReason);
    Check(Enhanced&&Near(Model->EquipmentBonus(TEXT("bowNockSpeed")),.52)&&Near(Model->EquipmentBonus(TEXT("bowDrawSpeed")),.06),TEXT("actual +0 to +1 enhancement updates both bonuses"),EnhanceReason);
    Check(Enhanced&&Model->CountMaterial(TEXT("enhancement_stone"))==1&&Model->Snapshot().Souls==900,TEXT("enhancement charges one stone and its quoted souls"));
    Model->Current.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Belt.InstanceId;})->Place=0;
    Check(Near(Model->EquipmentBonus(TEXT("bowNockSpeed")),0.)&&Near(Model->EquipmentBonus(TEXT("bowDrawSpeed")),0.),TEXT("unequipped inventory belt grants no bonuses"));
    SetLevel(Belt,15);

    // Old instance snapshots are canonicalized separately for guest and owner.
    auto Old=Base;auto Stale=Belt;auto O=Json(Stale.Data);O->RemoveField(TEXT("bonusStats"));O->RemoveField(TEXT("bonusPerEnhance"));O->RemoveField(TEXT("enhancement"));
    FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&Stale.Data));Old.Items.Add(Stale);Old.NetworkProfileId=FGuid::NewGuid();
    Model->Current=Base;auto* Shadow=Model->CreateShadowModel(Old);
    Check(Shadow&&Near(Shadow->EquipmentBonus(TEXT("bowNockSpeed")),.8)&&Near(Shadow->EquipmentBonus(TEXT("bowDrawSpeed")),.2),TEXT("guest old-item migration preserves +15 and refreshes stats"));
    Model->AdoptNetMirror(Old);
    Check(Near(Model->EquipmentBonus(TEXT("bowNockSpeed")),.8)&&Near(Model->EquipmentBonus(TEXT("bowDrawSpeed")),.2),TEXT("owner network mirror migrates old item"));
    Check(Model->FindItem(Belt.InstanceId)&&Model->FindItem(Belt.InstanceId)->Place==1&&Model->FindItem(Belt.InstanceId)->Cell==10
        &&Near(ColdSteelInventory::Number(*Model->FindItem(Belt.InstanceId),TEXT("enhanceLevel")),15.),TEXT("migration preserves instance, slot and enhancement level"));
    Check(Model->CommitState(Model->Snapshot())&&Model->ReloadProfile()&&Near(Model->EquipmentBonus(TEXT("bowNockSpeed")),.8),TEXT("isolated save/reload retains enhancement and stats"));
    auto Incorrect=Old;auto WrongData=Json(Incorrect.Items.Last().Data);auto WrongBonus=MakeShared<FJsonObject>();WrongBonus->SetNumberField(TEXT("bowNockSpeed"),999.);
    WrongData->SetObjectField(TEXT("bonusStats"),WrongBonus);FJsonSerializer::Serialize(WrongData.ToSharedRef(),TJsonWriterFactory<>::Create(&Incorrect.Items.Last().Data));
    auto* Corrected=Model->CreateShadowModel(Incorrect);
    Check(Corrected&&Near(Corrected->EquipmentBonus(TEXT("bowNockSpeed")),.8),TEXT("guest catalog replaces incorrect serialized base bonus"));
    auto Tactical=Model->CreateItem(TEXT("ue_tactical_magazine_belt"));Tactical.Place=1;Tactical.Cell=10;SetLevel(Tactical,15);
    auto TacticalData=Json(Tactical.Data);TacticalData->RemoveField(TEXT("bonusPerEnhance"));TacticalData->RemoveField(TEXT("enhancement"));
    FJsonSerializer::Serialize(TacticalData.ToSharedRef(),TJsonWriterFactory<>::Create(&Tactical.Data));auto TacticalOld=Base;TacticalOld.Items.Add(Tactical);
    auto* TacticalShadow=Model->CreateShadowModel(TacticalOld);
    Check(TacticalShadow&&Near(TacticalShadow->EquipmentBonus(TEXT("reloadSpeed")),.1),TEXT("tactical belt shares guest growth/cap migration"));
    Model->Current=Base;
    auto* RemotePC=World->SpawnActor<ABowSkillAuditRemoteController>();auto* PS=World->SpawnActor<AColdSteelPlayerState>();
    PS->SetOwner(RemotePC);PS->ShadowModel=Shadow;PS->SlotName=TEXT("ColdSteel_")+ProfileName+TEXT("_Guest");RemotePC->SetPlayerState(PS);
    auto* Remote=World->SpawnActor<AFPSGAMECharacter>(FVector(1000,0,0),FRotator::ZeroRotator);RemotePC->Possess(Remote);
    Remote->SetPlayerState(PS);Remote->NetShadowProfile=Shadow;Shadow->CurrentPawn=Remote;
    for(int32 I=0;I<30;++I)World->Tick(LEVELTICK_TimeOnly,.1f);
    PS->ServerSetBowDraw_Implementation(Remote,Weapon.InstanceId,true,0.f);
    const auto GuestStats=ColdSteelBow::Evaluate(Weapon,Shadow);
    Check(Near(PS->BowDrawSeconds,GuestStats.Draw)&&!Near(PS->BowDrawSeconds,Bare.Draw),TEXT("server draw uses guest belt, not host singleton"));
    const float Release=PS->BowDrawSeconds+.05f;PS->BowDrawStartedAt=World->GetTimeSeconds()-Release;PS->LastBowShotAt=-100.;
    FColdSteelInventoryRequest Request;Request.Item=Weapon.InstanceId;Request.Pawn=Remote;Request.Charge=1.f;
    Request.Eye=Remote->GetPawnViewLocation();Request.Origin=Request.Eye;Request.Direction=Remote->GetBaseAimRotation().Vector();Request.BowReleaseElapsed=Release;
    const int32 GuestAmmo=Shadow->PouchCount(Ammo),HostAmmo=Model->PouchCount(Ammo);FString Reason;
    Check(PS->ExecuteBowShot(Request,Shadow,Reason),TEXT("authority accepts shortened full draw"),Reason);
    Check(Shadow->PouchCount(Ammo)==GuestAmmo-1&&Model->PouchCount(Ammo)==HostAmmo,TEXT("only guest ammunition is charged once"));
    Check(!PS->ExecuteBowShot(Request,Shadow,Reason)&&Shadow->PouchCount(Ammo)==GuestAmmo-1,TEXT("duplicate release cannot spend a second arrow"));
    for(TActorIterator<ABowArrow> It(World);It;++It)It->Destroy();

    FString RecipeText;FFileHelper::LoadFileToString(RecipeText,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/modular_outfits.json")));
    auto Recipes=Json(RecipeText);auto* RemoteBody=Remote->FindComponentByClass<UFPSPlayerBodyComponent>();
    for(const TCHAR* Gender:{TEXT("Jason"),TEXT("Kaitlin")})
    {
        auto Config=FString(Gender)==TEXT("Jason")?Recipes:Recipes->GetObjectField(TEXT("body_variants"))->GetObjectField(TEXT("kaitlin"));
        auto Recipe=Config->GetObjectField(TEXT("items"))->GetObjectField(TEXT("ue_leather_quiver_belt"));
        auto Settings=Recipe->GetObjectField(TEXT("quiver_motion"));
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Recipe->GetObjectField(TEXT("rig_meshes"))->GetStringField(Gender));
        auto* ArrowMesh=LoadObject<UStaticMesh>(nullptr,*Settings->GetStringField(TEXT("arrow_mesh")));
        Check(Mesh&&ArrowMesh,FString(Gender)+TEXT(" saved wear and arrow assets load"));if(!Mesh||!ArrowMesh)continue;
        auto* Driver=NewObject<USkeletalMeshComponent>(Remote);Driver->SetSkeletalMeshAsset(Mesh);Driver->RegisterComponent();
        auto* Part=NewObject<USkeletalMeshComponent>(Remote);Part->SetSkeletalMeshAsset(Mesh);Part->RegisterComponent();
        auto Count=[&](bool Visible){TArray<UStaticMeshComponent*> Parts;Remote->GetComponents(Parts);int32 N=0;for(const auto* V:Parts)if(V->ComponentHasTag(TEXT("QuiverDecorativeArrow"))&&(!Visible||(V->IsVisible()&&!V->bHiddenInGame)))++N;return N;};
        {
            FFPSQuiverMotion Motion;RemoteBody->DisplayState.Family=TEXT("Rifle");Motion.Initialize(Driver,Part,Settings,ArrowMesh,false);
            Check(Count(false)==5&&Count(true)==0,FString(Gender)+TEXT(" five cosmetic arrows hidden with rifle"));
            RemoteBody->DisplayState.Family=TEXT("Bow");Motion.Tick(.016f);
            Check(Count(true)==5,FString(Gender)+TEXT(" guest body state reveals its arrows"));
            Part->SetHiddenInGame(true);Motion.Tick(.016f);Check(Count(true)==0,FString(Gender)+TEXT(" hidden belt hides arrows"));
            Part->SetHiddenInGame(false);RemoteBody->DisplayState.Family=TEXT("Rifle");Motion.Tick(.016f);
            Check(Count(true)==0,FString(Gender)+TEXT(" weapon switch hides arrows"));
        }
        Check(Count(false)==0,FString(Gender)+TEXT(" unequip destroys decorative components"));Part->DestroyComponent();Driver->DestroyComponent();
    }
    auto Root=MakeShared<FJsonObject>();Root->SetStringField(TEXT("profile"),ProfileName);Root->SetNumberField(TEXT("checks"),Rows.Num());Root->SetNumberField(TEXT("failed"),Failed);Root->SetArrayField(TEXT("results"),Rows);
    Root->SetStringField(TEXT("scope"),TEXT("isolated production formula/executor/authority/asset lifecycle calls; no UDP transport or rendered multiplayer"));
    FString Output;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Output));FString Dir=FPaths::ProjectSavedDir()/TEXT("QuiverBeltAudit20261025");FParse::Value(*Params,TEXT("ReportDir="),Dir);
    IFileManager::Get().MakeDirectory(*Dir,true);FFileHelper::SaveStringToFile(Output,*(Dir/TEXT("result.json")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
    UE_LOG(LogTemp,Display,TEXT("QUIVER_AUDIT_DONE checks=%d failed=%d"),Rows.Num(),Failed);
    GI->Shutdown();GEngine->DestroyWorldContext(World);World->DestroyWorld(false);GI->RemoveFromRoot();FCommandLine::Set(*OriginalCommand);return Failed?1:0;
}
