# Google Assistant Auto-Expose for Home Assistant
[![HACS](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://hacs.xyz/)
[![HACS Store](https://img.shields.io/badge/HACS-Default-orange.svg)](https://hacs.xyz/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Bridge the gap between YAML configuration and UI controls.**

Tired of manually adding entity IDs to the `google_assistant.entity_config` key in your `configuration.yaml`, while cloud subscribers get to configure them easily via the UI?

This custom component solves that problem. It automatically exports the entities you configure in Home Assistant’s UI (under **Settings > Voice assistants**) to a local file, including their aliases and **Room/Area** assignments. This allows you to use the robust local Google Assistant integration (YAML) combined with the ease of use of the UI.

---

## ✨ Features

- **Zero-Config Automation**  
  No external automations required. The component automatically detects changes in your settings, generates the file, and notifies you when a restart is needed.

- **UI-Driven Configuration**  
  Configure your devices in the HA UI; this component generates the necessary YAML configuration for you.

- **Smart Room Sync**  
  Automatically maps Home Assistant **Areas** to Google Home **Rooms**. If an entity doesn’t have an area assigned, it intelligently checks the parent device’s area.

- **Strict Filtering**  
  Designed to work perfectly with `expose_by_default: false`. It explicitly adds `expose: true` to the generated file for items you toggled on, ensuring Google actually sees them.

---

## 📋 Prerequisites

This component assumes you have already set up a working local Google Assistant integration via YAML.

For setup instructions and current requirements, see the official Home Assistant documentation:  
https://www.home-assistant.io/integrations/google_assistant

**Note on UI Availability:**  
To use the **Expose** controls in the UI (`Settings > Voice assistants`), the Home Assistant Cloud component is technically involved in the background to render the menu. You generally need to be logged in under **Settings > Home Assistant Cloud**, but **you do not need an active subscription**.

---

## 📥 Installation

### Option 1: HACS (Recommended)

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Click **Explore & Download Repositories** (the big **+** button).
4. Search for **Google Assistant Auto-Expose**.
5. Click on the integration in the list and then click **Download**.
6. Restart Home Assistant.

---

### Option 2: Manual

1. Download this repository.
2. Copy the `custom_components/ga_autoexpose` folder into your Home Assistant  
   `config/custom_components/` directory.
3. Restart Home Assistant.

---

## ⚙️ Configuration

### 1. Enable the component

Add the following line to your `configuration.yaml`:

```yaml
ga_autoexpose:
```

---

### 2. Configure Google Assistant

Update your existing `google_assistant` configuration to use the generated file.

**Recommended configuration:**

```yaml
google_assistant:
  project_id: YOUR_PROJECT_ID
  service_account: !include service_account.json
  report_state: true

  # Set this to false to have full control via the UI (Strict mode)
  expose_by_default: false

  # These domains act as a filter if you enable expose_by_default.
  # If expose_by_default is false, these are ignored.
  exposed_domains:
    - switch
    - light
    - climate

  # This is where the magic happens
  entity_config: !include exposed.yaml
```

**Note:**  
The `exposed.yaml` file will be created automatically in your config folder after the first run.

---

## 🚀 Usage

### Automatic Mode (Default)

Simply use Home Assistant as you normally would. The integration runs in the background.

1. Go to **Settings > Voice assistants > Google Assistant**.
2. Toggle **Expose** on or off for any device.
3. Wait ~30 seconds (the integration debounces multiple edits).
4. You will receive a **Notification** in Home Assistant with a direct link to restart your system.

---

### Manual Trigger

If you want to force an update immediately without changing settings, run the service:

- **Service:** `ga_autoexpose.export_entities`

---

## 🔄 Workflow

1. **Configure**  
   Toggle **Expose** on your entities in the UI.
2. **Wait**  
   Wait for the *Google Assistant Config Changed* notification.
3. **Restart**  
   Click the link in the notification to restart Home Assistant.
4. **Sync**  
   Say: *“Hey Google, sync my devices”*.

---

## 🤝 Contributing

Feel free to open issues or submit pull requests if you have ideas for improvements.

---

## 📄 License

MIT License
