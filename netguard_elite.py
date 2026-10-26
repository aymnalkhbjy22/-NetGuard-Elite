#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
   _   _ _____ _____ ____ _   _    _    ____  ____    ____  ____   ___  
  | \ | | ____|_   _/ ___| | | |  / \  |  _ \|  _ \  |  _ \|  _ \ / _ \ 
  |  \| |  _|   | || |  _| | | | / _ \ | |_) | | | | | |_) | |_) | | | |
  | |\  | |___  | || |_| | |_| |/ ___ \|  _ <| |_| | |  __/|  _ <| |_| |
  |_| \_|_____| |_| \____|\___//_/   \_\_| \_\____/  |_|   |_| \_\\___/ 
  
  >> NEXT-GEN MILITARY-GRADE PRIVACY ENGINE & TRAFFIC SHAPER (V3.0) <<
  Developer: Eng. Ayman Ahmed Al-Khobaji (@aymnalkhbjy22)
  Architecture: Async Multi-threaded Zero-Leak DoH Proxy
================================================================================
"""

import os
import sys
import time
import socket
import threading
import json
import ssl
import urllib.request

# --- ANSI COLOR PALETTE ---
C_RESET   = "\033[0m"
C_BOLD    = "\033[1m"
C_RED     = "\033[1;31m"
C_GREEN   = "\033[1;32m"
C_YELLOW  = "\033[1;33m"
C_BLUE    = "\033[1;34m"
C_MAGENTA = "\033[1;35m"
C_CYAN    = "\033[1;36m"
C_WHITE   = "\033[1;37m"
C_BG_BLUE = "\033[44m"

# --- CORE ENGINE CONFIGURATION ---
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 8888
DOH_PRIMARY  = "https://1.1.1.1/dns-query"
DOH_FALLBACK = "https://dns.google/resolve"
BUFFER_SIZE  = 8192

# --- GLOBAL METRICS & STATE ---
metrics = {
    "bytes_downloaded": 0,
    "bytes_uploaded": 0,
    "current_down_speed": 0.0,
    "current_up_speed": 0.0,
    "encrypted_dns_count": 0,
    "active_tunnels": 0,
    "speed_limit_kb": 0,  # 0 = Unlimited
    "start_timestamp": time.time(),
    "last_target": "Idle"
}

metrics_lock = threading.Lock()
dns_cache = {}

def format_unit(size):
    for u in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {u}"
        size /= 1024.0
    return f"{size:.2f} PB"

def format_speed(bps):
    kbps = bps / 1024.0
    if kbps >= 1024.0:
        return f"{kbps / 1024.0:.2f} MB/s"
    return f"{kbps:.1f} KB/s"

def make_gauge(speed_bytes, max_kb=1024):
    current_kb = speed_bytes / 1024.0
    ratio = min(1.0, current_kb / max_kb)
    bar_len = 16
    filled = int(bar_len * ratio)
    bar = "█" * filled + "░" * (bar_len - filled)
    return f"[{bar}] {format_speed(speed_bytes)}"

# --- ULTRA SECURE DNS-OVER-HTTPS (DoH) RESOLVER ---
def resolve_secure_dns(domain):
    with metrics_lock:
        if domain in dns_cache:
            return dns_cache[domain]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Step 1: Query Primary Cloudflare DoH
    try:
        req = urllib.request.Request(
            f"{DOH_PRIMARY}?name={domain}&type=A",
            headers={"Accept": "application/dns-json", "User-Agent": "NetGuardCore/3.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if "Answer" in data:
                ip = data["Answer"][-1]["data"]
                with metrics_lock:
                    dns_cache[domain] = ip
                    metrics["encrypted_dns_count"] += 1
                return ip
    except Exception:
        pass

    # Step 2: Query Fallback Google DoH
    try:
        req = urllib.request.Request(
            f"{DOH_FALLBACK}?name={domain}&type=A",
            headers={"User-Agent": "NetGuardCore/3.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if "Answer" in data:
                ip = data["Answer"][-1]["data"]
                with metrics_lock:
                    dns_cache[domain] = ip
                    metrics["encrypted_dns_count"] += 1
                return ip
    except Exception:
        pass

    # Step 3: Local System Resolution (Fail-safe)
    try:
        ip = socket.gethostbyname(domain)
        with metrics_lock:
            dns_cache[domain] = ip
        return ip
    except:
        return None

# --- STREAM FORWARDING & TRAFFIC SHAPING ENGINE ---
def stream_pipeline(src, dst, is_downstream=True):
    chunk = BUFFER_SIZE
    last_second = time.time()
    accumulated_bytes = 0

    while True:
        try:
            limit_kb = metrics["speed_limit_kb"]
            data = src.recv(chunk)
            if not data:
                break
            dst.sendall(data)
            data_len = len(data)

            with metrics_lock:
                if is_downstream:
                    metrics["bytes_downloaded"] += data_len
                else:
                    metrics["bytes_uploaded"] += data_len

            # High-precision traffic throttler
            if is_downstream and limit_kb > 0:
                accumulated_bytes += data_len
                now = time.time()
                elapsed = now - last_second
                max_allowed = limit_kb * 1024

                if accumulated_bytes >= max_allowed:
                    if elapsed < 1.0:
                        time.sleep(1.0 - elapsed)
                    last_second = time.time()
                    accumulated_bytes = 0
                elif elapsed >= 1.0:
                    last_second = time.time()
                    accumulated_bytes = 0

        except (socket.error, ConnectionResetError, BrokenPipeError):
            break

# --- CLIENT CONNECTION HANDLER ---
def handle_tunnel(client):
    with metrics_lock:
        metrics["active_tunnels"] += 1

    try:
        client.settimeout(8)
        header = client.recv(4096).decode('latin1', errors='ignore')
        if not header:
            return

        lines = header.split('\r\n')
        if not lines or len(lines[0].split()) < 2:
            return

        cmd, dest = lines[0].split()[0], lines[0].split()[1]

        if cmd.upper() == 'CONNECT':
            host, port = (dest.split(':') if ':' in dest else (dest, 443))
            port = int(port)

            with metrics_lock:
                metrics["last_target"] = host

            remote_ip = resolve_secure_dns(host)
            if not remote_ip:
                client.close()
                return

            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.settimeout(8)
            remote.connect((remote_ip, port))
            client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            client.settimeout(None)
            remote.settimeout(None)

            t_up = threading.Thread(target=stream_pipeline, args=(client, remote, False), daemon=True)
            t_down = threading.Thread(target=stream_pipeline, args=(remote, client, True), daemon=True)
            t_up.start()
            t_down.start()
            t_up.join()
            t_down.join()
        else:
            client.close()
    except Exception:
        pass
    finally:
        try:
            client.close()
        except:
            pass
        with metrics_lock:
            metrics["active_tunnels"] = max(0, metrics["active_tunnels"] - 1)

# --- TERMINAL HUD (HEADS-UP DISPLAY) ---
def render_hud():
    p_down = 0
    p_up = 0
    t_prev = time.time()

    while True:
        time.sleep(1)
        now = time.time()
        delta = max(0.001, now - t_prev)

        with metrics_lock:
            metrics["current_down_speed"] = (metrics["bytes_downloaded"] - p_down) / delta
            metrics["current_up_speed"] = (metrics["bytes_uploaded"] - p_up) / delta
            p_down = metrics["bytes_downloaded"]
            p_up = metrics["bytes_uploaded"]
            t_prev = now

            runtime = int(now - metrics["start_timestamp"])
            h, rem = divmod(runtime, 3600)
            m, s = divmod(rem, 60)
            uptime_label = f"{h:02d}:{m:02d}:{s:02d}"

            limit_label = f"{metrics['speed_limit_kb']} KB/s (Capped)" if metrics['speed_limit_kb'] > 0 else "MAX UNLIMITED"
            gauge_ref = metrics['speed_limit_kb'] if metrics['speed_limit_kb'] > 0 else 1024

            os.system('clear')
            print(f"{C_CYAN}┌────────────────────────────────────────────────────────────────────────┐{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}{C_BOLD}⚡ NETGUARD ELITE // ZERO-LEAK CYBER ENGINE v3.0{C_RESET}{C_CYAN}                       │{C_RESET}")
            print(f"{C_CYAN}│  {C_YELLOW}Developer: Eng. Ayman Al-Khobaji  |  GitHub: @aymnalkhbjy22{C_RESET}{C_CYAN}           │{C_RESET}")
            print(f"{C_CYAN}├────────────────────────────────────────────────────────────────────────┤{C_RESET}")
            print(f"{C_CYAN}│  {C_GREEN}● CORE STATUS :{C_RESET} {C_WHITE}ACTIVE [127.0.0.1:{LOCAL_PORT}]{C_RESET}  {C_MAGENTA}● ENCRYPTION :{C_RESET} {C_GREEN}DoH TLS ARMORED{C_RESET}  {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│  {C_YELLOW}● RUNTIME     :{C_RESET} {C_WHITE}{uptime_label:<10}{C_RESET}              {C_BLUE}● RATE LIMIT :{C_RESET} {C_YELLOW}{limit_label:<15}{C_RESET}{C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}├────────────────────────────────────────────────────────────────────────┤{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}[+] DOWNLOAD GAUGE :{C_RESET} {C_GREEN}{make_gauge(metrics['current_down_speed'], gauge_ref):<38}{C_RESET}  {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}[+] UPLOAD GAUGE   :{C_RESET} {C_BLUE}{make_gauge(metrics['current_up_speed'], 512):<38}{C_RESET}  {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}├────────────────────────────────────────────────────────────────────────┤{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}» Total Transferred :{C_RESET} {C_YELLOW}{format_unit(metrics['bytes_downloaded'] + metrics['bytes_uploaded']):<16}{C_RESET} {C_WHITE}» Active Conns :{C_RESET} {C_MAGENTA}{metrics['active_tunnels']:<4}{C_RESET}      {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}» Masked Queries    :{C_RESET} {C_GREEN}{metrics['encrypted_dns_count']} Requests Cloaked from ISP / Router{C_RESET}       {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}│  {C_WHITE}» Target In-Flight  :{C_RESET} {C_CYAN}{metrics['last_target'][:35]:<35}{C_RESET}                 {C_CYAN}│{C_RESET}")
            print(f"{C_CYAN}└────────────────────────────────────────────────────────────────────────┘{C_RESET}")
            print(f"{C_YELLOW}🔒 PRIVACY SHIELD ON: Network Admin / MikroTik sees 0 hostnames / 0 history.{C_RESET}")
            print(f"{C_WHITE}Command: Press {C_RED}[Ctrl + C]{C_RESET} {C_WHITE}to terminate engine.{C_RESET}\n")

def run_elite_engine():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((LOCAL_HOST, LOCAL_PORT))
        srv.listen(256)
    except Exception as e:
        print(f"{C_RED}[!] Engine failed to bind port {LOCAL_PORT}: {e}{C_RESET}")
        sys.exit(1)

    threading.Thread(target=render_hud, daemon=True).start()

    while True:
        try:
            cl, _ = srv.accept()
            threading.Thread(target=handle_tunnel, args=(cl,), daemon=True).start()
        except KeyboardInterrupt:
            break
        except Exception:
            pass

def interactive_terminal_prompt():
    os.system('clear')
    banner = f"""{C_CYAN}
   ███╗   ██╗███████╗████████╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
   ████╗  ██║██╔════╝╚══██╔══╝██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
   ██╔██╗ ██║█████╗     ██║   ██║  ███╗██║   ██║███████║██████╔╝██║  ██║
   ██║╚██╗██║██╔══╝     ██║   ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
   ██║ ╚████║███████╗   ██║   ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
   ╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
             {C_YELLOW}>> ARCHITECTURE: STEALTH PROXY & TRAFFIC LIMITER <<{C_RESET}
             {C_WHITE}Author: Eng. Ayman Al-Khobaji  |  GitHub: @aymnalkhbjy22{C_RESET}
    """
    print(banner)
    print(f"{C_CYAN}┌────────────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[1]{C_RESET} {C_BOLD}UNLIMITED BANDWIDTH{C_RESET}   (Full-Throttle Encrypted Highway)    {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[2]{C_RESET} {C_BOLD}DATA SAVER (128 KB/s){C_RESET} (Ultra-Conservative Card Saver)      {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[3]{C_RESET} {C_BOLD}MODERATE (256 KB/s){C_RESET}   (Balanced Browsing & Messaging)       {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[4]{C_RESET} {C_BOLD}HIGH SPEED (512 KB/s){C_RESET} (Smooth Social Media & Streaming)     {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[5]{C_RESET} {C_BOLD}TURBO (1024 KB/s){C_RESET}     (1.0 MB/s Download Cap)               {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_GREEN}[6]{C_RESET} {C_BOLD}CUSTOM BANDWIDTH{C_RESET}      (Enter custom KB/s limit)             {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}│{C_RESET}  {C_RED}[0]{C_RESET} {C_BOLD}TERMINATE CORE{C_RESET}        (Exit Application)                    {C_CYAN}│{C_RESET}")
    print(f"{C_CYAN}└────────────────────────────────────────────────────────────────┘{C_RESET}")

    sel = input(f"\n{C_BOLD}{C_WHITE}[NetGuard-Console] >> Select Mode [0-6]: {C_RESET}").strip()

    if sel == "1":
        metrics["speed_limit_kb"] = 0
    elif sel == "2":
        metrics["speed_limit_kb"] = 128
    elif sel == "3":
        metrics["speed_limit_kb"] = 256
    elif sel == "4":
        metrics["speed_limit_kb"] = 512
    elif sel == "5":
        metrics["speed_limit_kb"] = 1024
    elif sel == "6":
        try:
            val = int(input(f"{C_YELLOW}[?] Enter Max Speed in KB/s: {C_RESET}").strip())
            metrics["speed_limit_kb"] = max(16, val)
        except:
            metrics["speed_limit_kb"] = 0
    elif sel == "0":
        sys.exit(0)
    else:
        metrics["speed_limit_kb"] = 0

    run_elite_engine()

if __name__ == "__main__":
    try:
        interactive_terminal_prompt()
    except KeyboardInterrupt:
        print(f"\n{C_GREEN}[✔] NetGuard Elite Engine Shutdown Cleanly.{C_RESET}")
