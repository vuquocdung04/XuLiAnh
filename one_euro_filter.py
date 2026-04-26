import math

class LowPassFilter:
    def __init__(self):
        self.y = None
        self.s = None

    def __call__(self, x, alpha):
        if self.s is None:
            s = x
        else:
            s = alpha * x + (1.0 - alpha) * self.s
        self.y = x
        self.s = s
        return s

def _smoothing_factor(t_e, cutoff):
    r = 2.0 * math.pi * cutoff * t_e
    return r / (r + 1.0)

class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta       = float(beta)
        self.d_cutoff   = float(d_cutoff)
        self.x_filter   = LowPassFilter()
        self.dx_filter  = LowPassFilter()
        self.last_time  = None

    def __call__(self, x, t):
        if self.last_time is None:
            self.last_time = t
            self.x_filter(x, 1.0)
            self.dx_filter(0.0, 1.0)
            return x

        t_e = t - self.last_time
        # [XỬ LÝ NGOẠI LỆ] Tránh chia cho 0 khi timestamp trùng hoặc camera drop frame. Thiếu: filter crash → pipeline dừng hoàn toàn.
        if t_e <= 0:
            t_e = 1e-6

        prev_x = self.x_filter.y if self.x_filter.y is not None else x
        dx = (x - prev_x) / t_e
        a_d = _smoothing_factor(t_e, self.d_cutoff)
        edx = self.dx_filter(dx, a_d)

        # [LỌC THÍCH NGHI] Cutoff động theo vận tốc: đứng yên → mượt (khử jitter), di chuyển nhanh → bám sát (giảm trễ). Thiếu: phải chọn cứng giữa "rung" hoặc "trễ".
        cutoff = self.min_cutoff + self.beta * abs(edx)
        a = _smoothing_factor(t_e, cutoff)

        result = self.x_filter(x, a)
        self.last_time = t
        return result

    def reset(self):
        self.x_filter  = LowPassFilter()
        self.dx_filter = LowPassFilter()
        self.last_time = None