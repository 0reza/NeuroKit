# -*- coding: utf-8 -*-
import pandas as pd

from .ecg_eventrelated import ecg_eventrelated
from .ecg_intervalrelated import ecg_intervalrelated


def ecg_analyze(data, sampling_rate=1000, method="auto"):
    """Performs ECG analysis on either epochs (event-related analysis) or on longer periods of data such as resting-
    state data.

    Parameters
    ----------
    data : Union[dict, pd.DataFrame]
        A dictionary of epochs, containing one DataFrame per epoch, usually obtained via `epochs_create()`,
        or a DataFrame containing all epochs, usually obtained via `epochs_to_df()`. Can also take a
        DataFrame of processed signals from a longer period of data, typically generated by `ecg_process()`
        or `bio_process()`. Can also take a dict containing sets of separate periods of data.
    sampling_rate : int
        The sampling frequency of the signal (in Hz, i.e., samples/second).
        Defaults to 1000Hz.
    method : str
        Can be one of 'event-related' for event-related analysis on epochs, or 'interval-related' for
        analysis on longer periods of data. Defaults to 'auto' where the right method will be chosen
        based on the mean duration of the data ('event-related' for duration under 10s).

    Returns
    -------
    DataFrame
        A dataframe containing the analyzed ECG features. If
        event-related analysis is conducted, each epoch is indicated
        by the `Label` column. See `ecg_eventrelated()` and
        `ecg_intervalrelated()` docstrings for details.

    See Also
    --------
    bio_process, ecg_process, epochs_create, ecg_eventrelated, ecg_intervalrelated

    Examples
    ----------
    >>> import neurokit2 as nk
    >>>
    >>> # Example 1: Download the data for event-related analysis
    >>> data = nk.data("bio_eventrelated_100hz")
    >>>
    >>> # Process the data for event-related analysis
    >>> df, info = nk.bio_process(ecg=data["ECG"], sampling_rate=100)
    >>> events = nk.events_find(data["Photosensor"], threshold_keep='below',
    ...                         event_conditions=["Negative", "Neutral",
    ...                                           "Neutral", "Negative"])
    >>> epochs = nk.epochs_create(df, events, sampling_rate=100, epochs_start=-0.1, epochs_end=1.9)
    >>>
    >>> # Analyze
    >>> nk.ecg_analyze(epochs, sampling_rate=100) #doctest: +ELLIPSIS
      Label Condition  ...  ECG_Phase_Completion_Ventricular  ECG_Quality_Mean
    1     1  Negative  ...                               ...              ...
    2     2   Neutral  ...                               ...              ...
    3     3   Neutral  ...                               ...              ...
    4     4  Negative  ...                               ...              ...

    [4 rows x 17 columns]
    >>>
    >>> # Example 2: Download the resting-state data
    >>> data = nk.data("bio_resting_5min_100hz")
    >>>
    >>> # Process the data
    >>> df, info = nk.ecg_process(data["ECG"], sampling_rate=100)
    >>>
    >>> # Analyze
    >>> nk.ecg_analyze(df, sampling_rate=100) #doctest: +ELLIPSIS
      ECG_Rate_Mean  HRV_RMSSD  ...
    0 ...

    [1 rows x 37 columns]

    """
    method = method.lower()

    # Event-related analysis
    if method in ["event-related", "event", "epoch"]:
        # Sanity checks
        if isinstance(data, dict):
            for i in data:
                colnames = data[i].columns.values
        elif isinstance(data, pd.DataFrame):
            colnames = data.columns.values

        if len([i for i in colnames if "Label" in i]) == 0:
            raise ValueError(
                "NeuroKit error: ecg_analyze(): Wrong input or method," "we couldn't extract epochs features."
            )
        else:
            features = ecg_eventrelated(data)

    # Interval-related analysis
    elif method in ["interval-related", "interval", "resting-state"]:
        features = ecg_intervalrelated(data, sampling_rate=sampling_rate)

    # Auto
    elif method in ["auto"]:

        if isinstance(data, dict):
            for i in data:
                duration = len(data[i]) / sampling_rate
            if duration >= 10:
                features = ecg_intervalrelated(data, sampling_rate=sampling_rate)
            else:
                features = ecg_eventrelated(data)

        if isinstance(data, pd.DataFrame):
            if "Label" in data.columns:
                epoch_len = data["Label"].value_counts()[0]
                duration = epoch_len / sampling_rate
            else:
                duration = len(data) / sampling_rate
            if duration >= 10:
                features = ecg_intervalrelated(data, sampling_rate=sampling_rate)
            else:
                features = ecg_eventrelated(data)

    return features