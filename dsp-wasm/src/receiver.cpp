#include "receiver.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <complex>
#include <memory>
#include <numbers>
#include <numeric>
#include <type_traits>
#include <vector>
#include "liquid.h"
#ifdef __EMSCRIPTEN__
#include <emscripten.h>
#define DSP_EXPORT EMSCRIPTEN_KEEPALIVE
#else
#define DSP_EXPORT
#endif

namespace {
constexpr std::uint32_t max_chunk = 65536;
constexpr float tau = 2.0F * std::numbers::pi_v<float>;
using Complex = std::complex<float>;
template<class T, auto Destroy>
using Handle = std::unique_ptr<std::remove_pointer_t<T>, decltype(Destroy)>;

// Own library objects and reuse every sample buffer. DSP algorithms live in liquid-dsp.
class Receiver {
public:
    Receiver(std::uint32_t rate, std::uint32_t fft_size, float calibration)
        : rate_(rate), fft_size_(fft_size), calibration_(calibration),
          input_(max_chunk*2), complex_(max_chunk), shifted_(max_chunk),
          resampled_(max_chunk*2+16), audio_(max_chunk*2+16), spectrum_(fft_size),
          fft_ring_(fft_size), fft_in_(fft_size), fft_out_(fft_size), window_(fft_size),
          oscillator_(nco_crcf_create(LIQUID_VCO), nco_crcf_destroy),
          resampler_(msresamp_crcf_create(48000.0F/static_cast<float>(rate), 80.0F), msresamp_crcf_destroy),
          filter_(nullptr, firfilt_crcf_destroy), modem_(nullptr, ampmodem_destroy),
          fft_(fft_create_plan(fft_size, fft_in_.data(), fft_out_.data(), LIQUID_FFT_FORWARD, 0), fft_destroy_plan)
    {
        for (std::uint32_t i=0; i<fft_size; ++i) window_[i] = liquid_hann(i, fft_size);
        window_sum_ = std::accumulate(window_.begin(), window_.end(), 0.0F);
        tune(0, 2700, 1);
    }

    bool tune(double offset, double bandwidth, int side) {
        if (!std::isfinite(offset) || !std::isfinite(bandwidth) || bandwidth < 90 || bandwidth > 15000
            || (side != 1 && side != -1) || std::abs(offset) > rate_/2.0
            || std::abs(offset+side*bandwidth) > rate_/2.0) return false;
        const auto transition = static_cast<float>(std::max(100.0, std::min(600.0, bandwidth*0.15)));
        auto length = estimate_req_filter_len(transition/48000.0F, 60.0F) | 1U;
        // Kaiser filter creation/design and sideband recovery are library operations.
        Handle<firfilt_crcf, firfilt_crcf_destroy> filter(
            firfilt_crcf_create_kaiser(length, static_cast<float>(bandwidth)/48000.0F, 60.0F, 0),
            firfilt_crcf_destroy);
        Handle<ampmodem, ampmodem_destroy> modem(
            ampmodem_create(1.0F, side == 1 ? LIQUID_AMPMODEM_USB : LIQUID_AMPMODEM_LSB, 1),
            ampmodem_destroy);
        if (!filter || !modem) return false;
        // liquid's prototype has gain 1/(2*cutoff); explicitly normalize its DC gain.
        firfilt_crcf_set_scale(filter.get(), 2.0F*static_cast<float>(bandwidth)/48000.0F);
        filter_ = std::move(filter); modem_ = std::move(modem);
        frequency_ = tau*static_cast<float>(offset)/static_cast<float>(rate_);
        reset_audio();
        return true;
    }

    void reset_audio() {
        nco_crcf_reset(oscillator_.get());
        nco_crcf_set_frequency(oscillator_.get(), frequency_);
        msresamp_crcf_reset(resampler_.get());
        firfilt_crcf_reset(filter_.get());
        ampmodem_reset(modem_.get());
    }

    void reset() {
        reset_audio();
        std::fill(fft_ring_.begin(), fft_ring_.end(), Complex{});
        fft_pos_ = 0; fft_count_ = 0; fft_ready_ = false;
    }

    std::int32_t process(std::uint32_t count, bool listen, bool fft) {
        if (count == 0 || count > max_chunk) return -1;
        fft_ready_ = false;
        for (std::uint32_t i=0; i<count; ++i) {
            complex_[i] = {std::max(-1.0F, input_[2*i]/127.0F), std::max(-1.0F, input_[2*i+1]/127.0F)};
            fft_ring_[fft_pos_] = complex_[i];
            fft_pos_ = (fft_pos_+1)%fft_size_;
            fft_count_ = std::min(fft_count_+1, fft_size_);
        }
        std::uint32_t output = 0;
        if (listen) {
            nco_crcf_mix_block_down(oscillator_.get(), complex_.data(), shifted_.data(), count);
            if (msresamp_crcf_get_num_output(resampler_.get(), count) > resampled_.size()) return -1;
            msresamp_crcf_execute(resampler_.get(), shifted_.data(), count, resampled_.data(), &output);
            firfilt_crcf_execute_block(filter_.get(), resampled_.data(), output, resampled_.data());
            ampmodem_demodulate_block(modem_.get(), resampled_.data(), output, audio_.data());
            for (std::uint32_t i=0; i<output; ++i) audio_[i] = std::clamp(audio_[i], -1.0F, 1.0F);
        }
        if (fft && fft_count_ == fft_size_) {
            for (std::uint32_t i=0; i<fft_size_; ++i)
                fft_in_[i] = fft_ring_[(fft_pos_+i)%fft_size_]*window_[i];
            fft_execute(fft_.get());
            fft_shift(fft_out_.data(), fft_size_);
            for (std::uint32_t i=0; i<fft_size_; ++i) {
                auto power = std::norm(fft_out_[i])/(window_sum_*window_sum_);
                spectrum_[i] = 10.0F*std::log10(std::max(power, 1e-20F))+calibration_;
            }
            fft_ready_ = true;
        }
        return static_cast<std::int32_t>(output);
    }

    std::int8_t* input() { return input_.data(); }
    float* audio() { return audio_.data(); }
    float* spectrum() { return spectrum_.data(); }
    bool fft_ready() const { return fft_ready_; }
private:
    std::uint32_t rate_, fft_size_;
    float calibration_, window_sum_ = 0, frequency_ = 0;
    std::vector<std::int8_t> input_;
    std::vector<Complex> complex_, shifted_, resampled_;
    std::vector<float> audio_, spectrum_;
    std::vector<Complex> fft_ring_, fft_in_, fft_out_;
    std::vector<float> window_;
    Handle<nco_crcf, nco_crcf_destroy> oscillator_;
    Handle<msresamp_crcf, msresamp_crcf_destroy> resampler_;
    Handle<firfilt_crcf, firfilt_crcf_destroy> filter_;
    Handle<ampmodem, ampmodem_destroy> modem_;
    Handle<fftplan, fft_destroy_plan> fft_;
    std::uint32_t fft_pos_ = 0, fft_count_ = 0;
    bool fft_ready_ = false;
};

// IDs, rather than exposed object pointers, reject invalid ABI handles.
std::array<std::unique_ptr<Receiver>, 4> receivers;
Receiver* get(std::uint32_t id) {
    return id > 0 && id <= receivers.size() ? receivers[id-1].get() : nullptr;
}
}

extern "C" {
DSP_EXPORT std::uint32_t dsp_new(std::uint32_t rate, std::uint32_t audio_rate,
                                std::uint32_t fft, float calibration) {
    if (rate < 48000 || rate > 4000000 || audio_rate != 48000 || fft < 256 || fft > 8192
        || (fft & (fft-1)) != 0 || !std::isfinite(calibration)) return 0;
    for (std::uint32_t i=0; i<receivers.size(); ++i) {
        if (!receivers[i]) {
            receivers[i] = std::make_unique<Receiver>(rate, fft, calibration);
            return i+1;
        }
    }
    return 0;
}
DSP_EXPORT void dsp_free(std::uint32_t id) { if (get(id)) receivers[id-1].reset(); }
DSP_EXPORT std::int8_t* dsp_input(std::uint32_t id) { auto* r=get(id); return r ? r->input() : nullptr; }
DSP_EXPORT float* dsp_audio(std::uint32_t id) { auto* r=get(id); return r ? r->audio() : nullptr; }
DSP_EXPORT float* dsp_spectrum(std::uint32_t id) { auto* r=get(id); return r ? r->spectrum() : nullptr; }
DSP_EXPORT std::uint32_t dsp_fft_ready(std::uint32_t id) { auto* r=get(id); return r && r->fft_ready(); }
DSP_EXPORT void dsp_reset(std::uint32_t id) { if (auto* r=get(id)) r->reset(); }
DSP_EXPORT std::uint32_t dsp_tune(std::uint32_t id, double offset, double bandwidth, std::int32_t side) {
    auto* r=get(id); return r && r->tune(offset, bandwidth, side);
}
DSP_EXPORT std::int32_t dsp_process(std::uint32_t id, std::uint32_t count, std::uint32_t listen, std::uint32_t fft) {
    auto* r=get(id); return r ? r->process(count, listen != 0, fft != 0) : -1;
}
}
