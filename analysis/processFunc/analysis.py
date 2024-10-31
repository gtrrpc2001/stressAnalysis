import numpy as np
from .process import ECGserialize
from scipy.signal import find_peaks
from scipy import signal
from scipy.interpolate import interp1d
from scipy.stats import zscore
import neurokit2 as nk


def npFloatToFloat(value):
    result = np.round(value, 2)
    return float(result)


async def analysis_data(user: dict, eq: str) -> dict:
    print(f"{eq} : analysis start")
    value = await ECGserialize(user, eq)

    ecg = np.array(value)
    ecg = (ecg - ecg.mean()) / ecg.std()

    v = np.linspace(0.5 * np.pi, 0.6 * np.pi, 5)
    peak_filter = np.sin(v)
    ecg_transformed = np.correlate(ecg, peak_filter, mode="same")

    rr_peaks, _ = find_peaks(ecg_transformed, distance=1000*(30/375))
    rr_ecg = np.diff(rr_peaks * 8)
    x_ecg = np.cumsum(rr_ecg) / 1000

    # fit function to the dataset
    f_ecg = interp1d(x_ecg, rr_ecg, kind='cubic', fill_value='extrapolate')

    # sample rate for interpolation
    fs = 1
    steps = 1 / fs

    # sample using the interpolation function
    xx_ecg = np.arange(0, np.max(x_ecg), steps)
    rr_interpolated_ecg = f_ecg(xx_ecg)

    # we have a few false peak detections, lets replace them with the data medium
    rr_ecg[np.abs(zscore(rr_ecg)) > 2] = np.median(rr_ecg)

    x_ecg = np.cumsum(rr_ecg)/1000
    f_ecg = interp1d(x_ecg, rr_ecg, kind='cubic', fill_value='extrapolate')

    xx_ecg = np.arange(0, np.max(x_ecg), steps)
    clean_rr_interpolated_ecg = f_ecg(xx_ecg)

    results = {}

    hr = 60000/clean_rr_interpolated_ecg

    results["eq"] = eq
    results["sDate"] = user[eq]["body"][0]["writetime"]
    results["eDate"] = user[eq]["body"][-1]["writetime"]
    results["timezone"] = user[eq]["body"][0]["timezone"]
    results['Mean RR (ms)'] = npFloatToFloat(np.mean(clean_rr_interpolated_ecg))
    results['STD RR/SDNN (ms)'] = npFloatToFloat(np.std(clean_rr_interpolated_ecg))
    results['Mean HR (beats/min)'] = npFloatToFloat(np.mean(hr))
    results['STD HR (beats/min)'] = npFloatToFloat(np.std(hr))
    results['Min HR (beats/min)'] = npFloatToFloat(np.min(hr))
    results['Max HR (beats/min)'] = npFloatToFloat(np.max(hr))

    RMSSD_diff = np.diff(clean_rr_interpolated_ecg)
    RMSSD_square = np.square(RMSSD_diff)
    RMSSD_mean = np.mean(RMSSD_square)
    RMSSD_sqrt = np.sqrt(RMSSD_mean)
    results['RMSSD (ms)'] = npFloatToFloat(RMSSD_sqrt)

    NN50_diff = np.diff(clean_rr_interpolated_ecg)
    NN50_abs = np.abs(NN50_diff)
    NN50_sum = np.sum(NN50_abs > 50)
    results['NN50'] = npFloatToFloat(NN50_sum)

    pNN50 = np.diff(clean_rr_interpolated_ecg)
    pNN50_abs = np.abs(pNN50)
    pNN50_upper_50 = pNN50_abs > 50
    pNN50_sum = np.sum(pNN50_upper_50)
    pNN50_sum_percent = 100 * pNN50_sum / len(clean_rr_interpolated_ecg)
    results['pNN50 (%)'] = npFloatToFloat(pNN50_sum_percent)

    apen, _ = nk.entropy_approximate(clean_rr_interpolated_ecg)
    results["apen"] = npFloatToFloat(apen)

    srd_diff = np.diff(clean_rr_interpolated_ecg)
    srd = np.abs(srd_diff)
    srd1_3 = srd[:int(len(srd)/3)].mean()
    srd2_3 = srd[int(len(srd)/3):].mean()
    results['srd'] = npFloatToFloat(srd1_3 / srd2_3)

    tsrd_diff = np.diff(srd)
    tsrd_sum = np.sum(tsrd_diff)
    results['tsrd'] = npFloatToFloat(tsrd_sum)

    fxx, pxx = signal.welch(x=clean_rr_interpolated_ecg, fs=fs, nperseg=256)

    cond_vlf = (fxx >= 0) & (fxx < 0.04)
    cond_lf = (fxx >= 0.04) & (fxx < 0.15)
    cond_hf = (fxx >= 0.15) & (fxx < 0.4)

    vlf = np.trapezoid(pxx[cond_vlf], fxx[cond_vlf])
    lf = np.trapezoid(pxx[cond_lf], fxx[cond_lf])
    hf = np.trapezoid(pxx[cond_hf], fxx[cond_hf])
    tp = vlf + lf + hf

    results['vlf (ms2)'] = npFloatToFloat(vlf)
    results['lf (ms2)'] = npFloatToFloat(lf)
    results['hf (ms2)'] = npFloatToFloat(hf)
    results['tp (ms2)'] = npFloatToFloat(tp)

    # process = psutil.Process()
    # mem_info = process.memory_info()
    # print(f"Memory Using : {mem_info.rss / (1024 ** 2):.2f} MiB")

    return results
