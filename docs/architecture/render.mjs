import {build} from 'esbuild';
import {chromium} from 'playwright-core';
import {readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const root=path.dirname(fileURLToPath(import.meta.url));
const diagrams=[
 {id:'application',title:'Application architecture'},
 {id:'capture-storage',title:'Capture and storage'},
 {id:'local-testing',title:'Local testing in Kiro'}
];
const packs=[JSON.parse(await readFile(path.join(root,'aws-icons.json'),'utf8'))];
const bundle=await build({entryPoints:[path.join(root,'browser.mjs')],bundle:true,format:'iife',platform:'browser',minify:true,write:false,logLevel:'warning'});
const runtime=bundle.outputFiles[0].text.replaceAll('</script','<\\/script');
const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try {
 for(const {id,title} of diagrams) {
  const source=await readFile(path.join(root,`${id}.mmd`),'utf8');
  const payload=JSON.stringify({source,packs}).replaceAll('<','\\u003c');
  const html=`<!doctype html><html lang="en"><meta charset="utf-8"><title>${title}</title><style>*{box-sizing:border-box}body{margin:0;background:#fff;color:#182b43;font-family:Arial,sans-serif}main{width:1920px;height:1080px;padding:46px 56px;display:flex;flex-direction:column;gap:24px}h1{font-size:42px;line-height:1.1;margin:0}#diagram{flex:1;min-height:0;display:flex;align-items:center;justify-content:center}#diagram>svg{width:100%;height:100%;max-width:100%!important}</style><main><h1>${title}</h1><div id="diagram"></div></main><script>${runtime}</script><script>const payload=${payload};window.ready=drawArchitecture(payload.source,payload.packs);</script></html>`;
  await writeFile(path.join(root,`${id}.html`),html);
  const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:2});
  page.on('pageerror',e=>console.error(e.message));
  await page.goto('file://'+path.join(root,`${id}.html`));
  const svg=await page.evaluate(()=>window.ready);
  if(await page.locator('svg .error-text').count()) throw new Error('Mermaid reported a diagram error');
  await writeFile(path.join(root,`${id}.svg`),svg);
  await page.screenshot({path:path.join(root,`${id}-4k.png`)});
  console.log(JSON.stringify({source:`${id}.mmd`,svg:`${id}.svg`,png:`${id}-4k.png`,viewBox:await page.locator('#diagram>svg').getAttribute('viewBox')}));
  await page.close();
 }
} finally {await browser.close();}
