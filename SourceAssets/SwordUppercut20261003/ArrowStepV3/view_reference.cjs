const { chromium } = require('C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1200,height:850}});
    await page.goto('https://www.bilibili.com/video/BV1fB4y1v72r/', {waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForTimeout(6000);
    const info={title:await page.title(),url:page.url(),frames:[]};
    console.log(JSON.stringify({title:info.title,text:(await page.locator('body').innerText()).slice(0,1700)}));
    const video=page.locator('video').first();
    const times=process.argv.slice(2).map(Number);
    for (const seconds of times.length?times:[0.1,1,2,3,4,5,6,7,8]) {
      const decoded=await video.evaluate((v,t)=>new Promise(resolve=>{
        v.pause();
        const timer=setTimeout(()=>resolve({timeout:true,time:v.currentTime,seeking:v.seeking}),4000);
        v.requestVideoFrameCallback((now,meta)=>{clearTimeout(timer);resolve({time:meta.mediaTime});});
        v.currentTime=t;
      }),seconds);
      await page.waitForTimeout(120);
      const filename=`frame-${seconds.toFixed(2)}.jpg`;
      await video.screenshot({path:path.join(__dirname,filename),quality:88,type:'jpeg'});
      info.frames.push({seconds,decoded,filename});
      console.log(JSON.stringify({seconds,decoded}));
    }
    fs.writeFileSync(path.join(__dirname,'reference-observation.json'),JSON.stringify(info,null,2));
  } finally { await browser.close(); }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
