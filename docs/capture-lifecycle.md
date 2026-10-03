# Demand-driven receiver capture

Each backend opens one ZeroMQ SUB socket while it has at least one actual
WebSocket viewer. The last WebSocket disconnect closes that socket. Idle replicas
remain ready so a new viewer can reach them and wake the source.

The source uses XPUB subscription notifications to count subscribed backend
replicas, not people. `XPUB_VERBOSER` reports duplicate subscriptions and each
unsubscribe, including pipe disconnection; counting only the last unsubscribe
would leave capture running with multiple replicas. ZeroMQ heartbeats expire
unresponsive connections. There is no Redis, allocation service or remote DSP
control channel. See [the ZeroMQ socket options](https://libzmq.readthedocs.io/en/latest/zmq_setsockopt.html).

On first demand, the controller wakes the Pluto, constructs/configures a GNU Radio
capture graph and starts it. Source health allows a bounded 30-second warm-up.
Actual source and publication progress switch it to streaming. Active stalls fail
health and restart only the source; healthy backends remain alive and reconnect.

When demand reaches zero, a configurable `sdr_idle_seconds` grace (default 10,
range 0–300) avoids repeated hardware setup during brief reconnects. New demand
cancels the grace. Otherwise the graph stops, waits for its scheduler, disconnects
and releases its native IIO handles/buffers. Pending frames are discarded before
requesting AD9361 ENSM `sleep` through libiio. The original operating mode is
restored before applying hardware attributes on the next wake; the AD9361 driver
rejects most configuration writes in sleep. See [the ADI Linux driver](https://github.com/analogdevicesinc/linux/blob/main/drivers/iio/adc/ad9361.c).

The control thread owns the XPUB socket. GNU Radio's scheduler only quantizes and
enqueues frames into a bounded four-frame queue. This avoids socket sharing
between threads. Idle capture performs no sample processing. `/health`, `/ready`
and `/startup` remain successful during idle; unreachable hardware during an idle
sleep request is reported in `last_error` without restarting healthy idle pods.

Source diagnostics include `mode`, backend `subscribers`, `capture_active`, start
and stop counts, `power_state`, `last_error`, source/publication ages and bounded
queue counters. Backend `/stream-info` includes `receiving` and its local actual
WebSocket client count. Publication counts represent enqueued-to-socket frames;
ZeroMQ may still discard frames for slow subscribers. Sequence gaps detect loss.

`tools/synthetic_iq.py` uses the same publisher, health and capture controller with
simulated device power. Tests cover multiple replicas, first/last viewers, idle
publication stopping, grace cancellation and a fresh epoch after waking. They
prove software demand handling and graph lifecycle, not physical RF power saving.
Actual Pluto ENSM state, buffer release, first reception after wake and repeated
sleep/wake still need acceptance on the station's hardware. No production
deployment is part of these local checks.
