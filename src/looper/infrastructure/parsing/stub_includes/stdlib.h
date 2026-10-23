/* Freestanding stand-in for <stdlib.h> used while parsing firmware sources. */
#ifndef LOOPER_STUB_STDLIB_H
#define LOOPER_STUB_STDLIB_H

#include <stddef.h>

void *malloc(size_t size);
void *calloc(size_t count, size_t size);
void *realloc(void *block, size_t size);
void free(void *block);
void abort(void);
void exit(int status);
int atoi(const char *text);
long strtol(const char *text, char **end, int base);
unsigned long strtoul(const char *text, char **end, int base);
int abs(int value);

#endif /* LOOPER_STUB_STDLIB_H */
