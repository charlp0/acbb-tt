const test=require('node:test'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function files(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(f=>f.isDirectory()?files(path.join(dir,f.name)):[path.join(dir,f.name)]);}
test('chaque page et module partagé doit être interprétable avant publication',()=>{
 const html=[...fs.readdirSync('.').filter(f=>f.endsWith('.html')),...files('sportive'),...files('refonte')].filter(f=>f.endsWith('.html'));
 for(const f of html){for(const match of fs.readFileSync(f,'utf8').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)){
  if(/type=["'](?:application\/ld\+json|application\/json)/.test(match[1]))continue;
  new vm.Script(match[2],{filename:f});
 }}
 for(const f of files('shared').filter(f=>f.endsWith('.js')))new vm.Script(fs.readFileSync(f,'utf8'),{filename:f});
});
