# Boon Smart Home Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/makonaymada/ha-boon)](https://github.com/makonaymada/ha-boon/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A native Home Assistant custom component integration for **Boon Smart Home** (`boon.city` / Sputnik systems).

Enables seamless control of your building entrance intercoms, gate buzzers, live RTSP video feeds, emergency offline keypad codes, and apartment subscriptions directly within Home Assistant.

---

## ✨ Features

- 🚪 **1-Tap Door & Gate Buzzer (`button` entity)**: Unlock building entrance gates and intercom doors directly from Home Assistant dashboards. Supports dual-door intercoms (`open-second`).
- 🔒 **HomeKit & Voice Assistant Ready (`lock` entity)**: Exposes the gate as a standard lock platform with momentary buzzer strike action, allowing Apple Home, Google Assistant, or Alexa voice unlocking ("Hey Siri, unlock the building gate").
- 📹 **Live Intercom Video Feed (`camera` entity)**: Streams high-resolution RTSP video from your building intercom natively in Home Assistant.
- 🌐 **Multiple Camera Streams Support**: Manually register additional RTSP/HTTP camera URLs (from shared intercom links or secondary accounts) via the integration setup or Options Flow.
- 🔑 **Emergency Offline Unlock Codes (`sensor` entity)**: Displays the physical keypad offline access code directly in Home Assistant so you are never locked out during internet or cloud outages.
- 🔄 **Automatic Background Token Refresh**: Uses Boon's OAuth/JWT refresh protocol to transparently renew sessions without requiring repeated OTP logins.
- 📱 **Native Config Flow UI**: Set up directly via the Home Assistant UI by entering your phone number and SMS OTP code.

---

## ⚠️ Mobile App Session & Multi-Device Note

> **Important**: Boon's cloud architecture may invalidate existing mobile sessions when an account signs in with the same phone number on a new device.
>
> If you actively use the official Boon mobile app on your smartphone, **we recommend entering a secondary phone number** invited/registered to your apartment in the Boon app (e.g., a family member's number or a second SIM) when setting up this integration. Both sessions will stay active simultaneously without conflict.

---

## 📦 Installation

### Method 1: Via HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant.
2. In Home Assistant, open **HACS** > **Integrations** > Three dots menu (top right) > **Custom repositories**.
3. Enter Repository URL: `https://github.com/makonaymada/ha-boon`
4. Category: **Integration**
5. Click **Add**, locate **Boon Smart Home**, and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release from the [Releases](https://github.com/makonaymada/ha-boon/releases) page.
2. Copy the `custom_components/boon` directory into your Home Assistant `<config_dir>/custom_components/` directory:
   ```
   homeassistant/
   └── config/
       └── custom_components/
           └── boon/
               ├── __init__.py
               ├── api.py
               ├── button.py
               ├── camera.py
               ├── config_flow.py
               ├── const.py
               ├── coordinator.py
               ├── lock.py
               ├── manifest.json
               ├── sensor.py
               └── ...
   ```
3. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, navigate to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for **Boon Smart Home**.
3. Enter your phone number with country code (e.g., `+374XXXXXXXX`).
   - *(Optional)* Add any additional camera stream URLs, one per line (e.g., `Parking Gate = rtsp://...`).
4. Click **Submit**. You will receive an SMS containing a verification code.
5. Enter the SMS verification code and submit.
6. Your building intercom doors, cameras, sensors, and offline codes will be automatically discovered and added!

### Additional Cameras (Options Flow)
To add or modify custom camera stream URLs after setup:
1. Go to **Settings** > **Devices & Services** > **Boon Smart Home**.
2. Click **Configure**.
3. Enter or edit stream URLs in the text area (e.g., `Gate 2 = rtsp://...`) and submit.

---

## 🛡️ Offline Keypad Emergency Unlock

If cloud connectivity or building internet goes down, the integration exposes the physical keypad code:
- **Entity**: `sensor.<intercom_name>_offline_door_code`
- **Usage**: Type this code directly on the physical Sputnik/Boon intercom keypad at your building entrance to buzz open the door offline.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
