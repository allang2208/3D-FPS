#include "RuneSwordAuditCommandlet.h"
#include "RuneSwordComponent.h"
#include "../FPSGAMECharacter.h"
#include "../BallisticAuditTarget.h"
#include "../Monsters/NurseZombie.h"
#include "Animation/AnimSequence.h"
#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"

namespace
{
// Frozen V10 query, used only to preserve failure evidence against the same fixtures.
TArray<FHitResult> RuneLegacyQuery(UWorld* World,AActor* Owner,const FRuneSwordBladeSample& From,
    const FRuneSwordBladeSample& To,float Reach,const TSet<TWeakObjectPtr<AActor>>& Prior)
{
    TArray<FHitResult> Out;auto Seen=Prior;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(RuneSwordLegacyAudit),false,Owner);
    for(int I=0;I<=10;++I)
    {
        TArray<FHitResult> Hits;
        World->SweepMultiByChannel(Hits,FMath::Lerp(From.Base,From.Tip,I/10.f),FMath::Lerp(To.Base,To.Tip,I/10.f),FQuat::Identity,ECC_Visibility,FCollisionShape::MakeSphere(4),Q);
        for(const auto& Hit:Hits)
        {
            auto* Target=Hit.GetActor();if(!Target||Target==Owner||Seen.Contains(Target)||!Target->CanBeDamaged())continue;
            if(FVector::DistSquared(To.Origin,Hit.ImpactPoint)>FMath::Square(Reach))continue;
            FHitResult Cover;if(World->LineTraceSingleByChannel(Cover,To.Origin,Hit.ImpactPoint,ECC_Visibility,Q)&&Cover.GetActor()!=Target)continue;
            Seen.Add(Target);Out.Add(Hit);
        }
    }
    return Out;
}
}

int32 URuneSwordAuditCommandlet::Main(const FString& Params)
{
    FString Report;int32 Checks=0,Failures=0;
    auto Note=[&](const FString& Line){Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("%s"),*Line);};
    auto Check=[&](bool Pass,const FString& Name){++Checks;if(!Pass)++Failures;Note(FString::Printf(TEXT("SWORD_AUDIT %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),*Name));};
    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(true)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    UWorld* World=UWorld::CreateWorld(EWorldType::Game,false,TEXT("RuneSwordCombatAudit"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    if(!World)return 2;
    // No profile initialization, map startup, player save load, or BeginPlay.
    auto* GI=NewObject<UGameInstance>();World->SetGameInstance(GI);
    auto* Owner=World->SpawnActor<APawn>();Owner->SetActorLocation(FVector(-1000,0,0));
    TArray<AActor*> Fixtures;
    auto Target=[&](FVector Position,FVector Extent)
    {
        auto* A=World->SpawnActor<ABallisticAuditTarget>();A->FindComponentByClass<UBoxComponent>()->SetBoxExtent(Extent);
        A->SetActorLocation(Position);Fixtures.Add(A);return A;
    };
    auto Wall=[&](FVector Position,FVector Extent)
    {
        auto* A=World->SpawnActor<AActor>();auto* B=NewObject<UBoxComponent>(A);A->AddInstanceComponent(B);A->SetRootComponent(B);
        B->SetBoxExtent(Extent);B->SetCollisionProfileName(TEXT("BlockAll"));B->RegisterComponent();A->SetActorLocation(Position);A->SetCanBeDamaged(false);Fixtures.Add(A);return A;
    };
    auto Clear=[&](){for(auto* A:Fixtures)A->Destroy();Fixtures.Reset();};
    TSet<TWeakObjectPtr<AActor>> None;
    FRuneSwordBladeSample A{FVector(20,-20,0),FVector(97.6,-20,0),FVector::ZeroVector,FVector::ForwardVector};
    auto B=A;B.Base.Y=B.Tip.Y=20;
    auto* Thin=Target(FVector(23.88,0,2.5),FVector(.2));
    const auto OldGap=RuneLegacyQuery(World,Owner,A,B,180,None);
    Check(OldGap.IsEmpty(),TEXT("baseline reproduces thin edge-contact gap on 77.6 cm blade"));
    Check(RuneSwordCombat::Query(World,Owner,A,B,180,None).Num()==1,TEXT("thin target between old lanes now hits"));Clear();
    auto* First=Target(FVector(80,-10,0),FVector(2));auto* Second=Target(FVector(80,10,0),FVector(2));
    Check(RuneLegacyQuery(World,Owner,A,B,180,None).Num()==1,TEXT("baseline reproduces first body stopping cleave"));
    Check(RuneSwordCombat::Query(World,Owner,A,B,180,None).Num()==2,TEXT("one sweep reaches both bodies"));
    TSet<TWeakObjectPtr<AActor>> Prior{First};
    Check(RuneLegacyQuery(World,Owner,A,B,180,Prior).IsEmpty(),TEXT("baseline already-hit body still blocks second"));
    const auto Following=RuneSwordCombat::Query(World,Owner,A,B,180,Prior);
    Check(Following.Num()==1&&Following[0].GetActor()==Second,TEXT("already-hit body neither repeats nor shields next"));Clear();
    Target(FVector(80,10,0),FVector(2));Wall(FVector(40,0,0),FVector(2,35,30));
    Check(RuneSwordCombat::Query(World,Owner,A,B,180,None).IsEmpty(),TEXT("wall between eye and target blocks damage"));Clear();
    Target(FVector(80,10,0),FVector(2));Wall(FVector(80,-8,0),FVector(100,1,30));
    Check(RuneSwordCombat::Query(World,Owner,A,B,180,None).IsEmpty(),TEXT("wall along blade travel blocks otherwise visible target"));Clear();
    auto RearA=A,RearB=B;RearA.Base.X=RearA.Tip.X=RearB.Base.X=RearB.Tip.X=-50;
    RearA.Base.Z=RearB.Base.Z=-20;RearA.Tip.Z=RearB.Tip.Z=20;
    Target(FVector(-50,0,0),FVector(2));
    Check(RuneLegacyQuery(World,Owner,RearA,RearB,180,None).Num()==1,TEXT("baseline rear sweep damages behind player"));
    Check(RuneSwordCombat::Query(World,Owner,RearA,RearB,180,None).IsEmpty(),TEXT("backswing cannot damage rear hemisphere"));Clear();
    auto EdgeA=RearA,EdgeB=RearB;EdgeA.Base.X=EdgeA.Tip.X=EdgeB.Base.X=EdgeB.Tip.X=180;
    Target(FVector(179.8,0,0),FVector(.05));
    Check(RuneSwordCombat::Query(World,Owner,EdgeA,EdgeB,180,None).Num()==1,TEXT("contact inside 180 cm cap accepted"));Clear();
    Target(FVector(180.2,0,0),FVector(.05));
    Check(RuneSwordCombat::Query(World,Owner,EdgeA,EdgeB,180,None).IsEmpty(),TEXT("contact outside 180 cm cap rejected"));Clear();
    auto* Ignored=Target(FVector(80,0,0),FVector(3));Ignored->FindComponentByClass<UBoxComponent>()->SetCollisionResponseToChannel(ECC_Visibility,ECR_Ignore);
    Check(RuneSwordCombat::Query(World,Owner,A,B,180,None).IsEmpty(),TEXT("visibility-ignore collider not treated as damage body"));Clear();

    auto* Pawn=World->SpawnActor<AFPSGAMECharacter>();auto* PC=World->SpawnActor<APlayerController>();PC->Possess(Pawn);
    auto* Sword=Pawn->FindComponentByClass<URuneSwordComponent>();auto* Camera=Pawn->FindComponentByClass<UCameraComponent>();
    Sword->Character=Pawn;Sword->Camera=Camera;Sword->InstanceId=TEXT("isolated-audit");
    Sword->Viewmodel=NewObject<USkeletalMeshComponent>(Pawn);Pawn->AddInstanceComponent(Sword->Viewmodel);
    Sword->Viewmodel->SetupAttachment(Camera);Sword->Viewmodel->SetRelativeRotation(FRotator(0,90,0));
    Sword->Viewmodel->SetCollisionEnabled(ECollisionEnabled::NoCollision);Sword->Viewmodel->RegisterComponent();
    const FString Folder=TEXT("/Game/Weapons/AzureRunesword20260913/");
    Sword->Viewmodel->SetSkeletalMesh(LoadObject<USkeletalMesh>(nullptr,*(Folder+TEXT("SK_AzureRunesword_Manny"))));
    for(const TCHAR* Clip:{TEXT("Idle"),TEXT("Walk"),TEXT("Slash1"),TEXT("Slash2")})Sword->Animations.Add(FName(Clip),LoadObject<UAnimSequence>(nullptr,*(Folder+TEXT("A_RuneSword_")+Clip)));
    Check(Sword->Viewmodel->GetSkeletalMeshAsset()&&Sword->Animations.FindRef(TEXT("Slash1"))&&Sword->Animations.FindRef(TEXT("Slash2")),TEXT("installed sword mesh and compressed attack clips load"));
    Check(Sword->Viewmodel->DoesSocketExist(TEXT("Blade_Base"))&&Sword->Viewmodel->DoesSocketExist(TEXT("Blade_Tip")),TEXT("installed blade endpoints exist"));
    const FTransform Neutral=Pawn->GetMeleeAimTransform();
    TArray<FVector> Targets;TArray<float> TargetTimes;
    for(const FName Clip:{FName(TEXT("Slash1")),FName(TEXT("Slash2"))})
    {
        Sword->SetClip(Clip,false);float MinLength=BIG_NUMBER,MaxLength=0,MaxReach=0,MaxFront=0,BestTime=0;int32 RearSamples=0;FVector Best=Neutral.GetLocation();
        FBox Bounds(ForceInit),FrontBounds(ForceInit);
        for(int32 I=0;I<=120;++I)
        {
            Sword->SamplePose(FMath::Lerp(Sword->ContactStart,Sword->ContactEnd,I/120.f));const auto Sample=Sword->ReadBlade(Neutral);
            const float Length=FVector::Distance(Sample.Base,Sample.Tip);MinLength=FMath::Min(MinLength,Length);MaxLength=FMath::Max(MaxLength,Length);
            for(int32 J=0;J<=20;++J)
            {
                const FVector P=FMath::Lerp(Sample.Base,Sample.Tip,J/20.f),Local=Neutral.InverseTransformPosition(P);
                Bounds+=Local;if(Local.X>=0)FrontBounds+=Local;MaxReach=FMath::Max(MaxReach,float(Local.Length()));RearSamples+=Local.X<0;
                // A visible mid-blade surface, chosen independently of collision results.
                if(J==13&&Local.X>MaxFront){MaxFront=Local.X;Best=P;BestTime=FMath::Lerp(Sword->ContactStart,Sword->ContactEnd,I/120.f);}
            }
        }
        Targets.Add(Best);TargetTimes.Add(BestTime);
        Check(FMath::IsNearlyEqual(Sword->CurrentAnimation->GetPlayLength(),1.775f,.001f),Clip.ToString()+TEXT(" installed duration 1.775 s"));
        Check(MinLength>20&&MaxLength-MinLength<.1f,Clip.ToString()+TEXT(" blade length stable in compressed poses"));
        Note(FString::Printf(TEXT("SWORD_RANGE %s length_cm=%.3f..%.3f old_lane_spacing_cm=%.3f authored_max_radius_cm=%.3f bounds_min=%s bounds_max=%s rear_samples=%d"),*Clip.ToString(),MinLength,MaxLength,MaxLength/10,MaxReach,*Bounds.Min.ToString(),*Bounds.Max.ToString(),RearSamples));
        Note(FString::Printf(TEXT("SWORD_FRONT_BOUNDS %s min=%s max=%s"),*Clip.ToString(),*FrontBounds.Min.ToString(),*FrontBounds.Max.ToString()));
    }
    Sword->SetClip(TEXT("Slash1"),false);Sword->SamplePose(.92f);
    const auto Stable=Sword->ReadBlade(Pawn->GetMeleeAimTransform());const FVector VisualBefore=Sword->Viewmodel->GetSocketLocation(TEXT("Blade_Tip"));
    const FTransform CameraBefore=Camera->GetRelativeTransform();Camera->AddLocalOffset(FVector(25,-18,12));Camera->AddLocalRotation(FRotator(18,25,15));
    const auto Shaken=Sword->ReadBlade(Pawn->GetMeleeAimTransform());
    Check(!Sword->Viewmodel->GetSocketLocation(TEXT("Blade_Tip")).Equals(VisualBefore,1.f),TEXT("baseline cosmetic camera changes world blade endpoint"));
    Check(Stable.Base.Equals(Shaken.Base,.001)&&Stable.Tip.Equals(Shaken.Tip,.001),TEXT("damage blade is independent of camera shake"));Camera->SetRelativeTransform(CameraBefore);
    auto Run=[&](int32 Slash,float Hz,float Rate,bool Shake)
    {
        Sword->CancelAction();Sword->Damage=55;Sword->AttackRate=Rate;Sword->NextSlash=Slash;Sword->LastAttackEnd=World->GetTimeSeconds();
        Sword->BeginAttack();int32 Frames=0;
        while(Sword->bAttacking&&Frames++<2000)
        {
            if(Shake){Camera->SetRelativeLocation(CameraBefore.GetLocation()+FVector(FMath::Sin(float(Frames))*25,15,8));Camera->SetRelativeRotation(FRotator(20,Frames*13,14));}
            Sword->TickComponent(1.f/Hz,LEVELTICK_All,nullptr);
        }
        Camera->SetRelativeTransform(CameraBefore);return Frames;
    };
    for(int32 Slash=0;Slash<2;++Slash)for(float Rate:{.5f,1.f,4.f})for(float Hz:{5.f,15.f,30.f,60.f,144.f})
    {
        auto* Body=Target(Targets[Slash],FVector(6));Run(Slash,Hz,Rate,false);
        Check(FMath::IsNearlyEqual(Body->Received,55.f),FString::Printf(TEXT("native Slash%d %.0f FPS rate %.1f exactly one hit damage=%.1f"),Slash+1,Hz,Rate,Body->Received));Clear();
    }
    auto* Body=Target(Targets[0],FVector(6));Run(0,15,4,true);
    Check(FMath::IsNearlyEqual(Body->Received,55.f),TEXT("native fast slash with large camera motion still hits once"));Clear();
    auto* MultiA=Target(Targets[0]+FVector(0,-2,0),FVector(6));auto* MultiB=Target(Targets[0]+FVector(0,2,0),FVector(6));
    Run(0,15,4,false);Check(MultiA->Received==55&&MultiB->Received==55,TEXT("native overlapping bodies each take damage exactly once"));Clear();
    const FVector PawnBefore=Pawn->GetActorLocation(),Travel(0,200,0);
    Body=Target(Targets[0]+Travel*(TargetTimes[0]/2.f),FVector(6));Sword->CancelAction();Sword->AttackRate=1;Sword->NextSlash=0;Sword->LastAttackEnd=World->GetTimeSeconds();Sword->BeginAttack();
    Pawn->SetActorLocation(PawnBefore+Travel);Sword->TickComponent(2.f,LEVELTICK_All,nullptr);
    Check(Body->Received==55,TEXT("player movement interpolated across hitch longer than whole attack"));Pawn->SetActorLocation(PawnBefore);Clear();
    for(int32 Slash=0;Slash<2;++Slash)
    {
        auto* NurseClass=LoadClass<ANurseZombie>(nullptr,TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C"));
        Check(NurseClass!=nullptr,TEXT("installed nurse class loads for physical-body test"));
        if(NurseClass)
        {
            auto* Nurse=World->SpawnActor<ANurseZombie>(NurseClass,FVector(95,0,0),FRotator(0,180,0));
            Nurse->GetMesh()->PlayAnimation(Nurse->IdleClip,true);Nurse->GetMesh()->TickAnimation(0.f,false);Nurse->GetMesh()->RefreshBoneTransforms();
            const float Before=Nurse->Health;Run(Slash,30,1,false);
            Check(FMath::IsNearlyEqual(Before-Nurse->Health,55.f),FString::Printf(TEXT("native Slash%d installed nurse physics body damage=%.1f"),Slash+1,Before-Nurse->Health));Nurse->Destroy();
        }
    }
    Body=Target(Targets[0],FVector(6));Sword->CancelAction();Sword->AttackRate=1;Sword->NextSlash=0;Sword->LastAttackEnd=World->GetTimeSeconds();Sword->BeginAttack();
    Sword->TickComponent(.84f,LEVELTICK_All,nullptr);Check(Body->Received==0,TEXT("no damage during windup or held load"));
    Sword->TickComponent(.14f,LEVELTICK_All,nullptr);Check(Body->Received==55,TEXT("hitch crossing whole contact window hits once"));
    Sword->TickComponent(2.f,LEVELTICK_All,nullptr);Check(Body->Received==55,TEXT("recovery does not add damage"));
    Sword->NextSlash=0;Sword->BeginAttack();Sword->TickComponent(.84f,LEVELTICK_All,nullptr);Sword->CancelAction();Sword->TickComponent(1.f,LEVELTICK_All,nullptr);
    Check(Body->Received==55,TEXT("cancel before release prevents pending damage"));Clear();
    Note(FString::Printf(TEXT("SWORD_AUDIT_RESULT checks=%d failures=%d"),Checks,Failures));
    FString Output=FPaths::ProjectSavedDir()/TEXT("RuneSwordCombatAudit/report.txt");FParse::Value(*Params,TEXT("Report="),Output);
    IFileManager::Get().MakeDirectory(*FPaths::GetPath(Output),true);FFileHelper::SaveStringToFile(Report,*Output);
    World->DestroyWorld(false);return Failures?1:0;
}
