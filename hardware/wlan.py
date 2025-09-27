import network
import time
import hardware.WLAN_KEY as wlan_key

ssid = wlan_key.ssid
password = wlan_key.password

class WLAN:
    def __init__(self):
        self.wlan_obj = network.WLAN(network.WLAN.IF_STA)

    def connectWiFi(self, retries=5, wait_per_try=5):
        """
        Connect to WiFi with retries and clear status reporting.
        """
        if not self.wlan_obj.active():
            self.wlan_obj.active(True)

        for attempt in range(1, retries + 1):
            print(f"Connect attempt {attempt} to SSID: {repr(ssid)}")
            self.wlan_obj.connect(ssid, password)

            wait = wait_per_try
            while wait > 0:
                status = self.wlan_obj.status()
                if status < 0 or status >= 3:
                    break
                wait -= 1
                print("waiting for connection...")
                time.sleep(1)

            status = self.wlan_obj.status()
            if status == 3:
                print("Connected!")
                ip = self.wlan_obj.ifconfig()[0]
                print(f"IP address: {ip}")
                return True
            elif status == -1:
                print("Connection failed: generic error")
            elif status == -2:
                print("Connection failed: AP not found")
            elif status == -3:
                print("Connection failed: connection failed")
            elif status == -4:
                print("Connection failed: wrong password")
            else:
                print(f"Connection failed: unknown status {status}")

            print("Retrying...\n")
            time.sleep(2)  # short delay before next attempt

        # All retries failed
        raise RuntimeError("WiFi connection failed after multiple attempts.")

    def disconnectWiFi(self):
        if self.wlan_obj.isconnected():
            self.wlan_obj.disconnect()
        self.wlan_obj.active(False)

    def scanWiFi(self):
        if not self.wlan_obj.active():
            self.wlan_obj.active(True)
        if self.wlan_obj.isconnected():
            self.wlan_obj.disconnect()
            time.sleep(1)
        try:
            results = self.wlan_obj.scan()
            formatted = []
            for ssid_bytes, bssid, channel, rssi, authmode, hidden in results:
                formatted.append({
                    "ssid": ssid_bytes.decode(),
                    "rssi": rssi,
                    "channel": channel,
                    "authmode": authmode,
                    "hidden": hidden
                })
            return formatted
        except OSError as e:
            print("Scan failed:", e)
            return []

    def checkWiFi(self):
        return self.wlan_obj.isconnected()

######## Example usage
# wlan = WLAN()

# print("Scanning WiFi networks...")
# networks = wlan.scanWiFi()
# for net in networks:
#     print(f"SSID: {net['ssid']}  RSSI: {net['rssi']} dBm  Channel: {net['channel']}")

# wlan.connectWiFi()

# print("WiFi Connected:", wlan.checkWiFi())
