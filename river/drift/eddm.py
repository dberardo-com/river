import math

from river.base import DriftDetector


class EDDM(DriftDetector):
    r"""Early Drift Detection Method.

    EDDM (Early Drift Detection Method) aims to improve the
    detection rate of gradual concept drift in DDM, while keeping
    a good performance against abrupt concept drift.

    This method works by keeping track of the average distance
    between two errors instead of only the error rate. For this,
    it is necessary to keep track of the running average distance
    and the running standard deviation, as well as the maximum
    distance and the maximum standard deviation.

    The algorithm works similarly to the DDM algorithm, by keeping
    track of statistics only. It works with the running average
    distance ($p_i'$) and the running standard deviation ($s_i'$), as
    well as $p'_{max}$ and $s'_{max}$, which are the values of $p_i'$
    and $s_i'$ when $(p_i' + 2 * s_i')$ reaches its maximum.

    Like DDM, there are two threshold values that define the
    borderline between no change, warning zone, and drift detected.
    These are as follows:

    * if $(p_i' + 2 * s_i')/(p'_{max} + 2 * s'_{max}) < \alpha$ -> Warning zone

    * if $(p_i' + 2 * s_i')/(p'_{max} + 2 * s'_{max}) < \beta$ -> Change detected

    $\alpha$ and $\beta$ are set to 0.95 and 0.9, respectively.

    **Input:** `value` must be a binary signal, where 1 indicates error.
    For example, if a classifier's prediction $y'$ is right or wrong w.r.t the
    true target label $y$:

    - 0: Correct, $y=y'$

    - 1: Error, $y \neq y'$

    Parameters
    ----------
    min_num_instances
        The minimum required number of analyzed samples so change can be detected. This is used to
        avoid false detections during the early moments of the detector, when the weight of one
        sample is important.
    warning_level
        Warning level.
    out_control_level
        Out-control level.

    Examples
    --------
    >>> import random
    >>> from river import drift

    >>> rng = random.Random(42)
    >>> eddm = drift.EDDM()

    >>> # Simulate a data stream as a uniform distribution of 1's and 0's
    >>> data_stream = rng.choices([0, 1], k=2000)
    >>> # Change the data distribution from index 999 to 1500, simulating an
    >>> # increase in error rate (1 indicates error)
    >>> data_stream[999:1500] = [1] * 500

    >>> # Update drift detector and verify if change is detected
    >>> for i, val in enumerate(data_stream):
    ...     in_drift, in_warning = eddm.update(val)
    ...     if in_drift:
    ...         print(f"Change detected at index {i}, input value: {val}")
    Change detected at index 105, input value: 1
    Change detected at index 245, input value: 1
    Change detected at index 332, input value: 1
    Change detected at index 451, input value: 1
    Change detected at index 537, input value: 1
    Change detected at index 843, input value: 1
    Change detected at index 914, input value: 1
    Change detected at index 1015, input value: 1

    References
    ----------
    [^1]: Early Drift Detection Method. Manuel Baena-Garcia, Jose Del Campo-Avila, Raúl Fidalgo, Albert Bifet, Ricard Gavalda, Rafael Morales-Bueno. In Fourth International Workshop on Knowledge Discovery from Data Streams, 2006.

    """

    # FDDM_OUTCONTROL = 0.9
    # FDDM_WARNING = 0.95
    # FDDM_MIN_NUM_INSTANCES = 30

    def __init__(
        self,
        min_num_instances=30,
        warning_level=0.95,
        out_control_level=0.9,
    ):
        super().__init__()
        self.min_num_instances = min_num_instances
        self.warning = warning_level
        self.outcontrol = out_control_level
        self.m_num_errors = None
        self.m_min_num_errors = 30
        self.m_n = None
        self.m_d = None
        self.m_lastd = None
        self.m_mean = None
        self.m_std_temp = None
        self.m_m2s_max = None
        self.m_last_level = None
        self.estimation = None
        self.delay = None
        self.reset()

    def reset(self):
        """Reset the change detector."""
        super().reset()
        self.m_n = 1
        self.m_num_errors = 0
        self.m_d = 0
        self.m_lastd = 0
        self.m_mean = 0.0
        self.m_std_temp = 0.0
        self.m_m2s_max = 0.0
        self.estimation = 0.0

    def update(self, value) -> tuple:
        """Update the change detector with a single data point.

        Parameters
        ----------
        value
            This parameter indicates whether the last sample analyzed was correctly classified or
            not. 1 indicates an error (miss-classification).

        Returns
        -------
        A tuple (drift, warning) where its elements indicate if a drift or a warning is detected.

        """

        if self._in_concept_change:
            self.reset()

        self._in_concept_change = False

        self.m_n += 1

        if value == 1.0:
            self._in_warning_zone = False
            self.delay = 0
            self.m_num_errors += 1
            self.m_lastd = self.m_d
            self.m_d = self.m_n - 1
            distance = self.m_d - self.m_lastd
            old_mean = self.m_mean
            self.m_mean = (
                self.m_mean + (float(distance) - self.m_mean) / self.m_num_errors
            )
            self.estimation = self.m_mean
            self.m_std_temp += (distance - self.m_mean) * (distance - old_mean)
            std = math.sqrt(self.m_std_temp / self.m_num_errors)
            m2s = self.m_mean + 2 * std

            if self.m_n < self.min_num_instances:
                return self._in_concept_change, self._in_warning_zone

            if m2s > self.m_m2s_max:
                self.m_m2s_max = m2s
            else:
                p = m2s / self.m_m2s_max
                if (self.m_num_errors > self.m_min_num_errors) and (
                    p < self.outcontrol
                ):
                    self._in_concept_change = True

                elif (self.m_num_errors > self.m_min_num_errors) and (p < self.warning):
                    self._in_warning_zone = True

                else:
                    self._in_warning_zone = False

        return self._in_concept_change, self._in_warning_zone
