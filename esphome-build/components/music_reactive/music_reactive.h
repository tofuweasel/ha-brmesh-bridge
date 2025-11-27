/*
 * FFT Audio Analyzer with UDP Sound Sync
 * Master: Captures audio, performs FFT, broadcasts over UDP
 * Slave: Receives FFT data over UDP, no microphone needed
 * 
 * Compatible with WLED sound sync protocol (port 11988)
 */

#include "esphome.h"
#include "arduinoFFT.h"
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include "esphome/components/fastcon/fastcon_controller.h"

#define SAMPLES 256
#define SAMPLING_FREQUENCY 22050
#define UDP_PORT 11988  // WLED sound sync port
#define UDP_PACKET_SIZE 24  // FFT data packet size

// UDP packet structure (compatible with WLED)
struct AudioSyncPacket {
  uint8_t header[2];        // 'A', 'S' (Audio Sync)
  uint8_t volume;           // Overall volume 0-255
  uint8_t bass;             // Bass level 0-255
  uint8_t mid;              // Mid level 0-255
  uint8_t treble;           // Treble level 0-255
  uint8_t fft_bins[18];     // Simplified FFT spectrum (18 bins)
};

class MusicReactiveEffectUDP : public Component, public Sensor {
 private:
  bool is_master;           // True = mic + broadcast, False = receive only
  bool running = false;
  bool udp_enabled = true;
  
  WiFiUDP udp;
  IPAddress broadcast_ip;
  String master_ip = "";
  
  // FFT data (master only)
  arduinoFFT FFT = arduinoFFT();
  double vReal[SAMPLES];
  double vImag[SAMPLES];
  const i2s_port_t I2S_PORT = I2S_NUM_0;
  
  // Frequency levels (both master and slave)
  float bass_level = 0.0;
  float mid_level = 0.0;
  float treble_level = 0.0;
  float volume = 0.0;
  
  // Settings
  float sensitivity = 1.0;
  float update_rate = 10.0;
  uint8_t target_addr[2] = {0x2a, 0xa8};
  String color_mode = "RGB Frequency";
  
  // Statistics
  unsigned long packet_count = 0;
  unsigned long last_packet_time = 0;
  unsigned long last_update = 0;
  
  // Sensors
  Sensor *bass_sensor = new Sensor();
  Sensor *mid_sensor = new Sensor();
  Sensor *treble_sensor = new Sensor();
  
  esphome::fastcon::FastconController *controller = nullptr;

 public:
  MusicReactiveEffectUDP(bool master_mode) : is_master(master_mode) {}
  
  void set_controller(esphome::fastcon::FastconController *ctrl) {
    controller = ctrl;
  }

  void setup() override {
    if (is_master) {
      // Initialize I2S microphone
      i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLING_FREQUENCY,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = 1024,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
      };
      
      i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
      ESP_LOGI("music-udp", "Master mode: Microphone initialized");
    } else {
      ESP_LOGI("music-udp", "Slave mode: Waiting for UDP packets");
    }
    
    // Start UDP
    udp.begin(UDP_PORT);
    
    // Calculate broadcast address
    IPAddress local_ip = WiFi.localIP();
    IPAddress subnet = WiFi.subnetMask();
    broadcast_ip = IPAddress(
      local_ip[0] | (~subnet[0]),
      local_ip[1] | (~subnet[1]),
      local_ip[2] | (~subnet[2]),
      local_ip[3] | (~subnet[3])
    );
    
    ESP_LOGI("music-udp", "UDP initialized on port %d, broadcast: %s", 
             UDP_PORT, broadcast_ip.toString().c_str());
  }
  
  void loop() override {
    if (!running) return;
    
    if (is_master) {
      // Master: Sample audio, analyze, broadcast, control lights
      master_loop();
    } else {
      // Slave: Receive UDP packets, control lights
      slave_loop();
    }
  }
  
  void master_loop() {
    unsigned long now = millis();
    unsigned long interval = 1000.0 / update_rate;
    
    if (now - last_update < interval) return;
    last_update = now;
    
    // Sample and analyze audio
    sample_audio();
    analyze_frequencies();
    
    // Broadcast FFT data over UDP
    if (udp_enabled) {
      broadcast_audio_data();
    }
    
    // Control local lights
    send_color_command();
    
    // Update sensors
    update_sensors();
  }
  
  void slave_loop() {
    // Check for UDP packets
    int packet_size = udp.parsePacket();
    if (packet_size >= UDP_PACKET_SIZE) {
      receive_audio_data();
      
      // Control lights based on received data
      unsigned long now = millis();
      if (now - last_update >= 50) {  // Max 20fps
        last_update = now;
        send_color_command();
        update_sensors();
      }
    }
    
    // Timeout detection (no data received)
    if (millis() - last_packet_time > 5000 && packet_count > 0) {
      ESP_LOGW("music-udp", "No UDP packets received for 5 seconds");
    }
  }
  
  void sample_audio() {
    size_t bytes_read = 0;
    int32_t samples_buffer[SAMPLES];
    
    i2s_read(I2S_PORT, &samples_buffer, sizeof(samples_buffer), &bytes_read, portMAX_DELAY);
    
    for (int i = 0; i < SAMPLES; i++) {
      vReal[i] = (double)samples_buffer[i] / 2147483648.0;
      vImag[i] = 0.0;
    }
  }
  
  void analyze_frequencies() {
    FFT.Windowing(vReal, SAMPLES, FFT_WIN_TYP_HAMMING, FFT_FORWARD);
    FFT.Compute(vReal, vImag, SAMPLES, FFT_FORWARD);
    FFT.ComplexToMagnitude(vReal, vImag, SAMPLES);
    
    // Bass: 0-500Hz (bins 0-6)
    bass_level = 0.0;
    for (int i = 1; i <= 6; i++) {
      bass_level += vReal[i];
    }
    bass_level /= 6.0;
    
    // Mid: 500-2000Hz (bins 6-23)
    mid_level = 0.0;
    for (int i = 6; i <= 23; i++) {
      mid_level += vReal[i];
    }
    mid_level /= 18.0;
    
    // Treble: 2000-8000Hz (bins 23-93)
    treble_level = 0.0;
    for (int i = 23; i <= 93; i++) {
      treble_level += vReal[i];
    }
    treble_level /= 71.0;
    
    // Overall volume
    volume = (bass_level + mid_level + treble_level) / 3.0;
    
    // Apply sensitivity
    bass_level *= sensitivity;
    mid_level *= sensitivity;
    treble_level *= sensitivity;
    volume *= sensitivity;
    
    // Clamp
    bass_level = constrain(bass_level, 0.0, 1.0);
    mid_level = constrain(mid_level, 0.0, 1.0);
    treble_level = constrain(treble_level, 0.0, 1.0);
    volume = constrain(volume, 0.0, 1.0);
  }
  
  void broadcast_audio_data() {
    AudioSyncPacket packet;
    packet.header[0] = 'A';
    packet.header[1] = 'S';
    packet.volume = (uint8_t)(volume * 255.0);
    packet.bass = (uint8_t)(bass_level * 255.0);
    packet.mid = (uint8_t)(mid_level * 255.0);
    packet.treble = (uint8_t)(treble_level * 255.0);
    
    // Simplified FFT bins for spectrum display
    for (int i = 0; i < 18; i++) {
      int fft_idx = (i * SAMPLES / 2) / 18;
      packet.fft_bins[i] = (uint8_t)(constrain(vReal[fft_idx] * sensitivity * 255.0, 0.0, 255.0));
    }
    
    // Broadcast to all devices on network
    udp.beginPacket(broadcast_ip, UDP_PORT);
    udp.write((uint8_t*)&packet, sizeof(AudioSyncPacket));
    udp.endPacket();
  }
  
  void receive_audio_data() {
    AudioSyncPacket packet;
    udp.read((uint8_t*)&packet, sizeof(AudioSyncPacket));
    
    // Verify header
    if (packet.header[0] != 'A' || packet.header[1] != 'S') {
      ESP_LOGW("music-udp", "Invalid packet header");
      return;
    }
    
    // Extract frequency levels
    volume = packet.volume / 255.0;
    bass_level = packet.bass / 255.0;
    mid_level = packet.mid / 255.0;
    treble_level = packet.treble / 255.0;
    
    // Update statistics
    packet_count++;
    last_packet_time = millis();
    
    ESP_LOGV("music-udp", "Received: Vol=%d Bass=%d Mid=%d Treble=%d", 
             packet.volume, packet.bass, packet.mid, packet.treble);
  }
  
  void send_color_command() {
    uint8_t r = 0, g = 0, b = 0;
    
    if (color_mode == "RGB Frequency") {
      r = (uint8_t)(bass_level * 255.0);
      g = (uint8_t)(mid_level * 255.0);
      b = (uint8_t)(treble_level * 255.0);
    } else if (color_mode == "Amplitude") {
      r = g = b = (uint8_t)(volume * 255.0);
    } else if (color_mode == "Rainbow Cycle") {
      float max_level = max(bass_level, max(mid_level, treble_level));
      float hue = 0.0;
      if (max_level == bass_level) hue = 0.0;
      else if (max_level == mid_level) hue = 0.33;
      else hue = 0.66;
      hsv_to_rgb(hue, 1.0, max_level, r, g, b);
    } else if (color_mode == "Bass Pulse") {
      if (bass_level > 0.6) {
        r = 255; g = 0; b = 0;
      } else {
        r = (uint8_t)(bass_level * 100.0);
        g = (uint8_t)(mid_level * 50.0);
        b = (uint8_t)(treble_level * 150.0);
      }
    }
    
    // Build BRMesh command
    uint8_t payload[12] = {
      0x93, target_addr[0], target_addr[1], 0x04, 0xff,
      r, g, b, 0x00, 0x00, 0x00, 0x00
    };
    
    send_mesh_command(payload, 12);
  }
  
  void hsv_to_rgb(float h, float s, float v, uint8_t &r, uint8_t &g, uint8_t &b) {
    float c = v * s;
    float x = c * (1.0 - fabs(fmod(h * 6.0, 2.0) - 1.0));
    float m = v - c;
    
    float r_prime, g_prime, b_prime;
    if (h < 0.166) {
      r_prime = c; g_prime = x; b_prime = 0;
    } else if (h < 0.333) {
      r_prime = x; g_prime = c; b_prime = 0;
    } else if (h < 0.5) {
      r_prime = 0; g_prime = c; b_prime = x;
    } else if (h < 0.666) {
      r_prime = 0; g_prime = x; b_prime = c;
    } else if (h < 0.833) {
      r_prime = x; g_prime = 0; b_prime = c;
    } else {
      r_prime = c; g_prime = 0; b_prime = x;
    }
    
    r = (uint8_t)((r_prime + m) * 255.0);
    g = (uint8_t)((g_prime + m) * 255.0);
    b = (uint8_t)((b_prime + m) * 255.0);
  }
  
  void send_mesh_command(uint8_t *payload, size_t len) {
    if (controller != nullptr) {
      std::vector<uint8_t> data(payload, payload + len);
      // Send as broadcast (0xFFFF) since the payload contains the target address
      controller->send_raw_command(0xFFFF, data);
      ESP_LOGV("music-udp", "Sent color command via mesh");
    } else {
      ESP_LOGW("music-udp", "Controller not set, cannot send mesh command");
    }
  }
  
  void update_sensors() {
    bass_sensor->publish_state(bass_level * 100.0);
    mid_sensor->publish_state(mid_level * 100.0);
    treble_sensor->publish_state(treble_level * 100.0);
  }
  
  // Control methods
  void start() {
    running = true;
    ESP_LOGI("music-udp", "%s mode started", is_master ? "Master" : "Slave");
  }
  
  void stop() {
    running = false;
    ESP_LOGI("music-udp", "%s mode stopped", is_master ? "Master" : "Slave");
  }
  
  void enable_udp_broadcast(bool enable) {
    udp_enabled = enable;
    ESP_LOGI("music-udp", "UDP broadcast %s", enable ? "enabled" : "disabled");
  }
  
  void set_sensitivity(float sens) {
    sensitivity = sens;
  }
  
  void set_color_mode(const char *mode) {
    color_mode = String(mode);
  }
  
  void set_master_ip(const char *ip) {
    master_ip = String(ip);
    ESP_LOGI("music-udp", "Master IP set to %s", ip);
  }
  
  String get_status() {
    if (is_master) {
      return "Broadcasting";
    } else {
      if (millis() - last_packet_time < 2000) {
        return "Receiving (" + String((int)(1000.0 / (millis() - last_packet_time))) + " fps)";
      } else {
        return "No signal";
      }
    }
  }
  
  unsigned long get_packet_count() {
    return packet_count;
  }
  
  Sensor *get_bass_sensor() { return bass_sensor; }
  Sensor *get_mid_sensor() { return mid_sensor; }
  Sensor *get_treble_sensor() { return treble_sensor; }
};
