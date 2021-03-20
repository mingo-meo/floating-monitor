from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from PyQt5 import QtWidgets

import psutil
import sys
import threading


class Monitor(QWidget):
    trigger = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._startPos = None
        self._wmGap = None
        self.hidden = False
        dsk = QApplication.primaryScreen()
        self.screen_width = dsk.geometry().width()
        self.screen_height = dsk.geometry().height()
        self.window_width = 140
        self.window_height = 50
        self.label_size = 'font: 13px'
        self.cpu_gui_x = 75
        # Inform threading.Timer
        self.ui_alive = True
        # 设置窗口无边框； 设置窗口置顶；
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # 设置窗口背景透明
        # self.setAttribute(Qt.WA_TranslucentBackground)
        # 设置透明度(0~1)
        self.setWindowOpacity(0.9)
        # 设置鼠标为手状
        self.setCursor(Qt.PointingHandCursor)

        self.receive_pre = -1
        self.sent_pre = -1
        self.upload_bytes = 0
        self.upload_string = '↑' + '0B/S'
        self.download_bytes = 0
        self.download_string = '↓' + '0B/S'
        self.one_line = ''.join(['*' for i in range(40)])
        self.cpu_percent = 0
        self.cpu_percent_string = '0%'
        self.mem_percent = 0
        self.mem_percent_string = '0%'
        self.cpu_lines = ''
        self.mem_lines = ''

        # 启动线程定时器
        self.timer = threading.Timer(1, self.get_computer_info)
        self.timer.start()
        # 信号关联
        self.trigger.connect(self.update_ui_label)

    def enterEvent(self, event):
        self.hide_or_show('show', event)

    def leaveEvent(self, event):
        self.hide_or_show('hide', event)

    def hide_or_show(self, mode, event):
        # 获取窗口左上角x,y
        pos = self.frameGeometry().topLeft()
        if mode == 'show' and self.hidden:
            # 窗口左上角x + 窗口宽度 大于屏幕宽度，从右侧滑出
            if pos.x() + self.window_width >= self.screen_width:
                # 需要留10在里边，否则边界跳动
                self.startAnimation(self.screen_width - self.window_width, pos.y())
                event.accept()
                self.hidden = False
            # 窗口左上角x 小于0, 从左侧滑出
            elif pos.x() <= 0:
                self.startAnimation(0, pos.y())
                event.accept()
                self.hidden = False
            # 窗口左上角y 小于0, 从上方滑出
            elif pos.y() <= 0:
                self.startAnimation(pos.x(), 0)
                event.accept()
                self.hidden = False
        elif mode == 'hide' and (not self.hidden):
            if pos.x() + self.window_width >= self.screen_width:
                # 留10在外面
                self.startAnimation(self.screen_width - 10, pos.y(), mode, 'right')
                event.accept()
                self.hidden = True
            elif pos.x() <= 0:
                # 留10在外面
                self.startAnimation(10 - self.window_width, pos.y(), mode, 'left')
                event.accept()
                self.hidden = True
            elif pos.y() <= 0:
                # 留10在外面
                self.startAnimation(pos.x(), 10 - self.window_height, mode, 'up')
                event.accept()
                self.hidden = True

    def startAnimation(self, x, y, mode='show', direction=None):
        animation = QPropertyAnimation(self, b"geometry", self)
        # 滑出动画时长
        animation.setDuration(200)
        # 隐藏时，只留10在外边，防止跨屏
        # QRect限制其大小，防止跨屏
        num = QApplication.desktop().screenCount()
        if mode == 'hide':
            if direction == 'right':
                animation.setEndValue(QRect(x, y, 10, self.window_height))
            elif direction == 'left':
                # 多屏时采用不同的隐藏方法，防止跨屏
                if num < 2:
                    animation.setEndValue(QRect(x, y, self.window_width, self.window_height))
                else:
                    animation.setEndValue(QRect(0, y, 10, self.window_height))
            else:
                if num < 2:
                    animation.setEndValue(QRect(x, y, self.window_width, self.window_height))
                else:
                    animation.setEndValue(QRect(x, 0, self.window_width, 10))
        else:
            animation.setEndValue(QRect(x, y, self.window_width, self.window_height))
        animation.start()

    def mouseMoveEvent(self, event: QMouseEvent):
        # event.pos()减去最初相对窗口位置，获得移动距离(x,y)
        self._wmGap = event.pos() - self._startPos
        # 移动窗口，保持鼠标与窗口的相对位置不变
        # 检查是否移除了当前主屏幕
        # 左方界限
        final_pos = self.pos() + self._wmGap
        if self.frameGeometry().topLeft().x() + self._wmGap.x() <= 0:
            final_pos.setX(0)
        # 上方界限
        if self.frameGeometry().topLeft().y() + self._wmGap.y() <= 0:
            final_pos.setY(0)
        # 右方界限
        if self.frameGeometry().bottomRight().x() + self._wmGap.x() >= self.screen_width:
            final_pos.setX(self.screen_width - self.window_width)
        # 下方界限
        if self.frameGeometry().bottomRight().y() + self._wmGap.y() >= self.screen_height:
            final_pos.setY(self.screen_height - self.window_height)
        self.move(final_pos)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            # event.pos() 鼠标相对窗口的位置
            # event.globalPos() 鼠标在屏幕的绝对位置
            self._startPos = event.pos()
        if event.button() == Qt.RightButton:
            # 创建右键菜单
            menu = QMenu(self)
            menu.setStyleSheet(u"background-color: white;\n"
                               "selection-color: rgb(0, 255, 127);\n"
                               "selection-background-color: gray;\n"
                               "font: 8pt;")
            # 二级菜单
            size_menu = menu.addMenu('Bkcolor')
            light_gray = size_menu.addAction('Light-Gray')
            gray = size_menu.addAction('Gray')
            black = size_menu.addAction('Black')

            show_menu = menu.addMenu('Show')
            show_all = show_menu.addAction('show_all')
            speed_only = show_menu.addAction('speed_only')
            # 普通菜单
            quit_action = menu.addAction('Exit')
            about_action = menu.addAction('About')
            # 窗口定位到鼠标处
            action = menu.exec_(self.mapToGlobal(event.pos()))
            # 显示网速或全部显示
            if action == show_all:
                self.window_width = 140
                self.setGeometry(self.x(), self.y(), self.window_width, 50)
            if action == speed_only:
                self.window_width = 75
                self.setGeometry(self.x(), self.y(), self.window_width, 50)
            # 改变背景色
            if action == light_gray:
                self.setStyleSheet(u"background-color: rgb(100, 100, 100)")
            if action == gray:
                self.setStyleSheet(u"background-color: rgb(50, 50, 50)")
            if action == black:
                self.setStyleSheet(u"background-color: black")

            if action == quit_action:
                self.ui_alive = False
                QCoreApplication.quit()
            if action == about_action:
                # 新建MessageBox
                msg_box = QtWidgets.QMessageBox()
                # 支持HTML输入
                msg_box.about(self, "About", "<font size='3' color='white'>"
                                             "--------------------------"
                                             "<p>"
                                             "<i><b>Author: </b>Mingo.Meo</i>"
                                             "</p>"
                                             "<p>"
                                             "<i><b>Version: </b>1.0.0</i>"
                                             "</p>"
                                             "<p>"
                                             "<i><b>More: </b><a href='https://blog.csdn.net/weixin_44446598'>"
                                             "<span style='color:white'>Visit Me</span></a></i>"
                                             "</p>"
                                             "</font>")

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._startPos = None
            self._wmGap = None
        if event.button() == Qt.RightButton:
            self._startPos = None
            self._wmGap = None

    def setupUi(self):
        # 设置gui的font，获得小号字体
        font = QFont()
        font.setFamily(u"Agency FB")
        font.setPointSize(1)
        font.setBold(True)
        font.setWeight(75)
        font.setKerning(False)

        self.resize(self.window_width, self.window_height)
        self.setStyleSheet(u"background-color: rgb(50, 50, 50)")

        self.cpu_gui = QLabel(self)
        self.cpu_gui.setObjectName(u"cpu_gui")
        self.cpu_gui.setGeometry(QRect(self.cpu_gui_x, 18, 20, 24))
        self.cpu_gui.setFont(font)
        self.cpu_gui.setLayoutDirection(Qt.LeftToRight)
        self.cpu_gui.setStyleSheet(u"color: rgb(85, 170, 255);\n"
                                   "border: 1px solid;\n"
                                   "border-color: rgb(85, 170, 255);")
        self.cpu_gui.setTextFormat(Qt.AutoText)
        self.cpu_gui.setScaledContents(False)
        self.cpu_gui.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.cpu_gui.setWordWrap(False)
        self.cpu_gui.setMargin(0)
        self.cpu_gui.setIndent(-3)

        self.cpu_num = QLabel(self)
        self.cpu_num.setObjectName(u"cpu_num")
        self.cpu_num.setGeometry(QRect(self.cpu_gui_x, 0, 20, 16))
        self.cpu_num.setStyleSheet(u"color: rgb(85, 170, 255);\n%s" % self.label_size)
        self.cpu_num.setAlignment(Qt.AlignCenter)

        self.mem_gui = QLabel(self)
        self.mem_gui.setObjectName(u"mem_gui")
        self.mem_gui.setGeometry(QRect(self.cpu_gui_x + 30, 18, 20, 24))
        self.mem_gui.setFont(font)
        self.mem_gui.setLayoutDirection(Qt.LeftToRight)
        self.mem_gui.setStyleSheet(u"color: rgb(170, 255, 255);\n"
                                   "border: 1px solid;\n"
                                   "border-color: rgb(170, 255, 255);")
        self.mem_gui.setTextFormat(Qt.AutoText)
        self.mem_gui.setScaledContents(False)
        self.mem_gui.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        self.mem_gui.setWordWrap(False)
        self.mem_gui.setMargin(0)
        self.mem_gui.setIndent(-3)

        self.mem_num = QLabel(self)
        self.mem_num.setObjectName(u"mem_num")
        self.mem_num.setGeometry(QRect(self.cpu_gui_x + 30, 0, 20, 16))
        self.mem_num.setStyleSheet(u"color: rgb(170, 255, 255);\n%s" % self.label_size)
        self.mem_num.setAlignment(Qt.AlignCenter)

        self.upspeed = QLabel(self)
        self.upspeed.setObjectName(u"upspeed")
        self.upspeed.setGeometry(QRect(0, 5, 70, 16))
        self.upspeed.setStyleSheet(u"color: rgb(255, 170, 0);\n%s" % self.label_size)

        self.downspeed = QLabel(self)
        self.downspeed.setObjectName(u"downspeed")
        self.downspeed.setGeometry(QRect(0, 30, 70, 16))
        self.downspeed.setStyleSheet(u"color: rgb(85, 255, 0);\n%s" % self.label_size)
        # setupUi

    def retranslateUi(self):
        self.setWindowTitle("")
        one_line = ''.join(['*' for i in range(40)])
        n_line = ''.join([one_line + '\n' for i in range(5)])
        self.cpu_gui.setText(n_line)
        self.cpu_num.setText(u"0%")
        self.mem_gui.setText(n_line)
        self.mem_num.setText(u"0%")
        self.downspeed.setText(u"↓0.0KB/S")
        self.upspeed.setText(u"↑0.0KB/S")

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
            if net_bytes // 1024 ** 2 < 100:
                return "%.1fMB/S" % (net_bytes / 1024 ** 2)
            else:
                return "%sMB/S" % (net_bytes // 1024 ** 2)
        elif net_bytes >> 30 < 1024:
            if net_bytes // 1024 ** 3 < 100:
                return "%.1fGB/S" % (net_bytes / 1024 ** 3)
            else:
                return "%sGB/S" % (net_bytes // 1024 ** 3)
        else:
            return "xx.xB/S"

    def get_computer_info(self):
        self.get_net_speed()
        self.get_cpu_mem()
        # 通知面板更新
        self.trigger.emit()
        if self.ui_alive:
            # 重新设置定时器
            self.timer = threading.Timer(1, self.get_computer_info)
            self.timer.start()

    def get_net_speed(self):
        # 获取网速,当sent_pre或receive_pre为-1时，初始化窗口
        if self.sent_pre == -1 or self.receive_pre == -1:
            self.upload_bytes = 0
            self.download_bytes = 0
            try:
                self.sent_pre = psutil.net_io_counters().bytes_sent
                self.receive_pre = psutil.net_io_counters().bytes_recv
            except RuntimeError:
                # 如果获取失败，重新获取
                self.sent_pre = -1
                self.receive_pre = -1
        else:
            try:
                self.upload_bytes = psutil.net_io_counters().bytes_sent - self.sent_pre
                self.download_bytes = psutil.net_io_counters().bytes_recv - self.receive_pre
            except RuntimeError:
                self.sent_pre = -1
                self.receive_pre = -1
                self.upload_string = '↑' + '0B/S'
                self.download_string = '↓' + '0B/S'
            else:
                self.sent_pre += self.upload_bytes
                self.receive_pre += self.download_bytes
                self.upload_string = '↑' + Monitor.standard_net_speed(self.upload_bytes)
                self.download_string = '↓' + Monitor.standard_net_speed(self.download_bytes)

    def get_cpu_mem(self):
        self.cpu_percent = (psutil.cpu_percent(interval=0.0, percpu=False))
        self.mem_percent = psutil.virtual_memory().percent

        if self.cpu_percent >= 100:
            self.cpu_percent = 99
        if self.mem_percent >= 100:
            self.mem_percent = 99

        self.cpu_lines = ''.join([self.one_line + '\n' for i in range(int(self.cpu_percent) // 10)])
        self.mem_lines = ''.join([self.one_line + '\n' for i in range(int(self.mem_percent) // 10)])
        self.cpu_percent_string = "%d" % self.cpu_percent + '%'
        self.mem_percent_string = "%d" % self.mem_percent + '%'

    def update_ui_label(self):
        self.upspeed.setText(self.upload_string)
        self.downspeed.setText(self.download_string)
        self.cpu_num.setText("%d" % self.cpu_percent + '%')
        self.mem_num.setText("%d" % self.mem_percent + '%')
        self.cpu_gui.setText(self.cpu_lines)
        self.mem_gui.setText(self.mem_lines)


if __name__ == '__main__':
    # 设置屏幕自适应
    QtCore.QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication([])
    # 获取主显示器分辨率
    screen_width = app.primaryScreen().geometry().width()
    screen_height = app.primaryScreen().geometry().height()

    stats = Monitor()
    stats.setupUi()
    stats.retranslateUi()
    # 设置最初出现的位置
    window_width = stats.geometry().width()
    window_height = stats.geometry().height()
    stats.setGeometry(screen_width - window_width - 10, screen_height//2 - 150, window_width, window_height)

    stats.show()
    sys.exit(app.exec_())
