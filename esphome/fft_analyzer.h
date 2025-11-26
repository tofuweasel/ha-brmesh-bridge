/*
 * FFT Audio Analyzer for BRMesh Music Reactive Lighting
 * ESP32 with I2S Microphone
 * 
 * Hardware: INMP441 or similar I2S MEMS microphone
 * FFT Library: arduinoFFT
 */

#include "esphome.h"
#include "arduinoFFT.h"
#include <driver/i2s.h>

#define SAMPLES 256              // Must be a power of 2
#define SAMPLING_FREQUENCY 22050 // Hz, should match microphone config

class MusicReactiveEffect : public Component, public Sensor {
 private:
  arduinoFFT FFT = arduinoFFT();
  
  // FFT data arrays
  double vReal[SAMPLES];
  double vImag[SAMPLES];
  
  // Frequency band accumulators
  float bass_level = 0.0;    // 0-500Hz
  float mid_level = 0.0;     // 500-2000Hz
  float treble_level = 0.0;  // 2000-8000Hz
  
  // Settings
  float sensitivity = 1.0;
  float update_rate = 10.0;  // Hz
  bool running = false;
  String color_mode = "RGB Frequency";
  
  // BRMesh target address (group)
  uint8_t target_addr[2] = {0x2a, 0xa8};
  
  // I2S configuration
  const i2s_port_t I2S_PORT = I2S_NUM_0;
  
  // Sensor components for Home Assistant
  Sensor *bass_sensor = new Sensor();
  Sensor *mid_sensor = new Sensor();
  Sensor *treble_sensor = new Sensor();
  
  // Timing
  unsigned long last_update = 0;
  
 public:
  void setup() override {
    // Initialize I2S for microphone input
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
    
    ESP_LOGD("music", "Music reactive effect initialized");
  }
  
  void loop() override {
    if (!running) return;
    
    unsigned long now = millis();
    unsigned long interval = 1000.0 / update_rate;
    
    if (now - last_update < interval) return;
    last_update = now;
    
    // Sample audio and perform FFT
    sample_audio();
    analyze_frequencies();
    
    // Send color command based on mode
    send_color_command();
    
    // Update sensor values for Home Assistant
    bass_sensor->publish_state(bass_level * 100.0);
    mid_sensor->publish_state(mid_level * 100.0);
    treble_sensor->publish_state(treble_level * 100.0);
  }
  
  void sample_audio() {
    // Read audio samples from I2S microphone
    size_t bytes_read = 0;
    int32_t samples_buffer[SAMPLES];
    
    i2s_read(I2S_PORT, &samples_buffer, sizeof(samples_buffer), &bytes_read, portMAX_DELAY);
    
    // Convert to double and apply window
    for (int i = 0; i < SAMPLES; i++) {
      vReal[i] = (double)samples_buffer[i] / 2147483648.0;  // Normalize int32 to -1.0 to 1.0
      vImag[i] = 0.0;
    }
  }
  
  void analyze_frequencies() {
    // Perform FFT
    FFT.Windowing(vReal, SAMPLES, FFT_WIN_TYP_HAMMING, FFT_FORWARD);
    FFT.Compute(vReal, vImag, SAMPLES, FFT_FORWARD);
    FFT.ComplexToMagnitude(vReal, vImag, SAMPLES);
    
    // Calculate frequency bands
    // Frequency resolution = SAMPLING_FREQUENCY / SAMPLES
    // For 22050Hz / 256 = 86Hz per bin
    
    float freq_per_bin = (float)SAMPLING_FREQUENCY / (float)SAMPLES;
    
    // Bass: 0-500Hz (bins 0-6)
    bass_level = 0.0;
    for (int i = 1; i <= 6; i++) {  // Skip DC bin 0
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
    
    // Apply sensitivity scaling
    bass_level *= sensitivity;
    mid_level *= sensitivity;
    treble_level *= sensitivity;
    
    // Clamp to 0.0-1.0 range
    bass_level = constrain(bass_level, 0.0, 1.0);
    mid_level = constrain(mid_level, 0.0, 1.0);
    treble_level = constrain(treble_level, 0.0, 1.0);
  }
  
  void send_color_command() {
    uint8_t r = 0, g = 0, b = 0;
    
    if (color_mode == "RGB Frequency") {
      // Map frequency bands to RGB channels
      r = (uint8_t)(bass_level * 255.0);
      g = (uint8_t)(mid_level * 255.0);
      b = (uint8_t)(treble_level * 255.0);
      
    } else if (color_mode == "Amplitude") {
      // Total amplitude to brightness (white)
      float total = (bass_level + mid_level + treble_level) / 3.0;
      r = g = b = (uint8_t)(total * 255.0);
      
    } else if (color_mode == "Rainbow Cycle") {
      // Dominant frequency determines hue
      float max_level = max(bass_level, max(mid_level, treble_level));
      float hue = 0.0;
      
      if (max_level == bass_level) {
        hue = 0.0;  // Red
      } else if (max_level == mid_level) {
        hue = 0.33; // Green
      } else {
        hue = 0.66; // Blue
      }
      
      // Convert HSV to RGB
      float s = 1.0;
      float v = max_level;
      hsv_to_rgb(hue, s, v, r, g, b);
      
    } else if (color_mode == "Bass Pulse") {
      // Flash red on bass hits
      if (bass_level > 0.6) {
        r = 255;
        g = 0;
        b = 0;
      } else {
        r = (uint8_t)(bass_level * 100.0);
        g = (uint8_t)(mid_level * 50.0);
        b = (uint8_t)(treble_level * 150.0);
      }
    }
    
    // Build and send BRMesh 0x93 color command
    uint8_t payload[12] = {
      0x93,             // Opcode: color command
      target_addr[0],   // Target address byte 1
      target_addr[1],   // Target address byte 2
      0x04,             // Constant
      0xff,             // Mode: direct color (no effect mode)
      r, g, b,          // RGB values
      0x00, 0x00, 0x00, 0x00  // Padding
    };
    
    // Send via BLE mesh (implement your mesh sending function here)
    send_mesh_command(payload, 12);
  }
  
  void hsv_to_rgb(float h, float s, float v, uint8_t &r, uint8_t &g, uint8_t &b) {
    // HSV to RGB conversion
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
    // TODO: Implement BLE mesh sending
    // This should encrypt and send the payload via BLE
    ESP_LOGD("music", "Sending color: R=%d G=%d B=%d", payload[5], payload[6], payload[7]);
  }
  
  // Public control methods
  void start() {
    running = true;
    ESP_LOGI("music", "Music mode started");
  }
  
  void stop() {
    running = false;
    ESP_LOGI("music", "Music mode stopped");
  }
  
  void set_sensitivity(float sens) {
    sensitivity = sens;
    ESP_LOGD("music", "Sensitivity set to %.2f", sensitivity);
  }
  
  void set_update_rate(float rate) {
    update_rate = rate;
    ESP_LOGD("music", "Update rate set to %.1f Hz", update_rate);
  }
  
  void set_color_mode(const char *mode) {
    color_mode = String(mode);
    ESP_LOGD("music", "Color mode set to %s", mode);
  }
  
  void set_target_address(uint8_t addr1, uint8_t addr2) {
    target_addr[0] = addr1;
    target_addr[1] = addr2;
    ESP_LOGD("music", "Target address set to 0x%02x 0x%02x", addr1, addr2);
  }
  
  // Sensor getters for Home Assistant
  Sensor *get_bass_sensor() { return bass_sensor; }
  Sensor *get_mid_sensor() { return mid_sensor; }
  Sensor *get_treble_sensor() { return treble_sensor; }
};
