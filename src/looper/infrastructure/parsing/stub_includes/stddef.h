/* Freestanding stand-in for <stddef.h> used while parsing firmware headers. */
#ifndef LOOPER_STUB_STDDEF_H
#define LOOPER_STUB_STDDEF_H

typedef unsigned long long size_t;
typedef long long ptrdiff_t;
typedef unsigned short wchar_t;

#ifndef NULL
#define NULL ((void *)0)
#endif

#define offsetof(type, member) __builtin_offsetof(type, member)

#endif /* LOOPER_STUB_STDDEF_H */
