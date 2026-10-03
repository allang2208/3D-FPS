const { chromium } = require('C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const path = require('path');
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1000}});
    await page.goto('https://www.bilibili.com/video/BV1yx41187zP/?t=33', {waitUntil:'domcontentloaded',timeout:45000});
    await page.waitForTimeout(7000);
    console.log(JSON.stringify({title:await page.title(),url:page.url(),videos:await page.locator('video').evaluateAll(v=>v.map(x=>({duration:x.duration,time:x.currentTime,ready:x.readyState,width:x.videoWidth,height:x.videoHeight})))},null,2));
    const video=page.locator('video').first();
    for (const seconds of [30,30.5,31,31.5,32,32.25,32.5,32.75,33,34,35,36]) {
      const decoded=await video.evaluate((v,t)=>new Promise(resolve=>{
        v.pause();
        let timer=setTimeout(()=>resolve({timeout:true,current:v.currentTime,seeking:v.seeking}),4000);
        v.requestVideoFrameCallback((now,meta)=>{clearTimeout(timer);resolve({decodedTime:meta.mediaTime});});
        v.currentTime=t;
      }),seconds);
      await page.waitForTimeout(150);
      await video.screenshot({path:path.join(__dirname,`frame-${seconds.toFixed(2)}.png`)});
      console.log('REFERENCE_FRAME '+JSON.stringify({seconds,decoded}));
    }
  } finally { await browser.close(); }
})().catch(e=>{console.error(String(e));process.exitCode=1;});
