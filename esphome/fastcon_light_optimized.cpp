#include <algorithm>
#include "esphome/core/log.h"
#include "fastcon_light_optimized.h"
#include "fastcon_controller.h"
#include "utils.h"

namespace esphome
{
    namespace fastcon
    {
        static const char *const TAG = "fastcon.light";

        void FastconLight::setup()
        {
            if (this->controller_ == nullptr)
            {
                ESP_LOGE(TAG, "Controller not set for light %d!", this->light_id_);
                this->mark_failed();
                return;
            }
            ESP_LOGCONFIG(TAG, "Setting up Fastcon BLE light (ID: %d) with command deduplication...", this->light_id_);
        }

        void FastconLight::set_controller(FastconController *controller)
        {
            this->controller_ = controller;
        }

        light::LightTraits FastconLight::get_traits()
        {
            auto traits = light::LightTraits();
            traits.set_supported_color_modes({light::ColorMode::RGB, light::ColorMode::WHITE, light::ColorMode::BRIGHTNESS, light::ColorMode::COLD_WARM_WHITE});
            traits.set_min_mireds(153);
            traits.set_max_mireds(500);
            return traits;
        }

        void FastconLight::loop()
        {
            // **OPTIMIZATION: Debounced command sending**
            if (!has_pending_command_)
                return;

            uint32_t now = millis();
            
            // Check if debounce period has elapsed
            uint32_t time_since_change = now - last_state_change_;
            if (time_since_change < DEBOUNCE_MS)
                return;
            
            // Check if minimum interval between commands has elapsed
            uint32_t time_since_sent = now - last_command_sent_;
            if (time_since_sent < MIN_INTERVAL_MS)
                return;

            // **OPTIMIZATION: Command deduplication**
            // Skip if command is identical to last sent command
            if (pending_data_ == last_sent_data_)
            {
                ESP_LOGV(TAG, "Skipping duplicate command for light %d", light_id_);
                has_pending_command_ = false;
                return;
            }

            // Send the pending command
            ESP_LOGD(TAG, "Sending debounced command for light %d (delayed %dms)", light_id_, time_since_change);
            
            // Debug output - print payload as hex
            auto hex_str = vector_to_hex_string(pending_data_).data();
            ESP_LOGD(TAG, "Advertisement Payload (%d bytes): %s", pending_data_.size(), hex_str);

            // Send the advertisement
            this->controller_->queueCommand(this->light_id_, pending_data_);
            
            // Update tracking
            last_sent_data_ = pending_data_;
            last_command_sent_ = now;
            has_pending_command_ = false;
        }

        void FastconLight::write_state(light::LightState *state)
        {
            // Get the light data bits from the state
            auto light_data = this->controller_->get_light_data(state);

            // Debug output - print the light state values
            bool is_on = (light_data[0] & 0x80) != 0;
            float brightness = ((light_data[0] & 0x7F) / 127.0f) * 100.0f;
            if (light_data.size() == 1)
            {
                ESP_LOGV(TAG, "State change: light_id=%d, on=%d, brightness=%.1f%%", light_id_, is_on, brightness);
            }
            else
            {
                auto r = light_data[2];
                auto g = light_data[3];
                auto b = light_data[1];
                auto warm = light_data[4];
                auto cold = light_data[5];
                ESP_LOGV(TAG, "State change: light_id=%d, on=%d, brightness=%.1f%%, rgb=(%d,%d,%d), warm=%d, cold=%d", 
                         light_id_, is_on, brightness, r, g, b, warm, cold);
            }

            // Generate the advertisement payload
            auto adv_data = this->controller_->single_control(this->light_id_, light_data);

            // **OPTIMIZATION: Instead of sending immediately, mark as pending**
            pending_data_ = adv_data;
            last_state_change_ = millis();
            has_pending_command_ = true;
            
            ESP_LOGV(TAG, "Command pending for light %d, will send after debounce", light_id_);
        }
    } // namespace fastcon
} // namespace esphome
