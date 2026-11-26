// Opt-in rendered review: real Slate buttons -> conversation RPC -> world repair/save.
// Run only from an isolated project host with -VillageConstructionReview.
#include "../FPSGAMEPlayerController.h"
#if !UE_BUILD_SHIPPING
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../NPC/ChapelNun.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../UI/ColdSteelHUDWidget.h"
#include "../UI/ColdSteelNpcDialogue.h"
#include "../UI/ColdSteelSkillTreeScreen.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "Blueprint/UserWidget.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Engine/OverlapResult.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"
#include "Widgets/SWindow.h"
#include "Widgets/Text/STextBlock.h"
#include "UnrealClient.h"

namespace VillageConstructionReview
{
using FJson=TSharedPtr<FJsonObject>;
template<class T>T* Screen(UWorld* W)
{for(TObjectIterator<T> It;It;++It)if(It->GetWorld()==W&&It->IsInViewport())return *It;return nullptr;}
void Walk(const TSharedRef<SWidget>& W,TFunctionRef<void(const TSharedRef<SWidget>&)> Visit)
{
    if(!W->GetVisibility().IsVisible())return;
    Visit(W);if(auto* C=W->GetChildren())for(int32 I=0;I<C->Num();++I)Walk(C->GetChildAt(I),Visit);
}
bool HasText(const TSharedRef<SWidget>& W,const FString& Caption)
{
    bool Found=false;Walk(W,[&](const TSharedRef<SWidget>& V)
    {if(V->GetTypeAsString()==TEXT("STextBlock"))Found|=StaticCastSharedRef<STextBlock>(V)->GetText().ToString()==Caption;});return Found;
}
TSharedPtr<SWidget> Button(UUserWidget* W,const FString& Caption)
{
    TSharedPtr<SWidget> Result;if(!W)return Result;
    Walk(W->TakeWidget(),[&](const TSharedRef<SWidget>& V)
    {if(!Result&&V->GetTypeAsString()==TEXT("SButton")&&HasText(V,Caption))Result=V;});return Result;
}
bool Click(UWorld* W,UUserWidget* UI,const FString& Caption)
{
    auto B=Button(UI,Caption);if(!B||!B->IsEnabled()||!W->GetGameViewport()->GetWindow())return false;
    const auto G=B->GetCachedGeometry();const auto At=G.LocalToAbsolute(G.GetLocalSize()*.5);
    auto Pointer=[&](bool Down){return FPointerEvent(0,At,At,Down?TSet<FKey>{EKeys::LeftMouseButton}:TSet<FKey>{},EKeys::LeftMouseButton,0,FModifierKeysState());};
    auto& App=FSlateApplication::Get();App.ProcessMouseMoveEvent(Pointer(false));
    App.ProcessMouseButtonDownEvent(W->GetGameViewport()->GetWindow()->GetNativeWindow(),Pointer(true));
    App.ProcessMouseButtonUpEvent(Pointer(false));return true;
}
void Write(const FString& File,const FJson& Value)
{FString Text;FJsonSerializer::Serialize(Value.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));FFileHelper::SaveStringToFile(Text,*File);}
FJson Geometry(UUserWidget* UI)
{
    auto Result=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Widgets;
    Walk(UI->TakeWidget(),[&](const TSharedRef<SWidget>& W)
    {
        const FString Type=W->GetTypeAsString();
        if(Type!=TEXT("SBackgroundBlur")&&Type!=TEXT("SColdSteelSkillTreeCanvas")&&Type!=TEXT("STextBlock")&&Type!=TEXT("SButton"))return;
        auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("type"),Type);
        const auto G=W->GetCachedGeometry();const auto P=G.GetAbsolutePosition(),Size=G.GetAbsoluteSize();
        Item->SetNumberField(TEXT("x"),P.X);Item->SetNumberField(TEXT("y"),P.Y);Item->SetNumberField(TEXT("w"),Size.X);Item->SetNumberField(TEXT("h"),Size.Y);
        if(Type==TEXT("STextBlock")){auto T=StaticCastSharedRef<STextBlock>(W);Item->SetStringField(TEXT("text"),T->GetText().ToString());Item->SetNumberField(TEXT("font_size"),T->GetFont().Size);}
        if(Type==TEXT("SColdSteelSkillTreeCanvas")){auto C=StaticCastSharedRef<SColdSteelSkillTreeCanvas>(W);const auto& L=C->GetLayout();Item->SetNumberField(TEXT("card_w"),L.Config.W);Item->SetNumberField(TEXT("card_h"),L.Config.H);Item->SetNumberField(TEXT("zoom"),C->GetZoom());}
        Widgets.Add(MakeShared<FJsonValueObject>(Item));
    });Result->SetArrayField(TEXT("widgets"),Widgets);return Result;
}
struct FRun
{
    TWeakObjectPtr<UWorld> World;TWeakObjectPtr<ATemperateHillsWorld> Hills;TWeakObjectPtr<AHillsBlacksmith> Shop;TWeakObjectPtr<AChapelNun> Nun;TWeakObjectPtr<ACameraActor> Camera;
    FString Out,Trace,LastShot;TArray<TSharedPtr<FJsonValue>> Checks;
    double Began=FPlatformTime::Seconds(),Next=0.;int32 Stage=0,Errors=0;
    bool bShopRetried=false;
    FVector TalkAt;FRotator TalkView;
    void Record(const FString& Message){Trace+=Message+LINE_TERMINATOR;UE_LOG(LogTemp,Display,TEXT("VILLAGE_CONSTRUCTION_REVIEW %s"),*Message);FFileHelper::SaveStringToFile(Trace,*(Out/TEXT("trace.txt")));}
    void Check(bool Pass,const FString& Name)
    {auto J=MakeShared<FJsonObject>();J->SetStringField(TEXT("name"),Name);J->SetBoolField(TEXT("pass"),Pass);Checks.Add(MakeShared<FJsonValueObject>(J));if(!Pass)++Errors;Record((Pass?TEXT("PASS "):TEXT("FAIL "))+Name);}
    FJson Buildings()
    {
        auto J=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Parts;int32 Ruined=0,Repaired=0,Rubble=0;
        for(auto* C:TInlineComponentArray<UInstancedStaticMeshComponent*>(Hills.Get()))
        {
            if(!C->ComponentHasTag(TEXT("HillsVillagePerimeter")))continue;
            const FString Name=GetNameSafe(C->GetStaticMesh());const int32 Count=C->GetInstanceCount();
            if(Name.Contains(TEXT("Ruined")))Ruined+=Count;if(Name.Contains(TEXT("Repaired")))Repaired+=Count;if(Name.Contains(TEXT("Rubble")))Rubble+=Count;
            auto P=MakeShared<FJsonObject>();P->SetStringField(TEXT("mesh"),Name);P->SetNumberField(TEXT("count"),Count);P->SetBoolField(TEXT("visible"),C->IsVisible());P->SetNumberField(TEXT("collision"),int32(C->GetCollisionEnabled()));Parts.Add(MakeShared<FJsonValueObject>(P));
        }
        for(TActorIterator<AVillageDefenseSection> It(World.Get());It;++It)
        {
            if(It->GetHealth()<=0.f||Cast<AVillageDefenseGate>(*It))continue;
            const FString Name=GetNameSafe(It->GetMasonry()->GetStaticMesh());
            Ruined+=Name.Contains(TEXT("Ruined"));Repaired+=Name.Contains(TEXT("Repaired"));
        }
        J->SetNumberField(TEXT("wall_ruined_instances"),Ruined);J->SetNumberField(TEXT("wall_repaired_instances"),Repaired);J->SetNumberField(TEXT("wall_rubble_instances"),Rubble);J->SetArrayField(TEXT("wall_parts"),Parts);
        int32 RuinShown=0,RepairShown=0,RuinCollision=0,RepairCollision=0;
        if(Shop.IsValid())for(auto A:Shop->ShopAssemblies)if(A)for(auto* C:TInlineComponentArray<UPrimitiveComponent*>(A.Get()))
        {
            const bool Visible=C->IsVisible()&&!C->bHiddenInGame,Collision=C->GetCollisionEnabled()!=ECollisionEnabled::NoCollision;
            if(C->ComponentHasTag(TEXT("VillageShop.Ruined"))){RuinShown+=Visible;RuinCollision+=Collision;}
            if(C->ComponentHasTag(TEXT("VillageShop.Repaired"))){RepairShown+=Visible;RepairCollision+=Collision;}
        }
        J->SetNumberField(TEXT("shop_ruined_visible"),RuinShown);J->SetNumberField(TEXT("shop_repaired_visible"),RepairShown);J->SetNumberField(TEXT("shop_ruined_collision"),RuinCollision);J->SetNumberField(TEXT("shop_repaired_collision"),RepairCollision);
        J->SetBoolField(TEXT("wall_repaired"),Hills->IsVillageWallRepaired());J->SetBoolField(TEXT("shop_repaired"),Hills->IsVillageBlacksmithRepaired());J->SetBoolField(TEXT("station_available"),Shop.IsValid()&&Shop->IsSceneStationAvailable());return J;
    }
    void Shot(const FString& Name,bool UI=true)
    {LastShot=Out/(Name+TEXT(".png"));FScreenshotRequest::RequestScreenshot(LastShot,UI,false);Record(TEXT("screenshot ")+LastShot);}
    bool ClearShopTestOccupants()
    {
        // Only this opt-in isolated world is changed. Keep the production occupancy
        // guard intact and document every moved fixture before retrying the UI.
        TArray<FOverlapResult> Hits;TSet<AActor*> Actors;
        auto* W=World.Get();const FVector Center=Shop->GetActorTransform().TransformPosition(Shop->RepairAreaCenter);
        W->OverlapMultiByObjectType(Hits,Center,Shop->GetActorQuat(),FCollisionObjectQueryParams(ECC_Pawn),
            FCollisionShape::MakeBox(Shop->RepairAreaHalfExtent),FCollisionQueryParams(SCENE_QUERY_STAT(VillageReviewOccupants),false,Shop.Get()));
        auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Items;
        for(const auto& Hit:Hits)
        {
            auto* A=Hit.GetActor();if(!A||Actors.Contains(A))continue;Actors.Add(A);
            auto Item=MakeShared<FJsonObject>();Item->SetStringField(TEXT("actor"),A->GetPathName());Item->SetStringField(TEXT("class"),A->GetClass()->GetPathName());
            Item->SetStringField(TEXT("before"),A->GetActorLocation().ToString());
            const bool CanMove=Cast<APawn>(A)&&A!=W->GetFirstPlayerController()->GetPawn()&&A!=Nun.Get();
            Item->SetBoolField(TEXT("isolated_fixture_moved"),CanMove);
            if(CanMove)
            {
                if(auto* Character=Cast<ACharacter>(A))Character->GetCharacterMovement()->DisableMovement();
                FVector Destination=Center+FVector(6000.,Actors.Num()*300.,0.);Destination.Z=Hills->Height(Destination.X,Destination.Y)+250.;
                A->SetActorLocation(Destination,false,nullptr,ETeleportType::TeleportPhysics);
                Item->SetStringField(TEXT("after"),A->GetActorLocation().ToString());
            }
            Items.Add(MakeShared<FJsonValueObject>(Item));
        }
        Report->SetArrayField(TEXT("occupants"),Items);Write(Out/TEXT("blacksmith-occupants.json"),Report);
        return !Shop->RepairAreaOccupied();
    }
    void View(bool Wall)
    {
        auto* W=World.Get();auto* PC=W->GetFirstPlayerController();if(!Camera.IsValid())Camera=W->SpawnActor<ACameraActor>();
        FVector Eye,Target;
        if(Wall)
        {
            const auto& V=Hills->GetVillageSite();const auto P=V.World(-V.PadHalfX-1500.,-V.PadHalfY-1400.);const auto T=V.World(-V.PadHalfX+2500.,-V.PadHalfY+2500.);
            Eye=FVector(P,Hills->Height(P.X,P.Y)+2100.);Target=FVector(T,Hills->Height(T.X,T.Y)+100.);
        }
        else
        {
            Eye=Shop->GetActorTransform().TransformPosition(Shop->RepairAreaCenter+FVector(1600,-2200,650));
            Target=Shop->GetActorTransform().TransformPosition(Shop->RepairAreaCenter-FVector(0,0,170));
        }
        PC->GetPawn()->SetActorHiddenInGame(true);PC->GetPawn()->SetActorLocation(Eye+FVector(0,0,400),false,nullptr,ETeleportType::TeleportPhysics);
        Camera->SetActorLocationAndRotation(Eye,(Target-Eye).Rotation());Camera->GetCameraComponent()->SetFieldOfView(60);PC->SetViewTarget(Camera.Get());
    }
    void Talk()
    {
        auto* PC=Cast<AFPSGAMEPlayerController>(World->GetFirstPlayerController());PC->GetPawn()->SetActorLocation(TalkAt,false,nullptr,ETeleportType::TeleportPhysics);PC->SetViewTarget(PC->GetPawn());PC->SetControlRotation(TalkView);PC->PlayerCameraManager->UpdateCamera(0);PC->GetChapelDialogue()->Open(Nun.Get());
    }
    bool Finish()
    {
        auto J=MakeShared<FJsonObject>();J->SetBoolField(TEXT("pass"),Errors==0);J->SetNumberField(TEXT("errors"),Errors);J->SetArrayField(TEXT("checks"),Checks);J->SetStringField(TEXT("scope"),TEXT("rendered standalone UI clicks and same-world immediate building replacement; not multiplayer"));Write(Out/TEXT("result.json"),J);
        auto* W=World.Get();const FName Context=GEngine->GetWorldContextFromWorldChecked(W).ContextHandle;const int32 Exit=Errors?1:0;
        UGameplayStatics::OpenLevel(W,TEXT("/Engine/Maps/Entry"));FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Context,Exit](float)
        {const auto* C=GEngine->GetWorldContextFromHandle(Context);if(C&&C->World()&&C->World()->GetOutermost()->GetName()!=TEXT("/Engine/Maps/Entry"))return true;FPlatformMisc::RequestExitWithStatus(false,Exit);return false;}),3.f);return false;
    }
    bool Tick(float)
    {
        auto* W=World.Get();if(!W)return false;const double Now=FPlatformTime::Seconds();
        if(Now-Began>900){Check(false,TEXT("run timeout stage ")+FString::FromInt(Stage));return Finish();}if(Now<Next)return true;
        if(!LastShot.IsEmpty()){if(!IFileManager::Get().FileExists(*LastShot))return true;LastShot.Reset();}
        auto* PC=Cast<AFPSGAMEPlayerController>(W->GetFirstPlayerController());if(!PC||!PC->GetCharacter()||!PC->GetColdSteelHUD())return true;
        auto* D=PC->GetChapelDialogue();auto* HUD=PC->GetColdSteelHUD();
        if(Stage==0)
        {
            for(TActorIterator<ATemperateHillsWorld> It(W);It;++It)Hills=*It;
            for(TActorIterator<AChapelNun> It(W);It;++It)Nun=*It;
            for(TActorIterator<AHillsBlacksmith> It(W);It;++It)Shop=*It;
            if(!Hills.IsValid()||!Hills->bReady||!Nun.IsValid()||!Shop.IsValid()||!Shop->GetOwner())return true;
            Check(FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()).Contains(TEXT("VillageConstructionReview")),TEXT("isolated Saved directory"));
            auto* M=W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();Check(M&&M->ProfileSlot().Contains(TEXT("VillageConstructionReview")),TEXT("isolated player profile"));
            Check(!Hills->IsVillageWallRepaired()&&!Hills->IsVillageBlacksmithRepaired(),TEXT("both buildings initially ruined"));
            Check(W->GetGameViewport()->Viewport->GetSizeXY()==FIntPoint(1920,1080),TEXT("actual viewport is 1920 x 1080"));
            PC->GetCharacter()->GetCharacterMovement()->DisableMovement();
            TalkAt=Nun->GetActorLocation()+Nun->GetActorForwardVector()*180.+FVector(0,0,6);
            TalkView=(Nun->GetActorLocation()+FVector(0,0,45)-TalkAt-FVector(0,0,60)).Rotation();
            Talk();Next=Now+60.;++Stage;return true;
        }
        Record(FString::Printf(TEXT("stage %d"),Stage));
        auto* Dialogue=Screen<UColdSteelNpcDialogue>(W);
        switch(Stage)
        {
        case 1:Check(D->IsOpen(),TEXT("conversation opens with real range/visibility validation"));if(!D->IsOpen())return Finish();Check(Click(W,Dialogue,TEXT("继续交谈")),TEXT("first dialogue click"));break;
        case 2:Check(Click(W,Dialogue,TEXT("继续交谈")),TEXT("second dialogue click"));break;
        case 3:Check(Click(W,Dialogue,TEXT("1  建设村庄")),TEXT("construction entry click"));break;
        case 4:Check(Dialogue&&HasText(Dialogue->TakeWidget(),TEXT("解锁并修复")),TEXT("village detail ready"));Check(!PC->CanOpenGameMenu(),TEXT("menu entry hidden while construction owns input"));if(Dialogue)Write(Out/TEXT("village-ui.json"),Geometry(Dialogue));Write(Out/TEXT("buildings-before.json"),Buildings());Shot(TEXT("village-ui-before"));break;
        case 5:D->Close();HUD->OpenSkillTree();break;
        case 6:{auto* Skill=Screen<UColdSteelSkillTreeScreen>(W);Check(Skill!=nullptr,TEXT("real skill screen open"));Check(!PC->CanOpenGameMenu(),TEXT("menu entry hidden while skill tree owns input"));if(Skill)Write(Out/TEXT("skill-ui.json"),Geometry(Skill));Shot(TEXT("skill-ui"));break;}
        case 7:HUD->CloseSkillTree();View(true);Next=Now+15.;++Stage;return true;
        case 8:Shot(TEXT("wall-before"),false);break;
        case 9:View(false);Next=Now+15.;++Stage;return true;
        case 10:Shot(TEXT("blacksmith-before"),false);break;
        case 11:Talk();break;
        case 12:Check(Click(W,Dialogue,TEXT("继续交谈")),TEXT("reopen dialogue 1"));break;
        case 13:Check(Click(W,Dialogue,TEXT("继续交谈")),TEXT("reopen dialogue 2"));break;
        case 14:Check(Click(W,Dialogue,TEXT("1  建设村庄")),TEXT("reopen construction"));break;
        case 15:
        {
            const double Start=FPlatformTime::Seconds();Check(Click(W,Dialogue,TEXT("解锁并修复")),TEXT("wall real unlock button clicked"));
            const auto State=Buildings();State->SetNumberField(TEXT("click_return_ms"),(FPlatformTime::Seconds()-Start)*1000.);Write(Out/TEXT("wall-immediate.json"),State);
            Check(Hills->IsVillageWallRepaired()&&State->GetNumberField(TEXT("wall_ruined_instances"))==0&&State->GetNumberField(TEXT("wall_rubble_instances"))==0&&State->GetNumberField(TEXT("wall_repaired_instances"))>0,TEXT("whole wall replaced before click dispatch returned"));break;
        }
        case 16:Shot(TEXT("village-ui-wall-repaired"));break;
        case 17:Check(Click(W,Dialogue,TEXT("生产")),TEXT("production tab clicked"));break;
        case 18:
        {
            const double Start=FPlatformTime::Seconds();Check(Click(W,Dialogue,TEXT("解锁并修复")),TEXT("blacksmith real unlock button clicked"));
            const auto State=Buildings();State->SetNumberField(TEXT("click_return_ms"),(FPlatformTime::Seconds()-Start)*1000.);Write(Out/TEXT("blacksmith-immediate.json"),State);
            State->SetStringField(TEXT("ui_message"),D->Message);
            if(!Hills->IsVillageBlacksmithRepaired()&&Shop->RepairAreaOccupied()&&!bShopRetried)
            {
                Write(Out/TEXT("blacksmith-occupied-attempt.json"),State);
                Check(!Hills->IsVillagePlanUnlocked(TEXT("blacksmith"))&&D->Message.Contains(TEXT("有人或动物")),TEXT("occupied shop rejects unlock without committing a plan"));
                Check(ClearShopTestOccupants(),TEXT("isolated shop repair area cleared before retry"));
                bShopRetried=true;Next=Now+.5;return true;
            }
            Write(Out/TEXT("blacksmith-immediate.json"),State);
            Check(Hills->IsVillageBlacksmithRepaired()&&State->GetNumberField(TEXT("shop_ruined_visible"))==0&&State->GetNumberField(TEXT("shop_ruined_collision"))==0&&State->GetNumberField(TEXT("shop_repaired_visible"))>0&&Shop->IsSceneStationAvailable(),TEXT("shop visuals collision and station switch before click dispatch returned"));break;
        }
        case 19:Check(Click(W,Dialogue,TEXT("全部")),TEXT("all construction tab clicked"));break;
        case 20:Shot(TEXT("village-ui-complete"));break;
        case 21:D->Close();View(true);Next=Now+12.;++Stage;return true;
        case 22:Shot(TEXT("wall-after"),false);break;
        case 23:View(false);Next=Now+12.;++Stage;return true;
        case 24:Shot(TEXT("blacksmith-after"),false);break;
        case 25:
        {
            auto* Save=Cast<UTemperateHillsSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TemperateHills_ChapelReview"),0));
            Check(Save&&Save->bVillageWallRepaired&&Save->bVillageBlacksmithRepaired&&(Save->VillagePlansUnlocked&3)==3&&Save->VillagePlanVersion==2,TEXT("both unlocks and repairs saved together"));return Finish();
        }
        }
        ++Stage;Next=Now+2.;return true;
    }
};
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillageConstructionReview"),TEXT("Opt-in real UI/screenshots and village unlock replacement review."),FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!W||!W->IsGameWorld()||!FParse::Param(FCommandLine::Get(),TEXT("VillageConstructionReview")))return;
    auto R=MakeShared<FRun>();R->World=W;FParse::Value(FCommandLine::Get(),TEXT("VillageConstructionOut="),R->Out);
    if(R->Out.IsEmpty())return;IFileManager::Get().MakeDirectory(*R->Out,true);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([R](float Dt){return R->Tick(Dt);}),.25f);
}));
}
#endif
