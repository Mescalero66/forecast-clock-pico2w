### GPS Weather Clock Project
(Australia Only)

# Pico 2W Pinout
![Raspberry Pi Pico 2W](https://www.raspberrypi.com/documentation/microcontrollers/images/pico2w-pinout.svg)

## Pins
| Component | Interface | I/O | Pin |
| --- | --- | --- | --- |
| **GPS** | `UART1` | UART0 RX | GP1 |
| **Multiplexer** | `I2C` | I2C1 SDA<br>I2C1 SCL | GP14<br>GP15 |
| **8 Digit LED** | `I2C` | I2C0 SDA<br>I2C0 SCL | GP4<br>GP5 |
| **4 Digit LED (A)** | `GPIO` | Data<br>Clock | GP18<br>GP19 |
| **4 Digit LED (B)** | `GPIO` | Data<br>Clock | GP20<br>GP21 |
| **OLED (A)** | `I2C` | Mux SDA<br>Mux SCL | SDA0<br>SCL0 |
| **OLED (B)** | `I2C` | Mux SDA<br>Mux SCL | SDA1<br>SCL1 |
| **OLED (C)** | `I2C` | Mux SDA<br>Mux SCL | SDA2<br>SCL2 |
| **OLED (D)** | `I2C` | Mux SDA<br>Mux SCL | SDA3<br>SCL3 |


 - https://github.com/trickypr/bom-weather-docs/tree/main
 - https://github.com/peterhinch/micropython-async/blob/master/v3/docs/TUTORIAL.md

 - https://api.weather.bom.gov.au/v1/locations/r1r0mgn/

 - https://docs.micropython.org/en/latest/library/json.html
 

