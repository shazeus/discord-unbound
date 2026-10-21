"""Loopback-only Discord transport for ordinary system-proxy-aware browsers."""
from __future__ import annotations
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import re
import queue
import select
import socket
import ssl
import threading
import time
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.request import build_opener, ProxyHandler

ROOTS = ('discord.com', 'discord.gg', 'discordapp.com', 'discordapp.net', 'discord.media')
LINKS = ('discord.gift', 'dis.gd')


def allowed_host(host):
    if not isinstance(host, str) or not re.fullmatch(r'[a-zA-Z0-9.-]{1,253}', host): return False
    host = host.lower()
    return host in LINKS or any(host == root or host.endswith('.' + root) for root in ROOTS)


def allowed_target(host, port):
    return allowed_host(host) and type(port) is int and 1 <= port <= 65535 and (
        port == 443 or host.lower() == 'discord.media' or host.lower().endswith('.discord.media'))


def public_ipv4(address):
    try:
        parsed = ipaddress.ip_address(address)
        return parsed.version == 4 and parsed.is_global
    except ValueError: return False


class GoogleConnection(http.client.HTTPSConnection):
    def __init__(self): super().__init__('dns.google', timeout=4.5, context=ssl.create_default_context())
    def connect(self):
        sock = socket.create_connection(('8.8.8.8', 443), self.timeout)
        try: self.sock = self._context.wrap_socket(sock, server_hostname='dns.google')
        except BaseException: sock.close(); raise


class Resolver:
    def __init__(self): self.cache = {}; self.lock = threading.Lock(); self.dns_slots = threading.BoundedSemaphore(8); self.mode = 'unused'
    def system(self, host):
        if not self.dns_slots.acquire(blocking=False): raise OSError('DNS işçi sınırı.')
        result = queue.Queue(maxsize=1)
        def resolve():
            try: result.put([item[4][0] for item in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)])
            except OSError: result.put([])
            finally: self.dns_slots.release()
        threading.Thread(target=resolve, daemon=True).start()
        try: addresses = [ip for ip in result.get(timeout=2.5) if public_ipv4(ip)]
        except queue.Empty: raise OSError('Sistem DNS zaman aşımı.')
        if not addresses: raise OSError('Genel IPv4 adresi bulunamadı.')
        return list(dict.fromkeys(addresses))
    def __call__(self, host):
        with self.lock:
            cached = self.cache.get(host)
            if cached and cached[0] > time.monotonic(): return cached[1]
        connection = GoogleConnection()
        try:
            connection.request('GET', '/resolve?name=' + quote(host) + '&type=A', headers={'Accept': 'application/dns-json'})
            response = connection.getresponse(); raw = response.read(65537)
            if response.status != 200 or len(raw) > 65536: raise OSError('DNS yanıtı geçersiz.')
            result = json.loads(raw)
            if result.get('Status') != 0: raise OSError('DNS çözümlemesi başarısız.')
            records = [r for r in result.get('Answer', []) if r.get('type') == 1 and public_ipv4(r.get('data', ''))]
            if not records: raise OSError('Genel IPv4 adresi bulunamadı.')
            addresses = list(dict.fromkeys(r['data'] for r in records))
            ttl = max(5, min(300, min(r.get('TTL', 30) for r in records)))
            self.mode = 'doh'
        except (OSError, ValueError, http.client.HTTPException):
            addresses = self.system(host); ttl = 30; self.mode = 'system-fallback'
        finally: connection.close()
        with self.lock: self.cache[host] = (time.monotonic() + ttl, addresses)
        return addresses


def split_first_record(record, size=32):
    if len(record) < 9 or record[0] != 22 or record[1] != 3 or record[5] != 1:
        raise ValueError('TLS ClientHello bekleniyordu.')
    length = int.from_bytes(record[3:5], 'big')
    if not 4 <= length <= 18432 or len(record) != 5 + length: raise ValueError('TLS kayıt uzunluğu geçersiz.')
    payload = record[5:]
    return b''.join(record[:3] + len(payload[i:i + size]).to_bytes(2, 'big') + payload[i:i + size] for i in range(0, length, size))


def read_exact(stream, length):
    data = bytearray()
    while len(data) < length:
        chunk = stream.read(length - len(data))
        if not chunk: raise OSError('Bağlantı erken kapandı.')
        data.extend(chunk)
    return bytes(data)


def _static_pac(previous):
    server = previous['server'] if previous['flags'] & 2 else ''
    # Keep proxy selection and bypass rules from the previous manual setup.
    return '''var rules = %s, bypass = %s;
      var pats = bypass.split(';');
      for(var k=0;k<pats.length;k++) { var p=pats[k]; if(!p)continue;
        if((p==='<local>' && isPlainHostName(host)) || (p!=='<local>' && shExpMatch(host,p))) return 'DIRECT'; }
      if(!rules) return 'DIRECT';
      var parts=rules.split(';'), scheme=url.substring(0,url.indexOf(':')).toLowerCase();
      if(scheme==='wss')scheme='https'; if(scheme==='ws')scheme='http';
      var socks=null;
      for(var i=0;i<parts.length;i++){ var a=parts[i].split('=');
        if(a.length===1)return 'PROXY '+a[0]; if(a[0].toLowerCase()===scheme)return 'PROXY '+a[1];
        if(a[0].toLowerCase()==='socks')socks=a[1]; }
      return socks?'SOCKS '+socks:'DIRECT';''' % (json.dumps(server), json.dumps(previous['bypass']))


def compose_pac(port, previous, prior_script=None):
    if prior_script:
        fallback = 'var previous = (function(){\n' + prior_script + '\n;return FindProxyForURL;})();\n'
        fallback_call = 'return previous(url,host);'
    else:
        fallback = ''
        fallback_call = _static_pac(previous)
    return fallback + '''function FindProxyForURL(url,host){ host=host.toLowerCase();
      var roots=%s, links=%s;
      for(var i=0;i<roots.length;i++){if(host===roots[i] || dnsDomainIs(host,'.'+roots[i]))return 'PROXY 127.0.0.1:%d';}
      for(var j=0;j<links.length;j++){if(host===links[j])return 'PROXY 127.0.0.1:%d';}
      %s
    }''' % (json.dumps(ROOTS), json.dumps(LINKS), port, port, fallback_call)


def previous_script(previous):
    url = previous['url'] if previous['flags'] & 4 else ''
    if previous['flags'] & 8 and not url:
        raise RuntimeError('Mevcut WPAD otomatik keşif politikası bu sürümde birleştirilemiyor; ayarlar değiştirilmedi.')
    if not url: return None, 'static-or-direct'
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        raise RuntimeError('Mevcut PAC adresi güvenle birleştirilemiyor; ayarlar değiştirilmedi.')
    try:
        with build_opener(ProxyHandler({})).open(url, timeout=4) as response:
            raw = response.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024: raise RuntimeError('Mevcut PAC dosyası çok büyük.')
        script = raw.decode('utf-8-sig')
        if not re.search(r'\bFindProxyForURL\b', script): raise RuntimeError('Mevcut PAC dosyası geçersiz.')
        return script, 'previous-pac-composed'
    except (OSError, UnicodeError):
        # A dead loopback PAC has no active routing policy. Preserve its exact URL
        # for restoration, and retain its existing manual/direct fallback while active.
        if parsed.hostname in ('127.0.0.1', 'localhost', '::1'):
            return None, 'previous-local-pac-unavailable'
        raise RuntimeError('Mevcut PAC indirilemedi; diğer bağlantıların politikası korunamadığından ayarlar değiştirilmedi.')


class LocalProxy:
    def __init__(self, token, stop_event, resolver=None, connector=None):
        if not re.fullmatch(r'[a-f0-9]{48}', token): raise ValueError('Geçersiz oturum anahtarı.')
        self.token, self.stop_event = token, stop_event
        self.resolver = resolver or Resolver()
        self.connector = connector or (lambda address, port: socket.create_connection((address, port), timeout=4))
        self.pac = ''; self.counters = {'connections': 0, 'failures': 0, 'httpUpgrades': 0}
        self.lock = threading.Lock(); self.slots = threading.BoundedSemaphore(64)
        owner = self
        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = False
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            rbufsize = 0  # Do not consume TLS bytes beyond the exact ClientHello record.
            def setup(self):
                super().setup(); self.connection.settimeout(12)
            def log_message(self, *args): pass
            def answer(self, code, body=b'', headers=None):
                self.send_response(code)
                for key, value in (headers or {}).items(): self.send_header(key, value)
                self.send_header('Content-Length', str(len(body))); self.send_header('Connection', 'close'); self.end_headers()
                if self.command != 'HEAD': self.wfile.write(body)
                self.close_connection = True
            def do_GET(self):
                if self.path == '/' + owner.token + '/proxy.pac':
                    return self.answer(200, owner.pac.encode(), {'Content-Type': 'application/x-ns-proxy-autoconfig', 'Cache-Control': 'no-store'})
                if self.path == '/' + owner.token + '/status':
                    return self.answer(200, json.dumps(owner.counters).encode(), {'Content-Type': 'application/json'})
                try:
                    url = urlsplit(self.path)
                    if url.scheme != 'http' or not allowed_host(url.hostname) or url.username or url.password or url.port not in (None, 80):
                        return self.answer(403)
                except ValueError: return self.answer(400)
                owner.increment('httpUpgrades')
                return self.answer(307, headers={'Location': urlunsplit(('https', url.hostname, url.path, url.query, url.fragment)), 'Cache-Control': 'no-store'})
            do_HEAD = do_GET
            def do_POST(self):
                if self.path == '/' + owner.token + '/stop':
                    self.answer(200); owner.stop_event.set()
                else: self.answer(405)
            def do_CONNECT(self):
                match = re.fullmatch(r'([a-zA-Z0-9.-]+):([1-9][0-9]{0,4})', self.path)
                if not match or not allowed_target(match[1], int(match[2])): return self.answer(403)
                if not owner.slots.acquire(blocking=False): return self.answer(503)
                upstream = None; established = False
                try:
                    addresses = owner.resolver(match[1].lower())
                    for address in addresses[:3]:
                        if not public_ipv4(address): raise OSError('Genel hedef gerekli.')
                        try: upstream = owner.connector(address, int(match[2])); break
                        except OSError: continue
                    if upstream is None: raise OSError('Hedef bağlantısı kurulamadı.')
                    upstream.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    self.send_response(200, 'Connection Established'); self.end_headers(); self.wfile.flush(); established = True
                    header = read_exact(self.rfile, 5)
                    length = int.from_bytes(header[3:5], 'big')
                    if not 4 <= length <= 18432: raise OSError('TLS kayıt sınırı.')
                    hello = header + read_exact(self.rfile, length)
                    upstream.sendall(split_first_record(hello)); owner.increment('connections')
                    self.connection.settimeout(15); upstream.settimeout(15)
                    while not owner.stop_event.is_set():
                        ready, _, _ = select.select([self.connection, upstream], [], [], 1)
                        if not ready: continue
                        for source in ready:
                            data = source.recv(65536)
                            if not data: return
                            (upstream if source is self.connection else self.connection).sendall(data)
                except (OSError, ValueError, ssl.SSLError):
                    owner.increment('failures')
                    if not established:
                        try: self.answer(502)
                        except OSError: pass
                finally:
                    self.close_connection = True
                    if upstream: upstream.close()
                    owner.slots.release()
        self.server = Server(('127.0.0.1', 0), Handler)
        self.port = self.server.server_address[1]
        self.url = 'http://127.0.0.1:' + str(self.port) + '/' + token + '/proxy.pac'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def increment(self, key):
        with self.lock: self.counters[key] += 1
    def start(self): self.thread.start()
    def close(self):
        self.stop_event.set(); self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=3)
