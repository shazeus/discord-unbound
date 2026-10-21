'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const net = require('node:net');
const http = require('node:http');
const vm = require('node:vm');
const os = require('node:os');
const fs = require('node:fs');
const path = require('node:path');
const { EventEmitter } = require('node:events');
const { once } = require('node:events');
const { allowedHost, allowedTarget, publicIPv4, FirstRecordSplitter, createBridge, installElectronHook, rewriteManifest, wrapNativeUpdater, checkedUpdateUrl } = require('../src/bridge-hook.cjs');
function record(payload) { const h = Buffer.from([22, 3, 1, 0, 0]); h.writeUInt16BE(payload.length, 3); return Buffer.concat([h, payload]); }
function unpack(bytes) {
  const parts = []; let n = 0;
  while (n < bytes.length) { assert.equal(bytes[n], 22); const size = bytes.readUInt16BE(n + 3); parts.push(bytes.subarray(n + 5, n + 5 + size)); n += 5 + size; }
  assert.equal(n, bytes.length); return Buffer.concat(parts);
}
test('domain scope and DNS targets reject local and reserved addresses', () => {
  for (const host of ['discord.com', 'gateway.discord.gg', 'CDN.DISCORDAPP.COM', 'x.discord.media']) assert.ok(allowedHost(host));
  for (const host of ['discord.com.evil.test', 'evildiscord.com', '127.0.0.1', 'localhost', 'discord.com@localhost']) assert.equal(allowedHost(host), false);
  for (const address of ['127.0.0.1', '10.1.2.3', '192.168.1.1', '169.254.169.254', '100.64.1.2', '203.0.113.1', '::1', '::ffff:127.0.0.1']) assert.equal(publicIPv4(address), false);
  assert.equal(publicIPv4('8.8.8.8'), true);
  assert.equal(allowedTarget('c-waw02-123.discord.media', 2053), true);
  assert.equal(allowedTarget('discord.com', 2053), false);
  assert.equal(allowedTarget('discord.media.evil.test', 2053), false);
  assert.equal(allowedTarget('discord.media', 65536), false);
});
test('fragmented incoming ClientHello keeps exact handshake bytes and subsequent TLS records', async () => {
  const payload = Buffer.alloc(512); payload[0] = 1;
  for (let i = 4; i < payload.length; i++) payload[i] = i % 256;
  const input = record(payload); const tail = Buffer.from([23, 3, 3, 0, 1, 42]);
  const splitter = new FirstRecordSplitter(); const chunks = [];
  splitter.on('data', chunk => chunks.push(chunk));
  const complete = once(splitter, 'end');
  for (let i = 0; i < input.length; i++) splitter.write(input.subarray(i, i + 1));
  splitter.end(tail); await complete;
  const output = Buffer.concat(chunks);
  assert.deepEqual(output.subarray(-tail.length), tail);
  assert.deepEqual(unpack(output.subarray(0, -tail.length)), payload);
  assert.ok(output.length > input.length + tail.length);
});
test('invalid and truncated TLS fail closed', async () => {
  for (const input of [Buffer.from('GET / HTTP/1.1'), Buffer.from([22, 3, 1, 0xff, 0xff]), Buffer.from([22, 3])]) {
    const splitter = new FirstRecordSplitter();
    const error = once(splitter, 'error'); splitter.resume(); splitter.end(input); await error;
  }
});
test('loopback PAC routes Discord and leaves other resources direct', async t => {
  const bridge = await createBridge(); t.after(() => bridge.close());
  const source = await new Promise((resolve, reject) => http.get(bridge.pacUrl, response => {
    let source = ''; response.on('data', b => source += b); response.on('end', () => resolve(source));
  }).on('error', reject));
  const context = { dnsDomainIs: (host, suffix) => host.endsWith(suffix) }; vm.createContext(context); vm.runInContext(source, context);
  assert.equal(context.FindProxyForURL('https://discord.com', 'discord.com'), 'PROXY 127.0.0.1:' + bridge.port);
  assert.equal(context.FindProxyForURL('https://example.com', 'example.com'), 'DIRECT');
  assert.equal(context.FindProxyForURL('https://discord.com.evil.test', 'discord.com.evil.test'), 'DIRECT');
});
test('configured proxy port validates strictly and retains loopback binding', async t => {
  for (const port of [-1, 65536, 1.5, '443', null, NaN]) await assert.rejects(createBridge({ port }), /Invalid loopback proxy port/);
  const bridge = await createBridge({ port: 0 }); t.after(() => bridge.close());
  assert.ok(bridge.port > 0 && bridge.port <= 65535);
  assert.match(bridge.pacUrl, /^http:\/\/127\.0\.0\.1:/);
});

test('checkout providers remain DIRECT while official gift and support links use the bridge', async t => {
  const bridge = await createBridge(); t.after(() => bridge.close());
  const source = await (await fetch(bridge.pacUrl)).text();
  const context = { dnsDomainIs: (host, suffix) => host.endsWith(suffix) }; vm.createContext(context); vm.runInContext(source, context);
  for (const host of ['js.stripe.com', 'api.stripe.com', 'checkout.stripe.com', 'www.paypal.com', 'payments.braintree-api.com', 'hcaptcha.com', 'accounts.google.com']) {
    assert.equal(context.FindProxyForURL('https://' + host + '/', host), 'DIRECT');
  }
  for (const host of ['discord.gift', 'dis.gd', 'support.discord.com']) assert.equal(context.FindProxyForURL('https://' + host, host), 'PROXY 127.0.0.1:' + bridge.port);
  for (const host of ['discord.gift.evil.test', 'dis.gd.evil.test', 'untrusted.dis.gd']) assert.equal(context.FindProxyForURL('https://' + host, host), 'DIRECT');
  for (const host of ['discord.gift', 'dis.gd']) {
    assert.equal(allowedTarget(host, 443), true);
    assert.equal(allowedTarget(host, 80), false);
    assert.throws(() => checkedUpdateUrl('https://' + host + '/package'), /Unapproved/);
  }
});

test('plain HTTP Discord navigations upgrade to HTTPS without relaying bodies', async t => {
  let resolved = false;
  const bridge = await createBridge({ resolve: async () => { resolved = true; throw new Error('not used'); } }); t.after(() => bridge.close());
  const request = (target, method = 'GET') => new Promise((resolve, reject) => {
    const outgoing = http.request({ host: '127.0.0.1', port: bridge.port, path: target, method }, response => {
      response.resume(); response.on('end', () => resolve({ status: response.statusCode, location: response.headers.location }));
    }); outgoing.on('error', reject); outgoing.end();
  });
  for (const target of ['http://discord.com/nitro?ref=test', 'http://discord.gift/not-a-real-gift', 'http://dis.gd/contact']) {
    const result = await request(target); assert.equal(result.status, 307);
    assert.equal(result.location, target.replace('http:', 'https:'));
  }
  assert.equal((await request('http://discord.com/nitro', 'HEAD')).status, 307);
  assert.equal((await request('http://discord.com/api/payments', 'POST')).status, 405);
  for (const target of ['http://discord.com.evil.test/', 'http://user:pass@discord.com/', 'http://discord.com:8080/']) assert.equal((await request(target)).status, 403);
  assert.equal(resolved, false); assert.equal(bridge.status.httpUpgrades, 4);
});
test('CONNECT rejects unapproved domains and ports before resolving', async t => {
  let called = false; const bridge = await createBridge({ resolve: () => { called = true; throw new Error('unexpected'); } }); t.after(() => bridge.close());
  for (const target of ['localhost:443', 'discord.com:80', 'discord.com.evil.test:443', '[::1]:443']) {
    const socket = net.connect(bridge.port, '127.0.0.1'); socket.setEncoding('utf8');
    const response = once(socket, 'data'); socket.write('CONNECT ' + target + ' HTTP/1.1\r\nHost: ' + target + '\r\n\r\n');
    assert.match((await response)[0], /403 Forbidden/); socket.destroy();
  }
  assert.equal(called, false);
});
test('CONNECT forwards reframed handshake and receives target bytes', async t => {
  let received = Buffer.alloc(0);
  const target = net.createServer(socket => {
    socket.on('data', data => { received = Buffer.concat([received, data]); if (received.length >= 90) socket.write('upstream-reply'); });
  });
  await new Promise(resolve => target.listen(0, '127.0.0.1', resolve));
  const bridge = await createBridge({ allowTestAddress: true, resolve: async () => '127.0.0.1', connect: address => net.connect(target.address().port, address) });
  t.after(async () => { await bridge.close(); await new Promise(resolve => target.close(resolve)); });
  const client = net.connect(bridge.port, '127.0.0.1');
  const handshake = Buffer.alloc(80, 7); handshake[0] = 1;
  let response = once(client, 'data');
  client.write('CONNECT discord.com:443 HTTP/1.1\r\nHost: discord.com:443\r\n\r\n');
  assert.match((await response)[0].toString(), /200 Connection Established/);
  response = once(client, 'data');
  const hello = record(handshake); client.write(hello.subarray(0, 3)); client.write(hello.subarray(3));
  assert.equal((await response)[0].toString(), 'upstream-reply');
  assert.deepEqual(unpack(received), handshake); assert.equal(bridge.status.connections, 1); client.destroy();
});
test('voice signaling CONNECT retains Discord media TLS port 2053', async t => {
  let observedPort;
  const target = net.createServer(socket => socket.on('data', () => socket.write('voice-signaling-reply')));
  await new Promise(resolve => target.listen(0, '127.0.0.1', resolve));
  const bridge = await createBridge({ allowTestAddress: true, resolve: async () => '127.0.0.1', connect: (address, port) => {
    observedPort = port; return net.connect(target.address().port, address);
  } });
  t.after(async () => { await bridge.close(); await new Promise(resolve => target.close(resolve)); });
  const client = net.connect(bridge.port, '127.0.0.1');
  let response = once(client, 'data');
  client.write('CONNECT c-waw02-123.discord.media:2053 HTTP/1.1\r\nHost: c-waw02-123.discord.media:2053\r\n\r\n');
  assert.match((await response)[0].toString(), /200 Connection Established/);
  response = once(client, 'data'); client.write(record(Buffer.from([1, 0, 0, 0])));
  assert.equal((await response)[0].toString(), 'voice-signaling-reply');
  assert.equal(observedPort, 2053); client.destroy();
});
test('hook resolves before app readiness, sets startup PAC and applies future sessions', async t => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'discordbridge-test-'));
  const proxyEnvironment = new Map(['HTTPS_PROXY', 'https_proxy', 'NO_PROXY', 'no_proxy', 'DISCORD_BRIDGE_PORT'].map(key => [key, process.env[key]]));
  delete process.env.DISCORD_BRIDGE_PORT;
  const previousLocalAppData = process.env.LOCALAPPDATA; process.env.LOCALAPPDATA = folder;
  t.after(() => {
    for (const [key, value] of proxyEnvironment) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
    if (previousLocalAppData === undefined) delete process.env.LOCALAPPDATA; else process.env.LOCALAPPDATA = previousLocalAppData;
    fs.rmSync(folder, { recursive: true, force: true });
  });
  const app = new EventEmitter(); const switches = new Map(); let resolveReady;
  app.isReady = () => false;
  app.commandLine = { appendSwitch: (name, value) => switches.set(name, value) };
  app.whenReady = () => new Promise(resolve => { resolveReady = resolve; });
  const calls = []; const defaultSession = { setProxy: async options => calls.push(options) };
  const bridge = await installElectronHook({ app, session: { defaultSession } });
  t.after(async () => { app.emit('will-quit'); await bridge.close(); });
  assert.equal(calls.length, 0);
  assert.ok(switches.has('disable-quic'));
  assert.equal(switches.get('proxy-pac-url'), bridge.pacUrl);
  for (const key of ['HTTPS_PROXY', 'https_proxy', 'NO_PROXY', 'no_proxy']) assert.equal(process.env[key], proxyEnvironment.get(key));
  const futureCalls = [];
  app.emit('session-created', { setProxy: async options => futureCalls.push(options) });
  assert.equal(futureCalls[0].pacScript, bridge.pacUrl);
  resolveReady(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls[0].mode, 'pac_script');
  const status = JSON.parse(fs.readFileSync(path.join(folder, 'DiscordUnbound', 'runtime.json')));
  assert.equal(status.state, 'hook-active');
  assert.equal(status.udpSupported, false);
});
test('hook rejects malformed inherited ports before binding', async () => {
  const previous = process.env.DISCORD_BRIDGE_PORT;
  try {
    for (const value of ['65536', '-1', 'abc', '1.2', '', ' 443', '0443']) {
      process.env.DISCORD_BRIDGE_PORT = value;
      await assert.rejects(installElectronHook({ app: { isReady: () => false } }), /Invalid/);
    }
  } finally {
    if (previous === undefined) delete process.env.DISCORD_BRIDGE_PORT; else process.env.DISCORD_BRIDGE_PORT = previous;
  }
});
test('native updater adapter preserves constructor, arguments, options and hashes', async t => {
  const bridge = await createBridge(); t.after(() => bridge.close());
  class NativeUpdater { constructor(options, extra) { this.options = options; this.extra = extra; } command() { return 42; } }
  const native = { Updater: NativeUpdater, version: 7 };
  const wrapped = wrapNativeUpdater(native, bridge);
  const original = { repository_url: 'https://canary.discord.com/api/updates/', other: 'retained' };
  const updater = new wrapped.Updater(original, 'extra');
  assert.ok(updater instanceof NativeUpdater); assert.equal(updater.command(), 42);
  assert.equal(updater.extra, 'extra'); assert.equal(updater.options.other, 'retained');
  assert.ok(updater.options.repository_url.startsWith('http://127.0.0.1:'));
  assert.equal(original.repository_url, 'https://canary.discord.com/api/updates/');
  assert.equal(wrapped.version, 7);
  assert.throws(() => new wrapped.Updater({ repository_url: 'https://example.com/' }), /Unapproved/);
  const source = { package_sha256: 'abc', nested: [{ url: 'https://cdn.discordapp.com/pkg', sha256: 'xyz' }], url: 'https://example.com/unrelated' };
  const result = rewriteManifest(source, bridge.updateUrl);
  assert.equal(result.package_sha256, 'abc'); assert.equal(result.nested[0].sha256, 'xyz');
  assert.equal(result.nested[0].url, bridge.updateUrl(source.nested[0].url));
  assert.equal(result.url, source.url);
});
test('tokenized updater route rewrites JSON URL fields and streams binary bytes', async t => {
  const binary = Buffer.from([0, 255, 128, 1, 13, 10]); const targets = [];
  const bridge = await createBridge({ fetchUpstream: async (url, options) => {
    targets.push({ url, options });
    if (url.endsWith('/manifest')) return new Response(JSON.stringify({ package_sha256: '012345', packages: [{ url: 'https://cdn.discordapp.com/file.zip' }] }), { headers: { 'content-type': 'application/json' } });
    return new Response(binary, { headers: { 'content-type': 'application/octet-stream', 'content-length': String(binary.length) } });
  } }); t.after(() => bridge.close());
  const manifestResponse = await fetch(bridge.updateUrl('https://canary.discord.com/manifest'));
  assert.equal(manifestResponse.status, 200);
  const manifest = await manifestResponse.json(); assert.equal(manifest.package_sha256, '012345');
  assert.equal(manifest.packages[0].url, bridge.updateUrl('https://cdn.discordapp.com/file.zip'));
  const binaryResponse = await fetch(manifest.packages[0].url);
  assert.deepEqual(Buffer.from(await binaryResponse.arrayBuffer()), binary);
  assert.equal(targets[1].url, 'https://cdn.discordapp.com/file.zip');
  assert.equal(targets[0].options.redirect, 'manual');
  const unauthorized = bridge.updateUrl('https://discord.com/a').replace(/updates\/[a-f0-9]{48}/, 'updates/' + '0'.repeat(48));
  assert.equal((await fetch(unauthorized)).status, 403);
});
