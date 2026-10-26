# -*- coding: utf-8 -*-
"""
CATATAN KEUANGAN v2 (Kivy) - tampilan akuntan, dashboard interaktif, tema terang/gelap.

Isi: Beranda (dashboard), Transaksi (Daftar & Buku Kas), Hutang/Piutang, Tabungan,
     Anggaran, Laporan (Laba Rugi, Neraca, Grafik), Ekspor/Backup.
Data memakai database yang sama dengan versi sebelumnya (keuangan.db).
"""
import os
import re
import csv
import io
import math
import shutil
import sqlite3
import calendar
from datetime import date, datetime, timedelta

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse, Line, Mesh
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hx, platform

Window.softinput_mode = "below_target"

# ----------------------------------------------------------------------
# TEMA (terang / gelap)
# ----------------------------------------------------------------------
TEMA = {
    "terang": dict(BG="#EEF2F8", CARD="#FFFFFF", TEKS="#0B1B33", ABU="#64748B", FIELD="#E8EDF5",
                   GARIS="#DCE3EE", PRIMER="#12437A", HDR1="#0A2342", HDR2="#16457C",
                   HERO1="#0A2342", HERO2="#1F6FB5", AKSEN="#C99A2E", HIJAU="#059669",
                   MERAH="#DC2626", ORANYE="#D97706", BIRU="#0284C7", TOSCA="#0D9488", UNGU="#7C3AED"),
    "gelap": dict(BG="#0A1120", CARD="#131D31", TEKS="#E6ECF5", ABU="#8D9DB5", FIELD="#1B2842",
                  GARIS="#26354F", PRIMER="#3B82F6", HDR1="#0C1A33", HDR2="#14315C",
                  HERO1="#12315E", HERO2="#1E6FA8", AKSEN="#F5C451", HIJAU="#34D399",
                  MERAH="#F87171", ORANYE="#FBBF24", BIRU="#38BDF8", TOSCA="#2DD4BF", UNGU="#A78BFA"),
}
TEMA_AKTIF = "terang"
PUTIH = (1, 1, 1, 1)
PALET = []


def pasang_tema(nama):
    global TEMA_AKTIF, PALET
    TEMA_AKTIF = nama
    for k, v in TEMA[nama].items():
        globals()["C_" + k] = hx(v)
    PALET = [hx("#2563EB"), C_TOSCA, C_AKSEN, C_MERAH, C_UNGU, C_BIRU, C_ORANYE, C_HIJAU]
    Window.clearcolor = C_BG


pasang_tema("terang")

KAT_MASUK = ["Gaji", "Bonus", "Usaha", "Hadiah", "Investasi", "Terima Piutang", "Tarik Tabungan", "Lainnya"]
KAT_KELUAR = ["Makan & Minum", "Transportasi", "Belanja", "Tagihan", "Pulsa & Internet",
              "Kesehatan", "Pendidikan", "Hiburan", "Sedekah", "Rumah", "Tabungan",
              "Bayar Hutang", "Lainnya"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
PERIODE = [("bulan", "Bulan Ini"), ("3bln", "3 Bulan"), ("tahun", "Tahun Ini"), ("semua", "Semua")]


def tint(c, a=0.12):
    b = C_CARD
    return (b[0] * (1 - a) + c[0] * a, b[1] * (1 - a) + c[1] * a, b[2] * (1 - a) + c[2] * a, 1)


def fg_on(c):
    lum = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return hx("#0B1B33") if lum > 0.62 else PUTIH


def warna_kat(nama):
    return PALET[sum(ord(ch) for ch in nama) % len(PALET)]


_grad_cache = {}


def gradient(c1, c2):
    key = (tuple(c1), tuple(c2))
    if key not in _grad_cache:
        tex = Texture.create(size=(2, 1), colorfmt="rgba")
        buf = bytes([int(x * 255) for x in (list(c1) + list(c2))])
        tex.blit_buffer(buf, colorfmt="rgba", bufferfmt="ubyte")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
        _grad_cache[key] = tex
    return _grad_cache[key]


# ----------------------------------------------------------------------
# FUNGSI BANTU
# ----------------------------------------------------------------------
def rp(n):
    n = float(n or 0)
    s = "{:,.0f}".format(abs(n)).replace(",", ".")
    return ("-" if n < 0 else "") + "Rp " + s


def angka(n):
    n = float(n or 0)
    return ("-" if n < 0 else "") + "{:,.0f}".format(abs(n)).replace(",", ".")


def parse_uang(s):
    a = re.sub(r"\D", "", str(s))
    if not a or int(a) <= 0:
        raise ValueError("Jumlah harus berupa angka lebih dari 0.")
    return float(a)


def parse_uang_opsional(s):
    return parse_uang(s) if str(s).strip() else 0.0


def fmt_tgl(iso, kosong="Belum diatur"):
    if not iso:
        return kosong
    d = datetime.strptime(iso, "%Y-%m-%d").date()
    return "%d %s %d" % (d.day, BULAN[d.month - 1], d.year)


def bulan_label(d):
    return "%s %d" % (BULAN[d.month - 1], d.year)


def fmt_angka(s):
    d = re.sub(r"\D", "", str(s))
    return "{:,}".format(int(d)).replace(",", ".") if d else ""


def awal_bulan(d, n=0):
    m = d.month - 1 + n
    return date(d.year + m // 12, m % 12 + 1, 1)


def akhir_bulan(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def rentang(kode):
    t = date.today()
    if kode == "bulan":
        a, b = awal_bulan(t), akhir_bulan(t)
        pa = awal_bulan(t, -1)
        pb = akhir_bulan(pa)
    elif kode == "3bln":
        a, b = awal_bulan(t, -2), akhir_bulan(t)
        pa, pb = awal_bulan(t, -5), a - timedelta(days=1)
    elif kode == "tahun":
        a, b = date(t.year, 1, 1), date(t.year, 12, 31)
        pa, pb = date(t.year - 1, 1, 1), date(t.year - 1, 12, 31)
    else:
        return "0000-01-01", "9999-12-31", None, None
    return a.isoformat(), b.isoformat(), pa.isoformat(), pb.isoformat()


def delta(now, prev, naik_baik=True):
    if prev is None:
        return "", C_ABU
    if prev == 0 and now == 0:
        return "tidak ada perubahan", C_ABU
    if prev == 0:
        return "tanpa pembanding", C_ABU
    p = (now - prev) / abs(prev) * 100
    baik = (p >= 0) == naik_baik
    return "%+.0f%% vs periode lalu" % p, (C_HIJAU if baik else C_MERAH)


# ----------------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS transaksi(
    id INTEGER PRIMARY KEY AUTOINCREMENT, tipe TEXT, tanggal TEXT,
    kategori TEXT, jumlah REAL, catatan TEXT);
CREATE TABLE IF NOT EXISTS hutang(
    id INTEGER PRIMARY KEY AUTOINCREMENT, jenis TEXT, nama TEXT,
    jumlah REAL, terbayar REAL DEFAULT 0, jatuh_tempo TEXT, catatan TEXT);
CREATE TABLE IF NOT EXISTS tabungan(
    id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, target REAL,
    terkumpul REAL DEFAULT 0, tenggat TEXT, catatan TEXT);
CREATE TABLE IF NOT EXISTS anggaran(
    kategori TEXT PRIMARY KEY, batas REAL);
CREATE TABLE IF NOT EXISTS pengaturan(
    k TEXT PRIMARY KEY, v TEXT);
"""


class DB:
    def __init__(self, path):
        self.path = path
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SCHEMA)
        self.c.commit()

    def q(self, sql, a=()):
        return self.c.execute(sql, a).fetchall()

    def x(self, sql, a=()):
        cur = self.c.execute(sql, a)
        self.c.commit()
        return cur.lastrowid

    def val(self, sql, a=()):
        r = self.c.execute(sql, a).fetchone()
        return (r[0] or 0) if r else 0

    def get(self, k, default=""):
        r = self.c.execute("SELECT v FROM pengaturan WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    def put(self, k, v):
        self.x("INSERT OR REPLACE INTO pengaturan(k,v) VALUES(?,?)", (k, str(v)))


# ----------------------------------------------------------------------
# WIDGET DASAR
# ----------------------------------------------------------------------
class Lbl(Label):
    """Label rata kiri, teks membungkus & tinggi menyesuaikan."""

    def __init__(self, text="", size=14, warna=None, bold=False, rata="left", **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(text=text, font_size=sp(size), color=warna or C_TEKS,
                         bold=bold, halign=rata, valign="middle", **kw)
        self.bind(width=self._w, texture_size=self._t)

    def _w(self, *a):
        self.text_size = (self.width, None)

    def _t(self, *a):
        self.height = max(self.texture_size[1], dp(16))


class Angka(Lbl):
    """Angka yang berhitung naik (count-up)."""
    nilai = NumericProperty(0)

    def __init__(self, target=0, size=20, warna=None, bold=True, fmt=None, animasi=True, **kw):
        super().__init__("", size, warna, bold, **kw)
        self._fmt = fmt or rp
        self.bind(nilai=self._ubah)
        if animasi:
            self.text = self._fmt(0)
            Animation(nilai=target, d=0.8, t="out_cubic").start(self)
        else:
            self.nilai = target
            self.text = self._fmt(target)

    def _ubah(self, *a):
        self.text = self._fmt(self.nilai)


class Kolom(BoxLayout):
    def __init__(self, **kw):
        kw.setdefault("orientation", "vertical")
        kw.setdefault("size_hint_y", None)
        super().__init__(**kw)
        self.bind(minimum_height=self.setter("height"))


class Lapisan(BoxLayout):
    def __init__(self, warna=None, garis=False, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            Color(*(warna or C_BG))
            self._r = Rectangle()
            if garis:
                Color(*C_GARIS)
                self._g = Rectangle()
        self._garis = garis
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        if self._garis:
            self._g.pos = (self.x, self.top - dp(1))
            self._g.size = (self.width, dp(1))


class Kartu(Kolom):
    def __init__(self, warna=None, grad=None, pad=14, radius=16, shadow=True, garis=True, **kw):
        if "padding" not in kw:
            kw["padding"] = [dp(p) for p in pad] if isinstance(pad, (list, tuple)) else dp(pad)
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        rad = list(radius) if isinstance(radius, (list, tuple)) else [dp(radius)]
        self._sh = self._bd = None
        with self.canvas.before:
            if shadow and TEMA_AKTIF == "terang":
                Color(0.05, 0.1, 0.25, 0.06)
                self._sh = RoundedRectangle(radius=rad)
            if garis:
                Color(*C_GARIS)
                self._bd = RoundedRectangle(radius=rad)
            if grad:
                Color(1, 1, 1, 1)
                self._bg = RoundedRectangle(radius=rad, texture=gradient(*grad))
            else:
                Color(*(warna or C_CARD))
                self._bg = RoundedRectangle(radius=rad)
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        if self._sh is not None:
            self._sh.pos = (self.x, self.y - dp(2))
            self._sh.size = self.size
        if self._bd is not None:
            self._bd.pos = (self.x - 1, self.y - 1)
            self._bd.size = (self.width + 2, self.height + 2)
        self._bg.pos = self.pos
        self._bg.size = self.size


class KartuTap(ButtonBehavior, Kartu):
    pass


class Tombol(ButtonBehavior, Label):
    def __init__(self, text="", warna=None, fg=None, kecil=False, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(36 if kecil else 50))
        self.warna = warna or C_PRIMER
        super().__init__(text=text, bold=True, font_size=sp(12 if kecil else 15),
                         color=fg or fg_on(self.warna), **kw)
        with self.canvas.before:
            self._c = Color(*self.warna)
            self._r = RoundedRectangle(radius=[dp(10 if kecil else 14)])
        self.bind(pos=self._u, size=self._u, state=self._s)

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size

    def _s(self, *a):
        w = self.warna
        self._c.rgba = (w[0] * 0.8, w[1] * 0.8, w[2] * 0.8, w[3]) if self.state == "down" else w


class Fab(ButtonBehavior, Label):
    def __init__(self, **kw):
        super().__init__(text="+", font_size=sp(34), bold=True, color=hx("#0A2342"),
                         size_hint=(None, None), size=(dp(58), dp(58)), **kw)
        with self.canvas.before:
            Color(0, 0, 0, 0.22)
            self._s = Ellipse()
            self._c = Color(*C_AKSEN)
            self._e = Ellipse()
        self.bind(pos=self._u, size=self._u, state=self._st)

    def _u(self, *a):
        self._s.pos = (self.x, self.y - dp(3))
        self._s.size = self.size
        self._e.pos = self.pos
        self._e.size = self.size

    def _st(self, *a):
        a = C_AKSEN
        self._c.rgba = (a[0] * 0.8, a[1] * 0.8, a[2] * 0.8, 1) if self.state == "down" else a


class Entry(BoxLayout):
    text = StringProperty("")

    def __init__(self, text="", hint_text="", input_type="text", **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(50))
        super().__init__(padding=[dp(14), 0], **kw)
        self.ti = TextInput(text=text, hint_text=hint_text, input_type=input_type, multiline=False,
                            font_size=sp(16), padding=[0, dp(15), 0, dp(10)],
                            background_normal="", background_active="", background_color=(0, 0, 0, 0),
                            foreground_color=C_TEKS, cursor_color=C_PRIMER,
                            hint_text_color=(C_ABU[0], C_ABU[1], C_ABU[2], 0.7),
                            selection_color=(C_PRIMER[0], C_PRIMER[1], C_PRIMER[2], 0.3))
        self.text = text
        self.ti.bind(text=self._dari_ti)
        self.bind(text=self._ke_ti)
        self.add_widget(self.ti)
        with self.canvas.before:
            Color(*C_FIELD)
            self._r = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._u, size=self._u)

    def _dari_ti(self, inst, v):
        if self.text != v:
            self.text = v

    def _ke_ti(self, inst, v):
        if self.ti.text != v:
            self.ti.text = v

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class UangEntry(Entry):
    def __init__(self, **kw):
        kw.setdefault("input_type", "number")
        kw.setdefault("hint_text", "Rp 0")
        super().__init__(**kw)
        self.bind(text=self._fmt)
        self._fmt()

    def _fmt(self, *a):
        f = fmt_angka(self.text[:20])
        if f != self.text:
            self.text = f
            Clock.schedule_once(lambda dt: setattr(self.ti, "cursor", (len(f), 0)), 0)


class Opt(SpinnerOption):
    def __init__(self, **kw):
        super().__init__(background_normal="", background_down="", background_color=C_CARD,
                         color=C_TEKS, font_size=sp(15), size_hint_y=None, height=dp(46), **kw)


class Pilih(Spinner):
    def __init__(self, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(50))
        super().__init__(option_cls=Opt, background_normal="", background_down="",
                         background_color=(0, 0, 0, 0), color=C_TEKS, font_size=sp(15), **kw)
        with self.canvas.before:
            Color(*C_FIELD)
            self._r = RoundedRectangle(radius=[dp(12)])
        self.bind(pos=self._u, size=self._u)
        try:
            self._dropdown.max_height = dp(300)
        except Exception:
            pass

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class Baris(BoxLayout):
    def __init__(self, kiri, kanan, wk=None, size=14, bold_kiri=False, bold_kanan=True, wkiri=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(26), spacing=dp(8), **kw)
        self.k = Lbl(kiri, size, wkiri, bold_kiri, size_hint_y=1)
        self.r = Label(text=kanan, font_size=sp(size), color=wk or C_TEKS, bold=bold_kanan,
                       size_hint=(None, 1))
        self.r.bind(texture_size=lambda i, v: setattr(i, "width", v[0] + dp(2)))
        self.k.bind(texture_size=lambda i, v: setattr(self, "height", max(v[1] + dp(8), dp(26))))
        self.add_widget(self.k)
        self.add_widget(self.r)


class Garis(Widget):
    def __init__(self, tebal=1, **kw):
        super().__init__(size_hint_y=None, height=dp(tebal), **kw)
        with self.canvas:
            Color(*C_GARIS)
            self._r = Rectangle()
        self.bind(pos=lambda *a: setattr(self._r, "pos", self.pos),
                  size=lambda *a: setattr(self._r, "size", self.size))


class Bar(Widget):
    pct = NumericProperty(0)

    def __init__(self, target=0, warna=None, animasi=True, **kw):
        super().__init__(size_hint_y=None, height=dp(10), **kw)
        t = max(0.0, min(float(target), 1.0))
        with self.canvas:
            Color(*C_FIELD)
            self._t = RoundedRectangle(radius=[dp(5)])
            Color(*(warna or C_PRIMER))
            self._f = RoundedRectangle(radius=[dp(5)])
        self.bind(pos=self._u, size=self._u, pct=self._u)
        if animasi:
            Animation(pct=t, d=0.7, t="out_cubic").start(self)
        else:
            self.pct = t

    def _u(self, *a):
        self._t.pos = self.pos
        self._t.size = self.size
        self._f.pos = self.pos
        w = self.width * self.pct
        self._f.size = (max(w, dp(10)) if self.pct > 0.001 else 0, self.height)


class Avatar(Label):
    def __init__(self, teks, warna, **kw):
        super().__init__(text=(teks[:1] or "?").upper(), bold=True, font_size=sp(16), color=PUTIH,
                         size_hint=(None, None), size=(dp(40), dp(40)), **kw)
        with self.canvas.before:
            Color(*warna)
            self._e = Ellipse()
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._e.pos = self.pos
        self._e.size = self.size


class Dot(Widget):
    def __init__(self, warna, **kw):
        super().__init__(size_hint=(None, None), size=(dp(12), dp(12)), **kw)
        with self.canvas:
            Color(*warna)
            self._e = RoundedRectangle(radius=[dp(3)], pos=self.pos, size=self.size)
        self.bind(pos=lambda *a: setattr(self._e, "pos", self.pos),
                  size=lambda *a: setattr(self._e, "size", self.size))


class Header(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(68),
                         padding=[dp(14), dp(8), dp(12), dp(10)], spacing=dp(10), **kw)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._r = Rectangle(texture=gradient(C_HDR1, C_HDR2))
            Color(*C_AKSEN)
            self._g = Rectangle()
        self.bind(pos=self._u, size=self._u)
        self.judul = Label(text="", font_size=sp(19), bold=True, color=PUTIH, halign="left", valign="bottom")
        self.sub = Label(text="", font_size=sp(11), color=(1, 1, 1, 0.7), halign="left", valign="top")
        for lb in (self.judul, self.sub):
            lb.bind(size=lambda i, s: setattr(i, "text_size", s))
        self.kol = BoxLayout(orientation="vertical", spacing=dp(1))
        self.kol.add_widget(self.judul)
        self.kol.add_widget(self.sub)

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size
        self._g.pos = self.pos
        self._g.size = (self.width, dp(2))

    def set(self, teks, kembali=None, sub="", aksi=None):
        self.clear_widgets()
        if kembali:
            b = Tombol("<", warna=(1, 1, 1, 0.18), fg=PUTIH, size_hint=(None, None), size=(dp(40), dp(40)),
                       pos_hint={"center_y": 0.5})
            b.bind(on_release=lambda *a: kembali())
            self.add_widget(b)
        self.judul.text = teks
        self.sub.text = sub
        self.add_widget(self.kol)
        if aksi:
            b = Tombol(aksi[0], warna=(1, 1, 1, 0.16), fg=PUTIH, kecil=True, size_hint=(None, None),
                       size=(dp(74), dp(34)), pos_hint={"center_y": 0.5})
            b.bind(on_release=lambda *a: aksi[1]())
            self.add_widget(b)


class NavItem(ButtonBehavior, Label):
    aktif = BooleanProperty(False)

    def __init__(self, kode, teks, **kw):
        super().__init__(text=teks, font_size=sp(11), bold=True, halign="center", valign="bottom",
                         padding=[0, dp(7)], **kw)
        self.kode = kode
        with self.canvas.before:
            self._c = Color(0, 0, 0, 0)
            self._r = RoundedRectangle(radius=[dp(14)])
        self.bind(pos=self._u, size=self._u, aktif=self._u)
        self._u()

    def _u(self, *a):
        self.text_size = self.size
        w, h = self.width * 0.82, self.height - dp(8)
        self._r.size = (w, h)
        self._r.pos = (self.center_x - w / 2, self.y + dp(4))
        w_ = C_PRIMER if self.aktif else C_ABU
        self.color = w_
        self._c.rgba = tint(C_PRIMER, 0.13) if self.aktif else (0, 0, 0, 0)
        self._ikon(w_)

    def _ikon(self, warna):
        self.canvas.after.clear()
        cx, cy, s = self.center_x, self.y + self.height * 0.63, dp(9.5)
        lw = dp(1.6)
        with self.canvas.after:
            Color(*warna)
            k = self.kode
            if k == "ringkasan":
                q = s * 0.82
                for dx, dy in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
                    RoundedRectangle(pos=(cx + dx * s * 0.55 - q / 2, cy + dy * s * 0.55 - q / 2),
                                     size=(q, q), radius=[dp(2.5)])
            elif k == "transaksi":
                Line(points=[cx - s, cy + s * .45, cx + s, cy + s * .45], width=lw, cap="round")
                Line(points=[cx + s * .5, cy + s * .95, cx + s, cy + s * .45, cx + s * .5, cy - s * .05],
                     width=lw, cap="round", joint="round")
                Line(points=[cx + s, cy - s * .45, cx - s, cy - s * .45], width=lw, cap="round")
                Line(points=[cx - s * .5, cy + s * .05, cx - s, cy - s * .45, cx - s * .5, cy - s * .95],
                     width=lw, cap="round", joint="round")
            elif k == "hutang":
                Line(rounded_rectangle=(cx - s * .8, cy - s, s * 1.6, s * 2, dp(3)), width=lw)
                Line(points=[cx - s * .4, cy + s * .35, cx + s * .4, cy + s * .35], width=lw, cap="round")
                Line(points=[cx - s * .4, cy - s * .05, cx + s * .4, cy - s * .05], width=lw, cap="round")
                Line(points=[cx - s * .4, cy - s * .45, cx + s * .1, cy - s * .45], width=lw, cap="round")
            elif k == "tabungan":
                Line(circle=(cx, cy, s), width=lw)
                Line(circle=(cx, cy, s * .5), width=lw)
            else:
                for dx in (-1, 0, 1):
                    Ellipse(pos=(cx + dx * s * .8 - dp(2.2), cy - dp(2.2)), size=(dp(4.4), dp(4.4)))


class Fab_(Widget):
    pass


# ----------------------------------------------------------------------
# GRAFIK
# ----------------------------------------------------------------------
class ChartArus(Widget):
    """Grafik garis pemasukan vs pengeluaran, bisa disentuh."""
    sel = NumericProperty(-1)
    prog = NumericProperty(0)

    def __init__(self, data, on_pilih=None, **kw):
        super().__init__(size_hint_y=None, height=dp(170), **kw)
        self.data = data
        self.on_pilih = on_pilih
        self.maks = max([max(d[1], d[2]) for d in data] + [1])
        self.bind(pos=self.gambar, size=self.gambar, sel=self.gambar, prog=self.gambar)
        Animation(prog=1, d=0.8, t="out_cubic").start(self)

    def gambar(self, *a):
        self.canvas.clear()
        n = len(self.data)
        if n == 0 or self.width <= 1:
            return
        pt, pb = dp(10), dp(6)
        h, w = self.height - pt - pb, self.width
        base = self.y + pb
        xs = [self.x + (i + 0.5) * w / n for i in range(n)]

        def yv(v):
            return base + h * (v / float(self.maks)) * self.prog

        with self.canvas:
            Color(*C_GARIS)
            for k in range(4):
                y = base + h * k / 3.0
                Line(points=[self.x, y, self.x + w, y], width=1)
            if self.sel >= 0:
                Color(C_ABU[0], C_ABU[1], C_ABU[2], 0.35)
                Line(points=[xs[self.sel], base, xs[self.sel], base + h], width=dp(1))
            for col, idx in ((C_HIJAU, 1), (C_MERAH, 2)):
                ys = [yv(d[idx]) for d in self.data]
                verts = []
                for x, y in zip(xs, ys):
                    verts += [x, y, 0, 0, x, base, 0, 0]
                Color(col[0], col[1], col[2], 0.12)
                Mesh(vertices=verts, indices=list(range(2 * n)), mode="triangle_strip")
                Color(*col)
                Line(points=[c for p in zip(xs, ys) for c in p], width=dp(1.7), cap="round", joint="round")
                for i, (x, y) in enumerate(zip(xs, ys)):
                    r = dp(5) if i == self.sel else dp(3)
                    if i == self.sel:
                        Color(*C_CARD)
                        Ellipse(pos=(x - r - dp(1.5), y - r - dp(1.5)), size=((r + dp(1.5)) * 2,) * 2)
                        Color(*col)
                    Ellipse(pos=(x - r, y - r), size=(r * 2, r * 2))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.data:
            n = len(self.data)
            i = int((touch.x - self.x) / max(self.width, 1) * n)
            self.sel = max(0, min(n - 1, i))
            if self.on_pilih:
                self.on_pilih(self.sel)
            return True
        return super().on_touch_down(touch)


class Donat(FloatLayout):
    sel = NumericProperty(-1)

    def __init__(self, data, tengah, on_pilih=None, **kw):
        super().__init__(size_hint_y=None, height=dp(210), **kw)
        self.data = data  # [(nilai, warna)]
        self.on_pilih = on_pilih
        self.lbl = Label(text=tengah, halign="center", color=C_TEKS, font_size=sp(12), bold=True)
        self.add_widget(self.lbl)
        self.bind(pos=self.gambar, size=self.gambar, sel=self.gambar)

    def gambar(self, *a):
        self.canvas.before.clear()
        d = min(self.width, self.height) - dp(24)
        if d <= 0:
            return
        x, y = self.center_x - d / 2, self.center_y - d / 2
        total = sum(v for v, c in self.data)
        with self.canvas.before:
            if total <= 0:
                Color(*C_FIELD)
                Ellipse(pos=(x, y), size=(d, d))
            else:
                ang = 0.0
                for i, (v, c) in enumerate(self.data):
                    sw = 360.0 * v / total
                    al = 1 if self.sel < 0 or i == self.sel else 0.35
                    Color(c[0], c[1], c[2], al)
                    ex = dp(7) if i == self.sel else 0
                    Ellipse(pos=(x - ex, y - ex), size=(d + 2 * ex, d + 2 * ex),
                            angle_start=ang, angle_end=ang + sw)
                    ang += sw
            Color(*C_CARD)
            lub = d * 0.62
            Ellipse(pos=(self.center_x - lub / 2, self.center_y - lub / 2), size=(lub, lub))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and self.data:
            total = sum(v for v, c in self.data)
            dx, dy = touch.x - self.center_x, touch.y - self.center_y
            r = math.hypot(dx, dy)
            d = min(self.width, self.height) - dp(24)
            if total > 0 and d * 0.31 < r < d * 0.5 + dp(10):
                a = math.degrees(math.atan2(dx, dy)) % 360  # 0 = atas, searah jarum jam
                acc = 0.0
                for i, (v, c) in enumerate(self.data):
                    acc += 360.0 * v / total
                    if a <= acc:
                        if self.on_pilih:
                            self.on_pilih(i)
                        return True
        return super().on_touch_down(touch)


class BarisTap(ButtonBehavior, Lapisan):
    pass


# ----------------------------------------------------------------------
# TANGGAL
# ----------------------------------------------------------------------
class TanggalField(Kolom):
    def __init__(self, app, nilai="", opsional=False, **kw):
        super().__init__(spacing=dp(6), **kw)
        self.app = app
        self.nilai = nilai
        self.btn = Tombol(fmt_tgl(nilai), warna=C_FIELD, fg=C_TEKS)
        self.btn.bind(on_release=lambda *a: self.buka())
        self.add_widget(self.btn)
        q = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        opsi = [("+7 hari", 7), ("+30 hari", 30), ("+90 hari", 90), ("Kosongkan", None)] if opsional \
            else [("Hari ini", 0), ("Kemarin", -1)]
        for t, h in opsi:
            b = Tombol(t, warna=tint(C_PRIMER), fg=C_PRIMER, kecil=True)
            b.bind(on_release=lambda i, h=h: self.set_rel(h))
            q.add_widget(b)
        self.add_widget(q)

    def get(self):
        return self.nilai

    def set_rel(self, h):
        self.nilai = "" if h is None else (date.today() + timedelta(days=h)).isoformat()
        self.btn.text = fmt_tgl(self.nilai)

    def buka(self):
        base = datetime.strptime(self.nilai, "%Y-%m-%d").date() if self.nilai else date.today()
        k = Kartu(pad=18, shadow=False, spacing=dp(10))
        k.add_widget(Lbl("Pilih tanggal", 17, bold=True))
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        hari = Pilih(values=[str(i) for i in range(1, 32)], text=str(base.day), size_hint_x=0.24)
        bln = Pilih(values=BULAN, text=BULAN[base.month - 1], size_hint_x=0.44)
        y0 = min(date.today().year - 5, base.year)
        y1 = max(date.today().year + 10, base.year)
        thn = Pilih(values=[str(y) for y in range(y0, y1 + 1)], text=str(base.year), size_hint_x=0.32)
        for w in (hari, bln, thn):
            row.add_widget(w)
        k.add_widget(row)
        b = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        ok = Tombol("OK", warna=C_PRIMER)
        bt = Tombol("Batal", warna=C_FIELD, fg=C_TEKS)
        b.add_widget(bt)
        b.add_widget(ok)
        k.add_widget(b)
        mv = self.app.modal(k, "center", (0.92, None))
        bt.bind(on_release=lambda *a: mv.dismiss())

        def simpan(*a):
            y = int(thn.text)
            m = BULAN.index(bln.text) + 1
            d = min(int(hari.text), calendar.monthrange(y, m)[1])
            self.nilai = date(y, m, d).isoformat()
            self.btn.text = fmt_tgl(self.nilai)
            mv.dismiss()

        ok.bind(on_release=simpan)


# ----------------------------------------------------------------------
# APLIKASI UTAMA
# ----------------------------------------------------------------------
def gaya(k):
    return {"utama": (C_PRIMER, fg_on(C_PRIMER)), "hijau": (C_HIJAU, fg_on(C_HIJAU)),
            "bahaya": (tint(C_MERAH, 0.14), C_MERAH), "netral": (C_FIELD, C_TEKS)}[k]


TABS = [("ringkasan", "Beranda"), ("transaksi", "Transaksi"), ("hutang", "Hutang"),
        ("tabungan", "Tabungan"), ("lainnya", "Menu")]


class Utama(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.db = DB(os.path.join(app.user_data_dir, "keuangan.db"))
        pasang_tema(self.db.get("tema", "terang"))
        self.sembunyi = self.db.get("sembunyi", "0") == "1"
        self.periode = self.db.get("periode", "bulan")
        self.bulan = date.today().replace(day=1)
        self.filter = "semua"
        self.cari = ""
        self.mode_hutang = "hutang"
        self.mode_tx = "daftar"
        self.tab_lap = "labarugi"
        self.layar = ("ringkasan", None)
        self.modals = []
        self.bangun()

    def bangun(self):
        self.clear_widgets()
        utama = BoxLayout(orientation="vertical")
        self.header = Header()
        self.sv = ScrollView(do_scroll_x=False, bar_width=dp(3),
                             bar_color=(C_PRIMER[0], C_PRIMER[1], C_PRIMER[2], 0.5))
        self.box = Kolom(padding=[dp(14), dp(14), dp(14), dp(110)], spacing=dp(12))
        self.sv.add_widget(self.box)
        nav = Lapisan(orientation="horizontal", size_hint_y=None, height=dp(62), warna=C_CARD,
                      garis=True, padding=[dp(4), dp(2)])
        self.nav_items = {}
        for kode, teks in TABS:
            n = NavItem(kode, teks)
            n.bind(on_release=lambda i, k=kode: self.buka(k))
            nav.add_widget(n)
            self.nav_items[kode] = n
        utama.add_widget(self.header)
        utama.add_widget(self.sv)
        utama.add_widget(nav)
        self.add_widget(utama)
        self.fab = Fab()
        self.fab.bind(on_release=lambda *a: self.menu_tambah())
        self.add_widget(self.fab)
        self.bind(size=self._pos_fab)
        self._pos_fab()
        self.render()

    def _pos_fab(self, *a):
        self.fab.pos = (self.width - dp(76), dp(62) + dp(16))

    # ---------- pengaturan ----------
    def ganti_tema(self):
        nama = "gelap" if TEMA_AKTIF == "terang" else "terang"
        self.db.put("tema", nama)
        pasang_tema(nama)
        for m in list(self.modals):
            m.dismiss()
        self.bangun()

    def toggle_sembunyi(self):
        self.sembunyi = not self.sembunyi
        self.db.put("sembunyi", "1" if self.sembunyi else "0")
        self.refresh()

    def set_periode(self, kode):
        self.periode = kode
        self.db.put("periode", kode)
        self.refresh()

    def rpm(self, v):
        return "Rp ••••••" if self.sembunyi else rp(v)

    # ---------- navigasi ----------
    def buka(self, kode, sub=None):
        self.layar = (kode, sub)
        self.render()

    def refresh(self):
        y = self.sv.scroll_y
        self.render(reset=False)
        Clock.schedule_once(lambda dt: setattr(self.sv, "scroll_y", y), 0.05)

    def render(self, reset=True):
        kode, sub = self.layar
        self.box.clear_widgets()
        for k, n in self.nav_items.items():
            n.aktif = (k == kode)
        self.fab.opacity = 1 if (sub is None and kode != "lainnya") else 0
        self.fab.disabled = self.fab.opacity == 0
        t = date.today()
        tema_aksi = ("Gelap" if TEMA_AKTIF == "terang" else "Terang", self.ganti_tema)
        if sub == "anggaran":
            self.header.set("Anggaran Bulanan", lambda: self.buka("lainnya"), "Batas pengeluaran per kategori")
            self.s_anggaran()
        elif sub == "laporan":
            self.header.set("Laporan Keuangan", lambda: self.buka("lainnya"), "Laba Rugi, Neraca & Grafik")
            self.s_laporan()
        else:
            judul = {"ringkasan": ("Dashboard", "%s, %d %s %d" % (HARI[t.weekday()], t.day, BULAN[t.month - 1], t.year)),
                     "transaksi": ("Transaksi", "Daftar & Buku Kas"),
                     "hutang": ("Hutang & Piutang", "Pantau kewajiban dan tagihan"),
                     "tabungan": ("Rencana Tabungan", "Capai target keuangan Anda"),
                     "lainnya": ("Menu", "Pengaturan & laporan")}[kode]
            self.header.set(judul[0], None, judul[1], tema_aksi if kode == "ringkasan" else None)
            getattr(self, "s_" + kode)()
        if reset:
            self.sv.scroll_y = 1
        self.box.opacity = 0
        Animation(opacity=1, d=0.25).start(self.box)

    def geser(self, n):
        self.bulan = awal_bulan(self.bulan, n)
        self.refresh()

    def tambah(self, w):
        self.box.add_widget(w)
        return w

    def seksi(self, teks):
        self.tambah(Lbl(teks, 13, C_ABU, True))

    def chips(self, pilihan, aktif, fn):
        row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        for kode, teks in pilihan:
            a = kode == aktif
            b = Tombol(teks, warna=C_PRIMER if a else C_CARD, fg=fg_on(C_PRIMER) if a else C_ABU, kecil=True)
            b.bind(on_release=lambda i, kd=kode: fn(kd))
            row.add_widget(b)
        return row

    # ---------- modal ----------
    def modal(self, isi, anchor="center", ukuran=(0.92, None), luar=True):
        mv = ModalView(size_hint=ukuran, auto_dismiss=luar, background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.5), anchor_y=anchor)
        mv.add_widget(isi)
        if ukuran[1] is None:
            mv.height = isi.height
            isi.bind(height=lambda i, h: setattr(mv, "height", h))

        def tutup(*a):
            if mv in self.modals:
                self.modals.remove(mv)

        mv.bind(on_dismiss=tutup)
        self.modals.append(mv)
        mv.open()
        return mv

    def pesan(self, judul, teks, warna=None):
        k = Kartu(pad=20, shadow=False, spacing=dp(10))
        k.add_widget(Lbl(judul, 17, bold=True))
        k.add_widget(Lbl(teks, 14, C_ABU))
        b = Tombol("OK", warna=warna or C_PRIMER)
        k.add_widget(b)
        mv = self.modal(k, "center", (0.88, None))
        b.bind(on_release=lambda *a: mv.dismiss())

    def tanya(self, teks, ya, label="Ya, hapus"):
        k = Kartu(pad=20, shadow=False, spacing=dp(12))
        k.add_widget(Lbl("Konfirmasi", 17, bold=True))
        k.add_widget(Lbl(teks, 14, C_ABU))
        row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        tdk = Tombol("Batal", warna=C_FIELD, fg=C_TEKS)
        iya = Tombol(label, warna=C_MERAH)
        row.add_widget(tdk)
        row.add_widget(iya)
        k.add_widget(row)
        mv = self.modal(k, "center", (0.88, None))
        tdk.bind(on_release=lambda *a: mv.dismiss())

        def go(*a):
            mv.dismiss()
            Clock.schedule_once(lambda dt: ya(), 0)

        iya.bind(on_release=go)

    def sheet(self, judul, opsi):
        k = Kartu(pad=[18, 18, 18, 24], radius=[0, 0, dp(24), dp(24)], shadow=False, spacing=dp(10))
        k.add_widget(Lbl(judul, 16, bold=True))
        mv = self.modal(k, "bottom", (1, None))
        for teks, g, fn in opsi:
            bg, fg = gaya(g)
            b = Tombol(teks, warna=bg, fg=fg)

            def klik(i, fn=fn):
                mv.dismiss()
                Clock.schedule_once(lambda dt: fn(), 0.05)

            b.bind(on_release=klik)
            k.add_widget(b)

    def halaman_info(self, judul, bagian):
        root = Lapisan(orientation="vertical", warna=C_BG)
        hd = Header()
        sv = ScrollView(do_scroll_x=False)
        isi = Kolom(padding=dp(14), spacing=dp(12))
        for j, t in bagian:
            k = Kartu(pad=16)
            k.add_widget(Lbl(j, 15, C_PRIMER, True))
            k.add_widget(Lbl(t, 14, C_TEKS))
            isi.add_widget(k)
        sv.add_widget(isi)
        root.add_widget(hd)
        root.add_widget(sv)
        mv = self.modal(root, "center", (1, 1), luar=False)
        hd.set(judul, lambda: mv.dismiss())

    def tombol_kembali_android(self):
        if self.modals:
            self.modals[-1].dismiss()
            return True
        kode, sub = self.layar
        if sub is not None:
            self.buka("lainnya")
            return True
        if kode != "ringkasan":
            self.buka("ringkasan")
            return True
        return False

    # ---------- form generik ----------
    def form(self, judul, fields, simpan):
        root = Lapisan(orientation="vertical", warna=C_BG)
        hd = Header()
        sv = ScrollView(do_scroll_x=False)
        isi = Kolom(padding=[dp(16), dp(10), dp(16), dp(30)], spacing=dp(6))
        getters = {}
        for fl in fields:
            isi.add_widget(Widget(size_hint_y=None, height=dp(6)))
            isi.add_widget(Lbl(fl["l"], 13, C_ABU, True))
            t = fl.get("t", "teks")
            dv = fl.get("d", "")
            if t == "uang":
                w = UangEntry(text=fmt_angka(dv))
                isi.add_widget(w)
                getters[fl["k"]] = lambda w=w: w.text
            elif t in ("tgl", "tglx"):
                w = TanggalField(self, dv, opsional=(t == "tglx"))
                isi.add_widget(w)
                getters[fl["k"]] = w.get
            elif t == "pilih":
                w = Pilih(values=fl["o"], text=dv if dv in fl["o"] else fl["o"][0])
                isi.add_widget(w)
                getters[fl["k"]] = lambda w=w: w.text
            elif t == "combo":
                opts = list(fl["o"])
                s_ = Pilih(values=opts, text=dv if dv in opts else opts[0])
                e_ = Entry(hint_text="Atau ketik kategori sendiri...", text=dv if dv and dv not in opts else "")
                isi.add_widget(s_)
                isi.add_widget(e_)
                getters[fl["k"]] = lambda s=s_, e=e_: (e.text.strip() or s.text)
            else:
                w = Entry(text=dv, hint_text=fl.get("p", ""))
                isi.add_widget(w)
                getters[fl["k"]] = lambda w=w: w.text
            if fl.get("h"):
                isi.add_widget(Lbl(fl["h"], 12, C_ABU))
        sv.add_widget(isi)
        bawah = Lapisan(orientation="vertical", size_hint_y=None, height=dp(76), warna=C_CARD, garis=True,
                        padding=[dp(16), dp(12)])
        tmb = Tombol("SIMPAN", warna=C_PRIMER)
        bawah.add_widget(tmb)
        root.add_widget(hd)
        root.add_widget(sv)
        root.add_widget(bawah)
        mv = self.modal(root, "center", (1, 1), luar=False)
        hd.set(judul, lambda: mv.dismiss())

        def aksi(*a):
            d = {k: g() for k, g in getters.items()}
            try:
                simpan(d)
            except ValueError as e:
                self.pesan("Periksa isian", str(e), C_MERAH)
                return
            mv.dismiss()
            self.refresh()

        tmb.bind(on_release=aksi)

    # ---------- data bantu ----------
    def jml(self, tipe, a, b):
        return self.db.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe=? AND tanggal>=? AND tanggal<=?",
                           (tipe, a, b))

    def posisi(self):
        d = self.db
        kas = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk'") - \
            d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar'")
        tab = d.val("SELECT SUM(terkumpul) FROM tabungan")
        piut = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis='piutang' AND jumlah>terbayar")
        hut = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis='hutang' AND jumlah>terbayar")
        return kas, tab, piut, hut

    def data_tren(self, akhir):
        out = []
        for i in range(5, -1, -1):
            b = awal_bulan(akhir, -i)
            a, z = b.isoformat(), akhir_bulan(b).isoformat()
            out.append((BULAN[b.month - 1][:3], self.jml("masuk", a, z), self.jml("keluar", a, z),
                        bulan_label(b)))
        return out

    def w_arus(self, akhir, judul="Arus Kas 6 Bulan"):
        data = self.data_tren(akhir)
        k = Kartu(pad=14, spacing=dp(6))
        k.add_widget(Lbl(judul, 15, bold=True))
        tip = Lbl("", 12, C_ABU)
        k.add_widget(tip)

        def pilih(i):
            tip.text = "%s  |  Masuk %s  |  Keluar %s" % (data[i][3], rp(data[i][1]), rp(data[i][2]))

        chart = ChartArus(data, on_pilih=pilih)
        k.add_widget(chart)
        lab = BoxLayout(size_hint_y=None, height=dp(16))
        for d in data:
            lab.add_widget(Label(text=d[0], font_size=sp(10), color=C_ABU))
        k.add_widget(lab)
        lg = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
        lg.add_widget(Dot(C_HIJAU, pos_hint={"center_y": 0.5}))
        lg.add_widget(Lbl("Pemasukan", 11, C_ABU, size_hint_y=1))
        lg.add_widget(Dot(C_MERAH, pos_hint={"center_y": 0.5}))
        lg.add_widget(Lbl("Pengeluaran", 11, C_ABU, size_hint_y=1))
        k.add_widget(lg)
        chart.sel = len(data) - 1
        pilih(len(data) - 1)
        return k

    def w_donat(self, rows, judul, ket_total):
        """rows = [(nama, nilai)] ; legenda bisa disentuh."""
        total = sum(v for n, v in rows)
        k = Kartu(pad=14, spacing=dp(6))
        k.add_widget(Lbl(judul, 15, bold=True))
        if not rows or total <= 0:
            k.add_widget(Lbl("Tidak ada data pada periode ini.", 13, C_ABU))
            return k
        if len(rows) > 6:
            rows = rows[:5] + [("Lainnya", sum(v for n, v in rows[5:]))]
        warna = [PALET[i % len(PALET)] for i in range(len(rows))]
        tengah0 = "%s\n%s" % (ket_total, rp(total))
        legend = Kolom(spacing=dp(2))
        donat = Donat([(v, warna[i]) for i, (n, v) in enumerate(rows)], tengah0)

        def isi_legend():
            legend.clear_widgets()
            for i, (n, v) in enumerate(rows):
                aktif = donat.sel == i
                r = BarisTap(orientation="horizontal", size_hint_y=None, height=dp(34), spacing=dp(8),
                             padding=[dp(8), 0], warna=tint(warna[i], 0.16) if aktif else C_CARD)
                r.add_widget(Dot(warna[i], pos_hint={"center_y": 0.5}))
                r.add_widget(Lbl(n, 13, C_TEKS, aktif, size_hint_y=1))
                pc = Label(text="%s  (%.0f%%)" % (rp(v), v / total * 100), font_size=sp(12), bold=True,
                           color=C_TEKS, size_hint=(None, 1))
                pc.bind(texture_size=lambda inst, vv: setattr(inst, "width", vv[0] + dp(2)))
                r.add_widget(pc)
                r.bind(on_release=lambda inst, i=i: pilih(i))
                legend.add_widget(r)

        def pilih(i):
            donat.sel = -1 if donat.sel == i else i
            if donat.sel < 0:
                donat.lbl.text = tengah0
            else:
                n, v = rows[i]
                donat.lbl.text = "%s\n%.0f%%\n%s" % (n, v / total * 100, rp(v))
            isi_legend()

        donat.on_pilih = pilih
        k.add_widget(donat)
        k.add_widget(legend)
        isi_legend()
        return k

    # ==================================================================
    # DASHBOARD
    # ==================================================================
    def kpi(self, judul, nilai, warna, dl, fmt=None):
        k = Kartu(pad=[14, 12, 14, 12], spacing=dp(3))
        top = BoxLayout(size_hint_y=None, height=dp(16), spacing=dp(6))
        top.add_widget(Dot(warna, pos_hint={"center_y": 0.5}))
        top.add_widget(Lbl(judul, 11, C_ABU, True, size_hint_y=1))
        k.add_widget(top)
        k.add_widget(Angka(nilai, 17, warna, True, fmt or self.rpm, animasi=not self.sembunyi))
        k.add_widget(Lbl(dl[0], 10, dl[1]))
        return k

    def s_ringkasan(self):
        d = self.db
        a, b, pa, pb = rentang(self.periode)
        m, kl = self.jml("masuk", a, b), self.jml("keluar", a, b)
        pm = self.jml("masuk", pa, pb) if pa else None
        pk = self.jml("keluar", pa, pb) if pa else None
        kas, tab, piut, hut = self.posisi()
        nw = kas + tab + piut - hut

        self.tambah(self.chips(PERIODE, self.periode, self.set_periode))

        hero = KartuTap(grad=(C_HERO1, C_HERO2), garis=False, pad=18, spacing=dp(2), radius=20)
        hero.bind(on_release=lambda *x: self.toggle_sembunyi())
        hero.add_widget(Lbl("KEKAYAAN BERSIH", 11, (1, 1, 1, 0.75), True))
        hero.add_widget(Angka(nw, 30, PUTIH, True, self.rpm, animasi=not self.sembunyi))
        hero.add_widget(Lbl("Kas + Tabungan + Piutang - Hutang  |  ketuk untuk %s" % (
            "menampilkan" if self.sembunyi else "menyembunyikan"), 10, (1, 1, 1, 0.65)))
        hero.add_widget(Widget(size_hint_y=None, height=dp(6)))
        row = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(8))
        for jd, nl in (("Saldo Kas", kas), ("Tabungan", tab), ("Piutang - Hutang", piut - hut)):
            c = Kartu(warna=(1, 1, 1, 0.13), shadow=False, garis=False, pad=10, radius=12, spacing=dp(2))
            c.add_widget(Lbl(jd, 10, (1, 1, 1, 0.8)))
            c.add_widget(Lbl(self.rpm(nl) if not self.sembunyi else "••••", 12, PUTIH, True))
            row.add_widget(c)
        hero.add_widget(row)
        self.tambah(hero)

        qa = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        b1 = Tombol("+ Pemasukan", warna=tint(C_HIJAU, 0.16), fg=C_HIJAU)
        b2 = Tombol("+ Pengeluaran", warna=tint(C_MERAH, 0.16), fg=C_MERAH)
        b1.bind(on_release=lambda *x: self.f_transaksi("masuk"))
        b2.bind(on_release=lambda *x: self.f_transaksi("keluar"))
        qa.add_widget(b1)
        qa.add_widget(b2)
        self.tambah(qa)

        lbl = dict(PERIODE)[self.periode]
        self.seksi("Ringkasan " + lbl.upper())
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        grid.add_widget(self.kpi("Pemasukan", m, C_HIJAU, delta(m, pm, True)))
        grid.add_widget(self.kpi("Pengeluaran", kl, C_MERAH, delta(kl, pk, False)))
        grid.add_widget(self.kpi("Arus Kas Bersih", m - kl, C_HIJAU if m >= kl else C_MERAH,
                                 delta(m - kl, (pm - pk) if pa else None, True)))
        rasio = (m - kl) / m * 100 if m > 0 else 0
        prasio = ((pm - pk) / pm * 100) if pa and pm else None
        grid.add_widget(self.kpi("Rasio Tabungan", rasio, C_BIRU,
                                 delta(rasio, prasio, True) if prasio is not None else ("", C_ABU),
                                 fmt=lambda v: "%.0f%%" % v))
        self.tambah(grid)

        self.tambah(self.w_arus(date.today().replace(day=1)))

        rows = [(r["kategori"], r["t"]) for r in d.q(
            "SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe='keluar' AND tanggal>=? AND tanggal<=? "
            "GROUP BY kategori ORDER BY t DESC", (a, b))]
        self.tambah(self.w_donat(rows, "Pengeluaran per Kategori", "Total"))

        bl = date.today().strftime("%Y-%m")
        ang = d.q("SELECT * FROM anggaran ORDER BY kategori")
        if ang:
            c = Kartu(pad=14, spacing=dp(3))
            c.add_widget(Lbl("Anggaran Bulan Ini", 15, bold=True))
            for r in ang:
                pakai = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND kategori=? "
                              "AND substr(tanggal,1,7)=?", (r["kategori"], bl))
                pct = pakai / r["batas"] if r["batas"] else 0
                w = C_HIJAU if pct < 0.8 else (C_ORANYE if pct <= 1 else C_MERAH)
                c.add_widget(Baris(r["kategori"], "%.0f%%" % (pct * 100), w))
                c.add_widget(Bar(pct, w))
            self.tambah(c)

        pesan = []
        batas = (date.today() + timedelta(days=7)).isoformat()
        for r in d.q("SELECT * FROM hutang WHERE jumlah>terbayar AND jatuh_tempo<>'' AND jatuh_tempo<=? "
                     "ORDER BY jatuh_tempo", (batas,)):
            jenis = "Hutang ke" if r["jenis"] == "hutang" else "Piutang dari"
            st = "TERLAMBAT" if r["jatuh_tempo"] < date.today().isoformat() else "segera"
            pesan.append("%s %s: %s, jatuh tempo %s (%s)" % (
                jenis, r["nama"], rp(r["jumlah"] - r["terbayar"]), fmt_tgl(r["jatuh_tempo"]), st))
        if pesan:
            c = Kartu(warna=tint(C_ORANYE, 0.15), shadow=False, pad=14, spacing=dp(6))
            c.add_widget(Lbl("Perlu Perhatian", 15, C_ORANYE, True))
            for p in pesan:
                c.add_widget(Lbl("- " + p, 13, C_TEKS))
            self.tambah(c)

        terakhir = d.q("SELECT * FROM transaksi ORDER BY tanggal DESC, id DESC LIMIT 5")
        self.seksi("TRANSAKSI TERAKHIR")
        if terakhir:
            for r in terakhir:
                self.tambah(self.baris_tx(r))
            lh = Tombol("Lihat semua transaksi", warna=tint(C_PRIMER), fg=C_PRIMER, kecil=True)
            lh.bind(on_release=lambda *x: self.buka("transaksi"))
            self.tambah(lh)
        else:
            c = Kartu(pad=20)
            c.add_widget(Lbl("Selamat datang!", 17, bold=True))
            c.add_widget(Lbl("Mulai dengan menekan tombol + untuk mencatat pemasukan atau pengeluaran pertama.",
                             14, C_ABU))
            self.tambah(c)

    # ==================================================================
    # TRANSAKSI
    # ==================================================================
    def baris_tx(self, r):
        masuk = r["tipe"] == "masuk"
        k = KartuTap(orientation="horizontal", pad=12, spacing=dp(12))
        k.add_widget(Avatar(r["kategori"], warna_kat(r["kategori"]), pos_hint={"center_y": 0.5}))
        mid = Kolom(spacing=dp(2))
        mid.add_widget(Lbl(r["kategori"], 15, bold=True))
        sub = fmt_tgl(r["tanggal"]) + ((" | " + r["catatan"]) if r["catatan"] else "")
        mid.add_widget(Lbl(sub, 12, C_ABU))
        k.add_widget(mid)
        amt = Label(text=("+" if masuk else "-") + rp(r["jumlah"]), bold=True, font_size=sp(14),
                    color=C_HIJAU if masuk else C_MERAH, size_hint=(None, None))
        amt.bind(texture_size=amt.setter("size"))
        amt.pos_hint = {"center_y": 0.5}
        k.add_widget(amt)
        k.bind(on_release=lambda *a: self.opsi_tx(r))
        return k

    def opsi_tx(self, r):
        self.sheet("%s - %s" % (r["kategori"], rp(r["jumlah"])), [
            ("Ubah", "utama", lambda: self.f_transaksi(r["tipe"], r)),
            ("Hapus", "bahaya", lambda: self.tanya("Hapus transaksi ini?", lambda: self.hapus(
                "DELETE FROM transaksi WHERE id=?", (r["id"],)))),
            ("Batal", "netral", lambda: None)])

    def hapus(self, sql, args):
        self.db.x(sql, args)
        self.refresh()

    def w_nav_bulan(self):
        k = Kartu(orientation="horizontal", pad=8, spacing=dp(8))
        a = Tombol("<", warna=tint(C_PRIMER), fg=C_PRIMER, kecil=True, size_hint_x=None, width=dp(48))
        b = Tombol(">", warna=tint(C_PRIMER), fg=C_PRIMER, kecil=True, size_hint_x=None, width=dp(48))
        a.bind(on_release=lambda *x: self.geser(-1))
        b.bind(on_release=lambda *x: self.geser(1))
        k.add_widget(a)
        k.add_widget(Label(text=bulan_label(self.bulan), font_size=sp(16), bold=True, color=C_TEKS,
                           size_hint=(1, None), height=dp(36)))
        k.add_widget(b)
        return k

    def s_transaksi(self):
        bl = self.bulan.strftime("%Y-%m")
        a, z = self.bulan.isoformat(), akhir_bulan(self.bulan).isoformat()
        self.tambah(self.w_nav_bulan())
        m, kl = self.jml("masuk", a, z), self.jml("keluar", a, z)
        row = BoxLayout(size_hint_y=None, height=dp(66), spacing=dp(8))
        for judul, nilai, c in (("Masuk", m, C_HIJAU), ("Keluar", kl, C_MERAH),
                                ("Selisih", m - kl, C_HIJAU if m >= kl else C_MERAH)):
            s = Kartu(pad=10, spacing=dp(2))
            s.add_widget(Lbl(judul, 11, C_ABU, rata="center"))
            s.add_widget(Lbl(rp(nilai), 12, c, True, rata="center"))
            row.add_widget(s)
        self.tambah(row)

        self.tambah(self.chips([("daftar", "Daftar"), ("buku", "Buku Kas")], self.mode_tx, self.set_mode_tx))
        bt = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        b1 = Tombol("+ Pemasukan", warna=C_HIJAU)
        b2 = Tombol("+ Pengeluaran", warna=C_MERAH)
        b1.bind(on_release=lambda *x: self.f_transaksi("masuk"))
        b2.bind(on_release=lambda *x: self.f_transaksi("keluar"))
        bt.add_widget(b1)
        bt.add_widget(b2)
        self.tambah(bt)

        if self.mode_tx == "buku":
            self.tambah(self.w_buku(bl))
            return
        self.tambah(self.chips([("semua", "Semua"), ("masuk", "Pemasukan"), ("keluar", "Pengeluaran")],
                               self.filter, self.set_filter))
        e = Entry(hint_text="Cari kategori atau catatan...", text=self.cari)
        e.bind(text=self._cari_berubah)
        self.tambah(e)
        self.daftar = Kolom(spacing=dp(10))
        self.tambah(self.daftar)
        self.isi_tx()

    def set_mode_tx(self, kode):
        self.mode_tx = kode
        self.refresh()

    def set_filter(self, kode):
        self.filter = kode
        self.refresh()

    def _cari_berubah(self, inst, val):
        self.cari = val
        self.isi_tx()

    def isi_tx(self):
        self.daftar.clear_widgets()
        bl = self.bulan.strftime("%Y-%m")
        sql = "SELECT * FROM transaksi WHERE substr(tanggal,1,7)=?"
        args = [bl]
        if self.filter != "semua":
            sql += " AND tipe=?"
            args.append(self.filter)
        sql += " ORDER BY tanggal DESC, id DESC"
        rows = self.db.q(sql, args)
        kata = self.cari.strip().lower()
        if kata:
            rows = [r for r in rows if kata in r["kategori"].lower() or kata in (r["catatan"] or "").lower()]
        if not rows:
            c = Kartu(pad=24)
            c.add_widget(Lbl("Belum ada transaksi.", 14, C_ABU, rata="center"))
            self.daftar.add_widget(c)
        for r in rows[:200]:
            self.daftar.add_widget(self.baris_tx(r))

    # ----- Buku Kas (gaya akuntan: debit / kredit / saldo berjalan) -----
    def sel(self, teks, lebar, size=11, warna=None, bold=False, rata="right"):
        lb = Label(text=teks, font_size=sp(size), color=warna or C_TEKS, bold=bold, halign=rata, valign="middle",
                   shorten=True, shorten_from="right", size_hint=(None, 1) if lebar else (1, 1))
        if lebar:
            lb.width = dp(lebar)
        lb.bind(size=lambda i, s: setattr(i, "text_size", s))
        return lb

    def baris_buku(self, tgl, ket, sub, debit, kredit, bg, tap=None, bold=False, warna_teks=None, tinggi=46):
        cls = BarisTap if tap else Lapisan
        r = cls(orientation="horizontal", size_hint_y=None, height=dp(tinggi), warna=bg,
                padding=[dp(6), dp(2)], spacing=dp(2))
        r.add_widget(self.sel(tgl, 38, 11, warna_teks or C_ABU, False, "left"))
        mid = BoxLayout(orientation="vertical", size_hint_x=1)
        mid.add_widget(self.sel(ket, 0, 12, warna_teks, True, "left"))
        if sub:
            mid.add_widget(self.sel(sub, 0, 10, warna_teks or C_ABU, False, "left"))
        r.add_widget(mid)
        r.add_widget(self.sel(debit, 74, 11, warna_teks or C_HIJAU, bold))
        r.add_widget(self.sel(kredit, 74, 11, warna_teks or C_MERAH, bold))
        if tap:
            r.bind(on_release=lambda *x: tap())
        return r

    def w_buku(self, bl):
        awal = self.bulan.isoformat()
        sa = self.db.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk' AND tanggal<?", (awal,)) - \
            self.db.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND tanggal<?", (awal,))
        rows = self.db.q("SELECT * FROM transaksi WHERE substr(tanggal,1,7)=? ORDER BY tanggal, id", (bl,))
        k = Kartu(pad=1, spacing=0, radius=10)
        k.add_widget(self.baris_buku("Tgl", "Keterangan", "", "Debit", "Kredit", C_HDR1, None, True, PUTIH, 34))
        zebra = (C_FIELD[0], C_FIELD[1], C_FIELD[2], 0.55)
        k.add_widget(self.baris_buku("", "Saldo awal", "", angka(sa) if sa >= 0 else "",
                                     angka(-sa) if sa < 0 else "", C_CARD, None, True, None, 38))
        sd = sk = 0.0
        saldo = sa
        for i, r in enumerate(rows):
            masuk = r["tipe"] == "masuk"
            saldo += r["jumlah"] if masuk else -r["jumlah"]
            if masuk:
                sd += r["jumlah"]
            else:
                sk += r["jumlah"]
            sub = ((r["catatan"] + "  |  ") if r["catatan"] else "") + "Saldo " + angka(saldo)
            k.add_widget(self.baris_buku(r["tanggal"][8:10] + "/" + r["tanggal"][5:7], r["kategori"], sub,
                                         angka(r["jumlah"]) if masuk else "", "" if masuk else angka(r["jumlah"]),
                                         C_CARD if i % 2 == 0 else zebra,
                                         tap=lambda r=r: self.opsi_tx(r)))
        k.add_widget(Garis(2))
        k.add_widget(self.baris_buku("", "Jumlah", "", angka(sd), angka(sk), C_CARD, None, True, None, 38))
        akh = sa + sd - sk
        k.add_widget(self.baris_buku("", "Saldo akhir", "Saldo awal + Debit - Kredit", angka(akh) if akh >= 0 else "",
                                     angka(-akh) if akh < 0 else "", tint(C_PRIMER, 0.12), None, True, None, 46))
        if not rows:
            k.add_widget(Lbl("Belum ada transaksi pada bulan ini.", 12, C_ABU, rata="center"))
        return k

    def f_transaksi(self, tipe, row=None):
        masuk = tipe == "masuk"
        fields = [
            dict(k="tanggal", l="Tanggal", t="tgl", d=row["tanggal"] if row else date.today().isoformat()),
            dict(k="jumlah", l="Jumlah (Rp)", t="uang", d=str(int(row["jumlah"])) if row else ""),
            dict(k="kategori", l="Kategori", t="combo", o=KAT_MASUK if masuk else KAT_KELUAR,
                 d=row["kategori"] if row else ""),
            dict(k="catatan", l="Catatan (opsional)", d=row["catatan"] if row else ""),
        ]

        def simpan(d):
            tgl = d["tanggal"]
            jml = parse_uang(d["jumlah"])
            kat = d["kategori"].strip() or "Lainnya"
            cat = d["catatan"].strip()
            if row:
                self.db.x("UPDATE transaksi SET tanggal=?,kategori=?,jumlah=?,catatan=? WHERE id=?",
                          (tgl, kat, jml, cat, row["id"]))
            else:
                self.db.x("INSERT INTO transaksi(tipe,tanggal,kategori,jumlah,catatan) VALUES(?,?,?,?,?)",
                          (tipe, tgl, kat, jml, cat))
            self.bulan = date(int(tgl[:4]), int(tgl[5:7]), 1)
            if not masuk:
                self.cek_anggaran(kat, tgl[:7])

        self.form(("Ubah " if row else "Tambah ") + ("Pemasukan" if masuk else "Pengeluaran"), fields, simpan)

    def cek_anggaran(self, kategori, bl):
        a = self.db.q("SELECT * FROM anggaran WHERE kategori=?", (kategori,))
        if not a or a[0]["batas"] <= 0:
            return
        pakai = self.db.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND kategori=? "
                            "AND substr(tanggal,1,7)=?", (kategori, bl))
        if pakai > a[0]["batas"]:
            self.pesan("Anggaran terlampaui", "Pengeluaran %s bulan ini %s, melebihi anggaran %s." % (
                kategori, rp(pakai), rp(a[0]["batas"])), C_MERAH)
        elif pakai >= 0.8 * a[0]["batas"]:
            self.pesan("Anggaran hampir habis", "Pengeluaran %s sudah %.0f%% dari anggaran." % (
                kategori, pakai / a[0]["batas"] * 100), C_ORANYE)

    # ==================================================================
    # HUTANG & PIUTANG
    # ==================================================================
    def s_hutang(self):
        d = self.db
        mode = self.mode_hutang
        self.tambah(self.chips([("hutang", "Hutang Saya"), ("piutang", "Piutang")], mode, self.set_mode))
        sisa = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis=? AND jumlah>terbayar", (mode,))
        total = d.val("SELECT SUM(jumlah) FROM hutang WHERE jenis=?", (mode,))
        warna = (hx("#7F1D1D"), C_MERAH) if mode == "hutang" else (hx("#065F46"), C_HIJAU)
        hero = Kartu(grad=warna, garis=False, pad=18, spacing=dp(2), radius=20)
        hero.add_widget(Lbl("UANG YANG HARUS SAYA BAYAR" if mode == "hutang" else "UANG SAYA YANG BELUM KEMBALI",
                            11, (1, 1, 1, 0.8), True))
        hero.add_widget(Angka(sisa, 28, PUTIH, True))
        hero.add_widget(Lbl("Terlunasi %s dari total %s" % (rp(total - sisa), rp(total)), 11, (1, 1, 1, 0.75)))
        hero.add_widget(Bar((total - sisa) / total if total else 0, PUTIH))
        self.tambah(hero)
        b = Tombol("+ Tambah " + ("Hutang" if mode == "hutang" else "Piutang"), warna=C_PRIMER)
        b.bind(on_release=lambda *a: self.f_hutang())
        self.tambah(b)

        rows = d.q("SELECT * FROM hutang WHERE jenis=? ORDER BY (jumlah<=terbayar), "
                   "CASE WHEN jatuh_tempo='' THEN '9999' ELSE jatuh_tempo END", (mode,))
        if not rows:
            c = Kartu(pad=24)
            c.add_widget(Lbl("Belum ada data.", 14, C_ABU, rata="center"))
            self.tambah(c)
        for r in rows:
            self.tambah(self.kartu_hutang(r))

    def kartu_hutang(self, r):
        mode = r["jenis"]
        lunas = r["jumlah"] <= r["terbayar"]
        sisa = r["jumlah"] - r["terbayar"]
        warna = C_MERAH if mode == "hutang" else C_HIJAU
        k = KartuTap(pad=16, spacing=dp(4))
        k.bind(on_release=lambda *a: self.opsi_hutang(r))
        k.add_widget(Baris(r["nama"], "LUNAS" if lunas else rp(sisa), C_HIJAU if lunas else warna,
                           size=16, bold_kiri=True))
        k.add_widget(Lbl("Total %s | %s %s" % (rp(r["jumlah"]), "Dibayar" if mode == "hutang" else "Diterima",
                                              rp(r["terbayar"])), 12, C_ABU))
        k.add_widget(Bar(r["terbayar"] / r["jumlah"] if r["jumlah"] else 0, C_HIJAU))
        if r["jatuh_tempo"]:
            telat = (not lunas) and r["jatuh_tempo"] < date.today().isoformat()
            k.add_widget(Lbl("Jatuh tempo: %s%s" % (fmt_tgl(r["jatuh_tempo"]), "  (TERLAMBAT)" if telat else ""),
                             12, C_MERAH if telat else C_ABU))
        if r["catatan"]:
            k.add_widget(Lbl(r["catatan"], 12, C_ABU))
        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        if not lunas:
            b = Tombol("Bayar" if mode == "hutang" else "Terima", warna=C_HIJAU, kecil=True)
            b.bind(on_release=lambda *a: self.f_bayar(r))
            row.add_widget(b)
        o = Tombol("Opsi", warna=C_FIELD, fg=C_TEKS, kecil=True)
        o.bind(on_release=lambda *a: self.opsi_hutang(r))
        row.add_widget(o)
        k.add_widget(Widget(size_hint_y=None, height=dp(2)))
        k.add_widget(row)
        return k

    def opsi_hutang(self, r):
        lunas = r["jumlah"] <= r["terbayar"]
        opsi = []
        if not lunas:
            opsi.append(("Bayar" if r["jenis"] == "hutang" else "Terima pembayaran", "hijau",
                         lambda: self.f_bayar(r)))
        opsi += [("Ubah", "utama", lambda: self.f_hutang(r)),
                 ("Hapus", "bahaya", lambda: self.tanya("Hapus catatan %s?" % r["nama"], lambda: self.hapus(
                     "DELETE FROM hutang WHERE id=?", (r["id"],)))),
                 ("Batal", "netral", lambda: None)]
        self.sheet(r["nama"], opsi)

    def set_mode(self, m):
        self.mode_hutang = m
        self.refresh()

    def f_hutang(self, row=None):
        jenis = row["jenis"] if row else self.mode_hutang
        fields = [
            dict(k="nama", l="Berhutang kepada siapa?" if jenis == "hutang" else "Siapa yang berhutang ke saya?",
                 d=row["nama"] if row else ""),
            dict(k="jumlah", l="Jumlah total (Rp)", t="uang", d=str(int(row["jumlah"])) if row else ""),
            dict(k="tempo", l="Jatuh tempo (opsional)", t="tglx", d=row["jatuh_tempo"] if row else ""),
            dict(k="catatan", l="Catatan (opsional)", d=row["catatan"] if row else ""),
        ]

        def simpan(d):
            nama = d["nama"].strip()
            if not nama:
                raise ValueError("Nama tidak boleh kosong.")
            jml = parse_uang(d["jumlah"])
            if row:
                if jml < row["terbayar"]:
                    raise ValueError("Jumlah tidak boleh lebih kecil dari yang sudah dibayar (%s)." % rp(row["terbayar"]))
                self.db.x("UPDATE hutang SET nama=?,jumlah=?,jatuh_tempo=?,catatan=? WHERE id=?",
                          (nama, jml, d["tempo"], d["catatan"].strip(), row["id"]))
            else:
                self.db.x("INSERT INTO hutang(jenis,nama,jumlah,terbayar,jatuh_tempo,catatan) VALUES(?,?,?,0,?,?)",
                          (jenis, nama, jml, d["tempo"], d["catatan"].strip()))
                self.mode_hutang = jenis
                if self.layar[0] != "hutang":
                    self.layar = ("hutang", None)

        self.form(("Ubah " if row else "Tambah ") + ("Hutang" if jenis == "hutang" else "Piutang"), fields, simpan)

    def f_bayar(self, r):
        hutang = r["jenis"] == "hutang"
        sisa = r["jumlah"] - r["terbayar"]
        fields = [
            dict(k="tanggal", l="Tanggal", t="tgl", d=date.today().isoformat()),
            dict(k="jumlah", l="Jumlah %s (Rp)" % ("pembayaran" if hutang else "penerimaan"), t="uang",
                 d=str(int(sisa)), h="Sisa saat ini: " + rp(sisa)),
            dict(k="catat", l="Catat juga ke transaksi?", t="pilih", o=["Ya", "Tidak"], d="Ya",
                 h="Jika Ya, saldo ikut berubah."),
        ]

        def simpan(d):
            jml = parse_uang(d["jumlah"])
            if jml > sisa:
                raise ValueError("Jumlah melebihi sisa (%s)." % rp(sisa))
            self.db.x("UPDATE hutang SET terbayar=terbayar+? WHERE id=?", (jml, r["id"]))
            if d["catat"] == "Ya":
                self.db.x("INSERT INTO transaksi(tipe,tanggal,kategori,jumlah,catatan) VALUES(?,?,?,?,?)",
                          ("keluar" if hutang else "masuk", d["tanggal"],
                           "Bayar Hutang" if hutang else "Terima Piutang", jml,
                           ("Bayar hutang ke " if hutang else "Terima piutang dari ") + r["nama"]))

        self.form(("Bayar Hutang: " if hutang else "Terima Piutang: ") + r["nama"], fields, simpan)

    # ==================================================================
    # TABUNGAN
    # ==================================================================
    def s_tabungan(self):
        d = self.db
        total = d.val("SELECT SUM(terkumpul) FROM tabungan")
        target = d.val("SELECT SUM(target) FROM tabungan")
        hero = Kartu(grad=(C_HERO1, C_TOSCA), garis=False, pad=18, spacing=dp(2), radius=20)
        hero.add_widget(Lbl("TOTAL TABUNGAN", 11, (1, 1, 1, 0.8), True))
        hero.add_widget(Angka(total, 28, PUTIH, True))
        if target:
            hero.add_widget(Lbl("%.0f%% dari total target %s" % (total / target * 100, rp(target)), 11,
                                (1, 1, 1, 0.8)))
            hero.add_widget(Bar(total / target, C_AKSEN))
        self.tambah(hero)
        b = Tombol("+ Buat Target Tabungan", warna=C_PRIMER)
        b.bind(on_release=lambda *a: self.f_tabungan())
        self.tambah(b)
        rows = d.q("SELECT * FROM tabungan ORDER BY id DESC")
        if not rows:
            c = Kartu(pad=24)
            c.add_widget(Lbl("Belum ada target tabungan.", 14, C_ABU, rata="center"))
            self.tambah(c)
        for r in rows:
            self.tambah(self.kartu_tabungan(r))

    def saran_tabungan(self, r):
        kurang = r["target"] - r["terkumpul"]
        if kurang <= 0:
            return "Target tercapai! Selamat!"
        if not r["tenggat"]:
            return "Kurang " + rp(kurang)
        t = datetime.strptime(r["tenggat"], "%Y-%m-%d").date()
        hari = (t - date.today()).days
        if hari < 0:
            return "Kurang %s | sudah lewat tenggat" % rp(kurang)
        bln = max(1, math.ceil(hari / 30.0))
        return "Kurang %s | sisihkan sekitar %s per bulan (%d hari lagi)" % (rp(kurang), rp(kurang / bln), hari)

    def kartu_tabungan(self, r):
        pct = r["terkumpul"] / r["target"] if r["target"] else 0
        k = KartuTap(pad=16, spacing=dp(4))
        k.bind(on_release=lambda *a: self.opsi_tabungan(r))
        k.add_widget(Baris(r["nama"], "%.0f%%" % (pct * 100), C_HIJAU if pct >= 1 else C_PRIMER,
                           size=16, bold_kiri=True))
        k.add_widget(Lbl("%s dari %s" % (rp(r["terkumpul"]), rp(r["target"])), 13, C_TEKS))
        k.add_widget(Bar(pct, C_HIJAU if pct >= 1 else C_PRIMER))
        k.add_widget(Lbl(self.saran_tabungan(r), 12, C_ABU))
        if r["tenggat"]:
            k.add_widget(Lbl("Tenggat: " + fmt_tgl(r["tenggat"]), 12, C_ABU))
        if r["catatan"]:
            k.add_widget(Lbl(r["catatan"], 12, C_ABU))
        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        for teks, w, fn in (("Setor", C_HIJAU, lambda: self.f_setor(r, "setor")),
                            ("Tarik", C_ORANYE, lambda: self.f_setor(r, "tarik")),
                            ("Opsi", C_FIELD, lambda: self.opsi_tabungan(r))):
            b = Tombol(teks, warna=w, fg=C_TEKS if w == C_FIELD else None, kecil=True)
            b.bind(on_release=lambda i, fn=fn: fn())
            row.add_widget(b)
        k.add_widget(Widget(size_hint_y=None, height=dp(2)))
        k.add_widget(row)
        return k

    def opsi_tabungan(self, r):
        self.sheet(r["nama"], [
            ("Setor", "hijau", lambda: self.f_setor(r, "setor")),
            ("Tarik", "netral", lambda: self.f_setor(r, "tarik")),
            ("Ubah target", "utama", lambda: self.f_tabungan(r)),
            ("Hapus", "bahaya", lambda: self.tanya("Hapus tabungan %s?" % r["nama"], lambda: self.hapus(
                "DELETE FROM tabungan WHERE id=?", (r["id"],)))),
            ("Batal", "netral", lambda: None)])

    def f_tabungan(self, row=None):
        fields = [
            dict(k="nama", l="Nama target", p="mis. Beli HP, Umroh, Dana darurat", d=row["nama"] if row else ""),
            dict(k="target", l="Target jumlah (Rp)", t="uang", d=str(int(row["target"])) if row else ""),
            dict(k="tenggat", l="Tenggat waktu (opsional)", t="tglx", d=row["tenggat"] if row else ""),
        ]
        if not row:
            fields.append(dict(k="awal", l="Setoran awal (opsional)", t="uang", d=""))
        fields.append(dict(k="catatan", l="Catatan (opsional)", d=row["catatan"] if row else ""))

        def simpan(d):
            nama = d["nama"].strip()
            if not nama:
                raise ValueError("Nama target tidak boleh kosong.")
            target = parse_uang(d["target"])
            cat = d["catatan"].strip()
            if row:
                self.db.x("UPDATE tabungan SET nama=?,target=?,tenggat=?,catatan=? WHERE id=?",
                          (nama, target, d["tenggat"], cat, row["id"]))
            else:
                self.db.x("INSERT INTO tabungan(nama,target,terkumpul,tenggat,catatan) VALUES(?,?,?,?,?)",
                          (nama, target, parse_uang_opsional(d.get("awal", "")), d["tenggat"], cat))
                if self.layar[0] != "tabungan":
                    self.layar = ("tabungan", None)

        self.form("Ubah Target" if row else "Target Tabungan Baru", fields, simpan)

    def f_setor(self, r, mode):
        setor = mode == "setor"
        fields = [
            dict(k="tanggal", l="Tanggal", t="tgl", d=date.today().isoformat()),
            dict(k="jumlah", l="Jumlah (Rp)", t="uang", d="", h="Terkumpul saat ini: " + rp(r["terkumpul"])),
            dict(k="catat", l="Catat juga ke transaksi?", t="pilih", o=["Ya", "Tidak"], d="Ya",
                 h="Setor tercatat sebagai pengeluaran, Tarik sebagai pemasukan."),
        ]

        def simpan(d):
            jml = parse_uang(d["jumlah"])
            if not setor and jml > r["terkumpul"]:
                raise ValueError("Jumlah melebihi tabungan terkumpul (%s)." % rp(r["terkumpul"]))
            self.db.x("UPDATE tabungan SET terkumpul=terkumpul+? WHERE id=?", (jml if setor else -jml, r["id"]))
            if d["catat"] == "Ya":
                self.db.x("INSERT INTO transaksi(tipe,tanggal,kategori,jumlah,catatan) VALUES(?,?,?,?,?)",
                          ("keluar" if setor else "masuk", d["tanggal"],
                           "Tabungan" if setor else "Tarik Tabungan", jml,
                           ("Setor ke " if setor else "Tarik dari ") + r["nama"]))

        self.form(("Setor ke " if setor else "Tarik dari ") + r["nama"], fields, simpan)

    # ==================================================================
    # MENU
    # ==================================================================
    def menu_tambah(self):
        self.sheet("Tambah catatan baru", [
            ("Pemasukan", "hijau", lambda: self.f_transaksi("masuk")),
            ("Pengeluaran", "bahaya", lambda: self.f_transaksi("keluar")),
            ("Hutang / Piutang", "utama", lambda: self.f_hutang()),
            ("Target Tabungan", "netral", lambda: self.f_tabungan())])

    def s_lainnya(self):
        items = [
            ("Laporan Keuangan", "Laba Rugi, Neraca, grafik", "", lambda: self.buka("lainnya", "laporan"), C_PRIMER),
            ("Anggaran Bulanan", "Batasi pengeluaran per kategori", "", lambda: self.buka("lainnya", "anggaran"), C_TOSCA),
            ("Tema Tampilan", "Ketuk untuk mengganti", "Gelap" if TEMA_AKTIF == "gelap" else "Terang",
             self.ganti_tema, C_AKSEN),
            ("Sembunyikan Saldo", "Samarkan angka di Dashboard", "Ya" if self.sembunyi else "Tidak",
             self.toggle_sembunyi, C_UNGU),
            ("Ekspor & Bagikan Data", "CSV untuk Excel / WhatsApp / Email", "", self.menu_ekspor, C_HIJAU),
            ("Backup Database", "Simpan salinan data Anda", "", self.backup_db, C_BIRU),
            ("Panduan & Tentang", "Cara memakai aplikasi", "", self.panduan, C_ABU),
            ("Hapus Semua Data", "Mulai dari nol (tidak bisa dibatalkan)", "", self.hapus_semua, C_MERAH),
        ]
        for judul, ket, nilai, fn, w in items:
            k = KartuTap(orientation="horizontal", pad=14, spacing=dp(12))
            k.add_widget(Avatar(judul, w, pos_hint={"center_y": 0.5}))
            kol = Kolom(spacing=dp(2))
            kol.add_widget(Lbl(judul, 15, C_MERAH if judul.startswith("Hapus") else C_TEKS, True))
            kol.add_widget(Lbl(ket, 12, C_ABU))
            k.add_widget(kol)
            kanan = Label(text=nilai if nilai else ">", font_size=sp(13), bold=True, color=C_PRIMER if nilai else C_ABU,
                          size_hint=(None, None), size=(dp(56), dp(20)), pos_hint={"center_y": 0.5})
            k.add_widget(kanan)
            k.bind(on_release=lambda i, fn=fn: fn())
            self.tambah(k)

    def panduan(self):
        self.halaman_info("Panduan & Tentang", [
            ("Dashboard", "Pilih periode (Bulan Ini, 3 Bulan, Tahun Ini, Semua). Ketuk kartu Kekayaan Bersih untuk "
                          "menyembunyikan angka. Sentuh grafik untuk melihat nilai tiap bulan, dan sentuh irisan donat "
                          "atau daftar kategori untuk menyorotnya."),
            ("Transaksi & Buku Kas", "Daftar menampilkan kartu transaksi. Buku Kas menampilkan format akuntansi: "
                                     "Debit (uang masuk), Kredit (uang keluar) dan saldo berjalan. Ketuk baris untuk "
                                     "mengubah atau menghapus."),
            ("Hutang & Piutang", "Hutang Saya = yang harus Anda bayar. Piutang = uang Anda yang dipinjam orang lain. "
                                 "Tekan Bayar/Terima untuk mencatat cicilan."),
            ("Tabungan", "Buat target lalu Setor/Tarik. Aplikasi menghitung saran jumlah nabung per bulan."),
            ("Laporan", "Laba Rugi (pendapatan - beban), Neraca (aset, kewajiban, ekuitas) dan grafik tren."),
            ("Data Anda", "Data tersimpan di HP ini. Jika aplikasi dihapus, data ikut hilang, jadi rutin gunakan "
                          "Ekspor & Bagikan Data atau Backup Database."),
        ])

    def hapus_semua(self):
        def lanjut():
            def final():
                for t in ("transaksi", "hutang", "tabungan", "anggaran"):
                    self.db.x("DELETE FROM " + t)
                self.buka("ringkasan")
                self.pesan("Selesai", "Semua data telah dihapus.")
            self.tanya("Benar-benar hapus SEMUA data? Disarankan backup dulu.", final, "Hapus semua")
        self.tanya("Semua data (transaksi, hutang, tabungan, anggaran) akan dihapus permanen.", lanjut, "Lanjut")

    # ---------- ekspor / backup ----------
    def folder_simpan(self):
        kandidat = []
        if platform == "android":
            kandidat += ["/storage/emulated/0/Download", "/storage/emulated/0/Documents"]
            try:
                from jnius import autoclass
                act = autoclass("org.kivy.android.PythonActivity").mActivity
                f = act.getExternalFilesDir(None)
                if f:
                    kandidat.append(f.getAbsolutePath())
            except Exception:
                pass
        else:
            kandidat += [os.path.expanduser("~/Downloads"), os.path.expanduser("~/Download")]
        kandidat.append(self.app.user_data_dir)
        for p in kandidat:
            try:
                if os.path.isdir(p):
                    tes = os.path.join(p, ".tes_tulis")
                    with open(tes, "w") as fh:
                        fh.write("x")
                    os.remove(tes)
                    return p
            except Exception:
                continue
        return self.app.user_data_dir

    def csv_teks(self):
        out = io.StringIO()
        w = csv.writer(out)
        for judul, sql in (
                ("TRANSAKSI", "SELECT tanggal,tipe,kategori,jumlah,catatan FROM transaksi ORDER BY tanggal"),
                ("HUTANG & PIUTANG", "SELECT jenis,nama,jumlah,terbayar,jatuh_tempo,catatan FROM hutang"),
                ("TABUNGAN", "SELECT nama,target,terkumpul,tenggat,catatan FROM tabungan"),
                ("ANGGARAN", "SELECT kategori,batas FROM anggaran")):
            cur = self.db.c.execute(sql)
            w.writerow([judul])
            w.writerow([x[0] for x in cur.description])
            for r in cur.fetchall():
                w.writerow(tuple(r))
            w.writerow([])
        return out.getvalue()

    def menu_ekspor(self):
        self.sheet("Ekspor & Bagikan Data", [
            ("Bagikan (WhatsApp / Email / Drive)", "utama", self.bagikan),
            ("Simpan sebagai file CSV", "hijau", self.simpan_csv),
            ("Batal", "netral", lambda: None)])

    def bagikan(self):
        teks = self.csv_teks()
        if platform == "android":
            try:
                from jnius import autoclass, cast
                Intent = autoclass("android.content.Intent")
                String = autoclass("java.lang.String")
                act = autoclass("org.kivy.android.PythonActivity").mActivity
                it = Intent()
                it.setAction(Intent.ACTION_SEND)
                it.putExtra(Intent.EXTRA_SUBJECT, cast("java.lang.CharSequence", String("Data Catatan Keuangan")))
                it.putExtra(Intent.EXTRA_TEXT, cast("java.lang.CharSequence", String(teks)))
                it.setType("text/plain")
                act.startActivity(Intent.createChooser(it, cast("java.lang.CharSequence", String("Bagikan data"))))
                return
            except Exception as e:
                self.pesan("Gagal membagikan", str(e), C_MERAH)
                return
        Clipboard.copy(teks)
        self.pesan("Disalin", "Data CSV telah disalin ke clipboard. Tempel di aplikasi lain.")

    def simpan_csv(self):
        try:
            folder = self.folder_simpan()
            path = os.path.join(folder, "keuangan_%s.csv" % datetime.now().strftime("%Y%m%d_%H%M"))
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                fh.write(self.csv_teks())
            self.pesan("Berhasil", "File tersimpan di:\n" + path)
        except Exception as e:
            self.pesan("Gagal menyimpan", str(e), C_MERAH)

    def backup_db(self):
        try:
            folder = self.folder_simpan()
            path = os.path.join(folder, "keuangan_backup_%s.db" % datetime.now().strftime("%Y%m%d_%H%M"))
            self.db.c.commit()
            shutil.copy2(self.db.path, path)
            self.pesan("Backup berhasil", "Tersimpan di:\n" + path)
        except Exception as e:
            self.pesan("Gagal backup", str(e), C_MERAH)

    # ==================================================================
    # ANGGARAN
    # ==================================================================
    def s_anggaran(self):
        bl = date.today().strftime("%Y-%m")
        self.tambah(Lbl("Pemakaian bulan " + bulan_label(date.today()), 13, C_ABU))
        b = Tombol("+ Atur Anggaran", warna=C_PRIMER)
        b.bind(on_release=lambda *a: self.f_anggaran())
        self.tambah(b)
        rows = self.db.q("SELECT * FROM anggaran ORDER BY kategori")
        if not rows:
            c = Kartu(pad=24)
            c.add_widget(Lbl("Belum ada anggaran.", 14, C_ABU, rata="center"))
            self.tambah(c)
        for a in rows:
            pakai = self.db.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND kategori=? "
                                "AND substr(tanggal,1,7)=?", (a["kategori"], bl))
            pct = pakai / a["batas"] if a["batas"] else 0
            w = C_HIJAU if pct < 0.8 else (C_ORANYE if pct <= 1 else C_MERAH)
            k = KartuTap(pad=16, spacing=dp(4))
            k.bind(on_release=lambda i, a=a: self.sheet(a["kategori"], [
                ("Ubah", "utama", lambda: self.f_anggaran(a)),
                ("Hapus", "bahaya", lambda: self.tanya("Hapus anggaran %s?" % a["kategori"], lambda: self.hapus(
                    "DELETE FROM anggaran WHERE kategori=?", (a["kategori"],)))),
                ("Batal", "netral", lambda: None)]))
            k.add_widget(Baris(a["kategori"], "%.0f%%" % (pct * 100), w, size=16, bold_kiri=True))
            k.add_widget(Lbl("%s dari %s | sisa %s" % (rp(pakai), rp(a["batas"]), rp(a["batas"] - pakai)), 12, C_ABU))
            k.add_widget(Bar(pct, w))
            self.tambah(k)

    def f_anggaran(self, row=None):
        fields = [
            dict(k="kategori", l="Kategori pengeluaran", t="combo", o=KAT_KELUAR, d=row["kategori"] if row else ""),
            dict(k="batas", l="Batas per bulan (Rp)", t="uang", d=str(int(row["batas"])) if row else ""),
        ]

        def simpan(d):
            kat = d["kategori"].strip()
            if not kat:
                raise ValueError("Kategori tidak boleh kosong.")
            self.db.x("INSERT OR REPLACE INTO anggaran(kategori,batas) VALUES(?,?)", (kat, parse_uang(d["batas"])))

        self.form("Atur Anggaran", fields, simpan)

    # ==================================================================
    # LAPORAN: Laba Rugi, Neraca, Grafik
    # ==================================================================
    def s_laporan(self):
        self.tambah(self.chips([("labarugi", "Laba Rugi"), ("neraca", "Neraca"), ("grafik", "Grafik")],
                               self.tab_lap, self.set_tab_lap))
        if self.tab_lap == "neraca":
            self.lap_neraca()
            return
        self.tambah(self.w_nav_bulan())
        if self.tab_lap == "grafik":
            self.lap_grafik()
        else:
            self.lap_labarugi()

    def set_tab_lap(self, kode):
        self.tab_lap = kode
        self.refresh()

    def lap_labarugi(self):
        d = self.db
        a, z = self.bulan.isoformat(), akhir_bulan(self.bulan).isoformat()
        k = Kartu(pad=16, spacing=dp(3))
        k.add_widget(Lbl("LAPORAN LABA RUGI", 13, C_PRIMER, True))
        k.add_widget(Lbl("Periode %s" % bulan_label(self.bulan), 11, C_ABU))
        k.add_widget(Garis())
        totals = {}
        for tipe, judul, namatot in (("masuk", "PENDAPATAN", "Total Pendapatan"), ("keluar", "BEBAN", "Total Beban")):
            k.add_widget(Widget(size_hint_y=None, height=dp(4)))
            k.add_widget(Lbl(judul, 12, C_ABU, True))
            rows = d.q("SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe=? AND tanggal>=? AND tanggal<=? "
                       "GROUP BY kategori ORDER BY t DESC", (tipe, a, z))
            tot = 0.0
            if not rows:
                k.add_widget(Lbl("   (tidak ada)", 12, C_ABU))
            for r in rows:
                k.add_widget(Baris("   " + r["kategori"], rp(r["t"]), None, 13, bold_kanan=False))
                tot += r["t"]
            k.add_widget(Garis())
            k.add_widget(Baris(namatot, rp(tot), C_HIJAU if tipe == "masuk" else C_MERAH, 14, True))
            totals[tipe] = tot
        laba = totals["masuk"] - totals["keluar"]
        k.add_widget(Garis(2))
        k.add_widget(Baris("LABA (RUGI) BERSIH", rp(laba), C_HIJAU if laba >= 0 else C_MERAH, 15, True))
        if totals["masuk"] > 0:
            k.add_widget(Lbl("Margin: %.0f%% dari pendapatan" % (laba / totals["masuk"] * 100), 11, C_ABU))
        self.tambah(k)
        rows = [(r["kategori"], r["t"]) for r in d.q(
            "SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe='keluar' AND tanggal>=? AND tanggal<=? "
            "GROUP BY kategori ORDER BY t DESC", (a, z))]
        self.tambah(self.w_donat(rows, "Komposisi Beban", "Beban"))

    def lap_neraca(self):
        kas, tab, piut, hut = self.posisi()
        aset = kas + tab + piut
        eku = aset - hut
        k = Kartu(pad=16, spacing=dp(3))
        k.add_widget(Lbl("NERACA (POSISI KEUANGAN)", 13, C_PRIMER, True))
        k.add_widget(Lbl("Per %s" % fmt_tgl(date.today().isoformat()), 11, C_ABU))
        k.add_widget(Garis())
        k.add_widget(Widget(size_hint_y=None, height=dp(4)))
        k.add_widget(Lbl("ASET", 12, C_ABU, True))
        k.add_widget(Baris("   Kas & setara kas", rp(kas), None, 13, bold_kanan=False))
        k.add_widget(Baris("   Tabungan", rp(tab), None, 13, bold_kanan=False))
        k.add_widget(Baris("   Piutang", rp(piut), None, 13, bold_kanan=False))
        k.add_widget(Garis())
        k.add_widget(Baris("Total Aset", rp(aset), C_HIJAU, 14, True))
        k.add_widget(Widget(size_hint_y=None, height=dp(8)))
        k.add_widget(Lbl("KEWAJIBAN", 12, C_ABU, True))
        k.add_widget(Baris("   Hutang", rp(hut), None, 13, bold_kanan=False))
        k.add_widget(Garis())
        k.add_widget(Baris("Total Kewajiban", rp(hut), C_MERAH, 14, True))
        k.add_widget(Widget(size_hint_y=None, height=dp(8)))
        k.add_widget(Lbl("EKUITAS", 12, C_ABU, True))
        k.add_widget(Garis(2))
        k.add_widget(Baris("Kekayaan Bersih", rp(eku), C_HIJAU if eku >= 0 else C_MERAH, 15, True))
        k.add_widget(Lbl("Aset (%s) = Kewajiban (%s) + Ekuitas (%s)" % (rp(aset), rp(hut), rp(eku)), 10, C_ABU))
        self.tambah(k)
        if aset + hut > 0:
            self.tambah(self.w_donat([("Kas", max(kas, 0)), ("Tabungan", tab), ("Piutang", piut)],
                                     "Komposisi Aset", "Aset"))

    def lap_grafik(self):
        self.tambah(self.w_arus(self.bulan, "Tren 6 Bulan (sampai %s)" % bulan_label(self.bulan)))
        a, z = self.bulan.isoformat(), akhir_bulan(self.bulan).isoformat()
        for tipe, judul, ket in (("keluar", "Pengeluaran per Kategori", "Keluar"),
                                 ("masuk", "Pemasukan per Kategori", "Masuk")):
            rows = [(r["kategori"], r["t"]) for r in self.db.q(
                "SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe=? AND tanggal>=? AND tanggal<=? "
                "GROUP BY kategori ORDER BY t DESC", (tipe, a, z))]
            self.tambah(self.w_donat(rows, judul, ket))


# ----------------------------------------------------------------------
class CatatanKeuanganApp(App):
    title = "Catatan Keuangan"

    def build(self):
        if platform in ("linux", "win", "macosx"):
            Window.size = (420, 820)
        self.utama = Utama(self)
        Window.bind(on_keyboard=self._tombol)
        return self.utama

    def on_start(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE])
            except Exception:
                pass

    def on_pause(self):
        return True

    def _tombol(self, window, key, *args):
        if key == 27:
            return self.utama.tombol_kembali_android()
        return False


if __name__ == "__main__":
    CatatanKeuanganApp().run()
