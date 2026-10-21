'use strict';
// Experimental TCP-only transport adapter. TLS remains end-to-end; UDP voice is not handled.
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const dns = require('node:dns').promises;
const { Transform } = require('node:stream');
const { Readable } = require('node:stream');
const crypto = require('node:crypto');
const Module = require('node:module');
const fs = require('node:fs');
const path = require('node:path');
const SUFFIXES = ['discord.com', 'discord.gg', 'discordapp.com', 'discordapp.net', 'discord.media'];
const LINK_HOSTS = ['discord.gift', 'dis.gd'];
function coreHost(host) {
  return SUFFIXES.some(suffix => host === suffix || host.endsWith('.' + suffix));
}
function allowedHost(host) {
  return typeof host === 'string' && host.length <= 253 && /^[a-z0-9.-]+$/i.test(host) &&
    (coreHost(host.toLowerCase()) || LINK_HOSTS.includes(host.toLowerCase()));
}
function allowedTarget(host, port) {
  if (!allowedHost(host) || !Number.isInteger(port) || port < 1 || port > 65535) return false;
  const normalized = host.toLowerCase();
  return port === 443 || normalized === 'discord.media' || normalized.endsWith('.discord.media');
}
function publicIPv4(ip) {
  if (net.isIP(ip) !== 4) return false;
  const [a, b, c] = ip.split('.').map(Number);
  return !(a === 0 || a === 10 || a === 127 || a >= 224 ||
    (a === 100 && b >= 64 && b <= 127) || (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) || (a === 192 && (b === 168 || b === 0 || (b === 0 && c === 2))) ||
    (a === 198 && (b === 18 || b === 19 || (b === 51 && c === 100))) ||
    (a === 203 && b === 0 && c === 113));
}
class FirstRecordSplitter extends Transform {
  constructor(size = 32) { super(); this.size = size; this.buffer = Buffer.alloc(0); this.done = false; }
  _transform(chunk, encoding, callback) {
    if (this.done) { this.push(chunk); callback(); return; }
    this.buffer = Buffer.concat([this.buffer, chunk]);
    if (this.buffer.length < 5) { callback(); return; }
    const b = this.buffer;
    if (b[0] !== 22 || b[1] !== 3) { callback(new Error('Expected a TLS handshake')); return; }
    const length = b.readUInt16BE(3);
    if (length < 4 || length > 18432) { callback(new Error('Invalid TLS record length')); return; }
    if (b.length < 5 + length) { callback(); return; }
    if (b[5] !== 1) { callback(new Error('Expected TLS ClientHello')); return; }
    for (let offset = 0; offset < length; offset += this.size) {
      const payload = b.subarray(5 + offset, 5 + Math.min(length, offset + this.size));
      const header = Buffer.from([22, b[1], b[2], 0, 0]);
      header.writeUInt16BE(payload.length, 3);
      this.push(Buffer.concat([header, payload]));
    }
    this.push(b.subarray(5 + length));
    this.done = true; this.buffer = Buffer.alloc(0); callback();
  }
  _flush(callback) { callback(this.done ? undefined : new Error('Incomplete TLS handshake')); }
}
function doh(host) {
  return new Promise((resolve, reject) => {
    const request = https.get({ hostname: '8.8.8.8', servername: 'dns.google', port: 443,
      path: '/resolve?name=' + encodeURIComponent(host) + '&type=A',
      headers: { Host: 'dns.google', Accept: 'application/dns-json' }, timeout: 4500,
      rejectUnauthorized: true }, response => {
      let size = 0; const chunks = [];
      response.on('data', chunk => { size += chunk.length; if (size > 65536) response.destroy(new Error('DNS response too large')); else chunks.push(chunk); });
      response.on('error', reject);
      response.on('end', () => {
        try {
          if (response.statusCode !== 200) throw new Error('DNS HTTP status');
          const body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
          if (body.Status !== 0) throw new Error('DNS lookup failed');
          const answers = (body.Answer || []).filter(a => a.type === 1 && publicIPv4(a.data));
          if (!answers.length) throw new Error('No public DNS answer');
          resolve({ address: answers[0].data, ttl: Math.max(5, Math.min(300, answers[0].TTL || 30)), mode: 'doh' });
        } catch (error) { reject(error); }
      });
    });
    request.on('timeout', () => request.destroy(new Error('DNS timeout')));
    request.on('error', reject);
  });
}
function makeResolver(status) {
  const cache = new Map();
  const systemResolver = new dns.Resolver({ timeout: 2500, tries: 1 });
  return async host => {
    const entry = cache.get(host);
    if (entry && entry.expires > Date.now()) return entry.address;
    let answer;
    try { answer = await doh(host); }
    catch {
      // Explicit fallback: system DNS can still be filtered. It is never reported as DoH.
      const addresses = await systemResolver.resolve4(host);
      const address = addresses.find(publicIPv4);
      if (!address) throw new Error('No public system DNS answer');
      answer = { address, ttl: 30, mode: 'system-fallback' };
    }
    status.resolverMode = answer.mode;
    cache.set(host, { address: answer.address, expires: Date.now() + answer.ttl * 1000 });
    return answer.address;
  };
}
function pac(port) {
  return 'function FindProxyForURL(url, host) { host = host.toLowerCase(); var roots = ' + JSON.stringify(SUFFIXES) + '; var links = ' + JSON.stringify(LINK_HOSTS) + '; for (var i=0;i<roots.length;i++) { if(host===roots[i] || dnsDomainIs(host,"."+roots[i])) return "PROXY 127.0.0.1:' + port + '"; } for(var j=0;j<links.length;j++) { if(host===links[j]) return "PROXY 127.0.0.1:' + port + '"; } return "DIRECT"; }';
}
function checkedUpdateUrl(value) {
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443') || !coreHost(url.hostname)) throw new Error('Unapproved update URL');
  return url;
}
function rewriteManifest(value, updateUrl) {
  if (Array.isArray(value)) return value.map(item => rewriteManifest(item, updateUrl));
  if (!value || typeof value !== 'object') return value;
  const result = Object.create(null);
  for (const [key, item] of Object.entries(value)) {
    if (key === 'url' && typeof item === 'string') {
      try { checkedUpdateUrl(item); result[key] = updateUrl(item); } catch { result[key] = item; }
    } else result[key] = rewriteManifest(item, updateUrl);
  }
  return result;
}
function wrapNativeUpdater(native, bridge) {
  if (!native || typeof native.Updater !== 'function') throw new Error('Unsupported native updater export');
  const Updater = new Proxy(native.Updater, { construct(target, args, newTarget) {
    if (!args[0] || typeof args[0].repository_url !== 'string') throw new Error('Unsupported updater repository configuration');
    const rewritten = [{ ...args[0], repository_url: bridge.updateUrl(args[0].repository_url) }, ...args.slice(1)];
    bridge.status.nativeUpdaterConstructed = true;
    bridge.status.nativeUpdaterConstructs++;
    return Reflect.construct(target, rewritten, newTarget);
  } });
  const descriptors = Object.getOwnPropertyDescriptors(native);
  descriptors.Updater = { value: Updater, writable: true, configurable: true, enumerable: descriptors.Updater?.enumerable !== false };
  return Object.create(Object.getPrototypeOf(native), descriptors);
}
async function createBridge(options = {}) {
  const requestedPort = options.port === undefined ? 0 : options.port;
  if (!Number.isInteger(requestedPort) || requestedPort < 0 || requestedPort > 65535) throw new Error('Invalid loopback proxy port');
  const status = { experimental: true, udpSupported: false, connections: 0, failures: 0, httpUpgrades: 0, updateRequests: 0, manifestsRewritten: 0, nativeUpdaterConstructs: 0, nativeUpdaterConstructed: false, resolverMode: 'unused' };
  const resolve = options.resolve || makeResolver(status);
  const connect = options.connect || ((address, port) => net.connect({ host: address, port }));
  const sockets = new Set();
  const track = socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); socket.on('error', () => {}); };
  const token = crypto.randomBytes(24).toString('hex');
  const updateUrl = value => {
    const url = checkedUpdateUrl(value);
    return 'http://127.0.0.1:' + server.address().port + '/updates/' + token + '/' + Buffer.from(url.origin).toString('base64url') + url.pathname + url.search;
  };
  const forwardUpdate = async (request, response) => {
    const match = /^\/updates\/([a-f0-9]{48})\/([A-Za-z0-9_-]+)(\/.*)?$/.exec(request.url || '');
    if (!match || !crypto.timingSafeEqual(Buffer.from(match[1]), Buffer.from(token))) { response.writeHead(403); response.end(); return; }
    if (!['GET', 'HEAD'].includes(request.method)) { response.writeHead(405); response.end(); return; }
    if (!options.fetchUpstream) { response.writeHead(501); response.end(); return; }
    const origin = Buffer.from(match[2], 'base64url').toString('utf8');
    const parsedOrigin = checkedUpdateUrl(origin);
    if (parsedOrigin.origin !== origin || parsedOrigin.pathname !== '/') throw new Error('Invalid update origin');
    const target = checkedUpdateUrl(origin + (match[3] || '/'));
    status.updateRequests++;
    const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 120000); timer.unref();
    response.on('close', () => { clearTimeout(timer); controller.abort(); });
    try {
      const requestHeaders = { 'Accept-Encoding': 'identity' };
      for (const name of ['range', 'if-range']) if (typeof request.headers[name] === 'string') requestHeaders[name] = request.headers[name];
      const upstream = await options.fetchUpstream(target.href, { method: request.method, redirect: 'manual', headers: requestHeaders, signal: controller.signal });
      const headers = {};
      for (const key of ['content-type', 'content-length', 'content-range', 'accept-ranges', 'content-disposition', 'last-modified', 'etag', 'cache-control']) {
        const value = upstream.headers.get(key); if (value) headers[key] = value;
      }
      // Electron fetch transparently decodes content encodings; its body length can differ.
      if (upstream.headers.get('content-encoding')) delete headers['content-length'];
      const location = upstream.headers.get('location');
      if (location) headers.location = updateUrl(new URL(location, target).href);
      const isJson = /(?:application\/json|\+json)/i.test(headers['content-type'] || '');
      if (request.method === 'HEAD' || !upstream.body) { response.writeHead(upstream.status, headers); response.end(); return; }
      if (isJson && upstream.status >= 200 && upstream.status < 300) {
        const chunks = []; let length = 0;
        for await (const chunk of Readable.fromWeb(upstream.body)) { length += chunk.length; if (length > 8 * 1024 * 1024) throw new Error('Update manifest too large'); chunks.push(chunk); }
        const body = Buffer.from(JSON.stringify(rewriteManifest(JSON.parse(Buffer.concat(chunks).toString('utf8')), updateUrl)));
        status.manifestsRewritten++;
        headers['content-length'] = String(body.length); delete headers.etag;
        response.writeHead(upstream.status, headers); response.end(body);
      } else {
        response.writeHead(upstream.status, headers);
        const stream = Readable.fromWeb(upstream.body); stream.on('error', () => response.destroy()); stream.pipe(response);
      }
    } finally { /* Streaming response close releases its timer and request. */ }
  };
  const server = http.createServer((request, response) => {
    if (request.method === 'GET' && request.url === '/proxy.pac') {
      response.writeHead(200, { 'Content-Type': 'application/x-ns-proxy-autoconfig', 'Cache-Control': 'no-store' });
      response.end(pac(server.address().port));
    } else if ((request.url || '').startsWith('/updates/')) {
      forwardUpdate(request, response).catch(() => { status.failures++; if (response.headersSent) response.destroy(); else { response.writeHead(502); response.end(); } });
    } else if (/^http:\/\//i.test(request.url || '')) {
      // An HTTP proxy receives the absolute URL. Upgrade only navigations; never
      // forward a plaintext request body or synthesize payment/API responses.
      let target;
      try { target = new URL(request.url); } catch { response.writeHead(400); response.end(); return; }
      if (!allowedHost(target.hostname) || target.username || target.password || (target.port && target.port !== '80')) {
        response.writeHead(403); response.end(); return;
      }
      if (!['GET', 'HEAD'].includes(request.method)) {
        response.writeHead(405, { Allow: 'GET, HEAD' }); response.end(); return;
      }
      target.protocol = 'https:'; target.port = '';
      status.httpUpgrades++;
      response.writeHead(307, { Location: target.href, 'Cache-Control': 'no-store', 'Content-Length': '0' }); response.end();
    } else { response.writeHead(404); response.end(); }
  });
  server.on('connection', track);
  server.on('connect', async (request, client, head) => {
    const match = /^([a-z0-9.-]+):([1-9][0-9]{0,4})$/i.exec(request.url || '');
    if (!match || !allowedTarget(match[1], Number(match[2]))) { client.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); return; }
    let upstream; let splitter; let timer; let failed = false;
    const fail = () => { if (failed) return; failed = true; status.failures++; clearTimeout(timer); client.destroy(); upstream?.destroy(); splitter?.destroy(); };
    timer = setTimeout(fail, 10000); timer.unref();
    client.once('error', fail);
    try {
      const address = await resolve(match[1].toLowerCase());
      if (!options.allowTestAddress && !publicIPv4(address)) throw new Error('Nonpublic address');
      if (client.destroyed) { clearTimeout(timer); return; }
      upstream = connect(address, Number(match[2])); track(upstream);
      upstream.once('error', fail);
      client.once('close', () => { clearTimeout(timer); upstream.destroy(); });
      upstream.once('close', () => { clearTimeout(timer); if (!client.destroyed) client.end(); });
      upstream.once('connect', () => {
        status.connections++;
        client.write('HTTP/1.1 200 Connection Established\r\n\r\n');
        splitter = new FirstRecordSplitter();
        splitter.once('error', fail);
        splitter.on('data', () => { if (splitter.done) clearTimeout(timer); });
        client.setTimeout(180000, fail); upstream.setTimeout(180000, fail);
        splitter.pipe(upstream); upstream.pipe(client);
        if (head.length) splitter.write(head);
        client.pipe(splitter);
        // First record completion is checked after each transform has returned.
        const check = () => { if (splitter.done) { clearTimeout(timer); client.removeListener('data', check); } };
        client.on('data', check); check();
      });
    } catch { fail(); }
  });
  server.on('clientError', (_, socket) => socket.destroy());
  await new Promise((resolveListen, reject) => { server.once('error', reject); server.listen(requestedPort, '127.0.0.1', resolveListen); });
  const port = server.address().port;
  return { port, pacUrl: 'http://127.0.0.1:' + port + '/proxy.pac', updateUrl, status,
    close: () => { for (const socket of sockets) socket.destroy(); return new Promise(resolveClose => server.close(resolveClose)); } };
}
function writeStatus(status) {
  const folder = path.join(process.env.LOCALAPPDATA || process.cwd(), 'DiscordUnbound');
  fs.mkdirSync(folder, { recursive: true });
  const target = path.join(folder, 'runtime.json');
  const temporary = target + '.' + process.pid + '.tmp';
  fs.writeFileSync(temporary, JSON.stringify({ ...status, pid: process.pid, updatedAt: new Date().toISOString() }, null, 2));
  fs.renameSync(temporary, target);
}
async function installElectronHook(electron) {
  const { app, session } = electron;
  if (app.isReady()) throw new Error('DiscordUnbound must load before Electron is ready');
  const inheritedPort = process.env.DISCORD_BRIDGE_PORT;
  if (inheritedPort !== undefined && !/^(0|[1-9][0-9]{0,4})$/.test(inheritedPort)) throw new Error('Invalid DISCORD_BRIDGE_PORT');
  const bridge = await createBridge({ port: inheritedPort === undefined ? 0 : Number(inheritedPort),
    fetchUpstream: async (url, options) => { await app.whenReady(); return electron.net.fetch(url, options); } });
  const nativePath = path.join(path.dirname(process.execPath), 'updater.node');
  const originalLoad = Module._load;
  Module._load = function(request, parent, isMain) {
    const value = originalLoad.apply(this, arguments);
    let resolved;
    try { resolved = Module._resolveFilename(request, parent, isMain); } catch { return value; }
    if (typeof resolved === 'string' && path.resolve(resolved).toLowerCase() === nativePath.toLowerCase()) return wrapNativeUpdater(value, bridge);
    return value;
  };
  let state = 'hook-listening';
  app.commandLine.appendSwitch('disable-quic');
  app.commandLine.appendSwitch('proxy-pac-url', bridge.pacUrl);
  const apply = target => target.setProxy({ mode: 'pac_script', pacScript: bridge.pacUrl });
  app.on('session-created', target => { apply(target).catch(() => { bridge.status.failures++; }); });
  app.once('will-quit', () => { Module._load = originalLoad; clearInterval(interval); bridge.close(); });
  writeStatus({ ...bridge.status, state, port: bridge.port });
  const interval = setInterval(() => { try { writeStatus({ ...bridge.status, state, port: bridge.port }); } catch {} }, 10000);
  interval.unref();
  app.whenReady().then(async () => {
    await apply(session.defaultSession);
    state = 'hook-active';
    writeStatus({ ...bridge.status, state, port: bridge.port });
  }).catch(() => { state = 'hook-error'; bridge.status.failures++; });
  return bridge;
}
module.exports = { allowedHost, allowedTarget, publicIPv4, FirstRecordSplitter, createBridge, installElectronHook, checkedUpdateUrl, rewriteManifest, wrapNativeUpdater };
if (process.versions.electron) {
  module.exports.ready = installElectronHook(require('electron'));
  module.exports.ready.catch(() => { try { writeStatus({ state: 'hook-error', experimental: true, udpSupported: false }); } catch {} });
}
