/* Freestanding stand-in for <math.h> used while parsing firmware sources. */
#ifndef LOOPER_STUB_MATH_H
#define LOOPER_STUB_MATH_H

double fabs(double value);
float fabsf(float value);
double sqrt(double value);
float sqrtf(float value);
double round(double value);
long lround(double value);
int isfinite(double value);
int isnan(double value);

#endif /* LOOPER_STUB_MATH_H */
