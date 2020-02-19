# -*- coding: utf-8 -*-
#import IPython
import numpy as np
import pandas as pd
import pywt
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
import neurokit2 as nk
import pandas as pd

# outputs:
# - T peaks
# - P peaks
# func(ecg, sampling_rate):
# List[Dict[]]
#


# create ecg signal
def get_signal(filename=None, sampling_rate=2000):
    if filename is None:
        ecg = nk.ecg_simulate(
            duration=10, sampling_rate=sampling_rate, method="ecgsyn")
    else:
        ecg = np.array(pd.read_csv(filename))[:, 1]
    return ecg, sampling_rate


#ecg, sampling_rate = get_signal('ok_3000.csv', sampling_rate=3000)
ecg, sampling_rate = get_signal('good_4000.csv', sampling_rate=4000)
# ecg, sampling_rate = get_signal('bad_500.csv', sampling_rate=500)
# ecg, sampling_rate = get_signal('goodTbadP_1000.csv', sampling_rate=1000)

#ecg = nk.signal_smooth(ecg, size=sampling_rate*0.015)
# =============================================================================
# R Peaks
# =============================================================================
# warning: very ugly code ahead
scales = np.array([1, 2, 4, 8, 16, 32])
# first derivative of the Gaissian signal
cwtmatr, freqs = pywt.cwt(ecg, scales, 'gaus1', sampling_period=1.0/sampling_rate)

# For wt of scale 2^4
signal_4 = cwtmatr[4, :]
epsilon_4 = np.sqrt(np.mean(np.square(signal_4)))
peaks_4, _ = find_peaks(np.abs(signal_4), height=epsilon_4)
# plt.plot(signal_4)
#plt.scatter(peaks_4, signal_4[peaks_4], c='y')

# For wt of scale 2^3
signal_3 = cwtmatr[3, :]
epsilon_3 = np.sqrt(np.mean(np.square(signal_3)))
peaks_3, _ = find_peaks(np.abs(signal_3), height=epsilon_3)
# keep only peaks_3 that are nearest to peaks_4
peaks_3_keep = np.zeros_like(peaks_4)
for i in range(len(peaks_4)):
    peaks_distance = abs(peaks_4[i] - peaks_3)
    peaks_3_keep[i] = peaks_3[np.argmin(peaks_distance)]
# plt.plot(signal_3)
#plt.scatter(peaks_3_keep, signal_3[peaks_3_keep], c='y')

# For wt of scale 2^2
signal_2 = cwtmatr[2, :]
epsilon_2 = np.sqrt(np.mean(np.square(signal_2)))
peaks_2, _ = find_peaks(np.abs(signal_2), height=epsilon_2)
# keep only peaks_2 that are nearest to peaks_3
peaks_2_keep = np.zeros_like(peaks_4)
for i in range(len(peaks_4)):
    peaks_distance = abs(peaks_3_keep[i] - peaks_2)
    peaks_2_keep[i] = peaks_2[np.argmin(peaks_distance)]
# plt.plot(signal_2)
#plt.scatter(peaks_2_keep, signal_2[peaks_2_keep], c='y')

# For wt of scale 2^1
signal_1 = cwtmatr[1, :]
epsilon_1 = np.sqrt(np.mean(np.square(signal_1)))
peaks_1, _ = find_peaks(np.abs(signal_1), height=epsilon_1)
# keep only peaks_1 that are nearest to peaks_2
peaks_1_keep = np.zeros_like(peaks_4)
for i in range(len(peaks_4)):
    peaks_distance = abs(peaks_2_keep[i] - peaks_1)
    peaks_1_keep[i] = peaks_1[np.argmin(peaks_distance)]
# plt.plot(signal_1)
#plt.scatter(peaks_1_keep, signal_1[peaks_1_keep], c='y')

# find R peaks
max_R_peak_dist = int(0.1 * sampling_rate)
rpeaks = []
for index_cur, index_next in zip(peaks_1_keep[:-1], peaks_1_keep[1:]):
    # limit 1
    correct_sign = signal_1[index_cur] < 0 and signal_1[index_next] > 0
    near = (index_next - index_cur) < max_R_peak_dist  # limit 2
    if near and correct_sign:
        rpeaks.append(nk.signal_zerocrossings(
            signal_1[index_cur:index_next])[0] + index_cur)
nk.events_plot(rpeaks, ecg)
plt.show()

# Delinate QRS (onset and offset) using 2^2 WT
qrs_half_width = int(0.1*sampling_rate)  # NEED TO CHECK
qrs_onsets = []
qrs_offsets = []
for index_r_peak in rpeaks:
    # find onset
    search_window = cwtmatr[2, index_r_peak - qrs_half_width: index_r_peak]
    prominence = 0.20*max(search_window)
    height = 0.0
    peaks, peaks_data = find_peaks(search_window, height=height, prominence=prominence)
    # The last peak is nfirst in (Martinez, 2004)
    # nk.events_plot(peaks, search_window); plt.show()
    nfirst = peaks[-1] + index_r_peak - qrs_half_width
    leftbase = peaks_data['left_bases'][-1] + index_r_peak - qrs_half_width
    epsilon_qrson = 0.5 * peaks_data['peak_heights'][0]
    candidate_onsets = np.where(cwtmatr[2, nfirst-100: nfirst] < epsilon_qrson)[0] + nfirst - 100
    candidate_onsets = candidate_onsets.tolist() + [leftbase]
    qrs_onsets.append(max(candidate_onsets))

    # find offset
    search_window = - cwtmatr[2, index_r_peak: index_r_peak + qrs_half_width]
    prominence = 0.5*max(search_window)
    peaks, peaks_data = find_peaks(search_window, height=height, prominence=prominence)
    if len(peaks) == 0:
        print("Fail to find rs at index: %d", index_r_peak)
        continue
    nlast = peaks[0] + index_r_peak
    rightbase = peaks_data['right_bases'][0] + index_r_peak
    epsilon_qrsoff = 0.3 * peaks_data['peak_heights'][0]
    candidate_offsets = np.where((-cwtmatr[2, nlast: nlast + 100]) < epsilon_qrsoff)[0] + nlast
    candidate_offsets = candidate_offsets.tolist() + [rightbase]
    qrs_offsets.append(min(candidate_offsets))


nk.events_plot([qrs_onsets, qrs_offsets], ecg)
plt.plot(cwtmatr[2], '--')
plt.show()
# =============================================================================
# T P Peaks
# =============================================================================

# clean the signal for T P peaks
def my_cleaning(ecg_signal, sampling_rate, lowpass=False, smooth=False):
    detrended = nk.signal_detrend(ecg_signal, order=1)
    if lowpass:
        cleaned = nk.signal_filter(detrended, sampling_rate=sampling_rate, lowcut=2, highcut=12, method='butterworth')
        return cleaned
    elif smooth:
        ecg_smooth = nk.signal_smooth(ecg, size=sampling_rate*0.015)
        return ecg_smooth
    return detrended

qrs_duration = 0.1
max_search_duration = 0.05
show_significant_peaks = True


ecg_clean = my_cleaning(ecg, sampling_rate=sampling_rate, lowpass=True)
# first derivative of the Gaissian signal
scales = np.array([1, 2, 4, 8, 16, 32])
cwtmatr, freqs = pywt.cwt(ecg_clean, scales, 'gaus1', sampling_period=1.0/sampling_rate)

# find T P peaks
#max_wv_peak_dist = int(0.2 * sampling_rate)

def find_tppeaks(keep_tp):
    tppeaks = []
    for index_cur, index_next in zip(keep_tp[:-1], keep_tp[1:]):
        # limit 1
        correct_sign = cwtmatr[4, :][index_cur] < 0 and cwtmatr[4, :][index_next] > 0
    #    near = (index_next - index_cur) < max_wv_peak_dist #limit 2
    #    if near and correct_sign:
        if correct_sign:
            index_zero_cr = nk.signal_zerocrossings(
                cwtmatr[4, :][index_cur:index_next])[0] + index_cur
            nb_idx = int(max_search_duration * sampling_rate)
            index_max = np.argmax(ecg[index_zero_cr - nb_idx: index_zero_cr + nb_idx]) + (index_zero_cr - nb_idx)
            tppeaks.append(index_max)
    return tppeaks

# find 2^4 peaks between R peaks
search_window_offset = int(0.9 * qrs_duration * sampling_rate / 2)
#min_RT_duration = 0.3
#min_PR_duration = 0.15

significant_peaks_groups = []
tppeaks_pairs = []
tppeaks = []
for i in range(len(rpeaks)-1):
    start = rpeaks[i] + search_window_offset
    end = rpeaks[i + 1] - search_window_offset
    search_window = cwtmatr[4, start:end]
    height = 0.25*np.sqrt(np.mean(np.square(search_window)))
    peaks_tp, heights_tp = find_peaks(np.abs(search_window), height=height)
    peaks_tp = peaks_tp + rpeaks[i] + search_window_offset
    threshold1 = 0.125*max(search_window)
    significant_index = []
    significant_index = [j for j in range(len(peaks_tp)) if
                          heights_tp["peak_heights"][j] > threshold1]
    # nk.events_plot(significant_index, search_window); plt.show()
    significant_peaks_tp = []
    for index in significant_index:
        significant_peaks_tp.append(peaks_tp[index])
    significant_peaks_groups.append(find_tppeaks(significant_peaks_tp))

    # tppeaks.extend(significant_peaks_tp)
    # tppeaks_pairs.append(find_tppeaks_pair(significant_peaks_tp))

if show_significant_peaks:
    nk.events_plot(np.concatenate(significant_peaks_groups), ecg)
    plt.plot(cwtmatr[4, :], label="4")
    plt.plot(cwtmatr[3, :], label="3")
    plt.plot(cwtmatr[2, :], label="2")
    plt.plot(cwtmatr[1, :], label="1")
    plt.legend()
    plt.show()

tpeaks, ppeaks = zip(*[(g[0], g[-1]) for g in significant_peaks_groups])
nk.events_plot([tpeaks, ppeaks, rpeaks], ecg)
# nk.events_plot(tppeaks, ecg)
# plt.plot(cwtmatr[4])
plt.show()

# delineate T P peaks
#tpeaks = []
#ppeaks = []
#for i in range(len(tppeaks)):
#    rpeaks_distance = abs(tppeaks[i] - rpeaks)
#    rpeaks_closest = rpeaks[np.argmin(rpeaks_distance)]
#    if (rpeaks_closest - tppeaks[i]) > 0:
#        ppeaks.append(tppeaks[i])
#    elif (rpeaks_closest - tppeaks[i]) < 0:
#        tpeaks.append(tppeaks[i])

    # if len(ppeaks) > (int(np.argmin(rpeaks_closest)) + 1):


# Delinate P peaks (onset and offset) using 2^4 WT
p_half_width = int(0.1*sampling_rate)  # NEED TO CHECK
p_onsets = []
p_offsets = []
left_base=[]
for index_p_peak in ppeaks:
    # find onset
    search_window = - cwtmatr[4, index_p_peak - p_half_width: index_p_peak]
    prominence = 0.50*max(search_window)
    height = 0.0
    peaks, peaks_data = find_peaks(search_window, height=height, prominence=prominence)
    # The last peak is nfirst in (Martinez, 2004)
    # nk.events_plot(peaks, search_window); plt.show()
    nfirst = peaks[-1] + index_p_peak - p_half_width
    leftbase = peaks_data['left_bases'][-1] + index_p_peak - p_half_width
    left_base.append(leftbase)
    epsilon_pon = 0.5 * peaks_data['peak_heights'][0]
    candidate_onsets = np.where(-cwtmatr[4, nfirst-100: nfirst] < epsilon_pon)[0] + nfirst - 100
    candidate_onsets = candidate_onsets.tolist() + [leftbase]
    p_onsets.append(max(candidate_onsets))

    # find offset
    search_window =  cwtmatr[4, index_p_peak: index_p_peak + p_half_width]
    prominence = 0.5*max(search_window)
    peaks, peaks_data = find_peaks(search_window, height=height, prominence=prominence)
    if len(peaks) == 0:
        print("Fail to find rs at index: %d", index_p_peak)
        continue
    nlast = peaks[0] + index_p_peak
    rightbase = peaks_data['right_bases'][0] + index_p_peak
    epsilon_poff = 0.9 * peaks_data['peak_heights'][0]
    candidate_offsets = np.where((cwtmatr[4, nlast: nlast + 100]) < epsilon_poff)[0] + nlast
    candidate_offsets = candidate_offsets.tolist() + [rightbase]
    p_offsets.append(min(candidate_offsets))

nk.events_plot([p_onsets, p_offsets], ecg)
nk.events_plot([left_base, ppeaks], ecg)
plt.plot(cwtmatr[4, :])
