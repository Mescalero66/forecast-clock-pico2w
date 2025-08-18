import network
import time
import wlan_key

ssid = wlan_key.ssid
password = wlan_key.password

class WLAN:
    def __init__(self):
        self.wlan_obj = network.WLAN(network.WLAN.IF_STA)
    
    def connectWiFi(self):
        self.wlan_obj.active(True)
        self.wlan_obj.connect(ssid, password)
        # input patience level
        max_wait = 10
        # Wait for connection or fail
        while max_wait > 0:
            if self.wlan_obj.status() < 0 or self.wlan_obj.status() >= 3:
                break
            max_wait -= 1
            print('waiting for connection...')
            time.sleep(1)
        # Handle connection error
        if self.wlan_obj.status() != 3:
            raise RuntimeError('network connection failed')
        else:
            print('connected')
            status = self.wlan_obj.ifconfig()
            print( 'ip = ' + status[0] )

    def disconnectWiFi(self):
        self.wlan_obj.disconnect()
        self.wlan_obj.active(False)

    def scanWiFi(self):
        results = self.wlan_obj.scan()
        return results
    
    def checkWiFi(self):
        isconnected = self.wlan_obj.isconnected()
        return isconnected

wlan = WLAN()

print("WiFi Networks:")
print(wlan.scanWiFi())

wlan.connectWiFi()

print("WiFi Connected:", wlan.checkWiFi())

