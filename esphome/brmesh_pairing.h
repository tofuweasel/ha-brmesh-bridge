/*
 * BRMesh Native Pairing
 * Discover and pair lights directly from ESP32 without phone app
 * 
 * Protocol:
 * - Lights advertise manufacturer data 0xf0ff when unpaired
 * - Data format: [DeviceID:6][LightID:2][MeshKey:4]
 * - Mesh key is typically "0236" (ASCII: 30323336)
 * - Encryption key: "5e367bc4"
 */

#include "esphome.h"
#include <vector>
#include <string>
#include <Preferences.h>

struct PairedLight {
  std::string mac_address;
  std::string device_id;
  uint16_t light_id;
  std::string mesh_key;
  unsigned long paired_time;
  int rssi;
};

class BRMeshPairing : public Component {
 private:
  bool pairing_enabled = false;
  std::vector<PairedLight> paired_lights;
  Preferences prefs;
  
  const char* PREF_NAMESPACE = "brmesh";
  const char* PREF_COUNT_KEY = "light_count";
  
 public:
  void setup() override {
    // Load paired lights from flash
    prefs.begin(PREF_NAMESPACE, false);
    load_paired_lights();
    
    ESP_LOGI("pairing", "BRMesh Pairing initialized");
    ESP_LOGI("pairing", "Loaded %d paired lights from flash", paired_lights.size());
  }
  
  void start_pairing() {
    pairing_enabled = true;
    ESP_LOGI("pairing", "=== PAIRING MODE ACTIVE ===");
    ESP_LOGI("pairing", "Instructions:");
    ESP_LOGI("pairing", "1. Factory reset your light (turn on/off 5+ times)");
    ESP_LOGI("pairing", "2. Light will start blinking rapidly");
    ESP_LOGI("pairing", "3. ESP32 will auto-detect and pair");
    ESP_LOGI("pairing", "4. Light will be added to your network");
  }
  
  void stop_pairing() {
    pairing_enabled = false;
    ESP_LOGI("pairing", "Pairing mode disabled");
  }
  
  void add_light(const char* mac, const char* device_id, uint16_t light_id, const char* mesh_key) {
    // Check if already paired
    for (auto& light : paired_lights) {
      if (light.mac_address == mac) {
        ESP_LOGW("pairing", "Light %s already paired (ID: %d)", mac, light.light_id);
        return;
      }
    }
    
    // Add new light
    PairedLight light;
    light.mac_address = mac;
    light.device_id = device_id;
    light.light_id = light_id;
    light.mesh_key = mesh_key;
    light.paired_time = millis();
    light.rssi = -999;
    
    paired_lights.push_back(light);
    
    ESP_LOGI("pairing", "✓ Successfully paired light!");
    ESP_LOGI("pairing", "  MAC: %s", mac);
    ESP_LOGI("pairing", "  Device ID: %s", device_id);
    ESP_LOGI("pairing", "  Light ID: %d", light_id);
    ESP_LOGI("pairing", "  Mesh Key: %s", mesh_key);
    
    // Save to flash
    save_paired_lights();
    
    // Generate next available light ID for convenience
    ESP_LOGI("pairing", "");
    ESP_LOGI("pairing", "Next available light ID: %d", get_next_light_id());
    ESP_LOGI("pairing", "Total paired lights: %d", paired_lights.size());
  }
  
  void clear_all_lights() {
    paired_lights.clear();
    prefs.putUInt(PREF_COUNT_KEY, 0);
    ESP_LOGI("pairing", "All paired lights cleared");
  }
  
  uint16_t get_next_light_id() {
    uint16_t max_id = 0;
    for (auto& light : paired_lights) {
      if (light.light_id > max_id) {
        max_id = light.light_id;
      }
    }
    return max_id + 1;
  }
  
  void save_paired_lights() {
    prefs.putUInt(PREF_COUNT_KEY, paired_lights.size());
    
    for (size_t i = 0; i < paired_lights.size(); i++) {
      char key[32];
      
      sprintf(key, "mac_%d", i);
      prefs.putString(key, paired_lights[i].mac_address.c_str());
      
      sprintf(key, "devid_%d", i);
      prefs.putString(key, paired_lights[i].device_id.c_str());
      
      sprintf(key, "lightid_%d", i);
      prefs.putUShort(key, paired_lights[i].light_id);
      
      sprintf(key, "meshkey_%d", i);
      prefs.putString(key, paired_lights[i].mesh_key.c_str());
    }
    
    ESP_LOGD("pairing", "Saved %d lights to flash", paired_lights.size());
  }
  
  void load_paired_lights() {
    uint32_t count = prefs.getUInt(PREF_COUNT_KEY, 0);
    
    for (uint32_t i = 0; i < count; i++) {
      PairedLight light;
      char key[32];
      
      sprintf(key, "mac_%d", i);
      light.mac_address = prefs.getString(key, "").c_str();
      
      sprintf(key, "devid_%d", i);
      light.device_id = prefs.getString(key, "").c_str();
      
      sprintf(key, "lightid_%d", i);
      light.light_id = prefs.getUShort(key, 0);
      
      sprintf(key, "meshkey_%d", i);
      light.mesh_key = prefs.getString(key, "").c_str();
      
      light.paired_time = 0;
      light.rssi = -999;
      
      paired_lights.push_back(light);
    }
  }
  
  void export_config() {
    ESP_LOGI("pairing", "");
    ESP_LOGI("pairing", "=== ADDON CONFIGURATION ===");
    ESP_LOGI("pairing", "Copy this to your addon config.yaml:");
    ESP_LOGI("pairing", "");
    ESP_LOGI("pairing", "lights:");
    
    for (auto& light : paired_lights) {
      ESP_LOGI("pairing", "  - mac_address: \"%s\"", light.mac_address.c_str());
      ESP_LOGI("pairing", "    device_id: \"%s\"", light.device_id.c_str());
      ESP_LOGI("pairing", "    light_id: %d", light.light_id);
      ESP_LOGI("pairing", "    mesh_key: \"%s\"", light.mesh_key.c_str());
      ESP_LOGI("pairing", "    name: \"Light %d\"  # Customize this", light.light_id);
      ESP_LOGI("pairing", "");
    }
    
    ESP_LOGI("pairing", "mesh_key: \"30323336\"  # \"0236\" in hex");
    ESP_LOGI("pairing", "encryption_key: \"5e367bc4\"");
    ESP_LOGI("pairing", "");
  }
  
  std::string get_status() {
    if (pairing_enabled) {
      return "SCANNING - Factory reset a light to pair";
    } else {
      return "Ready (" + std::to_string(paired_lights.size()) + " lights)";
    }
  }
  
  std::string get_paired_lights() {
    if (paired_lights.empty()) {
      return "No lights paired yet";
    }
    
    std::string result = "";
    for (size_t i = 0; i < paired_lights.size(); i++) {
      result += std::to_string(i + 1) + ". ";
      result += "ID:" + std::to_string(paired_lights[i].light_id) + " ";
      result += "(" + paired_lights[i].mac_address + ")";
      if (i < paired_lights.size() - 1) {
        result += ", ";
      }
    }
    return result;
  }
  
  int get_light_count() {
    return paired_lights.size();
  }
};
