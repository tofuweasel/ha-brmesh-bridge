#pragma once

#include <array>
#include <vector>
#include "esphome/core/component.h"
#include "esphome/components/light/light_output.h"
#include "fastcon_controller.h"

namespace esphome
{
    namespace fastcon
    {
        enum class LightState
        {
            OFF,
            WARM_WHITE,
            RGB
        };

        class FastconLight : public Component, public light::LightOutput
        {
        public:
            FastconLight(uint8_t light_id) : light_id_(light_id) {}

            void setup() override;
            void loop() override;  // Add loop for debouncing
            light::LightTraits get_traits() override;
            void write_state(light::LightState *state) override;
            void set_controller(FastconController *controller);

        protected:
            FastconController *controller_{nullptr};
            uint8_t light_id_;
            
            // **OPTIMIZATION: State tracking and debouncing**
            std::vector<uint8_t> last_sent_data_;       // Track last command sent
            std::vector<uint8_t> pending_data_;         // Pending command to send
            uint32_t last_state_change_{0};             // Time of last write_state() call
            uint32_t last_command_sent_{0};             // Time of last actual BLE command
            bool has_pending_command_{false};           // Flag for pending command
            
            static const uint32_t DEBOUNCE_MS = 100;    // Wait 100ms before sending
            static const uint32_t MIN_INTERVAL_MS = 300; // Minimum 300ms between commands (matches throttle)
        };
    } // namespace fastcon
} // namespace esphome
