#ifndef MC146818RTC_H
#define MC146818RTC_H

#include "hw/isa/isa.h"
#include "hw/timer/mc146818rtc_regs.h"

#define TYPE_MC146818_RTC "mc146818rtc"

ISADevice *rtc_init(ISABus *bus, int base_year, qemu_irq intercept_irq);
void rtc_set_memory(ISADevice *dev, int addr, int val);
void rtc_set_date(ISADevice *dev, const struct tm *tm);

#endif /* !MC146818RTC_H */