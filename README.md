# ❄️ Wi-Fi Cold Room Temperature & Humidity Monitor

A real-time monitoring system for cold rooms, pharmacy fridges, or vaccine storage.  
It uses an **ESP32** with an **AHT10** sensor to measure temperature and humidity, sends data to a **Flask** server on a laptop/Raspberry Pi, and displays live charts on a web dashboard. Alerts trigger when temperature exceeds 8°C.

## Features

- Reads temperature & humidity every 10 seconds
- Sends data via HTTP POST to a local Flask server
- Web dashboard with live charts (Chart.js)
- Current value cards with last update time
- Temperature alert banner when > 8°C
- Alert history with start/end times and max temp
- Optional OLED display for local readings

## Hardware Components

- ESP32 DevKitC
- AHT10 temperature/humidity sensor (I2C)
- 0.96" SSD1306 OLED display (optional)
- Breadboard, jumper wires
- USB power supply

## Wiring Diagram

| ESP32 Pin | Connect to                     |
|-----------|--------------------------------|
| 3.3V      | AHT10 VCC, OLED VCC            |
| GND       | AHT10 GND, OLED GND            |
| GPIO21    | AHT10 SDA, OLED SDA            |
| GPIO22    | AHT10 SCL, OLED SCL            |

## Software Requirements

- **ESP32 firmware**: Arduino/PlatformIO, libraries: Adafruit AHTX0, SSD1306, GFX, ArduinoJson
- **Server**: Python 3, Flask

## Setup Instructions

### 1. Flask Server (on laptop/PC)

```bash
pip install flask
python app.py
