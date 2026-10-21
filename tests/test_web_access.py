"""Local fixtures: never change the tester's Windows proxy configuration."""
from pathlib import Path
import io
import json
import socket
import struct
import subprocess
import sys
import threading
import unittest
from urllib.request import build_opener, ProxyHandler, Request
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from proxy_settings import active_settings, restore_owned
from web_proxy import allowed_host, allowed_target, split_first_record, compose_pac, LocalProxy


class MemoryProxy:
    def __init__(self, settings): self.settings = settings.copy(); self.writes = 0
    def read(self): return self.settings.copy()
    def write(self, value): self.settings = value.copy(); self.writes += 1


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.previous = {'flags': 13, 'server': 'old.example:8080', 'bypass': '<local>', 'url': 'http://old.example/proxy.pac'}
        self.installed = active_settings(self.previous, 'http://127.0.0.1:12345/secret/proxy.pac')
    def test_round_trip_restores_original_flags_and_url(self):
        backend = MemoryProxy(self.installed)
        self.assertEqual(restore_owned(backend, self.previous, self.installed), 'restored')
        self.assertEqual(backend.read(), self.previous)
    def test_external_new_pac_is_never_overwritten(self):
        backend = MemoryProxy({**self.installed, 'url': 'https://new.example/new.pac'})
        before = backend.read()
        self.assertEqual(restore_owned(backend, self.previous, self.installed), 'external_change_preserved')
        self.assertEqual(backend.read(), before); self.assertEqual(backend.writes, 0)
    def test_manual_settings_changed_during_session_survive_restore(self):
        backend = MemoryProxy({**self.installed, 'server': 'new.example:9000', 'bypass': '*.example'})
        restore_owned(backend, self.previous, self.installed)
        self.assertEqual(backend.read(), {**self.previous, 'server': 'new.example:9000', 'bypass': '*.example'})
    def test_external_flag_change_survives_restore(self):
        backend = MemoryProxy({**self.installed, 'flags': 7})
        restore_owned(backend, self.previous, self.installed)
        self.assertEqual(backend.read()['flags'], 7)


def evaluate_pac(source, requests):
    script = '''const vm=require('vm');let s='';process.stdin.on('data',c=>s+=c);process.stdin.on('end',()=>{
      const d=JSON.parse(s),c={dnsDomainIs:(h,s)=>h.endsWith(s),isPlainHostName:h=>!h.includes('.'),
      shExpMatch:(h,p)=>new RegExp('^'+p.replace(/[.+^${}()|[\\]\\\\]/g,'\\\\$&').replace(/\\*/g,'.*').replace(/\\?/g,'.')+'$').test(h)};
      vm.createContext(c);vm.runInContext(d.source,c,{timeout:1000});
      console.log(JSON.stringify(d.requests.map(r=>c.FindProxyForURL(r[0],r[1]))));});'''
    result = subprocess.run(['node', '-e', script], input=json.dumps({'source': source, 'requests': requests}), text=True, capture_output=True, check=True, timeout=5)
    return json.loads(result.stdout)


class PacTests(unittest.TestCase):
    def test_discord_only_routing_and_direct_payment_provider(self):
        previous = {'flags': 1, 'server': '', 'bypass': '', 'url': ''}
        source = compose_pac(23456, previous)
        hosts = ['discord.com', 'cdn.discordapp.com', 'discord.gift', 'dis.gd', 'discord.com.evil.test', 'js.stripe.com', 'example.com']
        result = evaluate_pac(source, [('https://' + h, h) for h in hosts])
        self.assertEqual(result[:4], ['PROXY 127.0.0.1:23456'] * 4)
        self.assertEqual(result[4:], ['DIRECT'] * 3)
    def test_existing_pac_policy_is_composed_for_other_hosts(self):
        previous = {'flags': 5, 'server': '', 'bypass': '', 'url': 'https://corp.example/pac'}
        old = "function FindProxyForURL(url,host){return host==='inside.example'?'PROXY corp.example:8080':'DIRECT';}"
        result = evaluate_pac(compose_pac(23456, previous, old), [('https://inside.example', 'inside.example'), ('https://discord.com', 'discord.com')])
        self.assertEqual(result, ['PROXY corp.example:8080', 'PROXY 127.0.0.1:23456'])
    def test_manual_proxy_protocols_and_local_bypass_preserved(self):
        previous = {'flags': 3, 'server': 'http=corp.example:80;https=corp.example:443', 'bypass': '<local>;*.intranet', 'url': ''}
        result = evaluate_pac(compose_pac(23456, previous), [('https://outside.example', 'outside.example'), ('http://outside.example', 'outside.example'), ('https://printer', 'printer'), ('https://a.intranet', 'a.intranet')])
        self.assertEqual(result, ['PROXY corp.example:443', 'PROXY corp.example:80', 'DIRECT', 'DIRECT'])


class TransportTests(unittest.TestCase):
    def test_split_preserves_handshake_payload(self):
        payload = b'\x01' + bytes(range(255))
        record = b'\x16\x03\x01' + len(payload).to_bytes(2, 'big') + payload
        result = split_first_record(record)
        recovered = b''
        while result:
            size = int.from_bytes(result[3:5], 'big'); recovered += result[5:5+size]; result = result[5+size:]
        self.assertEqual(recovered, payload)
        for invalid in (b'', b'GET /', b'\x16\x03\x01\xff\xff' + payload):
            with self.assertRaises(ValueError): split_first_record(invalid)
    def test_scope_and_ports(self):
        self.assertTrue(allowed_target('voice.discord.media', 2053))
        for host, port in [('discord.com.evil.test',443), ('localhost',443), ('discord.com',80), ('discord.media',65536)]: self.assertFalse(allowed_target(host,port))
    def test_tunnel_preserves_coalesced_application_bytes_and_shutdown(self):
        listener = socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen()
        received = bytearray(); complete = threading.Event()
        appdata = b'\x17\x03\x03\x00\x09some-data'
        payload = b'\x01\x00\x00\x00' + b'a'*96
        hello = b'\x16\x03\x01' + len(payload).to_bytes(2,'big') + payload
        expected = split_first_record(hello) + appdata
        def target():
            connection,_ = listener.accept()
            with connection:
                while len(received) < len(expected):
                    chunk = connection.recv(4096)
                    if not chunk: break
                    received.extend(chunk)
                connection.sendall(b'reply'); complete.set()
        threading.Thread(target=target,daemon=True).start()
        event = threading.Event()
        proxy = LocalProxy('a'*48, event, resolver=lambda h:['8.8.8.8'], connector=lambda a,p:socket.create_connection(('127.0.0.1',listener.getsockname()[1])))
        proxy.pac = 'function FindProxyForURL(){return "DIRECT";}'; proxy.start()
        try:
            with socket.create_connection(('127.0.0.1',proxy.port),timeout=3) as client:
                client.sendall(b'CONNECT discord.com:443 HTTP/1.1\r\nHost: discord.com\r\n\r\n')
                data=b''
                while b'\r\n\r\n' not in data:data+=client.recv(1)
                self.assertIn(b'200 Connection Established',data)
                client.sendall(hello+appdata)
                self.assertEqual(client.recv(5),b'reply')
            self.assertTrue(complete.wait(2)); self.assertEqual(bytes(received),expected)
        finally: proxy.close(); listener.close()
    def test_pac_and_control_routes_require_session_token(self):
        event=threading.Event(); proxy=LocalProxy('b'*48,event);proxy.pac='test-pac';proxy.start()
        opener=build_opener(ProxyHandler({}))
        try:
            self.assertEqual(opener.open(proxy.url,timeout=2).read(),b'test-pac')
            with self.assertRaises(Exception):opener.open('http://127.0.0.1:'+str(proxy.port)+'/proxy.pac',timeout=2)
            response=opener.open(Request(proxy.url.replace('/proxy.pac','/stop'),method='POST'),timeout=2)
            self.assertEqual(response.status,200);self.assertTrue(event.wait(1))
        finally:proxy.close()


if __name__=='__main__':unittest.main()
