// Included by SpellbookFocus.cpp; explicit, editor-only reproduction command.
#include "SpellbookComponent.h"
#include "../../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Containers/Ticker.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "InputKeyEventArgs.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"

#if WITH_EDITOR
namespace
{
FAutoConsoleCommandWithWorldAndArgs Repro(TEXT("fps.Spellbook.ReproReturn"),
    TEXT("Reproduce RMB focus/return on the equipped book; capture this transition only."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateLambda([](const TArray<FString>& Args,UWorld* World)
{
    if((!World||!World->IsGameWorld())&&GEngine)
        for(const auto& C:GEngine->GetWorldContexts())if(C.World()&&C.World()->IsGameWorld()){World=C.World();break;}
    auto* PC=World?World->GetFirstPlayerController():nullptr;
    auto* Pawn=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    auto* Book=Pawn?Pawn->FindComponentByClass<USpellbookComponent>():nullptr;
    if(!Book||!Book->OwnsLeftHand())return;
    struct FRun { float Start=0.f,ClosedAt=-1.f,ShotAt=-1.f; bool Shot=false; FString Dir,Rows; };
    auto Run=MakeShared<FRun>();Run->Start=World->GetTimeSeconds();
    if(Args.Num()>1)Run->ShotAt=FCString::Atof(*Args[1]);
    Run->Dir=FPaths::ProjectDir()/TEXT("SourceAssets/SpellbookEvildeer20261009/Focus/Debug20261010")/(Args.IsEmpty()?TEXT("capture"):FPaths::GetCleanFilename(Args[0]));
    IFileManager::Get().MakeDirectory(*Run->Dir,true);
    if(Book->IsFocusActive())Book->CancelFocus();
    PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1.f));
    PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0.f));
    TWeakObjectPtr<USpellbookComponent> WeakBook(Book);TWeakObjectPtr<APlayerController> WeakPC(PC);
    FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Run,WeakBook,WeakPC](float)
    {
        auto* B=WeakBook.Get();auto* Controller=WeakPC.Get();if(!B||!Controller)return false;
        const float Now=B->GetWorld()->GetTimeSeconds(),Age=Now-Run->Start;
        if(Age<.25f)return true;
        if(Run->ClosedAt<0.f&&!B->IsFocusActive())
        {FFileHelper::SaveStringToFile(TEXT("RMB did not enter focus; no equipment/profile was changed."),*(Run->Dir/TEXT("failed.txt")));return false;}
        if(Age>=2.f&&Run->ClosedAt<0.f)
        {
            Controller->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Pressed,1.f));
            Controller->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,IE_Released,0.f));
            Run->ClosedAt=Now;
        }
        auto* Camera=B->GetOwner()->FindComponentByClass<UCameraComponent>();
        TArray<USkeletalMeshComponent*> Meshes;B->GetOwner()->GetComponents(Meshes);
        USkeletalMeshComponent* Floating=nullptr;
        for(auto* M:Meshes)if(M->GetFName()==TEXT("SpellbookFloatingPages")){Floating=M;break;}
        if(!Floating||!Camera)return false;
        const float T=Run->ClosedAt<0.f?-1.f:Now-Run->ClosedAt;
        auto* Arm=B->ArmsMesh();const auto View=Camera->GetComponentTransform();
        const FVector Hand=View.InverseTransformPosition(Arm->GetSocketLocation(TEXT("hand_l")));
        const FVector Index=View.InverseTransformPosition(Arm->GetSocketLocation(TEXT("index_01_l")));
        const FVector Pinky=View.InverseTransformPosition(Arm->GetSocketLocation(TEXT("pinky_01_l")));
        const FVector Palm=((Index-Hand)^(Pinky-Hand)).GetSafeNormal();
        const FVector BookPos=Floating->GetComponentTransform().GetRelativeTransform(View).GetLocation();
        const FQuat Cover=Floating->GetSocketTransform(TEXT("Cover_Front"),RTS_Component).GetRotation();
        const FQuat Root=Floating->GetSocketTransform(TEXT("Book_Root"),RTS_Component).GetRotation();
        const FVector BookScale=Floating->GetComponentTransform().GetScale3D();
        const FVector HandScale=Arm->GetSocketTransform(TEXT("hand_l"),RTS_World).GetScale3D();
        const FVector HeldScale=B->BookMesh()->GetComponentTransform().GetScale3D();
        Run->Rows+=FString::Printf(TEXT("%.5f,%d,%d,%.4f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.4f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f,%.5f\n"),T,B->IsFocusActive(),Floating->IsVisible(),
            FMath::RadiansToDegrees(Cover.AngularDistance(Root)),BookPos.X,BookPos.Y,BookPos.Z,Hand.X,Hand.Y,Hand.Z,Palm.Z,
            BookScale.X,BookScale.Y,BookScale.Z,HandScale.X,HandScale.Y,HandScale.Z,HeldScale.X,HeldScale.Y,HeldScale.Z);
        // Trace-only by default. A single optional capture avoids repeated PNG
        // compression stalls skipping the short phases being investigated.
        if(!Run->Shot&&Run->ShotAt>=0.f&&T>=Run->ShotAt)
        {
            FScreenshotRequest::RequestScreenshot(Run->Dir/TEXT("phase.png"),false,false);Run->Shot=true;
        }
        if(T<SpellbookFocusMotion::ReturnLength+.3f)return true;
        FFileHelper::SaveStringToFile(TEXT("close_age,active,floating,cover_degrees,book_x,book_y,book_z,hand_x,hand_y,hand_z,palm_up,book_scale_x,book_scale_y,book_scale_z,hand_scale_x,hand_scale_y,hand_scale_z,held_scale_x,held_scale_y,held_scale_z\n")+Run->Rows,*(Run->Dir/TEXT("transition.csv")));
        UE_LOG(LogTemp,Display,TEXT("SPELLBOOK_RETURN_REPRO_COMPLETE %s"),*Run->Dir);return false;
    }));
}));
}
#endif
