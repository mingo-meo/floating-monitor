from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication
from monitor_ui import Ui_Form
from PySide2 import QtCore
import psutil
import threading
import sys


class Stats(Ui_Form):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # self._init_ui()
        # 设置窗口无边框； 设置窗口置顶；
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # 设置窗口背景透明
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置透明度(0~1)
        self.setWindowOpacity(0.9)
        # 设置鼠标为手状
        self.setCursor(Qt.PointingHandCursor)
        # 设置初始值
        self.speed = 0
        self.cpu = 0
        self.receive_pre = -1
        self.sent_pre = -1
        self.one_line = ''.join(['*' for i in range(40)])

        self.timer = QtCore.QTimer(self)
        self.timer.start(1000)
        self.timer.timeout.connect(self.update_ui_label)

    def update_ui_label(self):
        # 开启独立线程
        threading.Thread(target=self.set_labels, daemon=True).start()

    def set_labels(self):
        self.set_net_speed()
        self.set_cpu_mem()

    def set_net_speed(self):
        # 获取网速,当sent_pre或receive_pre为-1时，初始化窗口
        if self.sent_pre == -1 or self.receive_pre == -1:
            upload_bytes = 0
            download_bytes = 0
            self.sent_pre = psutil.net_io_counters().bytes_sent
            self.receive_pre = psutil.net_io_counters().bytes_recv
        else:
            upload_bytes = psutil.net_io_counters().bytes_sent - self.sent_pre
            download_bytes = psutil.net_io_counters().bytes_recv - self.receive_pre
            self.sent_pre += upload_bytes
            self.receive_pre += download_bytes

        self.upspeed.setText('↑' + Stats.standard_net_speed(upload_bytes))
        self.downspeed.setText('↓' + Stats.standard_net_speed(download_bytes))

    def set_cpu_mem(self):
        # 整个进程尽量在1S内结束
        cpu_percent = (psutil.cpu_percent(interval=0, percpu=False))
        mem_percent = psutil.virtual_memory().percent

        if cpu_percent >= 100:
            cpu_percent = 99
        if mem_percent >= 100:
            mem_percent = 99

        self.cpu_num.setText("%d" % cpu_percent + '%')
        self.mem_num.setText("%d" % mem_percent + '%')

        cpu_lines = ''.join([self.one_line + '\n' for i in range(int(cpu_percent)//10 + 1)])
        mem_lines = ''.join([self.one_line + '\n' for i in range(int(mem_percent) // 10 + 1)])

        self.cpu_gui.setText(cpu_lines)
        self.mem_gui.setText(mem_lines)

    @staticmethod
    def standard_net_speed(net_bytes: int):
        # xx.xB/S or xxxB/S
        if net_bytes < 1000:
            if net_bytes < 100:
                return " %sB/S" % str(net_bytes)
            else:
                return "%sB/S" % str(net_bytes)

        elif net_bytes >> 10 < 1000:
            if net_bytes // 1024 < 100:
                return "%.1fKB/S" % (net_bytes / 1024)
            else:
                return "%sKB/S" % (net_bytes // 1024)
        elif net_bytes >> 20 < 1000:
            if net_bytes // 1024**2 < 100:
                return "%.1fMB/S" % (net_bytes / 1024**2)
            else:
                return "%sMB/S" % (net_bytes // 1024**2)
        elif net_bytes >> 30 < 1024:
            if net_bytes // 1024 ** 3 < 100:
                return "%.1fGB/S" % (net_bytes / 1024 ** 3)
            else:
                return "%sGB/S" % (net_bytes // 1024 ** 3)
        else:
            return "xx.xB/S"


if __name__ == '__main__':
    # 设置屏幕自适应
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

    app = QApplication([])
    # 获取主显示器分辨率
    screen_width = app.primaryScreen().geometry().width()
    screen_height = app.primaryScreen().geometry().height()

    stats = Stats()
    # 设置最初出现的位置
    window_width = stats.geometry().width()
    window_height = stats.geometry().height()
    stats.setGeometry(screen_width - window_width - 10, screen_height//2 - 150, window_width, window_height)

    stats.show()
    sys.exit(app.exec_())

