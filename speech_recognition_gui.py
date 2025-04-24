import sys
import os
import threading
import warnings

# PyQt5 modules for GUI components
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QFileDialog, QLabel, QComboBox, QHBoxLayout, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QMetaObject, Q_ARG, QSize
from PyQt5.QtGui import QMovie, QFont, QPixmap

# Libraries for speech recognition and audio conversion
import speech_recognition as sr
from pydub.utils import which

# Set FFmpeg environment path before importing AudioSegment
# This helps pydub find the correct ffmpeg binary for conversion
ffmpeg_path = which("ffmpeg") or r"C:\\ffmpeg\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe"
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)

from pydub import AudioSegment
AudioSegment.converter = ffmpeg_path

# Suppress unnecessary warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)


class SpeechRecognitionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.recognizer = sr.Recognizer()  # Speech recognizer instance
        self.recording = False             # Flag to track recording state
        self.thread = None                 # Thread for background recognition
        self.init_ui()                     # Build the GUI

    def init_ui(self):
        # Configure main window
        self.setWindowTitle("Speech Recognition System")
        self.setGeometry(50, 50, 1400, 900)

        # Apply dark-themed styling
        self.setStyleSheet("""
            QWidget {
                background-color: #002b2e;
                color: white;
                font-family: Arial;
            }
            QPushButton {
                background-color: #02828c;
                color: white;
                padding: 15px;
                font-size: 18px;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #00adc9;
            }
            QTextEdit {
                background-color: #035f64;
                color: white;
                font-size: 16px;
                padding: 15px;
                border-radius: 10px;
            }
            QComboBox {
                background-color: #035f64;
                color: white;
                padding: 10px;
                font-size: 16px;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout()

        # Animated logo displayed at the top
        self.logo_label = QLabel(self)
        self.logo_label.setAlignment(Qt.AlignCenter)
        movie = QMovie("logo.gif")
        movie.setScaledSize(QSize(300, 300))
        self.logo_label.setMovie(movie)
        movie.start()
        layout.addWidget(self.logo_label)

        # Dropdown to choose language for recognition
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English (US)", "en-US")
        self.lang_combo.addItem("Spanish (Spain)", "es-ES")
        self.lang_combo.addItem("French (France)", "fr-FR")
        self.lang_combo.addItem("Hindi (India)", "hi-IN")
        self.lang_combo.addItem("Chinese (Mandarin)", "zh-CN")
        layout.addWidget(self.lang_combo)

        # Buttons to start/stop recognition or open audio files
        button_layout = QHBoxLayout()

        self.btn_live = QPushButton("Start Live Recognition")
        self.btn_live.setMinimumHeight(50)
        self.btn_live.clicked.connect(self.toggle_live_recognition)
        button_layout.addWidget(self.btn_live)

        self.btn_open = QPushButton("Open Audio File")
        self.btn_open.setMinimumHeight(50)
        self.btn_open.clicked.connect(self.open_file)
        button_layout.addWidget(self.btn_open)

        layout.addLayout(button_layout)

        # Display transcribed text
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 16))
        self.text_edit.setMinimumHeight(300)
        layout.addWidget(self.text_edit)

        # Label to indicate listening mode
        self.loading_label = QLabel("Listening...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.loading_label.setStyleSheet("color: #00adc9")
        self.loading_label.hide()
        layout.addWidget(self.loading_label)

        self.setLayout(layout)

    def toggle_live_recognition(self):
        # Toggle live recognition on/off
        if not self.recording:
            self.recording = True
            self.btn_live.setText("Stop Live Recognition")
            self.thread = threading.Thread(target=self.live_recognition)
            self.thread.start()
        else:
            self.recording = False
            self.btn_live.setText("Start Live Recognition")

    def live_recognition(self):
        # Listen to microphone and transcribe in real-time
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                self.set_loading(True)
                while self.recording:
                    try:
                        audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=None)
                        if not self.recording:
                            break
                        lang = self.lang_combo.currentData()
                        text = self.recognizer.recognize_google(audio, language=lang)
                        self.update_text(f"Live ({lang}): {text}")
                    except sr.RequestError as e:
                        self.update_text(f"[API error: {e}]")
                    except Exception:
                        pass  # Suppress errors when stopping mid-sentence
        except Exception:
            pass  # Prevent microphone access errors when stopping
        finally:
            self.set_loading(False)

    def set_loading(self, visible):
        # Show or hide the listening label
        QMetaObject.invokeMethod(
            self.loading_label,
            "setVisible",
            Qt.QueuedConnection,
            Q_ARG(bool, visible)
        )

    def open_file(self):
        # Open file dialog to choose an audio file
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.mp4 *.flac *.ogg);;All Files (*)",
            options=options
        )
        if file_path:
            threading.Thread(target=self.transcribe_file, args=(file_path,)).start()

    def transcribe_file(self, file_path):
        # Transcribe an audio file (convert to WAV if needed)
        self.update_text(f"Transcribing: {os.path.basename(file_path)}")
        base, ext = os.path.splitext(file_path)

        if ext.lower() != ".wav":
            sound = AudioSegment.from_file(file_path)
            wav_path = base + "_converted.wav"
            sound.export(wav_path, format="wav")
        else:
            wav_path = file_path

        with sr.AudioFile(wav_path) as source:
            audio = self.recognizer.record(source)
            try:
                lang = self.lang_combo.currentData()
                text = self.recognizer.recognize_google(audio, language=lang)
                self.update_text(f"File ({lang}): {text}")
            except sr.RequestError as e:
                self.update_text(f"[API error: {e}]")
            except Exception as e:
                self.update_text(f"[Error: {e}]\n{str(e)}")

        if ext.lower() != ".wav" and os.path.exists(wav_path):
            os.remove(wav_path)

    def update_text(self, text):
        # Thread-safe update to text display box
        QMetaObject.invokeMethod(
            self.text_edit,
            "append",
            Qt.QueuedConnection,
            Q_ARG(str, text)
        )


# Entry point for the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpeechRecognitionApp()
    window.show()
    sys.exit(app.exec_())