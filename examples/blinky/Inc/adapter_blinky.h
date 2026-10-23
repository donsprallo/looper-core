/**
 * @file
 * @brief Hardware abstraction layer of the blinky example firmware.
 *
 * A deliberately small adapter in the shape of a real one: opaque pin
 * numbers, an abstract pin state, a time source, and a blocking delay.
 */
#ifndef ADAPTER_BLINKY_H
#define ADAPTER_BLINKY_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** @brief Abstract state of a pin, independent of its polarity. */
typedef enum {
    BLINKY_PIN_INACTIVE = 0,
    BLINKY_PIN_ACTIVE = 1
} blinky_pin_state_t;

/** @brief Opaque pin number as the hardware layer addresses it. */
typedef uint32_t blinky_pin_t;

/**
 * @brief Drive an output pin to an abstract state.
 * @param pin Pin to drive.
 * @param state Requested state.
 */
void adapter_blinky_gpio_set(blinky_pin_t pin, blinky_pin_state_t state);

/**
 * @brief Read the abstract state of a pin.
 * @param pin Pin to read.
 * @return Current state. An unknown pin reads as inactive.
 */
blinky_pin_state_t adapter_blinky_gpio_get(blinky_pin_t pin);

/**
 * @brief Read elapsed milliseconds since start up.
 * @return Milliseconds, wrapping naturally after its range is exhausted.
 */
uint32_t adapter_blinky_millis(void);

/**
 * @brief Read elapsed microseconds since start up.
 * @return Microseconds, wrapping naturally after its range is exhausted.
 */
uint64_t adapter_blinky_micros(void);

/**
 * @brief Busy wait for a number of milliseconds.
 * @param milliseconds Duration to wait.
 */
void adapter_blinky_delay_ms(uint32_t milliseconds);

/**
 * @brief Read one analog measurement channel.
 * @param channel Channel to measure.
 * @return The measured value in the unit of the channel.
 */
double adapter_blinky_measure(uint32_t channel);

/**
 * @brief Publish a computed value on an analog output channel.
 * @param channel Channel to publish on.
 * @param value Value the firmware produced.
 */
void adapter_blinky_publish(uint32_t channel, double value);

/**
 * @brief Report whether the hardware layer finished starting up.
 * @retval true The layer is ready.
 * @retval false The layer is still initialising.
 */
bool adapter_blinky_is_ready(void);

#ifdef __cplusplus
}
#endif

#endif /* ADAPTER_BLINKY_H */
