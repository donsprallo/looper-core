/*
 * The device model.
 *
 * Generated adapters forward to hooks. This file installs hooks that map the
 * adapter API onto the looper runtime, which is what turns a pile of stubs
 * into something a client can observe and drive. A test that wants different
 * behaviour installs its own hooks instead.
 */
#include "device_model.h"

#include "adapter_blinky.h"
#include "looper_analog.h"
#include "looper_clock.h"
#include "looper_gpio_model.h"
#include "looper_hooks.h"

#define MICROSECONDS_PER_MILLISECOND 1000u

static looper_signal_level_t level_for(blinky_pin_t pin, blinky_pin_state_t state)
{
    const looper_pin_t *entry = NULL;
    looper_active_polarity_t polarity = LOOPER_ACTIVE_POLARITY_HIGH;

    for (size_t index = 0u; index < looper_gpio_count(); index++) {
        entry = looper_gpio_at(index);
        if (entry != NULL && entry->id == pin) {
            polarity = entry->polarity;
            break;
        }
    }
    if (polarity == LOOPER_ACTIVE_POLARITY_LOW) {
        return (state == BLINKY_PIN_ACTIVE) ? LOOPER_SIGNAL_LEVEL_LOW : LOOPER_SIGNAL_LEVEL_HIGH;
    }
    return (state == BLINKY_PIN_ACTIVE) ? LOOPER_SIGNAL_LEVEL_HIGH : LOOPER_SIGNAL_LEVEL_LOW;
}

static blinky_pin_state_t state_for(blinky_pin_t pin, looper_signal_level_t level)
{
    looper_signal_level_t active = LOOPER_SIGNAL_LEVEL_HIGH;

    for (size_t index = 0u; index < looper_gpio_count(); index++) {
        const looper_pin_t *entry = looper_gpio_at(index);
        if (entry != NULL && entry->id == pin
            && entry->polarity == LOOPER_ACTIVE_POLARITY_LOW) {
            active = LOOPER_SIGNAL_LEVEL_LOW;
            break;
        }
    }
    return (level == active) ? BLINKY_PIN_ACTIVE : BLINKY_PIN_INACTIVE;
}

static void model_gpio_set(blinky_pin_t pin, blinky_pin_state_t state)
{
    looper_gpio_write(pin, level_for(pin, state));
}

static blinky_pin_state_t model_gpio_get(blinky_pin_t pin)
{
    return state_for(pin, looper_gpio_read(pin));
}

static uint32_t model_millis(void)
{
    return looper_clock_milliseconds();
}

static uint64_t model_micros(void)
{
    return looper_clock_microseconds();
}

static void model_delay_ms(uint32_t milliseconds)
{
    looper_clock_wait((uint64_t)milliseconds * MICROSECONDS_PER_MILLISECOND);
}

static double model_measure(uint32_t channel)
{
    return looper_analog_read(channel);
}

static void model_publish(uint32_t channel, double value)
{
    looper_analog_write(channel, value);
}

static bool model_is_ready(void)
{
    return true;
}

void device_model_install(void)
{
    looper_hooks_t *hooks = looper_hooks();

    hooks->adapter_blinky_gpio_set = model_gpio_set;
    hooks->adapter_blinky_gpio_get = model_gpio_get;
    hooks->adapter_blinky_millis = model_millis;
    hooks->adapter_blinky_micros = model_micros;
    hooks->adapter_blinky_delay_ms = model_delay_ms;
    hooks->adapter_blinky_measure = model_measure;
    hooks->adapter_blinky_publish = model_publish;
    hooks->adapter_blinky_is_ready = model_is_ready;
}
