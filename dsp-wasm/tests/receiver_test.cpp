#include "receiver.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <numbers>
#include <vector>

void require(bool ok, const char* message) {
    if (!ok) { std::cerr << message << '\n'; std::exit(1); }
}
void tone(unsigned id, unsigned rate, unsigned start, unsigned count, double frequency) {
    auto* input=dsp_input(id);
    for (unsigned i=0; i<count; ++i) {
        auto a=2*std::numbers::pi*frequency*(start+i)/rate;
        input[2*i]=static_cast<std::int8_t>(std::round(80*std::cos(a)));
        input[2*i+1]=static_cast<std::int8_t>(std::round(80*std::sin(a)));
    }
}
float rms(unsigned id, unsigned rate, double frequency) {
    double power=0; unsigned total=0;
    for (unsigned chunk=0; chunk<25; ++chunk) {
        tone(id, rate, chunk*8192, 8192, frequency);
        auto count=dsp_process(id, 8192, 1, 0); require(count>=0, "process failed");
        if (chunk>5) for (int i=0; i<count; ++i) { power+=dsp_audio(id)[i]*dsp_audio(id)[i]; ++total; }
    }
    return static_cast<float>(std::sqrt(power/total));
}
int main() {
    require(dsp_new(1000,48000,2048,0)==0, "invalid rate accepted");
    require(dsp_new(500000,48000,2000,0)==0, "invalid FFT accepted");
    require(dsp_process(99,8192,1,1)==-1, "invalid handle accepted");
    auto id=dsp_new(520834,48000,2048,0); require(id!=0,"creation failed");
    require(!dsp_tune(id,NAN,2700,1), "NaN accepted");
    require(!dsp_tune(id,260000,2700,1), "out-of-span tuning accepted");
    require(dsp_process(id,65537,1,1)==-1,"oversized input accepted");
    float wanted=rms(id,520834,1000); dsp_reset(id);
    float opposite=rms(id,520834,-1000); dsp_reset(id);
    float outside=rms(id,520834,9000); dsp_reset(id);
    float alias=rms(id,520834,52083.4+1000);
    std::cout << "RMS wanted=" << wanted << " opposite=" << opposite << " alias=" << alias << '\n';
    require(wanted>0.3,"wanted tone attenuated");
    require(opposite<wanted*0.03,"opposite sideband not rejected");
    require(outside<wanted*0.03,"out-of-passband channel not rejected");
    require(alias<wanted*0.03,"alias not rejected");
    require(dsp_tune(id,10000,2700,-1),"LSB retune failed");
    require(rms(id,520834,9000)>0.3,"LSB tone attenuated");
    dsp_free(id);
    for (auto frequency : {125000.0,-125000.0}) {
        id=dsp_new(500000,48000,2048,0); tone(id,500000,0,4096,frequency);
        dsp_process(id,4096,0,1);
        auto* spectrum=dsp_spectrum(id);
        auto peak=std::max_element(spectrum,spectrum+2048)-spectrum;
        require(peak==(frequency>0 ? 1536 : 512),"FFT bin wrong");
        require(spectrum[peak]>-5 && spectrum[peak]<-3,"FFT normalization wrong");
        dsp_free(id);
    }
    auto a=dsp_new(520834,48000,2048,0), b=dsp_new(520834,48000,2048,0);
    tone(a,520834,0,32768,1000); auto n=dsp_process(a,32768,1,1);
    std::vector<float> expected(dsp_audio(a),dsp_audio(a)+n), actual;
    unsigned start=0;
    for (auto count : {13U,101U,16000U,10000U,6654U}) {
        tone(b,520834,start,count,1000); start+=count;
        n=dsp_process(b,count,1,1); actual.insert(actual.end(),dsp_audio(b),dsp_audio(b)+n);
    }
    require(expected==actual,"packet boundaries changed PCM"); dsp_free(a); dsp_free(b);
    id=dsp_new(520834,48000,256,-72); unsigned input=0, output=0;
    while (input<5208340) {
        auto count=std::min(65536U,5208340-input);
        auto produced=dsp_process(id,count,1,0);
        require(produced>=0,"silence processing failed");
        require(std::all_of(dsp_audio(id),dsp_audio(id)+produced,
                           [](float value) { return value==0; }),"silence produced audio");
        output+=produced; input+=count;
    }
    std::cout << "10 seconds output samples=" << output << '\n';
    require(std::abs(static_cast<int>(output)-480000)<=2,"fractional rate conversion inaccurate");
    dsp_process(id,256,0,1);
    require(std::all_of(dsp_spectrum(id),dsp_spectrum(id)+256,
                       [](float value) { return std::isfinite(value) && value < -200; }),
            "silent FFT was not finite at its floor");
    std::fill_n(dsp_input(id),65536*2,static_cast<std::int8_t>(-128));
    auto produced=dsp_process(id,65536,1,1);
    require(produced>=0,"full-scale I/Q processing failed");
    require(std::all_of(dsp_audio(id),dsp_audio(id)+produced,
                       [](float value) { return std::isfinite(value) && std::abs(value)<=1; }),
            "full-scale I/Q produced invalid PCM");
    dsp_free(id);
    for (auto rate : {48000U,192000U,4000000U}) {
        id=dsp_new(rate,48000,256,0); require(id!=0,"supported rate rejected");
        unsigned total=0;
        for (unsigned start=0;start<rate;) {
            auto count=std::min(65536U,rate-start);
            auto produced=dsp_process(id,count,1,0);
            require(produced>=0,"supported rate processing failed");
            total+=produced;start+=count;
        }
        require(std::abs(static_cast<int>(total)-48000)<=2,"supported rate inaccurate");
        dsp_free(id);
    }
    for (int i=0;i<100;++i) { id=dsp_new(520834,48000,2048,0); require(id!=0,"leaked receiver"); dsp_reset(id); dsp_free(id); }
    std::cout << "Receiver tests passed\n";
}
