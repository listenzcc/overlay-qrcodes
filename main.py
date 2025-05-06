import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PIL import Image

from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel


class TransparentWindow(QMainWindow):
    labels = {}

    def __init__(self):
        super().__init__()

        # 获取主屏幕的几何信息
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()

        # 设置窗口属性
        # self.setWindowFlags(
        #     Qt.WindowStaysOnTopHint |  # 总在最前
        #     Qt.FramelessWindowHint  |   # 无边框
        #     Qt.Tool                   # 隐藏任务栏图标
        # )
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # 总在最前
            Qt.FramelessWindowHint |   # 无边框
            Qt.X11BypassWindowManagerHint  # 绕过窗口管理器（在某些系统上实现真正的全屏）
        )

        # 设置窗口透明度和点击穿透
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 设置窗口为屏幕大小
        self.setGeometry(screen_geometry)
        print(screen_geometry)

        # 加载并显示图片
        self.load_and_display_images()

        # Run the timer
        # self.setup_timer()

        # Start the HTTP server in a separate thread
        self.start_http_server()

    def load_and_display_images(self):
        # 图片路径列表 (请替换为你的实际图片路径)
        image_paths = {
            'top_left': 'nw.png',
            'top_right': 'ne.png',
            'bottom_left': 'sw.png',
            'gaze': 'gaze.png'
        }

        # 处理并显示每张图片
        for position, path in image_paths.items():
            try:
                # 使用PIL加载并调整图片大小
                with Image.open(path) as img:
                    img = img.convert('RGBA')  # 统一转换为RGBA格式
                    img = img.resize((200, 200), Image.LANCZOS)
                    # img = img.resize((200, 200), Image.LANCZOS)
                    print('Using img', position, path, img.size, img.mode)

                    # 转换为QPixmap
                    if img.mode == 'RGBA':
                        qimage = QImage(img.tobytes(), img.width,
                                        img.height, QImage.Format_RGBA8888)
                    else:
                        raise ValueError(
                            f'Can not convert mode: {img.mode}. Only support RGBA mode.')

                    pixmap = QPixmap.fromImage(qimage)

                    # 创建并放置QLabel
                    label = QLabel(self)
                    label.setPixmap(pixmap)
                    label.resize(pixmap.size())  # 确保Label尺寸与Pixmap一致

                    # 根据位置设置坐标
                    if position == 'top_left':
                        label.move(0, 0)
                    elif position == 'top_right':
                        label.move(self.width() - pixmap.width(), 0)
                    elif position == 'bottom_left':
                        label.move(0, self.height() - pixmap.height())
                    elif position == 'gaze':
                        label.move((self.width() - pixmap.width())//2,
                                   (self.height() - pixmap.height())//2)

                    # Register the label
                    self.labels[position] = label

                    label.show()

            except Exception as e:
                print(f"加载图片 {path} 失败: {str(e)}")

        return

    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.ontime_callback)
        self.timer.start()

    def ontime_callback(self):
        t = time.time()
        T = 10  # T in seconds
        x = int((t / T % 1) * self.width())
        label = self.labels['gaze']
        y = label.pos().y()
        label.move(x, y)

    def start_http_server(self):
        def run_server(labels, width, height):
            class RequestHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    try:
                        # Parse query parameters
                        query = self.path.split('?')[-1]
                        params = dict(param.split('=')
                                      for param in query.split('&'))
                        x = float(params.get('x', 0))
                        y = float(params.get('y', 0))

                        # Update gaze label position
                        if 'gaze' in labels:
                            label = labels['gaze']
                            label.move(int(x*width),
                                       int(y*height))

                        # Send response
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(f"Position updated {x}, {y}".encode())
                    except Exception as e:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(f"Error: {str(e)}".encode())

                def log_message(self, format, *args):
                    # Suppress HTTP server logs
                    return

            server = HTTPServer(('localhost', 8080), RequestHandler)
            print("HTTP server started on port 8080")
            server.serve_forever()

        thread = threading.Thread(
            target=run_server, args=(self.labels, self.width(), self.height(),), daemon=True)
        thread.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = TransparentWindow()
    window.show()

    sys.exit(app.exec_())
