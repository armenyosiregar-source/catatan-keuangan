[app]
title = Catatan Keuangan
package.name = catatankeuangan
package.domain = org.keuanganku
source.dir = .
source.include_exts = py,png
version = 1.0
requirements = python3,kivy==2.3.0,sqlite3,pyjnius
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.color = #4F46E5
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
