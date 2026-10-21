'use strict';
// Public unauthenticated probes only. No account tokens or user messages.
const {createBridge}=require('../src/bridge-hook.cjs');
const {execFile}=require('node:child_process');
const net=require('node:net');
const tls=require('node:tls');
const crypto=require('node:crypto');
const fs=require('node:fs');
const path=require('node:path');
function curl(url,port) {
  const proxy=port?['--proxy','http://127.0.0.1:'+port,'--noproxy','']:['--noproxy','*'];
  return new Promise(resolve=>execFile('curl.exe',[...proxy,'--max-time','12','--connect-timeout','8','-sS','-o','NUL','-w','%{http_code} %{time_total} %{ssl_verify_result}',url],{timeout:15000},(e,out)=>{
    const [code,time,verify]=out.trim().split(' ');
    resolve({exit:e?.code||0,httpStatus:Number(code)||0,seconds:Number(time)||0,tlsVerifyResult:Number(verify)||0});
  }));
}
function websocket(port,host='gateway.discord.gg',targetPort=443,query='/?v=10&encoding=json',helloOpcode=10) {
  return new Promise(resolve=>{
    let raw,secure,finished=false;
    const timer=setTimeout(()=>done({ok:false,error:'timeout'}),12000);
    function done(result) { if(finished)return;finished=true;clearTimeout(timer);secure?.destroy();raw?.destroy();resolve(result); }
    raw=net.connect(port,'127.0.0.1',()=>raw.write('CONNECT '+host+':'+targetPort+' HTTP/1.1\r\nHost: '+host+':'+targetPort+'\r\n\r\n'));
    raw.on('error',()=>done({ok:false,error:'connect'}));
    let response=Buffer.alloc(0);
    function handshake(chunk) {
      response=Buffer.concat([response,chunk]);
      const end=response.indexOf('\r\n\r\n'); if(end<0)return;
      raw.removeListener('data',handshake);
      if(!response.toString('ascii',0,end).startsWith('HTTP/1.1 200'))return done({ok:false,error:'proxy-status'});
      if(response.length>end+4)raw.unshift(response.subarray(end+4));
      secure=tls.connect({socket:raw,servername:host,rejectUnauthorized:true},()=>{
        const key=crypto.randomBytes(16).toString('base64');
        secure.write('GET '+query+' HTTP/1.1\r\nHost: '+host+':'+targetPort+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+key+'\r\n\r\n');
        let data=Buffer.alloc(0),upgraded=false;
        secure.on('data',chunk=>{
          data=Buffer.concat([data,chunk]);
          if(!upgraded){const at=data.indexOf('\r\n\r\n');if(at<0)return;
            if(!data.toString('ascii',0,at).startsWith('HTTP/1.1 101'))return done({ok:false,error:'upgrade-status'});
            const expected=crypto.createHash('sha1').update(key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
            if(!data.toString('ascii',0,at).includes(expected))return done({ok:false,error:'accept-mismatch'});
            data=data.subarray(at+4);upgraded=true;
          }
          if(data.length<2)return;let len=data[1]&127,offset=2;
          if(len===126){if(data.length<4)return;len=data.readUInt16BE(2);offset=4;}
          if(len===127)return done({ok:false,error:'oversized-frame'});
          if(data.length<offset+len)return;
          try { const hello=JSON.parse(data.subarray(offset,offset+len));done({ok:hello.op===helloOpcode,httpStatus:101,helloOpcode:hello.op,tlsVerified:secure.authorized}); }
          catch { done({ok:false,error:'hello-parse'}); }
        });
      });
      secure.on('error',()=>done({ok:false,error:'tls'}));
    }
    raw.on('data',handshake);
  });
}
(async()=>{
 const bridge=await createBridge();
 const urls={discovery:'https://discord.com/api/v10/gateway',app:'https://discord.com/app',gateway:'https://gateway.discord.gg/',cdn:'https://cdn.discordapp.com/embed/avatars/0.png'};
 const report={checkedAt:new Date().toISOString(),platform:process.platform,direct:{},bridge:{},limits:['Unauthenticated public endpoints only.','Voice, video, screen sharing, login and future updates are not verified by these probes.']};
 try{
   for(const [name,url] of Object.entries(urls)){
     report.direct[name]=await curl(url);
     report.bridge[name]=await curl(url,bridge.port);
   }
   report.websocket=await websocket(bridge.port);
   if(process.env.BRIDGE_VOICE_HOST && /^[a-zA-Z0-9.-]+\.discord\.media$/.test(process.env.BRIDGE_VOICE_HOST)) report.voiceSignaling=await websocket(bridge.port,process.env.BRIDGE_VOICE_HOST,2053,'/?v=8',8);
   report.runtime=bridge.status;
   const destination=process.argv[2]||path.join(__dirname,'live-result.json');
   fs.writeFileSync(destination,JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 } finally { await bridge.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
