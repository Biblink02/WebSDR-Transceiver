#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <memory>
#include <numbers>
#include <type_traits>
#include <vector>
#include "liquid.h"

namespace {
constexpr std::uint32_t max_chunk = 65536;
using Complex = std::complex<float>;
template<class T, auto Destroy>
using Handle = std::unique_ptr<std::remove_pointer_t<T>, decltype(Destroy)>;

// One stateful library channelizer per active band, shared by its listeners.
class Channelizer {
public:
    Channelizer(std::uint32_t input_rate, std::uint32_t output_rate, double offset)
        : input(max_chunk*2), output((max_chunk+16)*2),
          complex_(max_chunk), shifted_(max_chunk), resampled_(max_chunk+16),
          oscillator_(nco_crcf_create(LIQUID_VCO), nco_crcf_destroy),
          resampler_(msresamp_crcf_create(static_cast<float>(output_rate)/input_rate, 80.0F), msresamp_crcf_destroy)
    {
        nco_crcf_set_frequency(oscillator_.get(),
            2.0F*std::numbers::pi_v<float>*static_cast<float>(offset)/input_rate);
    }

    int process(std::uint32_t count) {
        if (!count || count > max_chunk ||
            msresamp_crcf_get_num_output(resampler_.get(), count) > resampled_.size()) return -1;
        for (std::uint32_t i=0; i<count; ++i)
            complex_[i] = {std::max(-1.0F, input[2*i]/127.0F), std::max(-1.0F, input[2*i+1]/127.0F)};
        nco_crcf_mix_block_down(oscillator_.get(), complex_.data(), shifted_.data(), count);
        unsigned int written = 0;
        msresamp_crcf_execute(resampler_.get(), shifted_.data(), count, resampled_.data(), &written);
        for (std::uint32_t i=0; i<written; ++i) {
            output[2*i] = static_cast<std::int8_t>(std::lround(std::clamp(resampled_[i].real(), -1.0F, 1.0F)*127.0F));
            output[2*i+1] = static_cast<std::int8_t>(std::lround(std::clamp(resampled_[i].imag(), -1.0F, 1.0F)*127.0F));
        }
        return static_cast<int>(written);
    }
    std::vector<std::int8_t> input, output;
private:
    std::vector<Complex> complex_, shifted_, resampled_;
    Handle<nco_crcf, nco_crcf_destroy> oscillator_;
    Handle<msresamp_crcf, msresamp_crcf_destroy> resampler_;
};
}

extern "C" {
void* channelizer_new(std::uint32_t input_rate, std::uint32_t output_rate, double offset) noexcept {
    if (output_rate < 48000 || output_rate > input_rate || input_rate > 4000000 ||
        !std::isfinite(offset) || std::abs(offset)+output_rate/2.0 > input_rate/2.0) return nullptr;
    try { return new Channelizer(input_rate, output_rate, offset); }
    catch (...) { return nullptr; }
}
void channelizer_free(void* handle) { delete static_cast<Channelizer*>(handle); }
void* channelizer_input(void* handle) { return handle ? static_cast<Channelizer*>(handle)->input.data() : nullptr; }
void* channelizer_output(void* handle) { return handle ? static_cast<Channelizer*>(handle)->output.data() : nullptr; }
int channelizer_process(void* handle, std::uint32_t count) {
    return handle ? static_cast<Channelizer*>(handle)->process(count) : -1;
}
}
