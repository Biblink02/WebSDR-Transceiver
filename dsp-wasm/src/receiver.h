#pragma once
#include <cstdint>
extern "C" {
std::uint32_t dsp_new(std::uint32_t rate, std::uint32_t audio_rate, std::uint32_t fft_size, float calibration);
void dsp_free(std::uint32_t handle);
std::int8_t* dsp_input(std::uint32_t handle);
float* dsp_audio(std::uint32_t handle);
float* dsp_spectrum(std::uint32_t handle);
std::uint32_t dsp_fft_ready(std::uint32_t handle);
void dsp_reset(std::uint32_t handle);
std::uint32_t dsp_tune(std::uint32_t handle, double offset, double bandwidth, std::int32_t sideband);
std::int32_t dsp_process(std::uint32_t handle, std::uint32_t count, std::uint32_t listen, std::uint32_t fft);
}
