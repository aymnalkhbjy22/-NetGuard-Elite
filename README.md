
# ⚡ NetGuard Elite v3.0
> **Next-Gen Privacy Shield & Precision Bandwidth Limiter**  
> *Developed by: Eng. Ayman Ahmed Al-Khobaji*

---

## 📖 About The Tool (نبذة عن الأداة)
**NetGuard Elite** is a lightweight, zero-leak network security engine built for **Android (Termux)** and **Linux**. It is engineered to bypass local network inspection (such as MikroTik and public Wi-Fi logs) by encrypting domain lookups and controlling internet consumption.

---

## ⚙️ How It Works (كيف تعمل الأداة؟)

1. **DNS-over-HTTPS (DoH) Encryption:**
   * Instead of sending unencrypted DNS queries to the router, all domain lookups are tunneled through **Cloudflare** (`1.1.1.1`) and **Google DNS** over encrypted HTTPS (TLS 1.3).
   * **Result:** The router/MikroTik log registers **ZERO hostnames, URLs, or browsing history**.

2. **Blind TLS Tunneling (Anti-DPI):**
   * Encapsulates all web traffic through a secure local proxy (`127.0.0.1:8888`), preventing Deep Packet Inspection (DPI) appliances from analyzing packet contents.

3. **Traffic Shaping & Speed Limiting:**
   * Uses an integrated packet throttler to enforce exact download limits (e.g., 128 KB/s, 256 KB/s, 512 KB/s, 1024 KB/s), preserving card quotas and preventing background data drain.

---

## 🌟 Key Features (أهم المميزات)

* 🔒 **Zero DNS Leaks:** Completely hides every website you visit from local network monitoring.
* ⚡ **Bandwidth Control:** Multiple speed profiles to suit your browsing needs and protect data balance.
* 📊 **Live Terminal HUD:** Dynamic ASCII gauges showing real-time upload/download speeds, live data usage, and encrypted query counts.
* 🪶 **100% Dependency-Free:** Runs natively using pure Python standard libraries without installing external packages.

---

## 🚀 Quick Usage (طريقة الاستخدام)

1. **Start the engine in Termux:**
   ```bash
   python3 netguard_elite.py

 * Configure your phone's Wi-Fi Proxy:
   * Proxy Type: Manual
   * Host: 127.0.0.1
   * Port: 8888
   * Bypass for: 192.168.88.1, 10.0.0.1 (Network Login Page)
👨‍💻 Developer & Author
 * Developer: Eng. Ayman Ahmed Al-Khobaji
 * GitHub: @aymnalkhbjy22
 * Specialty: Cybersecurity & Software    .
 

