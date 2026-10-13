const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
async function main(){
  const root=path.resolve(__dirname,'../Previews');
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  try{
    const page=await browser.newPage({viewport:{width:2000,height:1900},deviceScaleFactor:1});
    await page.goto(pathToFileURL(path.join(root,'collection-icons-contact-sheet.html')).href,{waitUntil:'load'});
    await page.evaluate(()=>document.fonts.ready);
    await page.locator('.sheet').screenshot({path:path.join(root,'collection-icons-contact-sheet.png')});
    console.log('CONTACT_SHEET_PNG_SAVED',path.join(root,'collection-icons-contact-sheet.png'));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
