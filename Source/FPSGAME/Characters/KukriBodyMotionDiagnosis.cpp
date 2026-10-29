#if WITH_EDITOR
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSBodyKukriMotion.h"
#include "Animation/AnimSequence.h"
#include "AssetCompilingManager.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

namespace KukriBodyMotionDiagnosis
{
static TSharedPtr<FJsonValue> Vector(const FVector& P)
{
    TArray<TSharedPtr<FJsonValue>> V;
    for(double X:{P.X,P.Y,P.Z})V.Add(MakeShared<FJsonValueNumber>(X));
    return MakeShared<FJsonValueArray>(V);
}
static void Run(const TArray<FString>& Args)
{
    if(Args.IsEmpty())return;
    FString Text;TSharedPtr<FJsonObject> Root;
    const FString Config=Args.Num()>1?Args[1]:FPaths::ProjectContentDir()/TEXT("ColdSteelData/player_body.json");
    const bool NativeOnly=Args.Num()>2&&Args[2]==TEXT("native-only");
    if(!FFileHelper::LoadFileToString(Text,*Config)||!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Root))return;
    auto Report=MakeShared<FJsonObject>();TArray<TSharedPtr<FJsonValue>> Rows,Errors;
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("KukriBodyMotionDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Floor=World->SpawnActor<AActor>();
    auto* Box=NewObject<UBoxComponent>(Floor);Floor->AddInstanceComponent(Box);Floor->SetRootComponent(Box);
    Box->SetBoxExtent(FVector(10000,10000,5));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
    Box->SetCollisionObjectType(ECC_WorldStatic);Box->SetCollisionResponseToAllChannels(ECR_Block);
    Box->RegisterComponentWithWorld(World);Floor->SetActorLocation(FVector(0,0,-5));
    struct FScenario { const TCHAR* Name;float Speed,Direction;bool Crouched; };
    const FScenario Scenarios[]={{TEXT("stand"),0,0,false},{TEXT("walk"),150,0,false},
        {TEXT("run"),450,0,false},{TEXT("crouch"),0,0,true},{TEXT("crouch_walk"),100,0,true},{TEXT("strafe"),150,90,false}};
    TArray<TPair<FString,TSharedPtr<FJsonObject>>> Bodies;
    Bodies.Emplace(TEXT("jason"),Root);
    const TSharedPtr<FJsonObject>* Variants=nullptr;
    if(Root->TryGetObjectField(TEXT("body_variants"),Variants))
        for(const auto& Pair:(*Variants)->Values)
            if(const auto Variant=Pair.Value->AsObject();Variant&&Variant->GetBoolField(TEXT("ready")))Bodies.Emplace(Pair.Key,Variant);
    for(const auto& BodyConfig:Bodies)
    {
        const auto Cfg=BodyConfig.Value;
        auto* Mesh=LoadObject<USkeletalMesh>(nullptr,*Cfg->GetStringField(TEXT("body_mesh")));if(!Mesh)continue;
        TMap<FName,TObjectPtr<UAnimSequence>> Clips;
        for(const auto& Pair:Cfg->GetObjectField(TEXT("clips"))->Values)
            if(Pair.Key.ToView().StartsWith(TEXT("Unarmed."))||Pair.Key.ToView().StartsWith(TEXT("Kukri.")))
                if(auto* Clip=LoadObject<UAnimSequence>(nullptr,*Pair.Value->AsString()))Clips.Add(*Pair.Key,Clip);
        FAssetCompilingManager::Get().FinishAllCompilation();
        auto* Actor=World->SpawnActor<ACharacter>();Actor->SetActorLocation(FVector(0,0,96));
        auto* Body=Actor->GetMesh();Body->SetRelativeTransform(FTransform(FVector(0,0,-96)));
        // Match the actual player body by default. A native-only result cannot
        // establish what the visible mesh emits after its asset post-process.
        Body->SetSkeletalMeshAsset(Mesh);Body->SetDisablePostProcessBlueprint(NativeOnly);
        Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Body->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        Actor->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
        for(const auto& Pair:Clips)if(Pair.Key.ToString().StartsWith(TEXT("Kukri.FullBody.")))
        {
            const FString Role=Pair.Key.ToString().RightChop(15);
            if(Pair.Value->GetSkeleton()!=Mesh->GetSkeleton())
            {Errors.Add(MakeShared<FJsonValueString>(BodyConfig.Key+TEXT(": skeleton mismatch ")+Role));continue;}
            for(const auto& Case:Scenarios)
            {
                Body->SetAnimInstanceClass(nullptr);Body->SetAnimInstanceClass(UFPSPlayerBodyAnimInstance::StaticClass());
                auto* Anim=CastChecked<UFPSPlayerBodyAnimInstance>(Body->GetAnimInstance());Anim->Clips=Clips;
                Anim->BodyState.Family=TEXT("Kukri");Anim->BodyState.Weapon=TEXT("ue_kukri");
                Anim->BodyState.bCrouched=Case.Crouched;Anim->Speed=Case.Speed;Anim->Direction=Case.Direction;
                const TArray<TSharedPtr<FJsonValue>>* Scale=nullptr;
                if(Cfg->TryGetArrayField(TEXT("pose_scale"),Scale)&&Scale->Num()>=3)
                    Anim->PoseScale=FVector((*Scale)[0]->AsNumber(),(*Scale)[1]->AsNumber(),(*Scale)[2]->AsNumber());
                const auto Tick=[&]()
                {
                    Anim->Clock+=1.f/60.f;
                    const float Heading=FMath::DegreesToRadians(Case.Direction);
                    Actor->AddActorWorldOffset(FVector(-FMath::Sin(Heading),FMath::Cos(Heading),0)*Case.Speed/60.f);
                    Body->TickAnimation(1.f/60.f,false);Body->RefreshBoneTransforms();
                };
                for(int32 Warm=0;Warm<24;++Warm)Tick();
                auto& S=Anim->BodyState;S.bHasActionProgress=true;S.ActionWeight=1.f;S.ContactFraction=.3f;S.ReleaseFraction=.55f;
                if(Role==TEXT("Slash1")){S.Action=EFPSBodyAction::Strike;S.ActionVariant=TEXT("Attack");}
                else if(Role==TEXT("Slash2")){S.Action=EFPSBodyAction::Strike;S.ActionVariant=TEXT("Attack2");}
                else if(Role==TEXT("Thrust")){S.Action=EFPSBodyAction::Thrust;S.ActionVariant=TEXT("Attack3");}
                else if(Role==TEXT("Charge")){S.Action=EFPSBodyAction::Charge;S.ActionVariant=TEXT("HeavyCharge");}
                else if(Role==TEXT("Heavy")){S.Action=EFPSBodyAction::HeavyStrike;S.ActionVariant=TEXT("HeavyRelease");S.ContactFraction=.0643f;S.ReleaseFraction=.1143f;}
                else if(Role==TEXT("Dash")){S.Action=EFPSBodyAction::HeavyStrike;S.ActionVariant=TEXT("SprintAttack");}
                else if(Role==TEXT("Uppercut")){S.Action=EFPSBodyAction::HeavyStrike;S.ActionVariant=TEXT("Uppercut");}
                else if(Role==TEXT("Pommel")){S.Action=EFPSBodyAction::Pommel;S.ActionVariant=TEXT("QuickPommel");}
                else if(Role==TEXT("Equip")){S.Action=EFPSBodyAction::Equip;S.ActionVariant=TEXT("Equip");}
                else if(Role.StartsWith(TEXT("Whirlwind"))){S.Action=EFPSBodyAction::Whirlwind;S.ActionVariant=TEXT("Whirlwind");S.ContactFraction=.25f;S.ReleaseFraction=.75f;}
                auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("body"),BodyConfig.Key);Row->SetStringField(TEXT("role"),Role);
                Row->SetStringField(TEXT("scenario"),Case.Name);Row->SetStringField(TEXT("asset"),Pair.Value->GetPathName());
                FVector Lo[2]={FVector(DBL_MAX),FVector(DBL_MAX)},Hi[2]={FVector(-DBL_MAX),FVector(-DBL_MAX)};
                double FlexLo[2]={180,180},FlexHi[2]={0,0};TArray<TSharedPtr<FJsonValue>> Samples;
                bool Finite=true;
                for(int32 Frame=0;Frame<=60;++Frame)
                {
                    const float P=Frame/60.f;S.ActionProgress=P;
                    if(Role==TEXT("Whirlwind.Start"))S.ActionProgress=P*.249f;
                    if(Role==TEXT("Whirlwind.Loop"))S.ActionProgress=.25f+P*.499f;
                    if(Role==TEXT("Whirlwind.End"))S.ActionProgress=.75f+P*.25f;
                    if(S.Action==EFPSBodyAction::Whirlwind)
                        Actor->SetActorRotation(FRotator(0,-720.f*FMath::Clamp((S.ActionProgress-.25f)/.5f,0.f,1.f),0));
                    Tick();auto Sample=MakeShared<FJsonObject>();Sample->SetNumberField(TEXT("progress"),P);
                    for(int32 I=0;I<2;++I)
                    {
                        const TCHAR* Side=I==0?TEXT("r"):TEXT("l");
                        const FVector H=Body->GetSocketTransform(FName(FString(TEXT("thigh_"))+Side),RTS_Component).GetLocation();
                        const FVector K=Body->GetSocketTransform(FName(FString(TEXT("calf_"))+Side),RTS_Component).GetLocation();
                        const FVector F=Body->GetSocketTransform(FName(FString(TEXT("foot_"))+Side),RTS_Component).GetLocation();
                        const double Flex=180.-FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct((H-K).GetSafeNormal(),(F-K).GetSafeNormal()),-1.,1.)));
                        Finite&=!F.ContainsNaN()&&FMath::IsFinite(Flex);
                        if(Frame>=9&&Frame<=49){FlexLo[I]=FMath::Min(FlexLo[I],Flex);FlexHi[I]=FMath::Max(FlexHi[I],Flex);}
                        Lo[I]=Lo[I].ComponentMin(F);Hi[I]=Hi[I].ComponentMax(F);
                        Sample->SetField(FString(TEXT("foot_"))+Side,Vector(F));Sample->SetNumberField(FString(TEXT("knee_flex_"))+Side,Flex);
                    }
                    Sample->SetField(TEXT("pelvis"),Vector(Body->GetSocketTransform(TEXT("pelvis"),RTS_Component).GetLocation()));
                    Sample->SetField(TEXT("hand_r"),Vector(Body->GetSocketTransform(TEXT("hand_r"),RTS_Component).GetLocation()));
                    if(Frame%3==0)Samples.Add(MakeShared<FJsonValueObject>(Sample));
                }
                Row->SetBoolField(TEXT("finite"),Finite);
                for(int32 I=0;I<2;++I)
                {
                    const FString Side=I==0?TEXT("right"):TEXT("left");
                    Row->SetNumberField(Side+TEXT("_flex_min"),FlexLo[I]);Row->SetNumberField(Side+TEXT("_flex_max"),FlexHi[I]);
                    Row->SetField(Side+TEXT("_ankle_range"),Vector(Hi[I]-Lo[I]));
                }
                Row->SetArrayField(TEXT("samples"),Samples);Rows.Add(MakeShared<FJsonValueObject>(Row));
                if(!Finite)Errors.Add(MakeShared<FJsonValueString>(BodyConfig.Key+TEXT(": nonfinite ")+Role));
                Actor->SetActorLocation(FVector(0,0,96));
            }
        }
        Actor->Destroy();
    }
    Report->SetArrayField(TEXT("rows"),Rows);Report->SetArrayField(TEXT("errors"),Errors);
    Report->SetBoolField(TEXT("post_process_enabled"),!NativeOnly);
    Report->SetStringField(TEXT("scope"),TEXT("Animation graph with configured body mesh, transient flat-floor fixture; no actual player executor, PIE or visual acceptance."));
    FString Output;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Output));FFileHelper::SaveStringToFile(Output,*Args[0]);
    World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("KUKRI_BODY_DIAGNOSIS rows=%d errors=%d %s"),Rows.Num(),Errors.Num(),*Args[0]);
}
static FAutoConsoleCommand Command(TEXT("fps.body.DiagnoseKukriMotion"),TEXT("Requested Kukri full-body diagnosis: output.json [configuration.json] [native-only]."),FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}
#endif
