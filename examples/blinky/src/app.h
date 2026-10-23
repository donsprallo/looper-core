/**
 * @file
 * @brief The firmware application under test.
 */
#ifndef BLINKY_APP_H
#define BLINKY_APP_H

#include <stdbool.h>
#include <stdint.h>

/** @brief Reset the application state and drive the LED to its start value. */
void app_init(void);

/** @brief Run one iteration of the firmware loop. */
void app_step(void);

/** @brief Read the shunt channel, filter it, and publish the result. */
void app_measure(void);

/**
 * @brief Read the filtered current the application last computed.
 * @return The filtered value in amperes.
 */
double app_filtered_current(void);

/**
 * @brief Report whether the filtered current exceeds the alarm threshold.
 * @retval true The measurement is above the threshold.
 * @retval false The measurement is within range.
 */
bool app_is_over_current(void);

/**
 * @brief Report the blink interval the application currently uses.
 * @return Interval in milliseconds, shorter while the mode button is active.
 */
uint32_t app_blink_interval_ms(void);

#endif /* BLINKY_APP_H */
