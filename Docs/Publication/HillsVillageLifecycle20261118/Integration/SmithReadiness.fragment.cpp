    const auto ResidentReady = [&](const TSharedPtr<FStreamableHandle>& Handle, auto GetPaths, auto IsCompiling)
    {
        if(!Handle || !Handle->HasLoadCompleted() || IsCompiling())
        {Report(FText::FromString(TEXT("正在准备村庄居民…")),.98f);return false;}
        for(const auto& Path:GetPaths())if(!Path.ResolveObject())
        {
            S.Failed=true;
            UE_LOG(LogTemp,Error,TEXT("HILLS_PREP missing resident asset=%s"),*Path.ToString());
            if(Loading)Loading->FailPreparation(FText::FromString(TEXT("村庄居民资源未能载入，请返回主场景后重试。")));
            return false;
        }
        return true;
    };
