#!/bin/bash
if [ ! -f "main.py" ]; then
echo "错误：请在项目根目录（包含 main.py）执行此脚本"
exit 1
fi
set -e
mkdir -p debian/source
# ========== control 修复：移除未使用的替换变量，Build‑Depends恢复dh‑python ==========
cat > debian/control <<'EOF'
Source: scrcpy-cast-gtk
Section: utils
Priority: optional
Maintainer: usbipad <1495941192+usbipad@users.noreply.github.com>
Build-Depends: debhelper-compat (= 13), dh-python
Standards-Version: 4.6.0
Homepage: https://github.com/usbipad/scrcpy-cast-gtk

Package: scrcpy-cast-gtk
Architecture: all
Depends: ${misc:Depends},
         python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, adb, scrcpy
Description: GTK frontend for scrcpy
 A simple GTK4 GUI to cast Android screen via scrcpy.
 Supports USB, WiFi (USB auth) and Wireless Debug (Android 11+).
 Depends on system‑installed scrcpy and adb.
EOF
# ========== copyright Expat(MIT) ==========
cat > debian/copyright <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: scrcpy-cast-gtk
Source: https://github.com/usbipad/scrcpy-cast-gtk
Files: *
Copyright: 2026 usbipad <1495941192+usbipad@users.noreply.github.com>
License: Expat
EOF
# ========== changelog 版本1.1.0 ==========
cat > debian/changelog <<'EOF'
scrcpy-cast-gtk (1.1.0) unstable; urgency=medium
  * Feature: Migrate to Adw.Application, real‑time light/dark theme via libadwaita
  * Add gir1.2-adw-1 runtime dependency
  * Minimum supported Debian version: 12 Bookworm (Debian11 unsupported)
  * Build as Architecture: all, pure python GUI package
  * Remove bundled binary support, depend on system scrcpy+adb
  * Install project LICENSE into /usr/share/doc
  * License: Expat(MIT)
  * Fix dpkg-gencontrol warnings: drop unused substitution variables
 -- usbipad <1495941192+usbipad@users.noreply.github.com>  Thu, 11 Sep 2026 20:00:00 +0800
EOF
# ========== source/format ==========
echo "3.0 (native)" > debian/source/format
# ========== desktop ==========
cat > debian/scrcpy-cast-gtk.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Scrcpy Cast GTK
Name[zh_CN]=Scrcpy投屏
Comment=Mirror and control Android devices via scrcpy
Comment[zh_CN]=投屏并控制 Android 设备
Exec=scrcpy-cast-gtk
Icon=scrcpy-cast-gtk
Terminal=false
Categories=Utility;AudioVideo;
Keywords=scrcpy;cast;mirror;android;投屏;
StartupWMClass=io.github.usbipad.scrcpycastgtk
StartupNotify=true
EOF
# ========== wrapper ==========
cat > debian/scrcpy-cast-gtk-wrapper <<'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/lib/scrcpy-cast-gtk/main.py "$@"
EOF
chmod +x debian/scrcpy-cast-gtk-wrapper
# ========== rules ==========
cat > debian/rules <<'RULES'
#!/usr/bin/make -f
%:
	dh $@
override_dh_install:
	# 安装主python程序
	mkdir -p debian/scrcpy-cast-gtk/usr/lib/scrcpy-cast-gtk
	install -D -m 755 main.py debian/scrcpy-cast-gtk/usr/lib/scrcpy-cast-gtk/main.py
	# 私有图标资源
	mkdir -p debian/scrcpy-cast-gtk/usr/lib/scrcpy-cast-gtk/icon-res
	cp icon/hicolor/scrcpy-cast-gtk/256x256/apps/scrcpy-cast-gtk.png debian/scrcpy-cast-gtk/usr/lib/scrcpy-cast-gtk/icon-res/scrcpy.png
	# 系统hicolor图标
	for size in 48x48 128x128 256x256; do \
		mkdir -p debian/scrcpy-cast-gtk/usr/share/icons/hicolor/$$size/apps; \
		cp icon/hicolor/scrcpy-cast-gtk/$$size/apps/scrcpy-cast-gtk.png debian/scrcpy-cast-gtk/usr/share/icons/hicolor/$$size/apps/; \
	done
	# desktop文件与wrapper启动脚本
	mkdir -p debian/scrcpy-cast-gtk/usr/share/applications
	cp debian/scrcpy-cast-gtk.desktop debian/scrcpy-cast-gtk/usr/share/applications/io.github.usbipad.scrcpycastgtk.desktop
	mkdir -p debian/scrcpy-cast-gtk/usr/bin
	cp debian/scrcpy-cast-gtk-wrapper debian/scrcpy-cast-gtk/usr/bin/scrcpy-cast-gtk
	chmod 755 debian/scrcpy-cast-gtk/usr/bin/scrcpy-cast-gtk
	# 将仓库根目录MIT LICENSE打入deb文档目录
	mkdir -p debian/scrcpy-cast-gtk/usr/share/doc/scrcpy-cast-gtk
	install -m 644 LICENSE debian/scrcpy-cast-gtk/usr/share/doc/scrcpy-cast-gtk/LICENSE
	dh_install
RULES
chmod +x debian/rules
# ========== postinst ==========
cat > debian/postinst <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if [ -d /usr/share/icons/hicolor ]; then
        gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
    fi
fi
EOF
chmod +x debian/postinst
# ========== prerm ==========
cat > debian/prerm <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] && [ -d /usr/share/icons/hicolor ]; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
fi
EOF
chmod +x debian/prerm
# ========== 构建deb ==========
dpkg-buildpackage -b -uc -us
# ========== 构建完成后：清理debhelper临时文件，保留debian配置文件 ==========
rm -rf debian/scrcpy-cast-gtk
rm -rf debian/.debhelper
rm -f debian/debhelper-build-stamp
rm -f debian/files
rm -f debian/*.substvars
rm -f debian/*.debhelper.log
echo "=========================================="
echo "✅ 构建完成，已自动清理debian内部构建临时文件"
echo "生成的 .deb 文件位于上级目录："
ls -lh ../scrcpy-cast-gtk_*.deb
echo
echo "安装命令："
echo "  sudo apt remove scrcpy-cast-gtk   # 如果已安装旧版"
echo "  sudo apt install ./../scrcpy-cast-gtk_*.deb"
echo
echo "此包为 Architecture: all，依赖系统 scrcpy + adb + gir1.2-adw-1"
