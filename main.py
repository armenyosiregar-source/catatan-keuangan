# -*- coding: utf-8 -*-
"""
CATATAN KEUANGAN (Kivy) - tampilan modern, mode portrait, bisa dijadikan APK.

Fitur: Beranda, Transaksi, Hutang & Piutang, Tabungan, Anggaran, Laporan (grafik),
       Ekspor/Bagikan CSV, Backup database.
Data tersimpan di database SQLite pada folder data aplikasi.
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

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Ellipse
from kivy.graphics.texture import Texture
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, StringProperty
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
# WARNA
# ----------------------------------------------------------------------
C_BG = hx("#F4F5FB")
C_CARD = (1, 1, 1, 1)
C_PRIMER = hx("#4F46E5")
C_UNGU = hx("#7C3AED")
C_HIJAU = hx("#16A34A")
C_TOSCA = hx("#0D9488")
C_MERAH = hx("#E11D48")
C_ORANYE = hx("#F59E0B")
C_BIRU = hx("#0EA5E9")
C_TEKS = hx("#1E1B4B")
C_ABU = hx("#6B7280")
C_FIELD = hx("#EEF0F7")
PUTIH = (1, 1, 1, 1)
PALET = [hx("#4F46E5"), hx("#0EA5E9"), hx("#16A34A"), hx("#F59E0B"),
         hx("#E11D48"), hx("#7C3AED"), hx("#0D9488"), hx("#EA580C")]

KAT_MASUK = ["Gaji", "Bonus", "Usaha", "Hadiah", "Investasi", "Terima Piutang", "Tarik Tabungan", "Lainnya"]
KAT_KELUAR = ["Makan & Minum", "Transportasi", "Belanja", "Tagihan", "Pulsa & Internet",
              "Kesehatan", "Pendidikan", "Hiburan", "Sedekah", "Rumah", "Tabungan",
              "Bayar Hutang", "Lainnya"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]


def tint(c, a=0.12):
    return (1 - a + a * c[0], 1 - a + a * c[1], 1 - a + a * c[2], 1)


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


def parse_uang(s):
    angka = re.sub(r"\D", "", str(s))
    if not angka or int(angka) <= 0:
        raise ValueError("Jumlah harus berupa angka lebih dari 0.")
    return float(angka)


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


# ----------------------------------------------------------------------
# WIDGET DASAR
# ----------------------------------------------------------------------
class Lbl(Label):
    """Label rata kiri yang otomatis membungkus teks & menyesuaikan tinggi."""

    def __init__(self, text="", size=14, warna=None, bold=False, rata="left", **kw):
        kw.setdefault("size_hint_y", None)
        super().__init__(text=text, font_size=sp(size), color=warna or C_TEKS,
                         bold=bold, halign=rata, valign="middle", **kw)
        self.bind(width=self._w, texture_size=self._t)

    def _w(self, *a):
        self.text_size = (self.width, None)

    def _t(self, *a):
        self.height = max(self.texture_size[1], dp(18))


class Kolom(BoxLayout):
    """BoxLayout vertikal yang tingginya menyesuaikan isi."""

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
                Color(0.1, 0.1, 0.3, 0.08)
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
    def __init__(self, warna=None, grad=None, pad=14, radius=18, shadow=True, **kw):
        if "padding" not in kw:
            kw["padding"] = [dp(p) for p in pad] if isinstance(pad, (list, tuple)) else dp(pad)
        kw.setdefault("spacing", dp(6))
        super().__init__(**kw)
        rad = list(radius) if isinstance(radius, (list, tuple)) else [dp(radius)]
        self._sh = None
        with self.canvas.before:
            if shadow:
                Color(0.1, 0.1, 0.3, 0.06)
                self._sh = RoundedRectangle(radius=rad)
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
        self._bg.pos = self.pos
        self._bg.size = self.size


class KartuTap(ButtonBehavior, Kartu):
    pass


class Tombol(ButtonBehavior, Label):
    def __init__(self, text="", warna=None, fg=None, kecil=False, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(38 if kecil else 50))
        super().__init__(text=text, bold=True, font_size=sp(13 if kecil else 15),
                         color=fg or PUTIH, **kw)
        self.warna = warna or C_PRIMER
        with self.canvas.before:
            self._c = Color(*self.warna)
            self._r = RoundedRectangle(radius=[dp(12 if kecil else 14)])
        self.bind(pos=self._u, size=self._u, state=self._s)

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size

    def _s(self, *a):
        w = self.warna
        self._c.rgba = (w[0] * 0.82, w[1] * 0.82, w[2] * 0.82, w[3]) if self.state == "down" else w


class Fab(ButtonBehavior, Label):
    def __init__(self, **kw):
        super().__init__(text="+", font_size=sp(34), bold=True, color=PUTIH,
                         size_hint=(None, None), size=(dp(58), dp(58)), **kw)
        with self.canvas.before:
            Color(0.1, 0.1, 0.3, 0.2)
            self._s = Ellipse()
            self._c = Color(*C_PRIMER)
            self._e = Ellipse()
        self.bind(pos=self._u, size=self._u, state=self._st)

    def _u(self, *a):
        self._s.pos = (self.x, self.y - dp(3))
        self._s.size = self.size
        self._e.pos = self.pos
        self._e.size = self.size

    def _st(self, *a):
        self._c.rgba = C_UNGU if self.state == "down" else C_PRIMER


class Entry(BoxLayout):
    """Kolom isian dengan latar membulat (TextInput dibungkus agar gambarnya tidak rusak)."""
    text = StringProperty("")

    def __init__(self, text="", hint_text="", input_type="text", **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(50))
        super().__init__(padding=[dp(14), 0], **kw)
        self.ti = TextInput(text=text, hint_text=hint_text, input_type=input_type, multiline=False,
                            font_size=sp(16), padding=[0, dp(15), 0, dp(10)],
                            background_normal="", background_active="", background_color=(0, 0, 0, 0),
                            foreground_color=C_TEKS, cursor_color=C_PRIMER,
                            hint_text_color=(0.6, 0.62, 0.7, 1), selection_color=(*C_PRIMER[:3], 0.3))
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
        super().__init__(background_normal="", background_down="", background_color=PUTIH,
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
    """Satu baris: teks kiri + teks kanan (angka)."""

    def __init__(self, kiri, kanan, wk=None, size=14, bold_kiri=False, bold_kanan=True, wkiri=None, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(26), spacing=dp(8), **kw)
        self.k = Lbl(kiri, size, wkiri, bold_kiri, size_hint_y=1)
        self.r = Label(text=kanan, font_size=sp(size), color=wk or C_TEKS, bold=bold_kanan,
                       size_hint=(None, 1))
        self.r.bind(texture_size=lambda i, v: setattr(i, "width", v[0] + dp(2)))
        self.k.bind(texture_size=lambda i, v: setattr(self, "height", max(v[1] + dp(8), dp(26))))
        self.add_widget(self.k)
        self.add_widget(self.r)


class Bar(Widget):
    def __init__(self, pct=0, warna=None, **kw):
        super().__init__(size_hint_y=None, height=dp(10), **kw)
        self.pct = max(0.0, min(float(pct), 1.0))
        with self.canvas:
            Color(*C_FIELD)
            self._t = RoundedRectangle(radius=[dp(5)])
            Color(*(warna or C_PRIMER))
            self._f = RoundedRectangle(radius=[dp(5)])
        self.bind(pos=self._u, size=self._u)

    def _u(self, *a):
        self._t.pos = self.pos
        self._t.size = self.size
        self._f.pos = self.pos
        w = self.width * self.pct
        self._f.size = (max(w, dp(10)) if self.pct > 0 else 0, self.height)


class Avatar(Label):
    def __init__(self, teks, warna, **kw):
        super().__init__(text=(teks[:1] or "?").upper(), bold=True, font_size=sp(17), color=PUTIH,
                         size_hint=(None, None), size=(dp(42), dp(42)), **kw)
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
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(64),
                         padding=[dp(14), dp(8), dp(14), dp(8)], spacing=dp(10), **kw)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._r = Rectangle(texture=gradient(C_PRIMER, C_UNGU))
        self.bind(pos=self._u, size=self._u)
        self.judul = Label(text="", font_size=sp(21), bold=True, color=PUTIH, halign="left", valign="middle")
        self.judul.bind(size=lambda i, s: setattr(i, "text_size", s))

    def _u(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size

    def set(self, teks, kembali=None):
        self.clear_widgets()
        if kembali:
            b = Tombol("<", warna=(1, 1, 1, 0.2), size_hint=(None, None), size=(dp(42), dp(42)),
                       pos_hint={"center_y": 0.5})
            b.bind(on_release=lambda *a: kembali())
            self.add_widget(b)
        self.judul.text = teks
        self.add_widget(self.judul)


class NavItem(ButtonBehavior, Label):
    aktif = BooleanProperty(False)

    def __init__(self, teks, **kw):
        super().__init__(text=teks, font_size=sp(12), bold=True, **kw)
        with self.canvas.before:
            self._c = Color(0, 0, 0, 0)
            self._r = RoundedRectangle(radius=[dp(16)])
        self.bind(pos=self._u, size=self._u, aktif=self._a)
        self._a()

    def _u(self, *a):
        w, h = self.width * 0.86, dp(36)
        self._r.size = (w, h)
        self._r.pos = (self.center_x - w / 2, self.center_y - h / 2)

    def _a(self, *a):
        self.color = C_PRIMER if self.aktif else C_ABU
        self._c.rgba = tint(C_PRIMER, 0.13) if self.aktif else (0, 0, 0, 0)


class Donat(FloatLayout):
    def __init__(self, data, tengah, **kw):
        super().__init__(size_hint_y=None, height=dp(200), **kw)
        self.data = data
        self.lbl = Label(text=tengah, halign="center", color=C_TEKS, font_size=sp(13), bold=True)
        self.add_widget(self.lbl)
        self.bind(pos=self.gambar, size=self.gambar)

    def gambar(self, *a):
        self.canvas.before.clear()
        d = min(self.width, self.height) - dp(10)
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
                for v, c in self.data:
                    Color(*c)
                    sw = 360.0 * v / total
                    Ellipse(pos=(x, y), size=(d, d), angle_start=ang, angle_end=ang + sw)
                    ang += sw
            Color(1, 1, 1, 1)
            lub = d * 0.6
            Ellipse(pos=(self.center_x - lub / 2, self.center_y - lub / 2), size=(lub, lub))


class BarArea(Widget):
    def __init__(self, m, k, maks, **kw):
        super().__init__(**kw)
        self.m, self.k, self.maks = m, k, max(maks, 1)
        self.bind(pos=self.gambar, size=self.gambar)

    def gambar(self, *a):
        self.canvas.clear()
        bw = max((self.width - dp(4)) / 2.0 - dp(2), dp(4))
        cx = self.center_x
        with self.canvas:
            for i, (v, c) in enumerate(((self.m, C_HIJAU), (self.k, C_MERAH))):
                h = max(self.height * v / self.maks, dp(3))
                x = cx - bw - dp(1) if i == 0 else cx + dp(1)
                Color(*c)
                RoundedRectangle(pos=(x, self.y), size=(bw, h), radius=[dp(3)])


# ----------------------------------------------------------------------
# TANGGAL
# ----------------------------------------------------------------------
class TanggalField(Kolom):
    def __init__(self, app, nilai="", opsional=False, **kw):
        super().__init__(spacing=dp(6), **kw)
        self.app = app
        self.nilai = nilai
        self.opsional = opsional
        self.btn = Tombol(fmt_tgl(nilai), warna=C_FIELD, fg=C_TEKS)
        self.btn.bind(on_release=lambda *a: self.buka())
        self.add_widget(self.btn)
        q = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
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
GAYA = {
    "utama": (C_PRIMER, PUTIH),
    "hijau": (C_HIJAU, PUTIH),
    "bahaya": (tint(C_MERAH, 0.12), C_MERAH),
    "netral": (C_FIELD, C_TEKS),
}
TABS = [("ringkasan", "Beranda"), ("transaksi", "Transaksi"), ("hutang", "Hutang"),
        ("tabungan", "Tabungan"), ("lainnya", "Menu")]


class Utama(FloatLayout):
    def __init__(self, app, **kw):
        super().__init__(**kw)
        self.app = app
        self.db = DB(os.path.join(app.user_data_dir, "keuangan.db"))
        self.bulan = date.today().replace(day=1)
        self.filter = "semua"
        self.cari = ""
        self.mode_hutang = "hutang"
        self.layar = ("ringkasan", None)
        self.modals = []

        utama = BoxLayout(orientation="vertical")
        self.header = Header()
        self.sv = ScrollView(do_scroll_x=False, bar_width=dp(3), bar_color=(*C_PRIMER[:3], 0.5))
        self.box = Kolom(padding=[dp(14), dp(14), dp(14), dp(110)], spacing=dp(12))
        self.sv.add_widget(self.box)
        nav = Lapisan(orientation="horizontal", size_hint_y=None, height=dp(62), warna=PUTIH,
                      garis=True, padding=[dp(6), dp(4)])
        self.nav_items = {}
        for kode, teks in TABS:
            n = NavItem(teks)
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
        if sub == "anggaran":
            self.header.set("Anggaran Bulanan", lambda: self.buka("lainnya"))
            self.s_anggaran()
        elif sub == "laporan":
            self.header.set("Laporan Keuangan", lambda: self.buka("lainnya"))
            self.s_laporan()
        else:
            judul = {"ringkasan": "Catatan Keuangan", "transaksi": "Transaksi",
                     "hutang": "Hutang & Piutang", "tabungan": "Rencana Tabungan",
                     "lainnya": "Menu"}[kode]
            self.header.set(judul)
            getattr(self, "s_" + kode)()
        if reset:
            self.sv.scroll_y = 1

    def geser(self, n):
        m = self.bulan.month - 1 + n
        self.bulan = date(self.bulan.year + m // 12, m % 12 + 1, 1)
        self.refresh()

    def tambah(self, w):
        self.box.add_widget(w)
        return w

    def seksi(self, teks):
        self.tambah(Lbl(teks, 15, C_TEKS, True))

    # ---------- modal ----------
    def modal(self, isi, anchor="center", ukuran=(0.92, None), luar=True):
        mv = ModalView(size_hint=ukuran, auto_dismiss=luar, background="", background_color=(0, 0, 0, 0),
                       overlay_color=(0, 0, 0, 0.45), anchor_y=anchor)
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
        for teks, gaya, fn in opsi:
            bg, fg = GAYA[gaya]
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
        """Dipanggil saat tombol Back ditekan. True = sudah ditangani."""
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
        bawah = Lapisan(orientation="vertical", size_hint_y=None, height=dp(76), warna=PUTIH, garis=True,
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

    # ==================================================================
    # BERANDA
    # ==================================================================
    def s_ringkasan(self):
        d = self.db
        hari = date.today()
        bl = hari.strftime("%Y-%m")
        tm = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk'")
        tk_ = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar'")
        m = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk' AND substr(tanggal,1,7)=?", (bl,))
        k = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND substr(tanggal,1,7)=?", (bl,))

        hero = Kartu(grad=(C_PRIMER, C_UNGU), pad=20, spacing=dp(4))
        hero.add_widget(Lbl("Total Saldo", 13, (1, 1, 1, 0.8)))
        hero.add_widget(Lbl(rp(tm - tk_), 30, PUTIH, True))
        hero.add_widget(Widget(size_hint_y=None, height=dp(8)))
        hero.add_widget(Lbl("Bulan " + bulan_label(hari), 12, (1, 1, 1, 0.75)))
        row = BoxLayout(size_hint_y=None, height=dp(66), spacing=dp(10))
        for judul, nilai in (("Pemasukan", m), ("Pengeluaran", k)):
            c = Kartu(warna=(1, 1, 1, 0.17), shadow=False, pad=12, radius=14, spacing=dp(2))
            c.add_widget(Lbl(judul, 12, (1, 1, 1, 0.85)))
            c.add_widget(Lbl(rp(nilai), 15, PUTIH, True))
            row.add_widget(c)
        hero.add_widget(row)
        self.tambah(hero)

        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for teks, c, fn in (("+ Pemasukan", C_HIJAU, lambda: self.f_transaksi("masuk")),
                            ("+ Pengeluaran", C_MERAH, lambda: self.f_transaksi("keluar")),
                            ("+ Hutang / Piutang", C_ORANYE, lambda: self.f_hutang()),
                            ("+ Tabungan", C_BIRU, lambda: self.f_tabungan())):
            b = Tombol(teks, warna=tint(c, 0.14), fg=c)
            b.bind(on_release=lambda i, fn=fn: fn())
            grid.add_widget(b)
        self.tambah(grid)

        sh = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis='hutang' AND jumlah>terbayar")
        sp_ = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis='piutang' AND jumlah>terbayar")
        tab = d.val("SELECT SUM(terkumpul) FROM tabungan")
        c = Kartu(pad=16, spacing=dp(4))
        c.add_widget(Lbl("Posisi Keuangan", 15, bold=True))
        c.add_widget(Baris("Hutang saya", rp(sh), C_MERAH))
        c.add_widget(Baris("Piutang", rp(sp_), C_HIJAU))
        c.add_widget(Baris("Total tabungan", rp(tab), C_PRIMER))
        self.tambah(c)

        pesan = []
        batas = (hari + timedelta(days=7)).isoformat()
        for r in d.q("SELECT * FROM hutang WHERE jumlah>terbayar AND jatuh_tempo<>'' AND jatuh_tempo<=? "
                     "ORDER BY jatuh_tempo", (batas,)):
            jenis = "Hutang ke" if r["jenis"] == "hutang" else "Piutang dari"
            st = "TERLAMBAT" if r["jatuh_tempo"] < hari.isoformat() else "segera"
            pesan.append("%s %s: %s, jatuh tempo %s (%s)" % (
                jenis, r["nama"], rp(r["jumlah"] - r["terbayar"]), fmt_tgl(r["jatuh_tempo"]), st))
        for a in d.q("SELECT * FROM anggaran"):
            pakai = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND kategori=? "
                          "AND substr(tanggal,1,7)=?", (a["kategori"], bl))
            if a["batas"] > 0 and pakai >= 0.8 * a["batas"]:
                pesan.append("Anggaran %s terpakai %.0f%% (%s dari %s)" % (
                    a["kategori"], pakai / a["batas"] * 100, rp(pakai), rp(a["batas"])))
        if pesan:
            c = Kartu(warna=tint(C_ORANYE, 0.14), shadow=False, pad=16, spacing=dp(6))
            c.add_widget(Lbl("Perhatian", 15, hx("#B45309"), True))
            for p in pesan:
                c.add_widget(Lbl("- " + p, 13, hx("#78350F")))
            self.tambah(c)

        top = d.q("SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe='keluar' AND substr(tanggal,1,7)=? "
                  "GROUP BY kategori ORDER BY t DESC LIMIT 3", (bl,))
        if top:
            c = Kartu(pad=16, spacing=dp(2))
            c.add_widget(Lbl("Pengeluaran terbesar bulan ini", 15, bold=True))
            for r in top:
                c.add_widget(Baris(r["kategori"], rp(r["t"])))
                c.add_widget(Bar(r["t"] / k if k else 0, warna_kat(r["kategori"])))
            self.tambah(c)

        terakhir = d.q("SELECT * FROM transaksi ORDER BY tanggal DESC, id DESC LIMIT 5")
        if terakhir:
            self.seksi("Transaksi terakhir")
            for r in terakhir:
                self.tambah(self.baris_tx(r))
        else:
            c = Kartu(pad=20)
            c.add_widget(Lbl("Selamat datang!", 17, bold=True))
            c.add_widget(Lbl("Mulai dengan menekan tombol + untuk mencatat pemasukan atau pengeluaran pertama Anda.",
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
                           size_hint=(1, None), height=dp(38)))
        k.add_widget(b)
        return k

    def s_transaksi(self):
        d = self.db
        bl = self.bulan.strftime("%Y-%m")
        self.tambah(self.w_nav_bulan())
        m = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk' AND substr(tanggal,1,7)=?", (bl,))
        k = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND substr(tanggal,1,7)=?", (bl,))
        row = BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(8))
        for judul, nilai, c in (("Masuk", m, C_HIJAU), ("Keluar", k, C_MERAH),
                                ("Selisih", m - k, C_HIJAU if m >= k else C_MERAH)):
            s = Kartu(pad=10, spacing=dp(2))
            s.add_widget(Lbl(judul, 12, C_ABU, rata="center"))
            s.add_widget(Lbl(rp(nilai), 12, c, True, rata="center"))
            row.add_widget(s)
        self.tambah(row)

        ch = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        for kode, teks in (("semua", "Semua"), ("masuk", "Pemasukan"), ("keluar", "Pengeluaran")):
            aktif = self.filter == kode
            b = Tombol(teks, warna=C_PRIMER if aktif else C_FIELD, fg=PUTIH if aktif else C_TEKS, kecil=True)
            b.bind(on_release=lambda i, kd=kode: self.set_filter(kd))
            ch.add_widget(b)
        self.tambah(ch)

        e = Entry(hint_text="Cari kategori atau catatan...", text=self.cari)
        e.bind(text=self._cari_berubah)
        self.tambah(e)
        self.daftar = Kolom(spacing=dp(10))
        self.tambah(self.daftar)
        self.isi_tx()

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
        t = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        for kode, teks in (("hutang", "Hutang Saya"), ("piutang", "Piutang")):
            aktif = mode == kode
            b = Tombol(teks, warna=C_PRIMER if aktif else C_FIELD, fg=PUTIH if aktif else C_TEKS)
            b.bind(on_release=lambda i, kd=kode: self.set_mode(kd))
            t.add_widget(b)
        self.tambah(t)

        sisa = d.val("SELECT SUM(jumlah-terbayar) FROM hutang WHERE jenis=? AND jumlah>terbayar", (mode,))
        warna = (C_MERAH, hx("#F97316")) if mode == "hutang" else (C_HIJAU, C_TOSCA)
        hero = Kartu(grad=warna, pad=20, spacing=dp(2))
        hero.add_widget(Lbl("Uang yang harus saya bayar" if mode == "hutang"
                            else "Uang saya yang belum dikembalikan", 13, (1, 1, 1, 0.85)))
        hero.add_widget(Lbl(rp(sisa), 28, PUTIH, True))
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
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
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
            if not row and self.layar[0] != "hutang":
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
        hero = Kartu(grad=(C_BIRU, C_PRIMER), pad=20, spacing=dp(2))
        hero.add_widget(Lbl("Total tabungan", 13, (1, 1, 1, 0.85)))
        hero.add_widget(Lbl(rp(total), 28, PUTIH, True))
        if target:
            hero.add_widget(Lbl("dari target %s" % rp(target), 12, (1, 1, 1, 0.85)))
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
        row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        for teks, w, fn in (("Setor", C_HIJAU, lambda: self.f_setor(r, "setor")),
                            ("Tarik", C_ORANYE, lambda: self.f_setor(r, "tarik")),
                            ("Opsi", C_FIELD, lambda: self.opsi_tabungan(r))):
            b = Tombol(teks, warna=w, fg=C_TEKS if w == C_FIELD else PUTIH, kecil=True)
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
    # MENU LAINNYA
    # ==================================================================
    def menu_tambah(self):
        self.sheet("Tambah catatan baru", [
            ("Pemasukan", "hijau", lambda: self.f_transaksi("masuk")),
            ("Pengeluaran", "bahaya", lambda: self.f_transaksi("keluar")),
            ("Hutang / Piutang", "utama", lambda: self.f_hutang()),
            ("Target Tabungan", "netral", lambda: self.f_tabungan())])

    def s_lainnya(self):
        items = [
            ("Anggaran Bulanan", "Batasi pengeluaran per kategori", lambda: self.buka("lainnya", "anggaran")),
            ("Laporan Keuangan", "Grafik per kategori & tren 6 bulan", lambda: self.buka("lainnya", "laporan")),
            ("Ekspor & Bagikan Data", "CSV untuk Excel / WhatsApp / Email", self.menu_ekspor),
            ("Backup Database", "Simpan salinan data Anda", self.backup_db),
            ("Panduan & Tentang", "Cara memakai aplikasi", self.panduan),
            ("Hapus Semua Data", "Mulai dari nol (tidak bisa dibatalkan)", self.hapus_semua),
        ]
        for judul, ket, fn in items:
            k = KartuTap(orientation="horizontal", pad=16, spacing=dp(10))
            kol = Kolom(spacing=dp(2))
            bahaya = judul.startswith("Hapus")
            kol.add_widget(Lbl(judul, 15, C_MERAH if bahaya else C_TEKS, True))
            kol.add_widget(Lbl(ket, 12, C_ABU))
            k.add_widget(kol)
            pan = Label(text=">", font_size=sp(20), bold=True, color=C_ABU, size_hint=(None, None),
                        size=(dp(20), dp(20)), pos_hint={"center_y": 0.5})
            k.add_widget(pan)
            k.bind(on_release=lambda i, fn=fn: fn())
            self.tambah(k)

    def panduan(self):
        self.halaman_info("Panduan & Tentang", [
            ("Beranda", "Lihat saldo, ringkasan bulan ini, hutang, piutang, tabungan, dan peringatan jatuh tempo / anggaran. "
                        "Tombol + di kanan bawah untuk menambah catatan baru dengan cepat."),
            ("Transaksi", "Catat pemasukan & pengeluaran. Ketuk satu transaksi untuk mengubah atau menghapus. "
                          "Gunakan tombol < > untuk pindah bulan."),
            ("Hutang & Piutang", "Hutang Saya = yang harus Anda bayar. Piutang = uang Anda yang dipinjam orang lain. "
                                 "Tekan Bayar/Terima untuk mencatat cicilan; bisa sekaligus dicatat ke transaksi."),
            ("Tabungan", "Buat target, lalu Setor/Tarik. Aplikasi menghitung saran jumlah nabung per bulan jika tenggat diisi."),
            ("Anggaran & Laporan", "Atur batas pengeluaran per kategori. Laporan menampilkan grafik donat dan tren 6 bulan."),
            ("Data Anda", "Data tersimpan di HP ini. Jika aplikasi dihapus, data ikut hilang, "
                          "jadi rutin gunakan Ekspor & Bagikan Data atau Backup Database."),
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
    # LAPORAN
    # ==================================================================
    def s_laporan(self):
        d = self.db
        bl = self.bulan.strftime("%Y-%m")
        self.tambah(self.w_nav_bulan())
        m = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk' AND substr(tanggal,1,7)=?", (bl,))
        k = d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND substr(tanggal,1,7)=?", (bl,))
        c = Kartu(pad=16, spacing=dp(4))
        c.add_widget(Baris("Total pemasukan", rp(m), C_HIJAU))
        c.add_widget(Baris("Total pengeluaran", rp(k), C_MERAH))
        c.add_widget(Baris("Sisa (selisih)", rp(m - k), C_HIJAU if m >= k else C_MERAH))
        if m > 0:
            c.add_widget(Baris("Rasio tabungan", "%.0f%%" % ((m - k) / m * 100), C_PRIMER))
        self.tambah(c)

        for tipe, judul, total in (("keluar", "Pengeluaran per kategori", k), ("masuk", "Pemasukan per kategori", m)):
            rows = d.q("SELECT kategori, SUM(jumlah) t FROM transaksi WHERE tipe=? AND substr(tanggal,1,7)=? "
                       "GROUP BY kategori ORDER BY t DESC", (tipe, bl))
            c = Kartu(pad=16, spacing=dp(4))
            c.add_widget(Lbl(judul, 15, bold=True))
            if not rows:
                c.add_widget(Lbl("Tidak ada data.", 13, C_ABU))
            else:
                c.add_widget(Donat([(r["t"], PALET[i % len(PALET)]) for i, r in enumerate(rows)],
                                   "Total\n" + rp(total)))
                for i, r in enumerate(rows):
                    row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
                    dot = Dot(PALET[i % len(PALET)], pos_hint={"center_y": 0.5})
                    row.add_widget(dot)
                    row.add_widget(Lbl(r["kategori"], 13, size_hint_y=1))
                    pc = Label(text="%s (%.0f%%)" % (rp(r["t"]), r["t"] / total * 100 if total else 0),
                               font_size=sp(13), bold=True, color=C_TEKS, size_hint=(None, 1))
                    pc.bind(texture_size=lambda inst, v: setattr(inst, "width", v[0] + dp(2)))
                    row.add_widget(pc)
                    c.add_widget(row)
            self.tambah(c)

        data = []
        for i in range(5, -1, -1):
            mm = self.bulan.month - 1 - i
            tgl = date(self.bulan.year + mm // 12, mm % 12 + 1, 1)
            b_ = tgl.strftime("%Y-%m")
            data.append((BULAN[tgl.month - 1][:3],
                         d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='masuk' AND substr(tanggal,1,7)=?", (b_,)),
                         d.val("SELECT SUM(jumlah) FROM transaksi WHERE tipe='keluar' AND substr(tanggal,1,7)=?", (b_,))))
        maks = max([max(a, b) for _, a, b in data] + [1])
        c = Kartu(pad=16, spacing=dp(6))
        c.add_widget(Lbl("Tren 6 bulan terakhir", 15, bold=True))
        lg = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(6))
        lg.add_widget(Dot(C_HIJAU, pos_hint={"center_y": 0.5}))
        lg.add_widget(Lbl("Masuk", 12, C_ABU, size_hint_y=1))
        lg.add_widget(Dot(C_MERAH, pos_hint={"center_y": 0.5}))
        lg.add_widget(Lbl("Keluar", 12, C_ABU, size_hint_y=1))
        c.add_widget(lg)
        tren = BoxLayout(size_hint_y=None, height=dp(170), spacing=dp(4))
        for nama, a, b in data:
            kol = BoxLayout(orientation="vertical", spacing=dp(4))
            kol.add_widget(BarArea(a, b, maks))
            kol.add_widget(Label(text=nama, font_size=sp(11), color=C_ABU, size_hint_y=None, height=dp(16)))
            tren.add_widget(kol)
        c.add_widget(tren)
        self.tambah(c)


# ----------------------------------------------------------------------
class CatatanKeuanganApp(App):
    title = "Catatan Keuangan"

    def build(self):
        Window.clearcolor = C_BG
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
        if key == 27:  # tombol Back
            return self.utama.tombol_kembali_android()
        return False


if __name__ == "__main__":
    CatatanKeuanganApp().run()
