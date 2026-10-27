        const double FoodDay=Save->Profile.FoodClockDay;
        Save->Profile.FoodClockDay=0.;
        TArray<uint8> WithoutFoodTime;
        if(!SaveToBlob(Save,WithoutFoodTime)||WithoutFoodTime==LastMirrorWithoutFoodTime)return;
        Save->Profile.FoodClockDay=FoodDay;
        TArray<uint8> Blob;
        if (!SaveToBlob(Save, Blob) || Blob == LastAppliedBlob || Blob == LastMirrorBlob) return;
        LastMirrorWithoutFoodTime=MoveTemp(WithoutFoodTime);
