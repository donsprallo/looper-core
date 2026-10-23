/*
 * The firmware under test.
 *
 * It talks to the hardware only through adapter_blinky.h and knows nothing
 * about the simulation. The same translation unit would compile for a target.
 */
#include "app.h"

#include <stdbool.h>

#include "adapter_blinky.h"

#define LED_PIN 17u
#define BUTTON_PIN 4u

#define SLOW_INTERVAL_MS 500u
#define FAST_INTERVAL_MS 100u

#define SHUNT_CHANNEL 0u
#define FILTERED_CHANNEL 1u
#define FILTER_WEIGHT 0.01
#define SAMPLE_INTERVAL_US 1000u
#define OVERCURRENT_THRESHOLD 4.0

/*
 * The status word a firmware of this kind keeps: a few flags packed into one
 * byte, which is how they would be laid out on a target and how they would be
 * reported over a bus. Packed flags are worth having in the example because
 * they are the one shape a watch cannot address a byte at a time.
 */
typedef struct {
    uint8_t led_on : 1;
    uint8_t blinking_fast : 1;
    uint8_t over_current : 1;
    uint8_t toggle_count : 5;
} app_status_t;

/*
 * What the board can do, packed the way a device would report it over a bus.
 * Written once at start up and never again, which is the other half of what
 * packed flags are used for.
 */
typedef struct {
    uint8_t has_shunt : 1;
    uint8_t has_button : 1;
    uint8_t revision : 6;
} app_capabilities_t;

static uint32_t last_toggle_ms;
static blinky_pin_state_t led_state;
static double filtered_current;
static uint64_t last_sample_us;
static app_status_t status;
static app_capabilities_t capabilities;

void app_init(void)
{
    last_toggle_ms = adapter_blinky_millis();
    led_state = BLINKY_PIN_INACTIVE;
    filtered_current = 0.0;
    last_sample_us = adapter_blinky_micros();
    status = (app_status_t){0};
    capabilities = (app_capabilities_t){.has_shunt = 1u, .has_button = 1u, .revision = 3u};
    adapter_blinky_gpio_set(LED_PIN, led_state);
}

uint32_t app_blink_interval_ms(void)
{
    if (adapter_blinky_gpio_get(BUTTON_PIN) == BLINKY_PIN_ACTIVE || app_is_over_current()) {
        return FAST_INTERVAL_MS;
    }
    return SLOW_INTERVAL_MS;
}

double app_filtered_current(void)
{
    return filtered_current;
}

/*
 * Samples the shunt channel at a fixed rate, smooths it with a first order
 * filter, and publishes the result. A client drives the shunt channel with a
 * generated signal and watches both traces, which is how the filter behaviour
 * is inspected. The rate limit matters: without it the loop would sample as
 * fast as the host allows and the filter would track the input exactly.
 */
void app_measure(void)
{
    uint64_t now_us = adapter_blinky_micros();
    double measured;

    if (now_us - last_sample_us < SAMPLE_INTERVAL_US) {
        return;
    }
    last_sample_us = now_us;
    measured = adapter_blinky_measure(SHUNT_CHANNEL);
    filtered_current += FILTER_WEIGHT * (measured - filtered_current);
    adapter_blinky_publish(FILTERED_CHANNEL, filtered_current);
}

bool app_is_over_current(void)
{
    return filtered_current > OVERCURRENT_THRESHOLD;
}

void app_step(void)
{
    uint32_t now = adapter_blinky_millis();

    if (!adapter_blinky_is_ready()) {
        return;
    }
    app_measure();
    if (now - last_toggle_ms < app_blink_interval_ms()) {
        return;
    }
    led_state = (led_state == BLINKY_PIN_ACTIVE) ? BLINKY_PIN_INACTIVE : BLINKY_PIN_ACTIVE;
    adapter_blinky_gpio_set(LED_PIN, led_state);
    last_toggle_ms = now;

    status.led_on = (led_state == BLINKY_PIN_ACTIVE) ? 1u : 0u;
    status.blinking_fast = (app_blink_interval_ms() == FAST_INTERVAL_MS) ? 1u : 0u;
    status.over_current = app_is_over_current() ? 1u : 0u;
    status.toggle_count++;
}
