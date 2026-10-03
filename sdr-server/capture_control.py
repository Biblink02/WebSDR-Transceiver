"""Demand-driven capture lifecycle shared by real and synthetic receiver sources."""
import logging
import math
import time


class CaptureController:
    def __init__(self, factory, power, publisher, health, idle_seconds=10, clock=time.monotonic):
        if not math.isfinite(idle_seconds) or not 0 <= idle_seconds <= 300:
            raise ValueError('Idle grace must be between 0 and 300 seconds')
        self.factory, self.power, self.publisher, self.health = factory, power, publisher, health
        self.idle_seconds, self.clock = idle_seconds, clock
        self.capture = None
        self.idle_deadline = None
        self.retry_at = 0
        self.sleep_attempted = False
        self.starts = 0
        self.stops = 0
        self.last_error = None
        self.health.set_mode('idle')
        self.health.details = self.diagnostics

    def diagnostics(self):
        return {'subscribers': self.publisher.subscribers, 'capture_active': self.capture is not None,
                'capture_starts': self.starts, 'capture_stops': self.stops,
                'idle_grace_seconds': self.idle_seconds,
                'power_state': self.power.state, 'last_error': self.last_error,
                'counters': dict(self.publisher.counters)}

    def _sleep(self):
        self.sleep_attempted = True
        try:
            self.power.sleep()
            self.last_error = None
        except Exception as error:
            # Capture is stopped even if the device is unreachable during idle.
            self.last_error = str(error)
            logging.warning('Capture idle; device sleep failed: %s', error)

    def tick(self):
        now = self.clock()
        if self.publisher.subscribers:
            self.idle_deadline = None
            if self.capture is not None:
                if self.health.mode != 'waking' or (
                        self.health.last_source is not None and self.health.last_publish is not None
                        and self.health.last_source >= self.health.mode_since
                        and self.health.last_publish >= self.health.mode_since):
                    self.health.set_mode('streaming')
                return
            if now < self.retry_at:
                return
            self.health.set_mode('waking')
            self.sleep_attempted = False
            capture = None
            try:
                self.power.wake()
                capture = self.factory()
                capture.start()
                self.capture = capture
                self.starts += 1
                self.last_error = None
                logging.info('Capture started for %s backend subscribers', self.publisher.subscribers)
            except Exception as error:
                if capture is not None:
                    capture.close()
                self.last_error = str(error)
                self.retry_at = now+5
                self.health.set_mode('fault')
                logging.exception('Unable to wake receiver')
        elif self.capture is not None:
            if self.idle_deadline is None:
                self.idle_deadline = now+self.idle_seconds
            self.health.set_mode('cooling')
            if now >= self.idle_deadline:
                self.capture.close()
                self.capture = None
                self.stops += 1
                self.publisher.discard_pending()
                self._sleep()
                self.health.set_mode('idle')
                logging.info('Capture released; receiver idle')
        else:
            self.health.set_mode('idle')
            if not self.sleep_attempted:
                self._sleep()

    def close(self):
        if self.capture is not None:
            self.capture.close()
            self.capture = None
        self.publisher.discard_pending()
        self._sleep()
        self.health.set_mode('idle')


class PlutoPower:
    """Use the AD9361 driver's existing ENSM sleep mode through libiio."""
    def __init__(self, uri, context_factory=None):
        if context_factory is None:
            import iio
            context_factory = iio.Context
        self.uri, self.context_factory = uri, context_factory
        self.wake_mode = 'fdd'
        self.state = 'unknown'

    def _set(self, sleeping):
        context = self.context_factory(self.uri)
        phy = context.find_device('ad9361-phy')
        if phy is None:
            raise RuntimeError('Pluto AD9361 PHY device is unavailable')
        mode = phy.attrs['ensm_mode']
        if sleeping and mode.value not in ('sleep', 'wait'):
            self.wake_mode = mode.value
        mode.value = 'sleep' if sleeping else self.wake_mode
        self.state = 'sleep' if sleeping else 'awake'

    def sleep(self):
        self._set(True)

    def wake(self):
        self._set(False)
