from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
p=root/'Source/FPSGAME/Monsters/M09CeilingRoute.h'
s=p.read_text(encoding='utf8').replace('/** Explicit ceiling graph; never projects onto the ground NavMesh. */','/** Optional authored routes; physical ceilings also support placement and local movement. */')
s=s.replace(' static bool Supported(', ' static bool FindSupport(UWorld* World,FVector Near,const AActor* Ignore,FVector& Contact);\n static bool Supported(')
s=s.replace(' static AM09CeilingRoute* FindPlacement(UWorld* World,FVector Near,const AActor* Ignore,FVector& Center);',
''' static bool FindPlacement(UWorld* World,FVector Near,const AActor* Ignore,FVector& Center,AM09CeilingRoute*& OptionalRoute);
 static AM09CeilingRoute* FindRoute(UWorld* World,FVector Ceiling);
 static bool FindLocalPath(const AHangingBellM09* Monster,FVector Destination,TArray<FVector>& Out);''')
p.write_text(s,encoding='utf8')
p=root/'Source/FPSGAME/Monsters/M09CeilingRoute.cpp';s=p.read_text(encoding='utf8')
a=s.index('bool AM09CeilingRoute::Supported(');b=s.index('bool AM09CeilingRoute::FindPath(',a)
s=s[:a]+'''namespace
{
bool TraceM09Ceiling(UWorld* World,FVector From,FVector To,const AActor* Ignore,FVector& Contact)
{
 if(!World)return false;
 FHitResult Hit;FCollisionQueryParams Query(SCENE_QUERY_STAT(M09CeilingSurface),false,Ignore);
 // Use solid collision, including ordinary roofs that ignore visibility traces.
 if(!World->LineTraceSingleByChannel(Hit,From,To,ECC_Pawn,Query)
    ||Hit.bStartPenetrating||Hit.ImpactNormal.Z>-.6f||!Hit.GetActor()||Hit.GetActor()->IsA<APawn>())return false;
 Contact=Hit.ImpactPoint;return true;
}
}
bool AM09CeilingRoute::FindSupport(UWorld* W,FVector Near,const AActor* Ignore,FVector& Contact)
{
 return TraceM09Ceiling(W,Near-FVector(0,0,25),Near+FVector(0,0,25),Ignore,Contact);
}
bool AM09CeilingRoute::Supported(UWorld* W,FVector P,const AActor* Ignore)
{
 FVector Contact;return FindSupport(W,P,Ignore,Contact);
}
bool AM09CeilingRoute::ClearBody(UWorld* W,FVector P,const AActor* Ignore)
{
 FCollisionQueryParams Q(SCENE_QUERY_STAT(M09Clearance),false,Ignore);
 // Match the actual collision body without an additional exclusion margin.
 return Supported(W,P,Ignore)&&!W->OverlapBlockingTestByChannel(P-FVector(0,0,143),FQuat::Identity,ECC_Pawn,
  FCollisionShape::MakeCapsule(85,137),Q);
}
bool AM09CeilingRoute::ClearSegment(UWorld* W,FVector A,FVector B,const AActor* Ignore)
{
 if(FMath::Abs(A.Z-B.Z)>30.f)return false;
 FHitResult H;FCollisionQueryParams Q(SCENE_QUERY_STAT(M09Edge),false,Ignore);
 if(W->SweepSingleByChannel(H,A-FVector(0,0,143),B-FVector(0,0,143),FQuat::Identity,ECC_Pawn,
   FCollisionShape::MakeCapsule(85,137),Q))return false;
 const int32 N=FMath::Clamp(FMath::CeilToInt(FVector::Distance(A,B)/35.f),1,16);
 for(int32 I=0;I<=N;++I)if(!Supported(W,FMath::Lerp(A,B,float(I)/N),Ignore))return false;
 return true;
}
AM09CeilingRoute* AM09CeilingRoute::FindRoute(UWorld* W,FVector Ceiling)
{
 AM09CeilingRoute* BestRoute=nullptr;float Best=FMath::Square(350.f);
 for(TActorIterator<AM09CeilingRoute> It(W);It;++It)
  for(int32 I=0;I<FMath::Min(It->GripCenters.Num(),256);++I)
  {
   const FVector P=It->Point(I);const float D=FVector::DistSquared2D(P,Ceiling);
   if(D<Best&&FMath::Abs(P.Z-Ceiling.Z)<30.f){Best=D;BestRoute=*It;}
  }
 return BestRoute;
}
bool AM09CeilingRoute::FindPlacement(UWorld* W,FVector Near,const AActor* Ignore,FVector& Center,AM09CeilingRoute*& OptionalRoute)
{
 OptionalRoute=nullptr;
 // No authored tag, grip node, ground navigation or 3-7 m height band is required.
 // The trace reach is a search budget; real body clearance decides the minimum height.
 if(!TraceM09Ceiling(W,Near+FVector(0,0,2),Near+FVector(0,0,10000),Ignore,Center))return false;
 const AActor* ClearanceIgnore=Cast<AHangingBellM09>(Ignore)?Ignore:nullptr;
 if(!ClearBody(W,Center,ClearanceIgnore))return false;
 OptionalRoute=FindRoute(W,Center);return true;
}
bool AM09CeilingRoute::FindLocalPath(const AHangingBellM09* M,FVector Destination,TArray<FVector>& Out)
{
 Out.Reset();if(!M)return false;
 const FVector Start=M->CeilingCenter(),Delta=(Destination-Start)*FVector(1,1,0);
 if(Delta.SizeSquared()<FMath::Square(8.f))return false;
 const FVector Near=Start+Delta.GetClampedToMaxSize(150.f);FVector End;
 if(!FindSupport(M->GetWorld(),Near,M,End)||!ClearSegment(M->GetWorld(),Start,End,M))return false;
 Out.Add(End);return true;
}
''' +s[b:]
p.write_text(s,encoding='utf8')
p=root/'Source/FPSGAME/Monsters/HangingBellM09.cpp';s=p.read_text(encoding='utf8')
old='''  FVector Center;auto* R=AM09CeilingRoute::FindPlacement(GetWorld(),GetActorLocation()-FVector(0,0,210),this,Center);
  if(R){SetActorLocation(Center-FVector(0,0,143));InitializeHang(R);}
  else{Health=0;EnterDeath();}'''
new='''  FVector Center=CeilingCenter();AM09CeilingRoute* CeilingRoute=nullptr;
  // Keep a valid spawn where it was placed; a missing authored route is not a failed hang.
  bool Placed=AM09CeilingRoute::ClearBody(GetWorld(),Center,this);
  if(Placed)CeilingRoute=AM09CeilingRoute::FindRoute(GetWorld(),Center);
  else Placed=AM09CeilingRoute::FindPlacement(GetWorld(),GetActorLocation()-FVector(0,0,137),this,Center,CeilingRoute);
  if(Placed){SetActorLocation(Center-FVector(0,0,143));InitializeHang(CeilingRoute);}
  else{Health=0;EnterDeath();}'''
if old not in s:raise RuntimeError('M09 BeginPlay changed; preserve current source')
s=s.replace(old,new).replace('if(!HasAuthority()||!R||!VisualMesh)return;','if(!HasAuthority()||!VisualMesh)return;')
s=s.replace('''  GripTargets[I]=GetActorTransform().TransformPosition(GripRest[I]);
  const int32 B=''','''  GripTargets[I]=GetActorTransform().TransformPosition(GripRest[I]);
  const FVector DesiredContact=GripTargets[I]+FVector(0,0,GripClearance[I]);
  // Bring the hands inward on beams or small roof panels instead of rejecting the body.
  for(float Width:{1.f,.75f,.5f,.25f,0.f})
  {
   FVector Contact;
   if(AM09CeilingRoute::FindSupport(GetWorld(),FMath::Lerp(CeilingCenter(),DesiredContact,Width),this,Contact))
   {GripTargets[I]=Contact-FVector(0,0,GripClearance[I]);break;}
  }
  const int32 B=''')
s=s.replace(' if(Busy()||!Route)return;',' if(Busy()||!bInitialized)return;')
s=s.replace('  PathAge=0;LastDestination=Destination;Route->FindPath(this,Destination,Path);',
'''  PathAge=0;LastDestination=Destination;
  if(!IsValid(Route)||!Route->FindPath(this,Destination,Path))
   AM09CeilingRoute::FindLocalPath(this,Destination,Path);''')
s=s.replace('''  if(AM09CeilingRoute::Supported(GetWorld(),End+FVector(0,0,GripClearance[GripSide]),this))
  {
   GripStart''','''  FVector Contact;
  if(AM09CeilingRoute::FindSupport(GetWorld(),End+FVector(0,0,GripClearance[GripSide]),this,Contact))
  {
   End=Contact-FVector(0,0,GripClearance[GripSide]);
   GripStart''')
p.write_text(s,encoding='utf8')
p=root/'Source/FPSGAME/Development/DevelopmentSpawnComponent.cpp';s=p.read_text(encoding='utf8')
s=s.replace('''        for(int32 I=0;I<25&&Created<Wanted;++I)
        {''','''        const float RequestedDistance=FMath::Clamp(DistanceMeters,3.f,15.f)*100.f;
        const float SearchDistances[]={RequestedDistance,RequestedDistance*.65f,RequestedDistance*.35f,150.f,0.f};
        for(int32 I=0;I<25&&Created<Wanted;++I)
        {''',1)
s=s.replace('''            const FVector Near=Feet+Forward*(FMath::Clamp(DistanceMeters,3.f,15.f)*100.f+(I/5)*180.f)+Right*Side*210.f;
            FVector Ceiling;auto* Route=AM09CeilingRoute::FindPlacement(GetWorld(),Near,Player->GetPawn(),Ceiling);
            if(!Route)continue;
            FActorSpawnParameters Params;Params.Owner=Player;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding;''','''            const FVector Near=Feet+Forward*SearchDistances[I/5]+Right*Side*210.f;
            FVector Ceiling;AM09CeilingRoute* Route=nullptr;
            if(!AM09CeilingRoute::FindPlacement(GetWorld(),Near,Player->GetPawn(),Ceiling,Route))continue;
            // ClearBody already tests the real body; do not reject again on decorative mesh tips.
            FActorSpawnParameters Params;Params.Owner=Player;Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;''')
s=s.replace('''                Monster->InitializeHang(Route);Monster->Tags.AddUnique(TEXT("DevelopmentSpawned"));Spawned.Add(Monster);++Created;''','''                if(Monster->Dead()){Monster->Destroy();continue;}
                Monster->InitializeHang(Route);Monster->Tags.AddUnique(TEXT("DevelopmentSpawned"));Spawned.Add(Monster);++Created;''')
s=s.replace('附近没有可悬挂的天花板或身体净空不足；请进入悬钟测试房并面向有顶区域','附近没有实体天花板，或下方空间不足以容纳悬钟；可换到更开阔的有顶位置')
p.write_text(s,encoding='utf8')
