/* Freestanding stand-in for <stdio.h> used while parsing firmware sources. */
#ifndef LOOPER_STUB_STDIO_H
#define LOOPER_STUB_STDIO_H

#include <stdarg.h>
#include <stddef.h>

int printf(const char *format, ...);
int snprintf(char *destination, size_t size, const char *format, ...);
int vsnprintf(char *destination, size_t size, const char *format, va_list arguments);
int sprintf(char *destination, const char *format, ...);

#endif /* LOOPER_STUB_STDIO_H */
