"""Canadian Forest Fire Weather Index System (Van Wagner 1987), daily version.

Equations follow Van Wagner (1987) "Development and structure of the Canadian
Forest Fire Weather Index System", Forestry Technical Report 35, as implemented
in the reference R package cffdrs (Wang et al. 2017), including its latitude
adjustments for day-length factors (DMC) and day-length adjustments (DC).

Inputs are noon local standard time observations:
  T  air temperature (°C), H relative humidity (%), W 10 m wind speed (km/h),
  ro rainfall over the previous 24 h (mm).
"""
import math

ELL01 = [6.5, 7.5, 9, 12.8, 13.9, 13.9, 12.4, 10.9, 9.4, 8, 7, 6]
ELL02 = [7.9, 8.4, 8.9, 9.5, 9.9, 10.2, 10.1, 9.7, 9.1, 8.6, 8.1, 7.8]
ELL03 = [10.1, 9.6, 9.1, 8.5, 8.1, 7.8, 7.9, 8.3, 8.9, 9.4, 9.9, 10.2]
ELL04 = [11.5, 10.5, 9.2, 7.9, 6.8, 6.2, 6.5, 7.4, 8.7, 10, 11.2, 11.8]
FL01 = [-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5, 2.4, 0.4, -1.6, -1.6]
FL02 = [6.4, 5, 2.4, 0.4, -1.6, -1.6, -1.6, -1.6, -1.6, 0.9, 3.8, 5.8]


def ffmc(T, H, W, ro, Fo):
    H = min(H, 100.0)
    mo = 147.2 * (101.0 - Fo) / (59.5 + Fo)
    if ro > 0.5:
        rf = ro - 0.5
        if mo > 150.0:
            mo = (mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
                  + 0.0015 * (mo - 150.0) ** 2 * math.sqrt(rf))
        else:
            mo = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
        mo = min(mo, 250.0)
    ed = 0.942 * H ** 0.679 + 11.0 * math.exp((H - 100.0) / 10.0) + 0.18 * (21.1 - T) * (1.0 - math.exp(-0.115 * H))
    if mo > ed:
        ko = 0.424 * (1.0 - (H / 100.0) ** 1.7) + 0.0694 * math.sqrt(W) * (1.0 - (H / 100.0) ** 8)
        kd = ko * 0.581 * math.exp(0.0365 * T)
        m = ed + (mo - ed) * 10.0 ** (-kd)
    else:
        ew = 0.618 * H ** 0.753 + 10.0 * math.exp((H - 100.0) / 10.0) + 0.18 * (21.1 - T) * (1.0 - math.exp(-0.115 * H))
        if mo < ew:
            k1 = 0.424 * (1.0 - ((100.0 - H) / 100.0) ** 1.7) + 0.0694 * math.sqrt(W) * (1.0 - ((100.0 - H) / 100.0) ** 8)
            kw = k1 * 0.581 * math.exp(0.0365 * T)
            m = ew - (ew - mo) * 10.0 ** (-kw)
        else:
            m = mo
    F = 59.5 * (250.0 - m) / (147.2 + m)
    return max(0.0, min(F, 101.0))


def day_length_dmc(lat, mon):
    if lat > 30:
        return ELL01[mon - 1]
    if lat > 10:
        return ELL02[mon - 1]
    if lat > -10:
        return 9.0
    if lat > -30:
        return ELL03[mon - 1]
    return ELL04[mon - 1]


def day_length_dc(lat, mon):
    if lat > 20:
        return FL01[mon - 1]
    if lat <= -20:
        return FL02[mon - 1]
    return 1.4


def dmc(T, H, ro, Po, mon, lat):
    H = min(H, 100.0)
    if ro > 1.5:
        re = 0.92 * ro - 1.27
        mo = 20.0 + 280.0 / math.exp(0.023 * Po)
        if Po <= 33.0:
            b = 100.0 / (0.5 + 0.3 * Po)
        elif Po <= 65.0:
            b = 14.0 - 1.3 * math.log(Po)
        else:
            b = 6.2 * math.log(Po) - 17.2
        mr = mo + 1000.0 * re / (48.77 + b * re)
        pr = 244.72 - 43.43 * math.log(mr - 20.0)
        Po = max(pr, 0.0)
    rk = 0.0
    if T > -1.1:
        rk = 1.894 * (T + 1.1) * (100.0 - H) * day_length_dmc(lat, mon) * 1e-4
    return max(Po + rk, 0.0)


def dc(T, ro, Do, mon, lat):
    if ro > 2.8:
        rd = 0.83 * ro - 1.27
        Qo = 800.0 * math.exp(-Do / 400.0)
        Qr = Qo + 3.937 * rd
        Do = max(400.0 * math.log(800.0 / Qr), 0.0)
    t = max(T, -2.8)
    pe = max((0.36 * (t + 2.8) + day_length_dc(lat, mon)) / 2.0, 0.0)
    return Do + pe


def isi(W, F):
    fW = math.exp(0.05039 * W)
    m = 147.2 * (101.0 - F) / (59.5 + F)
    fF = 91.9 * math.exp(-0.1386 * m) * (1.0 + m ** 5.31 / 4.93e7)
    return 0.208 * fW * fF


def bui(P, D):
    if P == 0 and D == 0:
        return 0.0
    if P <= 0.4 * D:
        U = 0.8 * P * D / (P + 0.4 * D)
    else:
        U = P - (1.0 - 0.8 * D / (P + 0.4 * D)) * (0.92 + (0.0114 * P) ** 1.7)
    return max(U, 0.0)


def fwi(R, U):
    if U <= 80.0:
        fD = 0.626 * U ** 0.809 + 2.0
    else:
        fD = 1000.0 / (25.0 + 108.64 * math.exp(-0.023 * U))
    B = 0.1 * R * fD
    if B > 1.0:
        return math.exp(2.72 * (0.434 * math.log(B)) ** 0.647)
    return B


def step(state, T, H, W, ro, mon, lat):
    """One daily step. state = (FFMC, DMC, DC). Returns new state and full record."""
    F0, P0, D0 = state
    F = ffmc(T, H, W, ro, F0)
    P = dmc(T, H, ro, P0, mon, lat)
    D = dc(T, ro, D0, mon, lat)
    R = isi(W, F)
    U = bui(P, D)
    S = fwi(R, U)
    return (F, P, D), {"ffmc": F, "dmc": P, "dc": D, "isi": R, "bui": U, "fwi": S}


START = (85.0, 6.0, 15.0)  # standard Canadian start-up values
