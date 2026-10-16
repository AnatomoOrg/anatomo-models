// Validate .glb files with the Khronos glTF validator (npm: gltf-validator). Usage: node pipeline/validate_gltf.js FILE...
const v=require('gltf-validator'),fs=require('fs');
(async()=>{for(const p of process.argv.slice(2)){const r=await v.validateBytes(new Uint8Array(fs.readFileSync(p)));
const i=r.issues;console.log(p,'errors',i.numErrors,'warnings',i.numWarnings,'infos',i.numInfos);
for(const m of i.messages.slice(0,10))console.log(' ',m.severity,m.code,m.message,m.pointer||'');
if(i.numErrors)process.exitCode=1;}})();
