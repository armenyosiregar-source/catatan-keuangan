[app]

# ---- Informasi aplikasi ----
title = Catatan Keuangan
package.name = catatankeuangan
package.domain = org.keuanganku
version = 1.0

# ---- Sumber kode ----
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = .git,.github,bin,.buildozer

# ---- Library (versi dikunci agar build stabil) ----
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,sqlite3,pyjnius

# ---- Tampilan ----
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.color = #4F46E5

# ---- Android ----
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

# ---- python-for-android (versi stabil) ----
p4a.branch = v2024.01.21


[buildozer]

log_level = 2
warn_on_root = 1
