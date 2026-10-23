/*
 * Entry point of the simulated firmware.
 *
 * Everything a simulation does around the firmware -- the clock, the control
 * channel, the loop -- is the same in every project and comes from
 * looper_main. What is left here is the part that is this board: which pins
 * and channels a client sees, which device model answers the adapter, and
 * what one iteration of this firmware is.
 *
 * Usage: blinky [--virtual] [--port N] [--steps N]
 */
#include "app.h"
#include "device_model.h"
#include "looper_analog.h"
#include "looper_app.h"
#include "looper_gpio_model.h"

#define LED_PIN 17u
#define BUTTON_PIN 4u
#define SHUNT_CHANNEL 0u
#define FILTERED_CHANNEL 1u
#define IDLE_STEP_MICROSECONDS 500u

static void register_pins(void)
{
    looper_gpio_register(
        LED_PIN, "LED_STATUS", LOOPER_PIN_DIRECTION_OUTPUT, LOOPER_ACTIVE_POLARITY_HIGH
    );
    looper_gpio_register(
        BUTTON_PIN, "BUTTON_MODE", LOOPER_PIN_DIRECTION_INPUT, LOOPER_ACTIVE_POLARITY_LOW
    );
}

static void register_channels(void)
{
    looper_analog_register(SHUNT_CHANNEL, "SHUNT_CURRENT", "A", LOOPER_CHANNEL_DIRECTION_INPUT);
    looper_analog_register(FILTERED_CHANNEL, "FILTERED", "A", LOOPER_CHANNEL_DIRECTION_OUTPUT);
}

/** @brief Set up what this board offers, before a client can look at it. */
static void prepare(void)
{
    register_pins();
    register_channels();
    device_model_install();
}

/** @brief Bring the firmware up. This one cannot fail. */
static bool start(void)
{
    app_init();
    return true;
}

int main(int argc, char **argv)
{
    static const looper_application_t blinky = {
        .name = "blinky",
        .prepare = prepare,
        .start = start,
        .step = app_step,
        .idle_microseconds = IDLE_STEP_MICROSECONDS,
    };

    return looper_main(argc, argv, &blinky);
}
