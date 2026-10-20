// Included in the existing opt-in character audit to exercise private fire state
// without introducing gameplay members or changing the character's layout.
struct FCase { bool Aim; float Distance; int32 Kind; const TCHAR* Optic; const TCHAR* Muzzle; int32 Shots; };
static const FCase Cases[]={
    {false,2000,0,TEXT("false"),TEXT("false"),16},
    {false,5000,0,TEXT("false"),TEXT("false"),16},
    {false,10000,0,TEXT("false"),TEXT("false"),16},
    {true,2000,0,TEXT("false"),TEXT("false"),4},
    {true,5000,0,TEXT("false"),TEXT("false"),4},
    {true,10000,0,TEXT("false"),TEXT("false"),4},
    {false,5000,1,TEXT("false"),TEXT("false"),1},
    {true,5000,1,TEXT("false"),TEXT("false"),1},
    {false,10000,1,TEXT("false"),TEXT("false"),1},
    {true,10000,1,TEXT("false"),TEXT("false"),1},
    {false,5000,2,TEXT("false"),TEXT("false"),1},
    {true,5000,2,TEXT("false"),TEXT("false"),1},
    {false,10000,2,TEXT("false"),TEXT("false"),1},
    {true,10000,2,TEXT("false"),TEXT("false"),1},
    {false,5000,3,TEXT("false"),TEXT("false"),1},
    {true,5000,3,TEXT("false"),TEXT("false"),1},
    {false,5000,4,TEXT("false"),TEXT("false"),1},
    {true,5000,4,TEXT("false"),TEXT("false"),1},
    {false,5000,0,TEXT("false"),TEXT("true"),4},
    {true,5000,0,TEXT("false"),TEXT("true"),2},
    {false,5000,0,TEXT("holographic"),TEXT("false"),4},
    {true,5000,0,TEXT("holographic"),TEXT("false"),2},
    {false,5000,0,TEXT("prism_scope_2x"),TEXT("false"),4},
    {true,5000,0,TEXT("prism_scope_2x"),TEXT("false"),2},
    {false,5000,0,TEXT("lpvo_1_6x"),TEXT("false"),4},
    {true,5000,0,TEXT("lpvo_1_6x"),TEXT("false"),2}
};
static int32 Phase=0,Case=0,Shot=0,Failures=0,Checks=0,BeforeShots=0,BeforeImpacts=0,ExpectedCenters=0,ActualCenters=0;
static double Next=2.;
static FString Report;
static AActor* Target=nullptr;
static ABallisticAuditTarget* Backstop=nullptr;
static ABallisticAuditTarget* Wall=nullptr;
static FVector ExpectedPoint;
static FVector ExpectedMuzzle,ExpectedFlight;
static bool ExpectTarget=false;
static float BeforeHealth=0,BeforeReceived=0;
const double Now=GetWorld()->GetTimeSeconds();
const auto Check=[&](bool Pass,const FString& Name)
{
    ++Checks;Failures+=!Pass;
    const FString Line=FString::Printf(TEXT("SVCH_FULL %s case=%d shot=%d %s\n"),Pass?TEXT("PASS"):TEXT("FAIL"),Case,Shot,*Name);
    Report+=Line;UE_LOG(LogTemp,Display,TEXT("%s"),*Line);
};
const auto Health=[&](AActor* Actor)
{
    float HP=0,Max=0;FText Name;
    if(auto* Combat=Actor?Actor->FindComponentByClass<UMonsterCombatComponent>():nullptr)Combat->GetVitals(HP,Max,Name);
    return HP;
};
const auto Cleanup=[&]()
{
    if(Target){Target->Destroy();Target=nullptr;}
    if(Backstop){Backstop->Destroy();Backstop=nullptr;}
    if(Wall){Wall->Destroy();Wall=nullptr;}
};
const auto Finish=[&]()
{
    Cleanup();
    const FString Dir=FPaths::ProjectSavedDir()/TEXT("SVCHFullFireReview");IFileManager::Get().MakeDirectory(*Dir,true);
    Report+=FString::Printf(TEXT("SVCH_FULL_COMPLETE checks=%d failures=%d\n"),Checks,Failures);
    FFileHelper::SaveStringToFile(Report,*(Dir/TEXT("assertions.log")));
    UE_LOG(LogTemp,Display,TEXT("SVCH_FULL_COMPLETE checks=%d failures=%d"),Checks,Failures);
    Phase=99;FPlatformMisc::RequestExitWithStatus(false,Failures?1:0);
};
if(Phase==99)return;
if(Now>180.){Check(false,TEXT("bounded review completed"));Finish();return;}
if(Now<Next)return;
if(Phase==0)
{
    auto* Model=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Model||!Model->IsAudit()||!Model->ProfileSlot().Contains(TEXT("SVCHBallisticAudit")))
    {Check(false,TEXT("isolated profile required"));Finish();return;}
    auto State=Model->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);State.ActiveWeaponSlot=6;
    auto Item=Model->CreateItem(SVCHWeaponAssets::Definition);Item.Place=1;Item.Cell=6;Item.Magazine=10;State.Items.Add(Item);
    Model->AddAmmoToState(State,SVCHWeaponAssets::ItemAmmoId,200);
    if(!Model->CommitState(State)){Check(false,TEXT("fixture commit"));Finish();return;}
    ApplyColdSteelProfile(Model);SetActorLocation(FVector(0,0,5000));
    auto* Floor=GetWorld()->SpawnActor<ABallisticAuditTarget>(FVector(0,0,5000-GetCapsuleComponent()->GetScaledCapsuleHalfHeight()-10),FRotator::ZeroRotator);
    Floor->Tags.Add(TEXT("DefenseStructure"));
    auto* FloorBox=Cast<UBoxComponent>(Floor->GetRootComponent());FloorBox->SetBoxExtent(FVector(500,500,10));
    FloorBox->SetCollisionObjectType(ECC_WorldStatic);FloorBox->SetCollisionResponseToChannel(ECC_Pawn,ECR_Block);
    GetCharacterMovement()->SetMovementMode(MOVE_Walking);
    auto* PC=Cast<APlayerController>(Controller);PC->SetIgnoreLookInput(true);PC->SetIgnoreMoveInput(true);PC->SetControlRotation(FRotator::ZeroRotator);
    AKMViewmodel->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
    Phase=1;Next=Now+3.;return;
}
const FCase& C=Cases[Case];
if(Phase==1)
{
    SetGunsmithOpticVariant(C.Optic);SetGunsmithMuzzle(C.Muzzle);
    if(C.Aim)AimPressed();else AimReleased();
    ResumeWeaponPose();Shot=0;ExpectedCenters=ActualCenters=0;Phase=2;Next=Now+1.2;return;
}
if(Phase==3)
{
    Check(ShotsFired==BeforeShots+1,TEXT("one actual shot fired"));
    const bool Damaged=Cast<ABallisticAuditTarget>(Target)?Cast<ABallisticAuditTarget>(Target)->Received>BeforeReceived:Health(Target)<BeforeHealth;
    ActualCenters+=Damaged;
    Check(Damaged==ExpectTarget,TEXT("target damage agrees with traced trajectory and occlusion"));
    Check(Ballistics->ImpactCount==BeforeImpacts+(C.Kind==3?0:1),TEXT("flight collision accounted for exactly once"));
    if(C.Kind!=3)
    {
        // Animated monster surfaces may move along the flight path before impact.
        // Static fixtures have an exact point; live meshes must lie on the same ray.
        const double Error=C.Kind==1||C.Kind==2?
            FVector::CrossProduct(Ballistics->LastImpactPoint-ExpectedMuzzle,ExpectedFlight).Size():
            FVector::Dist(Ballistics->LastImpactPoint,ExpectedPoint);
        Check(Error<.1,TEXT("actual projectile follows predicted ray within 1 mm"));
    }
    if(C.Kind==3)Check(bLastShotMuzzleBlocked,TEXT("near wall blocks muzzle"));
    if(C.Kind==1||C.Kind==2)
    {
        Report+=FString::Printf(TEXT("MONSTER class=%s hp_before=%.6f hp_after=%.6f\n"),*Target->GetClass()->GetPathName(),BeforeHealth,Health(Target));
        Check(Damaged,TEXT("real monster health decreases"));
    }
    Cleanup();++Shot;
    if(Shot>=C.Shots)
    {
        Report+=FString::Printf(TEXT("CASE index=%d aim=%d distance_m=%.1f kind=%d optic=%s muzzle=%s expected_target_hits=%d actual_target_hits=%d shots=%d\n"),
            Case,C.Aim,C.Distance/100.f,C.Kind,C.Optic,C.Muzzle,ExpectedCenters,ActualCenters,Shot);
        ++Case;if(Case==UE_ARRAY_COUNT(Cases)){Finish();return;}
        Phase=1;Next=Now+.2;return;
    }
    Phase=2;Next=Now+.15;return;
}
if(Phase==2)
{
    Check(C.Aim?bIsAiming&&WeaponADSFactor>.99f:!bIsAiming&&WeaponADSFactor<.01f,TEXT("requested aim state settled"));
    const FVector Eye=FirstPersonCamera->GetComponentLocation(),Forward=FirstPersonCamera->GetForwardVector();
    const FVector Right=FirstPersonCamera->GetRightVector(),Up=FirstPersonCamera->GetUpVector();
    const FVector Visible=(C.Aim?(bHolographicOptic?HolographicAimPoint():
        AKMViewmodel->GetSocketTransform(TEXT("WPN_root")).TransformPosition(SVCHWeaponAssets::FrontSight))-Eye:Forward).GetSafeNormal();
    const double AimError=FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(Visible,Forward),-1.,1.)));
    if(Shot==0)
    {
        Check(GetCharacterMovement()->IsMovingOnGround(),TEXT("standing scatter sampled on actual ground"));
        Report+=FString::Printf(TEXT("AIM case=%d camera_angle_deg=%.6f spread_tangent=%.6f halfwidth_at_target_cm=%.3f speed_cm=%.1f range_cm=%.1f ads=%.6f scope=%.6f\n"),
            Case,AimError,GetHipSpread(),GetHipSpread()*C.Distance,ProjectileSpeedCM,EffectiveWeaponRangeCM,WeaponADSFactor,GetScopePresentationAlpha());
        if(C.Aim&&GetScopePresentationAlpha()<.5f)Check(AimError<.05,TEXT("settled physical sight points at camera center"));
    }
    // Reset only the test RNG: target placement/physics uses an independently
    // predicted scatter sample, then FireShot draws the same sample itself.
    const int32 Seed=9137+Case*131+Shot*31;
    FMath::RandInit(Seed);const FVector Predicted=ComputeShotDirection();
    if(!C.Aim)
    {
        const double F=FVector::DotProduct(Predicted,Forward);
        Check(F>0&&FMath::Abs(FVector::DotProduct(Predicted,Right)/F)<=GetHipSpread()+1.e-6
              &&FMath::Abs(FVector::DotProduct(Predicted,Up)/F)<=GetHipSpread()+1.e-6,TEXT("hip sample inside displayed scatter cone"));
    }
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SVCHFullFireReview),true,this);FHitResult AimHit;
    if(C.Kind==1||C.Kind==2)
    {
        const TCHAR* Path=C.Kind==1?TEXT("/Game/Monsters/HandBrain/BP_HandBrain.BP_HandBrain_C"):
            TEXT("/Game/Monsters/NurseZombie/BP_NurseZombie.BP_NurseZombie_C");
        auto* Class=LoadClass<ACharacter>(nullptr,Path);
        if(!Class){Check(false,TEXT("real monster class loads"));Finish();return;}
        auto* Monster=GetWorld()->SpawnActor<ACharacter>(Class,Eye+Predicted*C.Distance,FRotator(0,180,0));Target=Monster;
        Monster->GetCharacterMovement()->DisableMovement();Monster->SetActorTickEnabled(false);
        if(auto* AI=Monster->GetController())AI->SetActorTickEnabled(false);
        if(auto* Combat=Monster->FindComponentByClass<UMonsterCombatComponent>())Combat->SetComponentTickEnabled(false);
        Monster->GetMesh()->TickAnimation(0.f,false);Monster->GetMesh()->RefreshBoneTransforms();Monster->GetMesh()->UpdateBounds();
        const FVector Base=Monster->GetActorLocation(),Center=Monster->GetMesh()->Bounds.Origin;
        // Find an actual body contact, without adding or expanding hit volumes.
        bool Contact=false;
        for(float Z:{0.f,20.f,-20.f,40.f,-40.f})
        {
            Monster->SetActorLocation(Base+(Eye+Predicted*C.Distance-Center)+Up*Z);
            Contact=RangedAttackQuery::LineTraceSingle(GetWorld(),this,AimHit,Eye,Eye+Predicted*TraceDistance,ECC_Visibility,Query)&&AimHit.GetActor()==Target;
            if(Contact)break;
        }
        Check(Contact,TEXT("authored monster body collision is traceable"));
        if(!Contact){Finish();return;}
    }
    else
    {
        Target=GetWorld()->SpawnActor<ABallisticAuditTarget>(Eye+Forward*C.Distance,Forward.Rotation());Target->Tags.Add(TEXT("Enemy"));
        Backstop=GetWorld()->SpawnActor<ABallisticAuditTarget>(Eye+Forward*(C.Distance+200),Forward.Rotation());
        Backstop->Tags.Add(TEXT("DefenseStructure"));
        Cast<UBoxComponent>(Backstop->GetRootComponent())->SetBoxExtent(FVector(2,20000,20000));
    }
    if(C.Kind>=3)
    {
        const FVector Muzzle=GetEffectiveMuzzleLocation()+GetEffectiveMuzzleForward()*2.f;
        const FVector Point=C.Kind==3?(Eye+Muzzle)*.5:Eye+Forward*C.Distance*.5;
        Wall=GetWorld()->SpawnActor<ABallisticAuditTarget>(Point,(Muzzle-Eye).Rotation());Wall->Tags.Add(TEXT("DefenseStructure"));
        Cast<UBoxComponent>(Wall->GetRootComponent())->SetBoxExtent(FVector(2,C.Kind==3?100.f:2000.f,C.Kind==3?100.f:2000.f));
    }
    Check(RangedAttackQuery::LineTraceSingle(GetWorld(),this,AimHit,Eye,Eye+Predicted*TraceDistance,ECC_Visibility,Query),TEXT("predicted shot reaches a blocking surface"));
    ExpectedPoint=AimHit.ImpactPoint;ExpectTarget=AimHit.GetActor()==Target&&C.Kind!=3;ExpectedCenters+=ExpectTarget;
    ExpectedMuzzle=GetEffectiveMuzzleLocation()+GetEffectiveMuzzleForward()*2.f;
    ExpectedFlight=(ExpectedPoint-ExpectedMuzzle).GetSafeNormal();
    BeforeHealth=Health(Target);BeforeReceived=Cast<ABallisticAuditTarget>(Target)?Cast<ABallisticAuditTarget>(Target)->Received:0.f;
    BeforeShots=ShotsFired;BeforeImpacts=Ballistics->ImpactCount;MagazineAmmo=10;NextAllowedShotTime=Now;
    FMath::RandInit(Seed);FireShot();Phase=3;Next=Now+.6;return;
}
