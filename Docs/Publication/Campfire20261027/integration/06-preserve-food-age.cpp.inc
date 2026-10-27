        // Preserve age even when the inventory receipt is equal (moves/splits
        // can upload independently of the periodic authority settlement).
        for(auto& Item:Adopted.Items)
        {
            const auto* Previous=Prev.Items.FindByPredicate([&](const auto& I){return I.InstanceId==Item.InstanceId;});
            if(!Previous||ColdSteelFood::LifetimeDays(*Previous)<=0.)continue;
            if(Item.Definition!=Previous->Definition){Item=*Previous;continue;}
            // Food definitions have no client-authored processing fields. Keep
            // the server lifetime contract as well as its accumulated age.
            Item.Data=Previous->Data;
            if(FoodClock.Id.IsValid())
            {
                const double UploadedAge=ColdSteelFood::AgeDays(Item,FoodClock);
                if(UploadedAge<=ColdSteelFood::AgeDays(*Previous,FoodClock))
                {
                    // Preserve the exact birth representation of the existing
                    // batch instead of repeatedly rounding it through Stamp.
                    Item.FoodVersion=Previous->FoodVersion;Item.FoodClockId=Previous->FoodClockId;
                    Item.FoodSampleDay=Previous->FoodSampleDay;Item.FoodAgeDays=Previous->FoodAgeDays;
                }
                else ColdSteelFood::Stamp(Item,FoodClock,UploadedAge);
            }
        }
