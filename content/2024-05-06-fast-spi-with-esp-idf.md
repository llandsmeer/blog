---
layout: post
title:  "Fast Spi With Esp Idf"
date:   2024-05-06T09:27:57.795235+00:00
status: draft
categories: tech
---

Don't forget IOMUX!

# Arduino vs ESP-IDF

Arduino is known as a great platform for _getting started_
MCU programming. It's not known for being a
professional-grade, or even optimal and efficient development platform.
Yet, to our surprise, and to a lot of others online[^spislow1][^spislow2][^spislow3],
Arduino completely outperforms the official ESP-IDF SDK in SPI speed.

[^spislow1]: https://www.esp32.com/viewtopic.php?t=25417
[^spislow2]: https://github.com/espressif/esp-idf/issues/368
[^spislow3]: https://www.esp32.com/viewtopic.php?t=16798

This is not a problem under usual circumstances, but when we had to read out
a 64-channel ADC at 22 kHz over SPI, this suddenly became an issue. The Arduino
prototyping code would happily achieve the required speeds, yet
the ESP-IDF code would not keep up.
The scope showed this was not because of the SPI transmission itself,
but much much larger delays between transmissions, caused a lot more code executing
between transmissions.

In the end, this is because the ESP-IDF master driver has a *lot*
more configuration options than the Arduino api, and tries to expose the entire API
using a single function call and a `spi_transmission_t` struct.

This single call then has to set up the required hardware registers,
*each time* it is called, even when the hardware registers are
already configured in the right way (which is definitely the case when
sending the same request over-and-over again).

# ESP-IDF internals

 - **User code**: the code you're writing calls into the
 - **SPI Master Driver**, which is a high level API over the
 - **Hardware Abstraction Layer (HAL)** which calls into the
 - **Low-level (LL)** header library to talk to the hardware registers

The SPI Master Driver and HAL
are separately compiled to object files,
meaning it is impossible for the compiler to
do something like contant-folding through the user-calling code.
Instead, it has to do a lot of checks
which we _could_ statically now not to happen.
Sadly, link-time-optimization is not officialy available[^lto].
[^lto]: https://esp32.com/viewtopic.php?t=21711

The final LL resides in inlinable functions in a header definition.
Ideally, we could call directly into these functions in the hot path!


# Faster in the loop

SPI setup is tedious, and we prefer not to write code for this manually.
The RX-TX loop is however much simpler, but very important to be performant.
So we came up with the following solution:

We use the SPI Master Driver to set up the neccesarily registers,
using an initial full transfer.
After that, we just re-execute the low-level calls needed to
perform a transmission:

 - *Writing the TX register*
 - *Set the transmission flag* to signal the hardware we're ready to transmit
 - *Keep polling the transmission flag* until the hardware signals the transmission is ready
 - *Reading the TX register*







