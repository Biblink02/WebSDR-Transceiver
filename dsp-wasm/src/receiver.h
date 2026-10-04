#pragma once
#include <cstdint>
extern "C" {
std::uint32_t dsp_new(std::uint32_t rate, std::uint32_t audio_rate, std::uint32_t fft_size, float calibration);
void dsp_free(std::uint32_t handle);
std::int8_t* dsp_input(std::uint32_t handle);
float* dsp_audio(std::uint32_t handle);
float* dsp_spectrum(std::uint32_t handle);
std::uint32_t dsp_fft_ready(std::uint32_t handle);
std::uint32_t dsp_set_fft(std::uint32_t handle, std::uint32_t size);
void dsp_reset(std::uint32_t handle);
std::uint32_t dsp_tune(std::uint32_t handle, double offset, double bandwidth, std::int32_t sideband);
std::uint32_t dsp_shift(std::uint32_t handle, double offset);
std::uint32_t dsp_mode(std::uint32_t handle, std::uint32_t cw, float pitch);
std::uint32_t dsp_audio_config(std::uint32_t handle, std::uint32_t agc, std::uint32_t squelch, float threshold);
float dsp_audio_rssi(std::uint32_t handle);
std::uint32_t dsp_squelch_open(std::uint32_t handle);
std::int32_t dsp_process(std::uint32_t handle, std::uint32_t count, std::uint32_t listen, std::uint32_t fft);
}
