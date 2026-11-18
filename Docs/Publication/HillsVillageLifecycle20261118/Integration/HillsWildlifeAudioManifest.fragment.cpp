    void AppendTakes(TArray<FSoftObjectPath>& Out,const FString& Prefix,const TCHAR* Role,int32 Count)
    {
        for(int32 Index=1;Index<=Count;++Index)
        {
            const FString Name=FString::Printf(TEXT("SW_%s_%s_%02d"),*Prefix,Role,Index);
            Out.Emplace(FString::Printf(TEXT("/Game/Monsters/Wildlife/Audio/%s.%s"),*Name,*Name));
        }
    }
    void LoadTakes(TArray<TObjectPtr<USoundWave>>& Out, const FString& Prefix, const TCHAR* Role, int32 Count)
    {
        Out.Reset(Count);
        TArray<FSoftObjectPath> Paths;AppendTakes(Paths,Prefix,Role,Count);
        for (const auto& Path:Paths)
        {
            if (USoundWave* Wave = LoadObject<USoundWave>(nullptr, *Path.ToString())) Out.Add(Wave);
        }
    }


TArray<FSoftObjectPath> UHillsWildlifeAudio::AssetPaths(const FString& Id)
{
    TArray<FSoftObjectPath> Paths;
    AppendTakes(Paths,Id,TEXT("Alarm"),2);AppendTakes(Paths,Id,TEXT("Hurt"),2);AppendTakes(Paths,Id,TEXT("Death"),1);
    if(Id==TEXT("boar")||Id.StartsWith(TEXT("deer_")))AppendTakes(Paths,Id==TEXT("boar")?TEXT("boar"):TEXT("deer"),TEXT("Hoof"),4);
    else if(Id==TEXT("crow"))AppendTakes(Paths,Id,TEXT("Wings"),2);
    return Paths;
}
