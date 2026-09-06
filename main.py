#! /usr/bin/python3
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Pango, Gio, GObject
import threading
import subprocess
import re
import os
import shutil
from datetime import datetime
import configparser
import platform
import logging
import time
import tempfile
import sys
from typing import List, Optional, Tuple, Set
from logging.handlers import RotatingFileHandler

# ========================== 日志系统 ==========================
LOG_DIR = os.path.join(os.path.expanduser("~"), ".config", "scrcpy-cast-gtk")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "log.txt")

_log_lock = threading.Lock()
handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

def safe_log(level: int, msg: str, *args, **kwargs):
    with _log_lock:
        logger.log(level, msg, *args, **kwargs)

os.chmod(LOG_FILE, 0o600)

# ========================== 国际化 ==========================
def _get_system_lang():
    lang_env = os.environ.get("LANG", "en_US.UTF-8")
    return lang_env.split("_")[0].lower()

SYS_LANG = _get_system_lang()
_TRANSLATIONS = {
    "zh": {
        "app_title": "Scrcpy投屏",
        "work_mode": "工作模式",
        "usb_mode": "USB直连模式",
        "wireless_mode": "无线连接模式",
        "wireless_usb_auth": "无线USB授权",
        "wireless_debug_auth": "无线调试授权（Android11+）",
        "settings": "参数设置",
        "video_codec": "视频编码",
        "h264_default": "H.264(默认)",
        "h265_hevc": "H.265(HEVC)",
        "max_resolution": "最大分辨率",
        "unlimited": "不限制",
        "max_fps": "最大帧率",
        "auto_unlimited": "自动(不限)",
        "enable_audio": "开启音频",
        "audio_quality": "音频品质",
        "default_opus128": "默认(Opus-128K)",
        "opus256": "Opus-256K",
        "aac256": "AAC-256K",
        "flac_lossless": "FLAC(无损)",
        "screen_off_cast": "息屏投屏",
        "record_screen": "录制屏幕",
        "select_dir": "选择目录",
        "current_record_dir": "当前录屏目录：",
        "record_hint": "开启【录制屏幕】，投屏时同步录制视频",
        "bottom_tip": "提示：部分手机不支持FLAC无损编码，出现无音频请切换其他编码尝试。",
        "help": "帮助",
        "start": "开始",
        "help_title": "模式帮助说明",
        "close": "关闭",
        "usb_cast_title": "USB投屏",
        "usb_wait_text": "请插入手机USB，并在手机点击【允许USB调试授权】\n检测到设备自动继续",
        "wifi_usb_cast_title": "WiFi无线投屏-USB授权",
        "connecting_text": "正在建立WiFi-ADB连接，正在切换TCP模式、建立网络连接，请稍候…",
        "get_ip_fail": "获取IP失败，无法自动读取手机WLAN IP\n请手动输入手机内网IP：",
        "port_open_fail": "端口开启失败，手机端端口 {port} 开启失败\n{err}\n可能端口占用或权限不足",
        "connect_success": "连接成功，建议拔出 USB 数据线开始投屏。",
        "connect_fail_msg": "WiFi-ADB连接失败，多次尝试连接 {addr} 失败\n返回：{out}\n{err}\n\n排查：\n1.电脑手机同一WiFi\n2.端口{port}未被占用\n3.防火墙未拦截\n\n是否重试连接？",
        "wireless_debug_title": "无线调试说明",
        "wireless_debug_desc": "手机开发者选项打开【无线调试】\n完成配对，填写无线调试页面显示的 IP:端口\n示例：192.168.1.51:41023\n手机重启端口会变化，需要重新填写",
        "input_wireless_addr": "输入手机无线调试地址，IP:端口",
        "empty_addr": "输入为空，请输入完整的 IP:端口 地址",
        "format_error": "格式错误，请输入 IP:端口，例如 192.168.1.100:41023",
        "connecting_wireless": "正在连接无线调试，正在执行adb connect，请稍候…",
        "wireless_connect_fail": "连接失败，连接返回信息：{out}\n{err}\n\n排查方向：\n1.同一WiFi局域网\n2.无线调试已开启\n3.地址格式 IP:端口 正确\n4.配对码配对是否已完成\n\n是否重新输入地址并重试？",
        "select_record_dir_title": "选择录屏保存目录",
        "save_record_title": "保存录制视频",
        "mkv_video_file": "MKV视频文件",
        "help_usb": "【USB直连模式】\n特点：延迟低，稳定性最好，适合日常使用。\n连接方式：\n1.手机进入设置-关于手机，连续点击版本号开启开发者选项\n2.开发者选项内打开【USB调试】\n3.数据线连接手机与电脑，手机弹窗允许USB调试授权",
        "help_wifi_usb": "【无线USB授权】\n先USB数据线完成调试授权，拔掉数据线后WiFi投屏。\n注意：无线环境会受WiFi质量影响。\n连接方式：\n1.开启手机开发者选项，打开【USB调试】\n2.数据线连接电脑，完成USB调试授权\n3.授权成功后可以拔掉数据线进行WiFi投屏",
        "help_wifi_debug": "【无线调试授权（Android11+）】\n无需USB线，要求手机Android11及以上版本。\n连接方式：\n1.开启手机开发者选项\n2.开发者选项内打开【无线调试】\n3.进入无线调试页面，获取IP和端口填入软件弹窗",
        "help_no_mode": "请先选择一个工作模式。",
        "dep_missing_title": "依赖缺失",
        "dep_missing_msg": "程序检测不到依赖程序：{tool}\n请先安装 adb 和 scrcpy 并确保在系统PATH环境变量中。",
        "multiple_ips_title": "检测到多个IP",
        "multiple_ips_msg": "手机有多个IP地址，请选择用于投屏的IP：",
        "record_dir_not_writable": "录屏目录不可写或无足够空间（至少需要100MB）",
        "record_dir_error": "录屏目录异常",
        "generic_error": "操作失败，请查看日志：{}",
        "timeout_wait_ip": "等待选择IP超时（30秒），操作已取消",
        "timeout_wait_device": "等待USB设备超时（120秒），操作已取消",
        "select_device_title": "选择设备",
        "select_device_msg": "检测到多个 USB 设备，请选择要投屏的设备：",
        "timeout_select_device": "选择设备超时（30秒），操作已取消",
        "usb_device_label": "USB设备：",
        "no_usb_device": "未检测到USB设备",
        "low_sdk_title": "低版本Android系统",
        "low_sdk_msg": "当前设备Android版本低于11，不支持系统音频转发，音频选项已禁用",
        "device_disconnected_title": "设备断开",
        "device_disconnected_msg": "设备已断开连接",
        "keep_active": "投屏常亮",
        "keep_active_desc": "通过模拟用户活动防止设备自动息屏"
    },
    "en": {
        "app_title": "Scrcpy-Cast-GTK",
        "work_mode": "Work Mode",
        "usb_mode": "USB Direct Mode",
        "wireless_mode": "Wireless Mode",
        "wireless_usb_auth": "Wireless USB Auth",
        "wireless_debug_auth": "Wireless Debug (Android 11+)",
        "settings": "Settings",
        "video_codec": "Video Codec",
        "h264_default": "H.264 (Default)",
        "h265_hevc": "H.265 (HEVC)",
        "max_resolution": "Max Resolution",
        "unlimited": "Unlimited",
        "max_fps": "Max FPS",
        "auto_unlimited": "Auto (Unlimited)",
        "enable_audio": "Enable Audio",
        "audio_quality": "Audio Quality",
        "default_opus128": "Default (Opus-128K)",
        "opus256": "Opus-256K",
        "aac256": "AAC-256K",
        "flac_lossless": "FLAC (Lossless)",
        "screen_off_cast": "Screen Off Cast",
        "record_screen": "Record Screen",
        "select_dir": "Select Folder",
        "current_record_dir": "Record Dir: ",
        "record_hint": "Enable [Record Screen] to record while casting",
        "bottom_tip": "Note: Some devices do not support FLAC. Switch codec if no audio. Keep-active simulates user activity to prevent device screen off, works over wireless as well.",
        "help": "Help",
        "start": "Start",
        "help_title": "Mode Help",
        "close": "Close",
        "usb_cast_title": "USB Cast",
        "usb_wait_text": "Plug in USB and allow USB debugging on your phone.\nWaiting for device...",
        "wifi_usb_cast_title": "WiFi Cast - USB Auth",
        "connecting_text": "Establishing WiFi-ADB connection, switching to TCP mode...",
        "get_ip_fail": "Failed to get device IP.\nPlease enter device LAN IP manually:",
        "port_open_fail": "Port open failed. Port {port} error:\n{err}\nMay be occupied or permission denied.",
        "connect_success": "Connected. Unplug USB cable to start casting.",
        "connect_fail_msg": "WiFi-ADB connection failed. {addr} retries exhausted.\nOutput: {out}\nError: {err}\n\nTroubleshooting:\n1. Same WiFi network\n2. Port {port} not occupied\n3. Firewall not blocking\n\nRetry?",
        "wireless_debug_title": "Wireless Debug Guide",
        "wireless_debug_desc": "Enable Wireless Debug in developer options.\nPair first, then enter IP:port from debug page.\nExample: 192.168.1.51:41023\nPort changes after reboot.",
        "input_wireless_addr": "Enter wireless debug address (IP:port)",
        "empty_addr": "Address cannot be empty.",
        "format_error": "Invalid format. Use IP:port, e.g. 192.168.1.100:41023",
        "connecting_wireless": "Connecting via adb connect...",
        "wireless_connect_fail": "Connection failed.\nOutput: {out}\nError: {err}\n\nTroubleshooting:\n1. Same WiFi network\n2. Wireless debug enabled\n3. Correct IP:port format\n4. Pairing completed\n\nRetry with new address?",
        "select_record_dir_title": "Select Record Folder",
        "save_record_title": "Save Recording",
        "mkv_video_file": "MKV Video",
        "help_usb": "[USB Direct Mode]\nLow latency, most stable.\nHow to use:\n1. Go to Settings - About phone, tap build number to enable developer options.\n2. Enable USB debugging.\n3. Connect phone to PC via USB, allow debugging on phone.",
        "help_wifi_usb": "[Wireless USB Auth]\nAuthorize via USB first, then cast over WiFi.\nNote: Quality depends on WiFi signal.\nHow to use:\n1. Enable USB debugging on phone.\n2. Connect to PC via USB, authorize.\n3. Unplug cable to cast wirelessly.",
        "help_wifi_debug": "[Wireless Debug (Android 11+)]\nNo USB cable required, Android 11+ only.\nHow to use:\n1. Enable developer options.\n2. Enable Wireless debugging.\n3. Get IP:port from debug page and enter here.",
        "help_no_mode": "Please select a mode first.",
        "dep_missing_title": "Dependency Missing",
        "dep_missing_msg": "Tool not found: {tool}\nPlease install adb and scrcpy and ensure they are in system PATH.",
        "multiple_ips_title": "Multiple IPs Detected",
        "multiple_ips_msg": "Phone has multiple IPs, please select one for casting:",
        "record_dir_not_writable": "Record directory is not writable or has insufficient space (need at least 100MB)",
        "record_dir_error": "Record directory error",
        "generic_error": "Operation failed, see log: {}",
        "timeout_wait_ip": "IP selection timeout (30s), operation cancelled",
        "timeout_wait_device": "USB device wait timeout (120s), operation cancelled",
        "select_device_title": "Select Device",
        "select_device_msg": "Multiple USB devices detected, please select one:",
        "timeout_select_device": "Device selection timeout (30s), operation cancelled",
        "usb_device_label": "USB Device:",
        "no_usb_device": "No USB device detected",
        "low_sdk_title": "Low Android Version",
        "low_sdk_msg": "Device Android version is below 11, system audio forwarding not supported, audio disabled",
        "device_disconnected_title": "Device Disconnected",
        "device_disconnected_msg": "Device has been disconnected",
        "keep_active": "Stay awake",
        "keep_active_desc": "Simulates user activity to prevent device screen off"
    }
}

def tr(key: str) -> str:
    lang_map = _TRANSLATIONS.get(SYS_LANG, _TRANSLATIONS["en"])
    return lang_map.get(key, key)

# ========================== 常量与工具函数 ==========================
PORT = 5555
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "scrcpy-cast-gtk")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.chmod(CONFIG_DIR, 0o700)
CONFIG_FILENAME = os.path.join(CONFIG_DIR, "config.ini")

BUNDLED_SCRCPY = "/usr/lib/scrcpy-cast-gtk/scrcpy"
BUNDLED_SCRCPY_SERVER = "/usr/lib/scrcpy-cast-gtk/scrcpy-server"
MIN_SCRCPY_VER = (3, 3, 4)

APP_ID = "io.github.usbipad.scrcpycastgtk"
ICON_DIR = "/usr/lib/scrcpy-cast-gtk/icon-res"

DEFAULT_CONFIG = {
    "mode": {"selected_mode": "usb", "wifi_sub_index": "0"},
    "audio": {"audio_enable": "True", "audio_quality": "0"},
    "video": {"video_codec_idx": "0", "max_size_idx": "0", "max_fps_idx": "0"},
    "other": {"sleep_screen": "False", "record_enable": "False", "record_dir": "", "keep_active": "False"},
    "window": {"width": "740", "height": "580"}
}

_active_wait_dialogs = []
_dialog_lock = threading.Lock()
_stop_event = threading.Event()

TRANSIENT_WINDOW_SEC = 1.0

# ========================== 通用函数 ==========================
def check_tool_exists(tool_name: str) -> bool:
    try:
        subprocess.run([tool_name, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except FileNotFoundError:
        return False

def get_adb_path() -> str:
    return shutil.which("adb") or "adb"

def get_scrcpy_binary() -> Optional[str]:
    arch = platform.machine()
    if arch == "x86_64" and os.path.isfile(BUNDLED_SCRCPY):
        return BUNDLED_SCRCPY
    return shutil.which("scrcpy")

def parse_scrcpy_version(bin_path: str) -> Optional[Tuple[int, int, int]]:
    try:
        ret = subprocess.run([bin_path, "--version"], capture_output=True, text=True, timeout=5)
        output = ret.stdout + ret.stderr
        match = re.search(r'(\d+)\.(\d+)\.(\d+)', output)
        if match:
            return tuple(map(int, match.groups()))
        return None
    except Exception as e:
        safe_log(logging.ERROR, f"Version parse error: {e}")
        return None

def check_scrcpy_with_version():
    bin_path = get_scrcpy_binary()
    if not bin_path:
        return None, tr("dep_missing_msg").format(tool="scrcpy")
    ver = parse_scrcpy_version(bin_path)
    if not ver:
        return None, "无法读取 scrcpy 版本信息（可能权限不足或者二进制损坏）"
    if ver < MIN_SCRCPY_VER:
        return None, (f"scrcpy版本过低({'.'.join(map(str,ver))})\n"
                      f"最低要求：{'.'.join(map(str,MIN_SCRCPY_VER))}\n"
                      "请安装新版scrcpy")
    return bin_path, None

def load_config():
    cfg = configparser.ConfigParser()
    for sec, items in DEFAULT_CONFIG.items():
        cfg[sec] = items
    if os.path.exists(CONFIG_FILENAME):
        try:
            cfg.read(CONFIG_FILENAME, encoding="utf-8")
        except Exception as e:
            safe_log(logging.ERROR, f"Config read error: {e}")
    return cfg

def save_config(cfg):
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=CONFIG_DIR,
            prefix=".config.ini.", delete=False
        ) as f:
            temp_path = f.name
            cfg.write(f)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, CONFIG_FILENAME)
    except Exception as e:
        safe_log(logging.ERROR, f"Config save error: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

def get_default_video_dir():
    home = os.path.expanduser("~")
    vid_dir = os.path.join(home, "Videos")
    if os.path.isdir(vid_dir):
        return vid_dir
    return os.getcwd()

def run_cmd(args: List[str], timeout=10) -> Tuple[int, str, str]:
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return -1, "", "Command timeout"

def adb_run(args: List[str], timeout=10) -> Tuple[int, str, str]:
    return run_cmd([get_adb_path()] + args, timeout=timeout)

def get_usb_devices() -> List[str]:
    rc, out, _ = adb_run(["devices"])
    if rc != 0:
        return []
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line or "List of devices" in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            if ":" not in serial:
                devices.append(serial)
    return devices

def get_phone_private_ips(serial: str, timeout=5) -> List[str]:
    rc, out, _ = adb_run(["-s", serial, "shell", "ip", "-4", "addr", "show"], timeout=timeout)
    if rc != 0:
        safe_log(logging.INFO, "Phone network IP summary: none")
        return []

    lines = out.splitlines()
    current_iface = None
    interface_ips = {}
    for line in lines:
        line = line.strip()
        iface_match = re.match(r'^\d+:\s+(\S+):', line)
        if iface_match:
            current_iface = None if re.search(
                r'(?:\bstate\s+DOWN\b|<[^>]*\bDOWN\b)', line, re.I
            ) else iface_match.group(1)
            continue
        if current_iface and 'inet' in line:
            ip_match = re.search(r'inet\s+(\d{1,3}(?:\.\d{1,3}){3})/\d+', line)
            if ip_match:
                ip = ip_match.group(1)
                if (ip != "0.0.0.0" and not ip.startswith("127.") and
                        not re.search(r'(ap0|wlan_ap0|usb0|rndis|ncm|lo|tun|rmnet)', current_iface, re.I)):
                    ips = interface_ips.setdefault(current_iface, [])
                    if ip not in ips:
                        ips.append(ip)

    summary = ", ".join(
        f"{iface}={','.join(dict.fromkeys(ips))}"
        for iface, ips in interface_ips.items()
    ) or "none"
    safe_log(logging.INFO, f"Phone network IP summary: {summary}")

    ordered_interfaces = ["wlan0", "wlan1"]
    ordered_interfaces.extend(
        iface for iface in interface_ips if iface not in ordered_interfaces
    )
    unique = []
    seen = set()
    for iface in ordered_interfaces:
        for ip in interface_ips.get(iface, []):
            if ip not in seen:
                seen.add(ip)
                unique.append(ip)
    return unique

def validate_plain_ipv4(ip_str: str) -> bool:
    parts = ip_str.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        num = int(part)
        if num < 0 or num > 255:
            return False
    return True

def validate_ip_port(addr: str) -> bool:
    pattern = r'^(\d{1,3}\.){3}\d{1,3}:\d{1,5}$'
    if not re.match(pattern, addr):
        return False
    ip, port_str = addr.split(':')
    for part in ip.split('.'):
        if not 0 <= int(part) <= 255:
            return False
    try:
        port = int(port_str)
        if not 1 <= port <= 65535:
            return False
    except ValueError:
        return False
    return True

def check_record_dir(dir_path: str) -> Tuple[bool, str]:
    if not os.path.isdir(dir_path):
        return False, "目录不存在"
    if not os.access(dir_path, os.W_OK):
        return False, "目录不可写"
    try:
        stat = os.statvfs(dir_path)
        free_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)
        if free_mb < 100:
            return False, f"剩余空间不足 ({free_mb:.1f}MB < 100MB)"
    except Exception as e:
        safe_log(logging.ERROR, f"Check dir space error: {e}")
        return False, str(e)
    return True, "OK"

def append_video_args(args: List[str], video_codec: str, max_size: int, max_fps: int):
    args.extend(["--video-codec", video_codec])
    if max_size > 0:
        args.extend(["--max-size", str(max_size)])
    if max_fps > 0:
        args.extend(["--max-fps", str(max_fps)])

def gen_record_output_path(base_dir: str, device_model: str = "unknown") -> str:
    os.makedirs(base_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    safe_model = re.sub(r"[^A-Za-z0-9._-]+", "_", device_model).strip("._-") or "unknown"
    return os.path.join(base_dir, f"{safe_model}_{ts}.mkv")

def get_mode_desc_text(mode: str) -> str:
    if mode == "wifi_usb_auth":
        return tr("help_wifi_usb")
    elif mode == "usb":
        return tr("help_usb")
    elif mode == "wifi_debug":
        return tr("help_wifi_debug")
    else:
        return tr("help_no_mode")

# ========================== 设备信息获取 ==========================
def get_device_info(serial: str) -> Tuple[str, str]:
    try:
        rc_b, out_b, _ = adb_run(["-s", serial, "shell", "getprop", "ro.product.brand"], timeout=3)
        brand = out_b.strip() if rc_b == 0 else ""
        rc_m, out_m, _ = adb_run(["-s", serial, "shell", "getprop", "ro.product.model"], timeout=3)
        model = out_m.strip() if rc_m == 0 else ""
        if brand and model:
            display = f"{brand} {model} [{serial}]"
        elif brand:
            display = f"{brand} [{serial}]"
        elif model:
            display = f"{model} [{serial}]"
        else:
            display = serial
        return display, serial
    except Exception:
        return serial, serial

def get_device_full_info(serial: str) -> dict:
    info = {}
    try:
        rc_b, out_b, _ = adb_run(["-s", serial, "shell", "getprop", "ro.product.brand"], timeout=3)
        if rc_b == 0:
            info['brand'] = out_b.strip()
        rc_m, out_m, _ = adb_run(["-s", serial, "shell", "getprop", "ro.product.model"], timeout=3)
        if rc_m == 0:
            info['model'] = out_m.strip()
        rc_s, out_s, _ = adb_run(["-s", serial, "shell", "getprop", "ro.build.version.sdk"], timeout=3)
        if rc_s == 0 and out_s.strip().isdigit():
            info['sdk'] = int(out_s.strip())
    except Exception as e:
        safe_log(logging.WARNING, f"Failed to get full info for {serial}: {e}")
    return info

def get_device_display_text(serial: str, info: dict) -> str:
    brand = info.get('brand', '')
    model = info.get('model', '')
    if brand and model:
        return f"{brand} {model} [{serial}]"
    elif brand:
        return f"{brand} [{serial}]"
    elif model:
        return f"{model} [{serial}]"
    else:
        return f"[{serial}]"

# ========================== 对话框工具 (GTK4) ==========================
def run_dialog(dialog):
    if hasattr(dialog, "run"):
        return dialog.run()

    result = None
    loop = GLib.MainLoop()

    def on_response(_dialog, response_id):
        nonlocal result
        result = response_id
        if loop.is_running():
            loop.quit()

    def on_close(_dialog):
        nonlocal result
        result = Gtk.ResponseType.DELETE_EVENT
        if loop.is_running():
            loop.quit()
        return False

    dialog.connect("response", on_response)
    dialog.connect("close-request", on_close)
    loop.run()
    return result

def show_info(parent, title: str, msg: str):
    dlg = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dlg.add_button("_OK", Gtk.ResponseType.OK)
    content = dlg.get_content_area()
    label = Gtk.Label(label=msg, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
    label.set_margin_top(12)
    label.set_margin_bottom(12)
    label.set_margin_start(12)
    label.set_margin_end(12)
    content.append(label)
    dlg.set_default_response(Gtk.ResponseType.OK)
    dlg.present()
    run_dialog(dlg)
    dlg.close()

def show_error(parent, title: str, msg: str):
    dlg = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dlg.add_button("_OK", Gtk.ResponseType.OK)
    content = dlg.get_content_area()
    label = Gtk.Label(label=msg, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
    label.set_margin_top(12)
    label.set_margin_bottom(12)
    label.set_margin_start(12)
    label.set_margin_end(12)
    content.append(label)
    dlg.set_default_response(Gtk.ResponseType.OK)
    dlg.present()
    run_dialog(dlg)
    dlg.close()

def ask_question(parent, title: str, msg: str) -> bool:
    dlg = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dlg.add_button("_Yes", Gtk.ResponseType.YES)
    dlg.add_button("_No", Gtk.ResponseType.NO)
    content = dlg.get_content_area()
    label = Gtk.Label(label=msg, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
    label.set_margin_top(12)
    label.set_margin_bottom(12)
    label.set_margin_start(12)
    label.set_margin_end(12)
    content.append(label)
    dlg.set_default_response(Gtk.ResponseType.YES)
    dlg.present()
    resp = run_dialog(dlg)
    dlg.close()
    return resp == Gtk.ResponseType.YES

def entry_dialog(parent, title: str, prompt_text: str, default_text="") -> Optional[str]:
    dlg = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dlg.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dlg.add_button("_OK", Gtk.ResponseType.OK)
    dlg.set_default_size(420, 150)
    content = dlg.get_content_area()
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    content.set_spacing(10)
    label = Gtk.Label(label=prompt_text, xalign=0)
    content.append(label)
    entry = Gtk.Entry()
    entry.set_text(default_text)
    entry.set_activates_default(True)
    content.append(entry)
    dlg.set_default_response(Gtk.ResponseType.OK)
    dlg.present()
    resp = run_dialog(dlg)
    result = None
    if resp == Gtk.ResponseType.OK:
        result = entry.get_text()
    dlg.close()
    return result

def select_ip_dialog(parent, ips: List[str]) -> Optional[str]:
    dlg = Gtk.Dialog(title=tr("multiple_ips_title"), transient_for=parent, modal=True)
    dlg.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dlg.add_button("_OK", Gtk.ResponseType.OK)
    dlg.set_default_size(350, 200)
    content = dlg.get_content_area()
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    content.set_spacing(10)
    label = Gtk.Label(label=tr("multiple_ips_msg"), xalign=0)
    content.append(label)
    model = Gtk.StringList.new(ips)
    combo = Gtk.DropDown.new(model, None)
    combo.set_selected(0)
    content.append(combo)
    dlg.set_default_response(Gtk.ResponseType.OK)
    dlg.present()
    resp = run_dialog(dlg)
    result = None
    if resp == Gtk.ResponseType.OK:
        pos = combo.get_selected()
        if pos != Gtk.INVALID_LIST_POSITION:
            result = model.get_string(pos)
    dlg.close()
    return result

# ========================== 等待进度对话框 (GTK4) ==========================
class PulseWaitDialog(Gtk.Window):
    def __init__(self, parent: Gtk.Window, title: str, text: str, on_close_callback=None):
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_resizable(False)
        self.set_default_size(440, 130)
        self._stop_event = threading.Event()
        self._stop_event.clear()
        self._closing = False
        self._on_close_callback = on_close_callback
        with _dialog_lock:
            _active_wait_dialogs.append(self)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)
        self.set_child(vbox)

        self.label = Gtk.Label(label=text)
        vbox.append(self.label)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_pulse_step(0.1)
        vbox.append(self.progressbar)

        self.connect("close-request", self._on_user_close)
        self._timer_id = GLib.timeout_add(100, self._pulse_cb)
        self.present()

    def _on_user_close(self, *_args):
        if self._closing:
            return False
        if self._on_close_callback:
            GLib.idle_add(self._on_close_callback)
        self._stop_event.set()
        self.safe_close()
        return False

    def is_stopped(self):
        return self._stop_event.is_set()

    def _pulse_cb(self):
        self.progressbar.pulse()
        return True

    def safe_close(self):
        self._closing = True
        with _dialog_lock:
            if self._timer_id:
                GLib.source_remove(self._timer_id)
                self._timer_id = 0
            if self in _active_wait_dialogs:
                _active_wait_dialogs.remove(self)
            if self.get_realized():
                self.close()

# ========================== 自定义设备列表项 ==========================
class DeviceItem(GObject.Object):
    display = GObject.Property(type=str, default="")
    serial = GObject.Property(type=str, default="")
    def __init__(self, display: str, serial: str):
        super().__init__()
        self.display = display
        self.serial = serial

# ========================== 主窗口类 ==========================
class ScrcpyCastWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title=tr("app_title"))
        self.set_icon_name("scrcpy-cast-gtk")
        self.app = application
        self.selected_func = None
        self.connected_target = None
        self.scrcpy_bin = None
        self.adb_path = get_adb_path()
        self.current_settings = {
            "audio_enable": True,
            "audio_quality": "default",
            "sleep_enable": False,
            "enable_record": False,
            "video_codec": "h264",
            "max_size": 0,
            "max_fps": 0,
            "record_dir": get_default_video_dir(),
            "keep_active": False
        }
        self.win_width = 740
        self.win_height = 580
        self.scrcpy_procs = []
        self.proc_lock = threading.Lock()
        self._processing = False
        self._processing_lock = threading.Lock()
        self._bg_threads = []
        self._thread_lock = threading.Lock()
        self._window_destroyed = False
        self._window_size_timer_id = None
        self._ui_flag_lock = threading.Lock()

        self.usb_device_store = Gio.ListStore.new(DeviceItem.__gtype__)
        self.device_cache = {}
        self.pop_disconnect_alert = False
        self._disconnect_idle_pending = False
        self.device_audio_limited = False
        self._audio_preference_before_low_sdk: Optional[bool] = None
        self.scan_timer_id = None
        self._updating_combo = False
        self.user_selected_serial: Optional[str] = None
        self.last_known_serials: Set[str] = set()
        self._scan_paused = False
        self._scan_running = False
        self._scan_thread = None
        self._sdk_low_pop_shown: Set[str] = set()

        self._wifi_usb_abort = False
        self._wifi_usb_work_wait = None
        self._wifi_usb_selected_ip = None

        self._wifi_debug_abort = False
        self._wifi_debug_wait = None

        self._suppress_usb_disconnect_popup = False
        self._tcpip_transient_suppress = False
        self._transient_timer_id = None
        self._this_scan_added_serials: Set[str] = set()
        self._scrcpy_running = False

        self.cfg = load_config()
        self._restore_config()
        self._build_ui()
        self._connect_signals()
        self._apply_saved_state()
        self.connect("close-request", self.on_app_exit)
        self._window_size_timer_id = GLib.timeout_add(250, self._poll_window_size)

        self._start_scan_timer()

    def _start_scan_timer(self):
        if self.scan_timer_id is not None:
            GLib.source_remove(self.scan_timer_id)
        self.scan_timer_id = GLib.timeout_add(1000, self._scan_usb_devices)
        self._scan_paused = False
        safe_log(logging.DEBUG, "USB scan timer started")

    def _pause_scan_timer(self):
        if self.scan_timer_id is not None:
            GLib.source_remove(self.scan_timer_id)
            self.scan_timer_id = None
        self._scan_paused = True
        safe_log(logging.DEBUG, "USB scan paused")

    def _resume_scan_timer(self):
        if self._scan_paused:
            self._start_scan_timer()
            safe_log(logging.DEBUG, "USB scan resumed")

    def _scan_usb_devices(self):
        if self._scan_running or (self._scan_thread and self._scan_thread.is_alive()):
            return True
        self._scan_running = True
        self._scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self._scan_thread.start()
        return True

    def _scan_worker(self):
        if _stop_event.is_set():
            self._scan_running = False
            return
        update_queued = False
        try:
            current_serials = set(get_usb_devices())
            new_cache = {}
            for serial in current_serials:
                if serial in self.device_cache:
                    new_cache[serial] = self.device_cache[serial]
                else:
                    info = get_device_full_info(serial)
                    new_cache[serial] = info
            if not _stop_event.is_set():
                GLib.idle_add(self._apply_device_changes, current_serials, new_cache)
                update_queued = True
        except Exception as e:
            safe_log(logging.ERROR, f"USB scan worker error: {e}", exc_info=True)
        finally:
            if not update_queued:
                self._scan_running = False

    def _apply_device_changes(self, current_serials: Set[str], new_cache: dict):
        if _stop_event.is_set():
            return
        self._updating_combo = True
        removed = self.last_known_serials - current_serials
        added = current_serials - self.last_known_serials
        self._this_scan_added_serials = set(added)
        self.device_cache = new_cache
        self.last_known_serials = current_serials

        # Remove devices that disappeared (unless suppressed)
        if removed:
            for serial in removed:
                if serial == self.user_selected_serial and self._tcpip_transient_suppress:
                    continue
                item = self._find_item_by_serial(serial)
                if item is not None:
                    self._remove_item(item)
            safe_log(logging.DEBUG, f"Removed devices: {removed}")

        # Add new devices
        if added:
            for serial in added:
                info = self.device_cache.get(serial, {})
                display = get_device_display_text(serial, info)
                item = self._find_item_by_serial(serial)
                if item is None:
                    self.usb_device_store.append(DeviceItem(display, serial))
            safe_log(logging.DEBUG, f"Added devices: {added}")

        # Manage placeholder
        placeholder = self._find_item_by_serial("")
        has_placeholder = placeholder is not None
        if len(current_serials) == 0:
            if not has_placeholder:
                self.usb_device_store.append(DeviceItem(tr("no_usb_device"), ""))
                safe_log(logging.DEBUG, "Added placeholder (no devices)")
        else:
            if has_placeholder:
                self._remove_item(placeholder)
                safe_log(logging.DEBUG, "Removed placeholder (devices present)")

        self._handle_auto_selection(current_serials, removed)
        self._this_scan_added_serials.clear()
        self._updating_combo = False
        self._scan_running = False

    def _find_item_by_serial(self, serial: str) -> Optional[DeviceItem]:
        for i in range(self.usb_device_store.get_n_items()):
            item = self.usb_device_store.get_item(i)
            if item.serial == serial:
                return item
        return None

    def _remove_item(self, item: DeviceItem):
        for i in range(self.usb_device_store.get_n_items()):
            if self.usb_device_store.get_item(i) is item:
                self.usb_device_store.remove(i)
                return

    def _handle_auto_selection(self, current_serials: Set[str], removed: Set[str]):
        if self.user_selected_serial is not None and self.user_selected_serial in current_serials:
            return

        if self.user_selected_serial and self.user_selected_serial in removed:
            with self._ui_flag_lock:
                suppress = self._suppress_usb_disconnect_popup
                transient = self._tcpip_transient_suppress
                pop_alert = self.pop_disconnect_alert
                pending = self._disconnect_idle_pending
            if transient:
                if self.user_selected_serial in current_serials:
                    self._select_device(self.user_selected_serial)
                return
            if suppress:
                safe_log(logging.DEBUG, f"Suppressed disconnect popup for {self.user_selected_serial}")
            else:
                if not pop_alert and not pending:
                    with self._ui_flag_lock:
                        self.pop_disconnect_alert = True
                        self._disconnect_idle_pending = True
                    GLib.idle_add(self._show_disconnect_alert)
                    safe_log(logging.WARNING, f"User device {self.user_selected_serial} disconnected")
            if current_serials:
                first_serial = next(iter(current_serials))
                self._select_device(first_serial)
                self.user_selected_serial = first_serial
                safe_log(logging.INFO, f"Auto-selected {first_serial} after removal")
            else:
                self.user_selected_serial = None
                self._set_placeholder_selected()
                self.device_audio_limited = False
                self.switch_audio.set_sensitive(True)
                self.combo_audio_qual.set_sensitive(True)
                self.btn_start.set_sensitive(False)
                with self._ui_flag_lock:
                    self.pop_disconnect_alert = False
                    self._disconnect_idle_pending = False
            return

        if self.user_selected_serial is None and current_serials:
            first_serial = next(iter(current_serials))
            self._select_device(first_serial)
            self.user_selected_serial = first_serial
            safe_log(logging.INFO, f"Auto-selected {first_serial} (no user selection)")

    def _show_disconnect_alert(self):
        if self._window_destroyed or _stop_event.is_set():
            with self._ui_flag_lock:
                self.pop_disconnect_alert = False
                self._disconnect_idle_pending = False
            return
        if not self.get_visible():
            safe_log(logging.DEBUG, "_show_disconnect_alert skip: main window not visible")
            with self._ui_flag_lock:
                self.pop_disconnect_alert = False
                self._disconnect_idle_pending = False
            return
        show_error(self, tr("device_disconnected_title"), tr("device_disconnected_msg"))
        with self._ui_flag_lock:
            self.pop_disconnect_alert = False
            self._disconnect_idle_pending = False

    def _select_device(self, serial: str):
        self._updating_combo = True
        if serial:
            pos = self._find_position_by_serial(serial)
            if pos is not None:
                self.usb_device_combo.set_selected(pos)
            else:
                self.usb_device_combo.set_selected(Gtk.INVALID_LIST_POSITION)
        else:
            self.usb_device_combo.set_selected(Gtk.INVALID_LIST_POSITION)
        self._updating_combo = False

        if not serial:
            self.user_selected_serial = None
            self.device_audio_limited = False
            self.switch_audio.set_sensitive(True)
            self.combo_audio_qual.set_sensitive(True)
            self.btn_start.set_sensitive(False)
            safe_log(logging.DEBUG, "Selected placeholder")
        else:
            self.user_selected_serial = serial
            self._refresh_device_ui(serial)

    def _find_position_by_serial(self, serial: str) -> Optional[int]:
        for i in range(self.usb_device_store.get_n_items()):
            item = self.usb_device_store.get_item(i)
            if item.serial == serial:
                return i
        return None

    def _set_placeholder_selected(self):
        self._select_device("")

    def _refresh_device_ui(self, serial: str):
        info = self.device_cache.get(serial)
        if info is None:
            info = get_device_full_info(serial)
            self.device_cache[serial] = info
        sdk = info.get('sdk', 0)
        if sdk < 30:
            self.device_audio_limited = True
            if self._audio_preference_before_low_sdk is None:
                self._audio_preference_before_low_sdk = self.switch_audio.get_active()
            if self.switch_audio.get_active():
                self.switch_audio.set_active(False)
            self.switch_audio.set_sensitive(False)
            self.combo_audio_qual.set_sensitive(False)
            self.btn_start.set_sensitive(True)
            safe_log(logging.INFO, f"Device {serial} SDK={sdk}, audio disabled")
            if (serial not in self._sdk_low_pop_shown and
                serial in self._this_scan_added_serials and
                self.connected_target is None):
                self._sdk_low_pop_shown.add(serial)
                GLib.idle_add(lambda: show_info(self, tr("low_sdk_title"), tr("low_sdk_msg")))
        else:
            self.device_audio_limited = False
            self.switch_audio.set_sensitive(True)
            self.combo_audio_qual.set_sensitive(True)
            if self._audio_preference_before_low_sdk is not None:
                self.switch_audio.set_active(self._audio_preference_before_low_sdk)
                self._audio_preference_before_low_sdk = None
            self.btn_start.set_sensitive(True)
            safe_log(logging.INFO, f"Device {serial} SDK={sdk}, audio enabled")

    def _on_usb_device_changed(self, combo, _pspec):
        if self._updating_combo:
            return
        self.pop_disconnect_alert = False
        self._disconnect_idle_pending = False
        pos = combo.get_selected()
        if pos == Gtk.INVALID_LIST_POSITION:
            return
        item = self.usb_device_store.get_item(pos)
        if item is None:
            return
        serial = item.serial
        if serial:
            self.user_selected_serial = serial
        else:
            self.user_selected_serial = None
        if not serial:
            self.device_audio_limited = False
            self.switch_audio.set_sensitive(True)
            self.combo_audio_qual.set_sensitive(True)
            self.btn_start.set_sensitive(False)
            return
        self._refresh_device_ui(serial)

    def _restore_config(self):
        try:
            w = int(self.cfg["window"]["width"])
            h = int(self.cfg["window"]["height"])
            self.win_width, self.win_height = w, h
        except (ValueError, KeyError):
            pass
        self.set_default_size(self.win_width, self.win_height)

    def _capture_window_size(self):
        if not self.get_realized():
            return
        width = self.get_width()
        height = self.get_height()
        if width > 10 and height > 10:
            if (width, height) != (self.win_width, self.win_height):
                self.win_width, self.win_height = width, height

    def _poll_window_size(self):
        if self._window_destroyed:
            return False
        self._capture_window_size()
        return True

    # ---------- UI 构建 ----------
    def _build_ui(self):
        root_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        root_vbox.set_margin_top(18)
        root_vbox.set_margin_bottom(18)
        root_vbox.set_margin_start(18)
        root_vbox.set_margin_end(18)
        self.set_child(root_vbox)

        top_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        lbl_mode_title = Gtk.Label(label=tr("work_mode"), xalign=0)
        lbl_mode_title.set_markup(f"<b>{tr('work_mode')}</b>")
        top_box.append(lbl_mode_title)

        self.rb_usb = Gtk.CheckButton.new_with_label(tr("usb_mode"))
        self.rb_wireless = Gtk.CheckButton.new_with_label(tr("wireless_mode"))
        self.rb_wireless.set_group(self.rb_usb)

        top_box.append(self.rb_usb)

        h_wireless_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        h_wireless_line.append(self.rb_wireless)
        self.combo_wireless_sub_model = Gtk.StringList.new([tr("wireless_usb_auth"), tr("wireless_debug_auth")])
        self.combo_wireless_sub = Gtk.DropDown.new(self.combo_wireless_sub_model, None)
        self.combo_wireless_sub.set_selected(0)
        self.combo_wireless_sub.set_sensitive(False)
        h_wireless_line.append(self.combo_wireless_sub)
        top_box.append(h_wireless_line)

        sep1 = Gtk.Separator()
        top_box.append(sep1)
        root_vbox.append(top_box)

        scrolled_mid = Gtk.ScrolledWindow()
        scrolled_mid.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_mid.set_vexpand(True)
        mid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)

        lbl_param_title = Gtk.Label(label=tr("settings"), xalign=0)
        lbl_param_title.set_markup(f"<b>{tr('settings')}</b>")
        mid_box.append(lbl_param_title)

        # USB设备下拉（使用 Gtk.DropDown + 自定义工厂）
        usb_device_box = Gtk.Box(spacing=10)
        lbl_usb_device = Gtk.Label(label=tr("usb_device_label"), xalign=0)
        self.usb_device_combo = Gtk.DropDown.new(self.usb_device_store, None)

        # 自定义工厂显示 display 属性
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_device_item_setup)
        factory.connect("bind", self._on_device_item_bind)
        self.usb_device_combo.set_factory(factory)
        self.usb_device_combo.set_selected(0)

        usb_device_box.append(lbl_usb_device)
        usb_device_box.append(self.usb_device_combo)
        mid_box.append(usb_device_box)

        # 视频和音频参数
        h_param_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        v_video_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        v_audio_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        lbl_vid_codec = Gtk.Label(label=tr("video_codec"), xalign=0)
        v_video_group.append(lbl_vid_codec)
        self.combo_vid_codec_model = Gtk.StringList.new([tr("h264_default"), tr("h265_hevc")])
        self.combo_vid_codec = Gtk.DropDown.new(self.combo_vid_codec_model, None)
        v_video_group.append(self.combo_vid_codec)

        lbl_max_size = Gtk.Label(label=tr("max_resolution"), xalign=0)
        v_video_group.append(lbl_max_size)
        self.combo_max_size_model = Gtk.StringList.new([tr("unlimited"), "1080", "720"])
        self.combo_max_size = Gtk.DropDown.new(self.combo_max_size_model, None)
        self.combo_max_size.set_selected(0)
        v_video_group.append(self.combo_max_size)

        lbl_fps = Gtk.Label(label=tr("max_fps"), xalign=0)
        v_video_group.append(lbl_fps)
        self.combo_fps_model = Gtk.StringList.new([tr("auto_unlimited"), "30", "60", "90", "120"])
        self.combo_fps = Gtk.DropDown.new(self.combo_fps_model, None)
        self.combo_fps.set_selected(0)
        v_video_group.append(self.combo_fps)

        audio_switch_box = Gtk.Box(spacing=10)
        lbl_audio = Gtk.Label(label=tr("enable_audio"), xalign=0)
        self.switch_audio = Gtk.Switch()
        audio_switch_box.append(lbl_audio)
        audio_switch_box.append(self.switch_audio)
        v_audio_group.append(audio_switch_box)

        lbl_audio_qual = Gtk.Label(label=tr("audio_quality"), xalign=0)
        v_audio_group.append(lbl_audio_qual)
        self.combo_audio_qual_model = Gtk.StringList.new([
            tr("default_opus128"), tr("opus256"), tr("aac256"), tr("flac_lossless")
        ])
        self.combo_audio_qual = Gtk.DropDown.new(self.combo_audio_qual_model, None)
        self.combo_audio_qual.set_selected(0)
        v_audio_group.append(self.combo_audio_qual)

        h_param_box.append(v_video_group)
        h_param_box.append(v_audio_group)
        mid_box.append(h_param_box)

        sleep_box = Gtk.Box(spacing=20)
        sleep_left = Gtk.Box(spacing=10)
        lbl_sleep = Gtk.Label(label=tr("screen_off_cast"), xalign=0)
        self.switch_sleep = Gtk.Switch()
        sleep_left.append(lbl_sleep)
        sleep_left.append(self.switch_sleep)
        sleep_box.append(sleep_left)

        keep_active_box = Gtk.Box(spacing=10)
        lbl_keep_active = Gtk.Label(label=tr("keep_active"), xalign=0)
        self.switch_keep_active = Gtk.Switch()
        keep_active_box.append(lbl_keep_active)
        keep_active_box.append(self.switch_keep_active)
        sleep_box.append(keep_active_box)
        mid_box.append(sleep_box)

        record_switch_box = Gtk.Box(spacing=10)
        lbl_record = Gtk.Label(label=tr("record_screen"), xalign=0)
        self.switch_record = Gtk.Switch()
        self.btn_select_record_dir = Gtk.Button(label=tr("select_dir"))
        record_switch_box.append(lbl_record)
        record_switch_box.append(self.switch_record)
        record_switch_box.append(self.btn_select_record_dir)
        mid_box.append(record_switch_box)

        self.lbl_record_dir = Gtk.Label(xalign=0)
        self.lbl_record_dir.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self.lbl_record_dir.set_max_width_chars(30)
        mid_box.append(self.lbl_record_dir)

        lbl_record_hint = Gtk.Label(label=tr("record_hint"), xalign=0)
        lbl_record_hint.set_wrap(True)
        lbl_record_hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        mid_box.append(lbl_record_hint)

        lbl_bottom_tip = Gtk.Label(label=tr("bottom_tip"), xalign=0)
        lbl_bottom_tip.set_wrap(True)
        lbl_bottom_tip.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        mid_box.append(lbl_bottom_tip)

        scrolled_mid.set_child(mid_box)
        root_vbox.append(scrolled_mid)

        btn_box = Gtk.CenterBox()
        self.btn_help = Gtk.Button(label=tr("help"))
        self.btn_start = Gtk.Button(label=tr("start"))
        self.btn_start.set_sensitive(False)
        self.btn_start.set_size_request(-1, 36)
        self.btn_help.set_size_request(90, 36)
        self.btn_help.set_margin_start(6)
        btn_box.set_start_widget(self.btn_help)
        btn_box.set_center_widget(self.btn_start)
        root_vbox.append(btn_box)

    # 用于 USB 设备下拉的工厂回调
    def _on_device_item_setup(self, factory, list_item):
        label = Gtk.Label()
        list_item.set_child(label)

    def _on_device_item_bind(self, factory, list_item):
        item = list_item.get_item()
        label = list_item.get_child()
        if isinstance(item, DeviceItem):
            label.set_text(item.display)

    def _connect_signals(self):
        self.btn_help.connect("clicked", self.on_help_clicked)
        self.btn_start.connect("clicked", self.on_start_clicked)
        self.btn_select_record_dir.connect("clicked", self.on_select_record_dir)
        self.rb_usb.connect("toggled", self.on_mode_toggled)
        self.rb_wireless.connect("toggled", self.on_mode_toggled)
        self.combo_wireless_sub.connect("notify::selected", self.on_mode_toggled)
        self.usb_device_combo.connect("notify::selected", self._on_usb_device_changed)

        self.switch_audio.connect("notify::active", self._on_setting_changed)
        self.combo_audio_qual.connect("notify::selected", self._on_setting_changed)
        self.combo_vid_codec.connect("notify::selected", self._on_setting_changed)
        self.combo_max_size.connect("notify::selected", self._on_setting_changed)
        self.combo_fps.connect("notify::selected", self._on_setting_changed)
        self.switch_sleep.connect("notify::active", self._on_setting_changed)
        self.switch_record.connect("notify::active", self._on_setting_changed)
        self.switch_keep_active.connect("notify::active", self._on_setting_changed)

    def _apply_saved_state(self):
        sel_mode = self.cfg["mode"].get("selected_mode", "usb")
        if sel_mode not in ("usb", "wifi_usb_auth", "wifi_debug"):
            sel_mode = "usb"
        wifi_sub_idx = self._get_config_int("mode", "wifi_sub_index", 0, 0, 1)
        if sel_mode == "wifi_usb_auth":
            wifi_sub_idx = 0
        elif sel_mode == "wifi_debug":
            wifi_sub_idx = 1
        audio_enable = self._get_config_bool("audio", "audio_enable", True)
        audio_qual_idx = self._get_config_int("audio", "audio_quality", 0, 0, 3)
        vid_idx = self._get_config_int("video", "video_codec_idx", 0, 0, 1)
        maxsize_idx = self._get_config_int("video", "max_size_idx", 0, 0, 2)
        maxfps_idx = self._get_config_int("video", "max_fps_idx", 0, 0, 4)
        sleep_scr = self._get_config_bool("other", "sleep_screen", False)
        rec_enable = self._get_config_bool("other", "record_enable", False)
        rec_dir_saved = self.cfg["other"].get("record_dir", "")
        keep_active = self._get_config_bool("other", "keep_active", False)

        if sel_mode == "usb":
            self.rb_usb.set_active(True)
        else:
            self.rb_wireless.set_active(True)

        self.switch_audio.set_active(audio_enable)
        self.combo_audio_qual.set_selected(audio_qual_idx)
        self.combo_vid_codec.set_selected(vid_idx)
        self.combo_max_size.set_selected(maxsize_idx)
        self.combo_fps.set_selected(maxfps_idx)
        self.switch_sleep.set_active(sleep_scr)
        self.switch_record.set_active(rec_enable)
        self.switch_keep_active.set_active(keep_active)
        self.current_settings["keep_active"] = keep_active

        if rec_dir_saved.strip() and os.path.isdir(rec_dir_saved.strip()):
            self.current_settings["record_dir"] = rec_dir_saved.strip()
        self.lbl_record_dir.set_text(tr("current_record_dir") + self.current_settings["record_dir"])

        def delayed_set_wireless(idx):
            self.combo_wireless_sub.set_sensitive(True)
            self.combo_wireless_sub.set_selected(idx)
            self.update_ui_by_selected_mode()
        GLib.idle_add(delayed_set_wireless, wifi_sub_idx)

    def _get_config_int(self, section, key, default, minimum, maximum):
        try:
            value = self.cfg[section].getint(key)
        except (KeyError, ValueError, TypeError, configparser.Error):
            return default
        return value if minimum <= value <= maximum else default

    def _get_config_bool(self, section, key, default):
        try:
            return self.cfg[section].getboolean(key)
        except (KeyError, ValueError, TypeError, configparser.Error):
            return default

    # ========== 线程管理 ==========
    def _start_bg_thread(self, target, args=(), daemon=True):
        def wrapped():
            try:
                target(*args)
            except Exception as e:
                safe_log(logging.ERROR, f"Background thread error: {e}", exc_info=True)
        t = threading.Thread(target=wrapped, daemon=daemon)
        with self._thread_lock:
            self._bg_threads.append(t)
        t.start()
        return t

    def _stop_bg_threads(self, timeout=1):
        _stop_event.set()
        self._scan_running = False
        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=timeout)
        self._scan_thread = None
        with self._thread_lock:
            for t in self._bg_threads:
                if t.is_alive():
                    t.join(timeout=timeout)
            self._bg_threads.clear()

    def _safe_finalize(self, finalize_callback=None):
        with self._processing_lock:
            self._processing = False
        if finalize_callback:
            GLib.idle_add(finalize_callback)
        else:
            GLib.idle_add(lambda: self.btn_start.set_sensitive(True))

    # ========== 配置增量保存 ==========
    def _save_config_ui(self):
        self.cfg["mode"]["selected_mode"] = self.get_current_mode_key()
        self.cfg["mode"]["wifi_sub_index"] = str(self.combo_wireless_sub.get_selected())
        self.cfg["audio"]["audio_enable"] = str(self.switch_audio.get_active())
        self.cfg["audio"]["audio_quality"] = str(self.combo_audio_qual.get_selected())
        self.cfg["video"]["video_codec_idx"] = str(self.combo_vid_codec.get_selected())
        self.cfg["video"]["max_size_idx"] = str(self.combo_max_size.get_selected())
        self.cfg["video"]["max_fps_idx"] = str(self.combo_fps.get_selected())
        self.cfg["other"]["sleep_screen"] = str(self.switch_sleep.get_active())
        self.cfg["other"]["record_enable"] = str(self.switch_record.get_active())
        self.cfg["other"]["record_dir"] = self.current_settings["record_dir"]
        self.cfg["other"]["keep_active"] = str(self.switch_keep_active.get_active())
        save_config(self.cfg)

    def _on_setting_changed(self, *args):
        self._save_config_ui()

    # ========== 回调 ==========
    def on_app_exit(self, widget):
        if self._window_destroyed:
            return False
        self._window_destroyed = True
        if self._window_size_timer_id is not None:
            GLib.source_remove(self._window_size_timer_id)
            self._window_size_timer_id = None
        _stop_event.set()
        if self.scan_timer_id:
            GLib.source_remove(self.scan_timer_id)
            self.scan_timer_id = None
        if self._transient_timer_id:
            GLib.source_remove(self._transient_timer_id)
            self._transient_timer_id = None
        with _dialog_lock:
            for dlg in list(_active_wait_dialogs):
                dlg.safe_close()
        with self.proc_lock:
            for proc in self.scrcpy_procs:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            self.scrcpy_procs.clear()
        if self.connected_target:
            adb_run(["disconnect", self.connected_target], timeout=2)
            self.connected_target = None

        for win in list(Gtk.Window.list_toplevels()):
            if win != self and isinstance(win, Gtk.Window):
                win.close()

        self._stop_bg_threads(timeout=1)
        self.cfg["window"]["width"] = str(self.win_width)
        self.cfg["window"]["height"] = str(self.win_height)
        self._save_config_ui()
        self._suppress_usb_disconnect_popup = False
        self.app.quit()
        return False

    def on_help_clicked(self, widget):
        dlg = Gtk.Dialog(title=tr("help_title"), transient_for=self, modal=True)
        dlg.set_default_size(520, 420)
        dlg.add_button("_Close", Gtk.ResponseType.CLOSE)
        content = dlg.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True)
        label_text = Gtk.Label(xalign=0)
        label_text.set_wrap(True)
        label_text.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label_text.set_justify(Gtk.Justification.LEFT)
        label_text.set_text(get_mode_desc_text(self.get_current_mode_key()))
        sw.set_child(label_text)
        content.append(sw)
        dlg.present()
        run_dialog(dlg)
        dlg.close()

    def on_mode_toggled(self, widget, *args):
        self.update_ui_by_selected_mode()
        self._save_config_ui()

    def on_select_record_dir(self, button):
        dlg = Gtk.FileChooserDialog(title=tr("select_record_dir_title"), transient_for=self, action=Gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dlg.add_button("_OK", Gtk.ResponseType.OK)
        dlg.set_current_folder(Gio.File.new_for_path(self.current_settings["record_dir"]))
        dlg.present()
        resp = run_dialog(dlg)
        if resp == Gtk.ResponseType.OK:
            file = dlg.get_file()
            if file is not None:
                folder = file.get_path()
                if folder and os.path.isdir(folder):
                    self.current_settings["record_dir"] = folder
                    self.lbl_record_dir.set_text(tr("current_record_dir") + self.current_settings["record_dir"])
                    self._save_config_ui()
        dlg.close()

    def on_start_clicked(self, widget):
        func = self.get_current_mode_key()
        if func in ("usb", "wifi_usb_auth"):
            pos = self.usb_device_combo.get_selected()
            if pos == Gtk.INVALID_LIST_POSITION:
                show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                return
            item = self.usb_device_store.get_item(pos)
            if item is None or not item.serial:
                show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                return
            serial = item.serial
            current_devices = get_usb_devices()
            if serial not in current_devices:
                show_error(self, tr("device_disconnected_title"), tr("device_disconnected_msg"))
                return

        with self._processing_lock:
            if self._processing:
                return
            self._processing = True
        self.btn_start.set_sensitive(False)

        def finalize():
            self._safe_finalize()

        try:
            self.current_settings["audio_enable"] = self.switch_audio.get_active()
            self.current_settings["sleep_enable"] = self.switch_sleep.get_active()
            self.current_settings["enable_record"] = self.switch_record.get_active()
            self.current_settings["keep_active"] = self.switch_keep_active.get_active()

            aud_idx = self.combo_audio_qual.get_selected()
            qual_map = {1: "opus256", 2: "aac256", 3: "flac_lossless"}
            self.current_settings["audio_quality"] = qual_map.get(aud_idx, "default")

            vid_idx = self.combo_vid_codec.get_selected()
            self.current_settings["video_codec"] = "h265" if vid_idx == 1 else "h264"

            sz_map = {1: 1080, 2: 720}
            self.current_settings["max_size"] = sz_map.get(self.combo_max_size.get_selected(), 0)

            fps_map = {1: 30, 2: 60, 3: 90, 4: 120}
            self.current_settings["max_fps"] = fps_map.get(self.combo_fps.get_selected(), 0)

            record_file = None
            if self.current_settings["enable_record"]:
                rec_dir = self.current_settings["record_dir"]
                ok, msg = check_record_dir(rec_dir)
                if not ok:
                    show_error(self, tr("record_dir_error"), f"{tr('record_dir_not_writable')}\n{msg}")
                    finalize()
                    return
                device_model = "unknown"
                device_pos = self.usb_device_combo.get_selected()
                if device_pos != Gtk.INVALID_LIST_POSITION:
                    device_item = self.usb_device_store.get_item(device_pos)
                    if device_item is not None and device_item.serial:
                        device_info = self.device_cache.get(device_item.serial)
                        if device_info is None:
                            device_info = get_device_full_info(device_item.serial)
                            self.device_cache[device_item.serial] = device_info
                        device_model = " ".join(
                            part for part in (
                                device_info.get("brand", ""),
                                device_info.get("model", "")
                            ) if part
                        ) or device_item.serial
                record_file = gen_record_output_path(rec_dir, device_model)

            vc = self.current_settings["video_codec"]
            ms = self.current_settings["max_size"]
            mf = self.current_settings["max_fps"]

            if func == "usb":
                pos = self.usb_device_combo.get_selected()
                if pos == Gtk.INVALID_LIST_POSITION:
                    show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                    finalize()
                    return
                item = self.usb_device_store.get_item(pos)
                if item is None or not item.serial:
                    show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                    finalize()
                    return
                serial = item.serial
                self.usb_flow(serial,
                              self.current_settings["audio_enable"],
                              self.current_settings["audio_quality"],
                              self.current_settings["sleep_enable"],
                              vc, ms, mf, record_file,
                              finalize_callback=finalize)
            elif func == "wifi_usb_auth":
                pos = self.usb_device_combo.get_selected()
                if pos == Gtk.INVALID_LIST_POSITION:
                    show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                    finalize()
                    return
                item = self.usb_device_store.get_item(pos)
                if item is None or not item.serial:
                    show_error(self, tr("app_title"), tr("device_disconnected_msg"))
                    finalize()
                    return
                serial = item.serial
                self.wifi_usb_auth_flow(serial,
                                        self.current_settings["audio_enable"],
                                        self.current_settings["audio_quality"],
                                        self.current_settings["sleep_enable"],
                                        vc, ms, mf, record_file,
                                        finalize_callback=finalize)
            elif func == "wifi_debug":
                self.wifi_wireless_auth_flow(self.current_settings["audio_enable"],
                                             self.current_settings["audio_quality"],
                                             self.current_settings["sleep_enable"],
                                             vc, ms, mf, record_file,
                                             finalize_callback=finalize)
            else:
                finalize()
        except Exception as e:
            safe_log(logging.ERROR, f"Start flow error: {e}", exc_info=True)
            show_error(self, tr("app_title"), tr("generic_error").format(str(e)))
            finalize()

    def get_current_mode_key(self):
        if self.rb_usb.get_active():
            return "usb"
        idx = self.combo_wireless_sub.get_selected()
        return "wifi_usb_auth" if idx == 0 else "wifi_debug"

    def update_ui_by_selected_mode(self):
        func = self.get_current_mode_key()
        if func == "usb":
            self.combo_wireless_sub.set_sensitive(False)
            self.usb_device_combo.set_sensitive(True)
            pos = self.usb_device_combo.get_selected()
            if pos != Gtk.INVALID_LIST_POSITION:
                item = self.usb_device_store.get_item(pos)
                self.btn_start.set_sensitive(item is not None and bool(item.serial))
            else:
                self.btn_start.set_sensitive(False)
        elif func == "wifi_usb_auth":
            self.combo_wireless_sub.set_sensitive(True)
            self.usb_device_combo.set_sensitive(True)
            pos = self.usb_device_combo.get_selected()
            if pos != Gtk.INVALID_LIST_POSITION:
                item = self.usb_device_store.get_item(pos)
                self.btn_start.set_sensitive(item is not None and bool(item.serial))
            else:
                self.btn_start.set_sensitive(False)
        else:
            self.combo_wireless_sub.set_sensitive(True)
            self.usb_device_combo.set_sensitive(False)
            self.btn_start.set_sensitive(True)
        with self._ui_flag_lock:
            self._suppress_usb_disconnect_popup = (func == "wifi_debug")

    # ========== 启动 scrcpy ==========
    def _start_scrcpy(self, args: List[str], record_file: Optional[str] = None, is_usb: bool = False) -> subprocess.Popen:
        env = os.environ.copy()
        env["ADB"] = self.adb_path
        env["SDL_APP_ID"] = APP_ID
        env["SCRCPY_ICON_DIR"] = ICON_DIR
        if False:  # 保留捆绑模式入口，未来切回时改为 True 或删除此行
            env["SCRCPY_SERVER_PATH"] = BUNDLED_SCRCPY_SERVER
        proc = subprocess.Popen([self.scrcpy_bin] + args, env=env)
        with self.proc_lock:
            self.scrcpy_procs.append(proc)
        self._scrcpy_running = True
        self._pause_scan_timer()
        safe_log(logging.DEBUG, "scrcpy started, USB scan paused")


        def monitor():
            while proc.poll() is None and not _stop_event.is_set():
                time.sleep(0.5)
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            with self.proc_lock:
                if proc in self.scrcpy_procs:
                    self.scrcpy_procs.remove(proc)
            if record_file and os.path.exists(record_file) and os.path.getsize(record_file) == 0:
                try:
                    os.remove(record_file)
                    safe_log(logging.INFO, f"Removed empty record file: {record_file}")
                except Exception as e:
                    safe_log(logging.WARNING, f"Failed to remove empty record file: {e}")
            if self.connected_target:
                adb_run(["disconnect", self.connected_target], timeout=2)
                self.connected_target = None
            self._scrcpy_running = False
            if not _stop_event.is_set():
                GLib.idle_add(self._resume_scan_timer)
                safe_log(logging.DEBUG, "scrcpy ended, USB scan resumed")
                with self._ui_flag_lock:
                    pending = self._disconnect_idle_pending
                if pending:
                    safe_log(logging.DEBUG, "Disconnect alert pending, deferring window show")
                else:
                    GLib.idle_add(self.present)
                GLib.idle_add(self._on_scrcpy_ended)

        self._start_bg_thread(monitor, daemon=True)
        return proc

    def _on_scrcpy_ended(self):
        if _stop_event.is_set():
            return
        mode = self.get_current_mode_key()
        with self._ui_flag_lock:
            if mode == "wifi_usb_auth":
                self._suppress_usb_disconnect_popup = False
                safe_log(logging.DEBUG, "Reset suppress popup to False after scrcpy ended (wifi_usb_auth)")
            elif mode == "wifi_debug":
                safe_log(logging.DEBUG, "scrcpy ended but mode is wifi_debug, keeping suppress=True")
            else:
                self._suppress_usb_disconnect_popup = False
                safe_log(logging.DEBUG, "scrcpy ended, mode is usb, suppress=False")

    # ========== USB直连模式 ==========
    def usb_flow(self, serial: str, audio_enable: bool, audio_quality: str, sleep_enable: bool,
                 video_codec: str, max_size: int, max_fps: int, record_file: Optional[str],
                 finalize_callback=None):
        scrcpy_args = ["-s", serial, "--always-on-top", "--window-title", tr("app_title")]
        append_video_args(scrcpy_args, video_codec, max_size, max_fps)
        if record_file:
            scrcpy_args.extend(["--record", record_file])
        if self.device_audio_limited:
            scrcpy_args.append("--no-audio")
        elif audio_enable:
            scrcpy_args.append("--audio-source=playback")
            if audio_quality == "opus256":
                scrcpy_args.extend(["--audio-codec=opus", "--audio-bit-rate=256000"])
            elif audio_quality == "aac256":
                scrcpy_args.extend(["--audio-codec=aac", "--audio-bit-rate=256000"])
            elif audio_quality == "flac_lossless":
                scrcpy_args.extend(["--audio-codec=flac", "--audio-codec-options=flac-compression-level=8", "--audio-buffer=120"])
        else:
            scrcpy_args.append("--no-audio")
        if sleep_enable:
            scrcpy_args.append("-S")
        if self.current_settings.get("keep_active", False):
            scrcpy_args.append("--keep-active")
        self._start_scrcpy(scrcpy_args, record_file, is_usb=True)
        self.set_visible(False)
        self._safe_finalize(finalize_callback)

    # ========== WiFi USB授权模式 ==========
    def wifi_usb_auth_flow(self, serial: str, audio_enable: bool, audio_quality: str, sleep_enable: bool,
                           video_codec: str, max_size: int, max_fps: int, record_file: Optional[str],
                           finalize_callback=None):
        self._wifi_usb_abort = False
        self._wifi_usb_selected_ip = None

        def on_wait_dialog_closed():
            self._wifi_usb_abort = True
            self._wifi_usb_cleanup_and_finalize(finalize_callback)

        work_wait = PulseWaitDialog(self, tr("wifi_usb_cast_title"), tr("connecting_text"),
                                    on_close_callback=on_wait_dialog_closed)
        work_wait.present()
        self._wifi_usb_work_wait = work_wait

        def fetch_ips_in_bg():
            try:
                if self._wifi_usb_abort or _stop_event.is_set():
                    return
                ips = get_phone_private_ips(serial, timeout=5)
                if not _stop_event.is_set():
                    GLib.idle_add(lambda: self._wifi_usb_handle_ips(serial, ips, audio_enable, audio_quality,
                                                                    sleep_enable, video_codec, max_size, max_fps,
                                                                    record_file, finalize_callback))
            except Exception as e:
                safe_log(logging.ERROR, f"wifi_usb_auth fetch IP error: {e}", exc_info=True)
                GLib.idle_add(self._wifi_usb_cleanup_and_finalize, finalize_callback)

        self._start_bg_thread(fetch_ips_in_bg)

    def _wifi_usb_handle_ips(self, serial: str, ips: List[str], audio_enable: bool, audio_quality: str,
                             sleep_enable: bool, video_codec: str, max_size: int, max_fps: int,
                             record_file: Optional[str], finalize_callback):
        if self._wifi_usb_abort or _stop_event.is_set():
            self._wifi_usb_cleanup_and_finalize(finalize_callback)
            return
        work_wait = self._wifi_usb_work_wait
        if not work_wait or work_wait.is_stopped():
            self._wifi_usb_cleanup_and_finalize(finalize_callback)
            return

        if not ips:
            def on_input_done():
                if self._wifi_usb_abort or _stop_event.is_set():
                    self._wifi_usb_cleanup_and_finalize(finalize_callback)
                    return
                if self._wifi_usb_selected_ip is not None:
                    self._wifi_usb_do_connect(self._wifi_usb_selected_ip, serial, audio_enable, audio_quality,
                                              sleep_enable, video_codec, max_size, max_fps,
                                              record_file, finalize_callback)
                else:
                    self._wifi_usb_cleanup_and_finalize(finalize_callback)

            def input_ip_cb():
                if self._wifi_usb_abort or _stop_event.is_set():
                    self._wifi_usb_cleanup_and_finalize(finalize_callback)
                    return
                man_ip = entry_dialog(self, tr("wifi_usb_cast_title"), tr("get_ip_fail"))
                if man_ip is None:
                    self._wifi_usb_selected_ip = None
                    GLib.idle_add(on_input_done)
                    return
                man_ip = man_ip.strip()
                if not man_ip:
                    show_error(self, tr("wifi_usb_cast_title"), tr("empty_addr"))
                    GLib.idle_add(input_ip_cb)
                    return
                if not validate_plain_ipv4(man_ip):
                    show_error(self, tr("wifi_usb_cast_title"), tr("invalid_ip_format"))
                    GLib.idle_add(input_ip_cb)
                    return
                self._wifi_usb_selected_ip = man_ip
                GLib.idle_add(on_input_done)

            GLib.idle_add(input_ip_cb)
            return

        if len(ips) == 1:
            self._wifi_usb_selected_ip = ips[0]
            self._wifi_usb_do_connect(ips[0], serial, audio_enable, audio_quality,
                                      sleep_enable, video_codec, max_size, max_fps,
                                      record_file, finalize_callback)
            return

        def on_select_done():
            if self._wifi_usb_abort or _stop_event.is_set():
                self._wifi_usb_cleanup_and_finalize(finalize_callback)
                return
            if self._wifi_usb_selected_ip is not None:
                self._wifi_usb_do_connect(self._wifi_usb_selected_ip, serial, audio_enable, audio_quality,
                                          sleep_enable, video_codec, max_size, max_fps,
                                          record_file, finalize_callback)
            else:
                self._wifi_usb_cleanup_and_finalize(finalize_callback)

        def select_ip_cb():
            if self._wifi_usb_abort or _stop_event.is_set():
                self._wifi_usb_cleanup_and_finalize(finalize_callback)
                return
            sel = select_ip_dialog(self, ips)
            self._wifi_usb_selected_ip = sel
            GLib.idle_add(on_select_done)
        GLib.idle_add(select_ip_cb)

    def _wifi_usb_do_connect(self, ip: str, serial: str, audio_enable: bool, audio_quality: str,
                             sleep_enable: bool, video_codec: str, max_size: int, max_fps: int,
                             record_file: Optional[str], finalize_callback):
        if self._wifi_usb_abort or _stop_event.is_set():
            self._wifi_usb_cleanup_and_finalize(finalize_callback)
            return

        work_wait = self._wifi_usb_work_wait
        if not work_wait or work_wait.is_stopped():
            def on_wait_dialog_closed():
                self._wifi_usb_abort = True
                self._wifi_usb_cleanup_and_finalize(finalize_callback)
            work_wait = PulseWaitDialog(self, tr("wifi_usb_cast_title"), tr("connecting_text"),
                                        on_close_callback=on_wait_dialog_closed)
            work_wait.present()
            self._wifi_usb_work_wait = work_wait

        def start_bg_connect():
            if self._wifi_usb_abort or _stop_event.is_set():
                return

            def bg_connect():
                try:
                    if self._wifi_usb_abort or _stop_event.is_set():
                        GLib.idle_add(self._wifi_usb_cleanup_and_finalize, finalize_callback)
                        return

                    if self._transient_timer_id:
                        GLib.source_remove(self._transient_timer_id)
                        self._transient_timer_id = None
                    with self._ui_flag_lock:
                        self._tcpip_transient_suppress = True
                    safe_log(logging.DEBUG, f"tcpip transient suppress enabled for {TRANSIENT_WINDOW_SEC}s")

                    def clear_transient():
                        if not self._window_destroyed:
                            with self._ui_flag_lock:
                                self._tcpip_transient_suppress = False
                            safe_log(logging.DEBUG, "tcpip transient suppress expired")
                        self._transient_timer_id = None
                        return False
                    self._transient_timer_id = GLib.timeout_add(int(TRANSIENT_WINDOW_SEC * 1000), clear_transient)

                    adb_run(["disconnect", f"{ip}:{PORT}"], timeout=2)
                    rc_tcpip, _, err_tcpip = adb_run(["-s", serial, "tcpip", str(PORT)], timeout=5)
                    if rc_tcpip != 0:
                        def tcpip_err_cb():
                            if self._wifi_usb_abort or _stop_event.is_set():
                                self._wifi_usb_cleanup_and_finalize(finalize_callback)
                                return
                            show_error(self, tr("wifi_usb_cast_title"),
                                       tr("port_open_fail").format(port=PORT, err=err_tcpip))
                            self._wifi_usb_cleanup_and_finalize(finalize_callback)
                        GLib.idle_add(tcpip_err_cb)
                        return

                    target_addr = f"{ip}:{PORT}"
                    delay = 1
                    out_conn = err_conn = ""
                    ok_flag = False
                    current_ip = ip
                    for attempt in range(2):
                        if self._wifi_usb_abort or _stop_event.is_set():
                            return
                        if work_wait.is_stopped():
                            return
                        new_ips = get_phone_private_ips(serial, timeout=3)
                        if new_ips:
                            new_ip = new_ips[0]
                            if new_ip != current_ip:
                                safe_log(logging.INFO, f"IP changed from {current_ip} to {new_ip}, updating target")
                                current_ip = new_ip
                                target_addr = f"{current_ip}:{PORT}"
                        rc_conn, out_conn, err_conn = adb_run(["connect", target_addr], timeout=3)
                        if "connected to" in out_conn:
                            ok_flag = True
                            break
                        if attempt == 0:
                            time.sleep(delay)
                            delay = min(delay * 2, 4)

                    def handle_result():
                        if self._wifi_usb_abort or _stop_event.is_set():
                            work_wait.safe_close()
                            self._wifi_usb_cleanup_and_finalize(finalize_callback)
                            return
                        if work_wait.is_stopped():
                            work_wait.safe_close()
                            self._wifi_usb_cleanup_and_finalize(finalize_callback)
                            return
                        work_wait.safe_close()

                        if ok_flag:
                            self.connected_target = target_addr
                            with self._ui_flag_lock:
                                self._suppress_usb_disconnect_popup = True
                            safe_log(logging.DEBUG, "wifi_usb_auth connected, suppress popup set to True")
                            show_info(self, tr("wifi_usb_cast_title"), tr("connect_success"))

                            scrcpy_args = ["-s", target_addr, "--always-on-top", "--window-title", tr("app_title")]
                            append_video_args(scrcpy_args, video_codec, max_size, max_fps)
                            if record_file:
                                scrcpy_args.extend(["--record", record_file])
                            if self.device_audio_limited:
                                scrcpy_args.append("--no-audio")
                            elif audio_enable:
                                scrcpy_args.append("--audio-source=playback")
                                if audio_quality == "opus256":
                                    scrcpy_args.extend(["--audio-codec=opus", "--audio-bit-rate=256000", "--audio-buffer=120"])
                                elif audio_quality == "aac256":
                                    scrcpy_args.extend(["--audio-codec=aac", "--audio-bit-rate=256000", "--audio-buffer=120"])
                                elif audio_quality == "flac_lossless":
                                    scrcpy_args.extend(["--audio-codec=flac", "--audio-codec-options=flac-compression-level=5", "--audio-buffer=120"])
                                else:
                                    scrcpy_args.append("--audio-buffer=120")
                            else:
                                scrcpy_args.append("--no-audio")
                            if sleep_enable:
                                scrcpy_args.append("-S")
                            if self.current_settings.get("keep_active", False):
                                scrcpy_args.append("--keep-active")

                            self._start_scrcpy(scrcpy_args, record_file)
                            self.set_visible(False)

                            self._wifi_usb_abort = True
                            self._wifi_usb_work_wait = None
                            self._wifi_usb_selected_ip = None
                            self._safe_finalize(finalize_callback)
                        else:
                            yes = ask_question(self, tr("wifi_usb_cast_title"),
                                               tr("connect_fail_msg").format(addr=target_addr, out=out_conn,
                                                                              err=err_conn, port=PORT))
                            if yes and not self._wifi_usb_abort:
                                self._wifi_usb_abort = False
                                self._wifi_usb_selected_ip = None

                                def on_retry_wait_closed():
                                    self._wifi_usb_abort = True
                                    self._wifi_usb_cleanup_and_finalize(finalize_callback)

                                new_wait = PulseWaitDialog(self, tr("wifi_usb_cast_title"), tr("connecting_text"),
                                                           on_close_callback=on_retry_wait_closed)
                                new_wait.present()
                                self._wifi_usb_work_wait = new_wait

                                GLib.idle_add(lambda: self._wifi_usb_handle_ips(serial, [ip], audio_enable, audio_quality,
                                                                                sleep_enable, video_codec, max_size, max_fps,
                                                                                record_file, finalize_callback))
                            else:
                                self._wifi_usb_cleanup_and_finalize(finalize_callback)

                    GLib.idle_add(handle_result)
                except Exception as e:
                    safe_log(logging.ERROR, f"wifi_usb_auth connect error: {e}", exc_info=True)
                    GLib.idle_add(lambda: show_error(self, tr("app_title"), tr("generic_error").format(str(e))))
                    GLib.idle_add(self._wifi_usb_cleanup_and_finalize, finalize_callback)

            self._start_bg_thread(bg_connect)

        GLib.idle_add(start_bg_connect)

    def _wifi_usb_cleanup_and_finalize(self, finalize_callback=None, is_success: bool = False):
        self._wifi_usb_abort = True
        work_wait = self._wifi_usb_work_wait
        if work_wait:
            work_wait.safe_close()
            self._wifi_usb_work_wait = None
        self._wifi_usb_selected_ip = None
        if not is_success and not _stop_event.is_set():
            with self._ui_flag_lock:
                self._suppress_usb_disconnect_popup = False
            safe_log(logging.DEBUG, "wifi_usb cleanup (fail/cancel): suppress popup reset to False")
            self._resume_scan_timer()
        self._safe_finalize(finalize_callback)

    # ========== 无线调试模式 ==========
    def wifi_wireless_auth_flow(self, audio_enable, audio_quality, sleep_enable,
                                video_codec, max_size, max_fps, record_file,
                                finalize_callback=None):
        self._wifi_debug_abort = False
        self._wifi_debug_wait = None
        self._pause_scan_timer()
        safe_log(logging.DEBUG, "wifi_debug flow entered: pause usb scan immediately")

        def on_wait_dialog_closed():
            self._wifi_debug_abort = True
            self._wifi_debug_cleanup_and_finalize(finalize_callback)

        show_info(self, tr("wireless_debug_title"), tr("wireless_debug_desc"))

        def try_input_loop():
            while not self._wifi_debug_abort and not _stop_event.is_set():
                addr = entry_dialog(self, tr("wireless_debug_title"), tr("input_wireless_addr"))
                if addr is None:
                    self._wifi_debug_abort = True
                    self._wifi_debug_cleanup_and_finalize(finalize_callback)
                    return
                addr = addr.strip()
                if not addr:
                    show_error(self, tr("wireless_debug_title"), tr("empty_addr"))
                    continue
                if not validate_ip_port(addr):
                    show_error(self, tr("wireless_debug_title"), tr("format_error"))
                    continue

                wait_dlg = PulseWaitDialog(self, tr("wireless_debug_title"), tr("connecting_wireless"),
                                           on_close_callback=on_wait_dialog_closed)
                wait_dlg.present()
                self._wifi_debug_wait = wait_dlg

                def bg_connect():
                    try:
                        adb_run(["disconnect", addr], timeout=2)
                        delay = 1
                        out_conn = err_conn = ""
                        ok_flag = False
                        for _ in range(3):
                            if self._wifi_debug_abort or wait_dlg.is_stopped() or _stop_event.is_set():
                                return
                            rc, out_conn, err_conn = adb_run(["connect", addr], timeout=3)
                            if "connected to" in out_conn:
                                ok_flag = True
                                break
                            time.sleep(delay)
                            delay = min(delay * 2, 4)

                        def handle_res():
                            if self._wifi_debug_abort or wait_dlg.is_stopped() or _stop_event.is_set():
                                wait_dlg.safe_close()
                                self._wifi_debug_cleanup_and_finalize(finalize_callback)
                                return
                            wait_dlg.safe_close()
                            if ok_flag:
                                self.connected_target = addr
                                self._refresh_device_ui(addr)
                                scrcpy_args = ["-s", addr, "--always-on-top", "--window-title", tr("app_title")]
                                append_video_args(scrcpy_args, video_codec, max_size, max_fps)
                                if record_file:
                                    scrcpy_args.extend(["--record", record_file])
                                if self.device_audio_limited:
                                    scrcpy_args.append("--no-audio")
                                elif audio_enable:
                                    scrcpy_args.append("--audio-source=playback")
                                    if audio_quality == "opus256":
                                        scrcpy_args.extend(["--audio-codec=opus", "--audio-bit-rate=256000", "--audio-buffer=120"])
                                    elif audio_quality == "aac256":
                                        scrcpy_args.extend(["--audio-codec=aac", "--audio-bit-rate=256000", "--audio-buffer=120"])
                                    elif audio_quality == "flac_lossless":
                                        scrcpy_args.extend(["--audio-codec=flac", "--audio-codec-options=flac-compression-level=5", "--audio-buffer=120"])
                                    else:
                                        scrcpy_args.append("--audio-buffer=120")
                                else:
                                    scrcpy_args.append("--no-audio")
                                if sleep_enable:
                                    scrcpy_args.append("-S")
                                if self.current_settings.get("keep_active", False):
                                    scrcpy_args.append("--keep-active")
                                self._start_scrcpy(scrcpy_args, record_file)
                                self.set_visible(False)
                                self._wifi_debug_cleanup_and_finalize(finalize_callback)
                            else:
                                ok = ask_question(self, tr("wireless_debug_title"),
                                                  tr("wireless_connect_fail").format(out=out_conn, err=err_conn))
                                if ok and not self._wifi_debug_abort and not _stop_event.is_set():
                                    GLib.idle_add(try_input_loop)
                                else:
                                    self._wifi_debug_abort = True
                                    self._wifi_debug_cleanup_and_finalize(finalize_callback)

                        GLib.idle_add(handle_res)
                    except Exception as e:
                        safe_log(logging.ERROR, f"Wireless debug error: {e}", exc_info=True)
                        GLib.idle_add(lambda: show_error(self, tr("app_title"), tr("generic_error").format(str(e))))
                        GLib.idle_add(lambda: self._wifi_debug_cleanup_and_finalize(finalize_callback))

                self._start_bg_thread(bg_connect, daemon=True)
                return

        try_input_loop()

    def _wifi_debug_cleanup_and_finalize(self, finalize_callback=None):
        self._wifi_debug_abort = True
        wait = self._wifi_debug_wait
        if wait:
            wait.safe_close()
            self._wifi_debug_wait = None
        if not _stop_event.is_set():
            self._resume_scan_timer()
            safe_log(logging.DEBUG, "wifi_debug cleanup: resume usb scan")
        self._safe_finalize(finalize_callback)


# ========================== Gtk.Application 子类 ==========================
class ScrcpyCastApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.scrcpy_bin = None
        self.startup_error = None

    def do_activate(self):
        win = self.get_active_window()
        if win is not None:
            win.present()
            return

        win = ScrcpyCastWindow(application=self)
        win.scrcpy_bin = self.scrcpy_bin
        win.present()

        if self.startup_error is not None:
            def fatal_err_work():
                show_error(win, tr("dep_missing_title"), self.startup_error)
                win.close()
                self.quit()
                return False
            GLib.idle_add(fatal_err_work)
        else:
            win._start_scan_timer()


# ========================== 主入口 ==========================
def main():
    os.environ["SDL_APP_ID"] = APP_ID
    os.environ["SCRCPY_ICON_DIR"] = ICON_DIR
    if False:  # 保留捆绑模式入口，未来切回时改为 True 或删除此行
        os.environ["SCRCPY_SERVER_PATH"] = BUNDLED_SCRCPY_SERVER

    app = ScrcpyCastApplication()

    if not check_tool_exists("adb"):
        app.startup_error = tr("dep_missing_msg").format(tool="adb")
        sys.stderr.write(app.startup_error + "\n")
    else:
        scrcpy_bin, err = check_scrcpy_with_version()
        if err:
            app.startup_error = err
            sys.stderr.write(err + "\n")
        else:
            app.scrcpy_bin = scrcpy_bin

    exit_code = app.run(sys.argv)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()