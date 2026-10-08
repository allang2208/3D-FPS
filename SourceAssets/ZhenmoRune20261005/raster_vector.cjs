// Production export of our original vector masks; no raster image editing.
const sharp=require('C:/Users/allan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
sharp(process.argv[2]).png().toFile(process.argv[3]).catch(error=>{console.error(error);process.exitCode=1;});
