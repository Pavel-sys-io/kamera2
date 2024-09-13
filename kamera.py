import cv2
import telebot
import os
import time
import threading
import subprocess
import pygetwindow as gw
import pyautogui
import tempfile
import glob
import sounddevice as sd
import wave
import pyttsx3

TELEGRAM_BOT_TOKEN = '6644857900:AAFRRC2ep9sS3M24RVgz7qvu6sgikZZMBCk'

CHAT_ID = '1588129424'#Паша

NOTEPAD_PATH = 'C:\\WINDOWS\\system32\\notepad.exe'
TEXT_FILE_PATH = 'C:\\Users\\Public\\Downloads\\message.txt'

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
pause_signal = threading.Event()  # Сигнал для паузы
motion_detection_active = False  # Флаг для отслеживания состояния детектора движения
recording = False  # Флаг для состояния записи звука

audio_file_path = os.path.join(tempfile.gettempdir(), "audio_recording.wav")


# Функция для воспроизведения текста через колонки
def speak_text(text):
    engine = pyttsx3.init()
    
    # Настройка параметров голоса (необязательно)
    engine.setProperty('rate', 150)  # Скорость речи
    engine.setProperty('volume', 1)  # Громкость (1.0 - максимальная)
    
    engine.say(text)  # Озвучиваем текст
    engine.runAndWait()  # Ждем завершения озвучивания

# Функция для записи аудио
def record_audio():
    global recording, audio_file_path

    # Настройки для аудиозаписи
    fs = 44100  # Частота дискретизации
    duration = 60  # Максимальная продолжительность записи

    # Открытие файла для записи
    with wave.open(audio_file_path, 'wb') as wf:
        wf.setnchannels(1)  # Моно
        wf.setsampwidth(2)  # Размер семпла
        wf.setframerate(fs)  # Частота дискретизации

        def callback(indata, frames, time, status):
            if not recording:
                raise sd.CallbackStop()  # Остановка записи
            wf.writeframes(indata)

        # Запуск записи
        with sd.InputStream(callback=callback, channels=1, samplerate=fs, dtype='int16'):
            while recording:
                time.sleep(1)

# Функция для отправки аудиофайла в Telegram
def send_audio_to_telegram():
    try:
        with open(audio_file_path, 'rb') as audio:
            bot.send_audio(CHAT_ID, audio, caption="Аудиозапись")
        os.remove(audio_file_path)
    except Exception as e:
        print(f"Ошибка при отправке аудиофайла: {e}")

def shutdown_pc():
    if os.name == 'nt':
        os.system("shutdown /s /t 1")
    else:
        os.system("sudo shutdown now")

def reboot_pc():
    if os.name == 'nt':
        os.system("shutdown /r /t 1")
    else:
        os.system("sudo reboot")

def open_notepad():
    if not os.path.exists(TEXT_FILE_PATH):
        with open(TEXT_FILE_PATH, 'w') as f:
            pass

def close_notepad():
    windows = gw.getWindowsWithTitle('message.txt')
    if windows:
        notepad_window = windows[0]
        notepad_window.close()

def open_notepad():
    subprocess.Popen([NOTEPAD_PATH, TEXT_FILE_PATH])
    time.sleep(2)
    pyautogui.hotkey('alt', 'tab')
    windows = gw.getWindowsWithTitle('message.txt')
    if windows:
        notepad_window = windows[0]
        notepad_window.activate()
        notepad_window.alwaysOnTop = True

def write_to_file(text):
    with open(TEXT_FILE_PATH, 'w', encoding='utf-8') as file:
        file.write(text)

def clean_old_temp_files():
    temp_dir = tempfile.gettempdir()  # Получаем путь к временной директории
    now = time.time()  # Текущее время
    old_time_threshold = 10  # Порог в 10 секунд для старых файлов (в секундах)

    for temp_file in glob.glob(os.path.join(temp_dir, '*')):
        if os.stat(temp_file).st_mtime < now - old_time_threshold:
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"Не удалось удалить файл {temp_file}: {e}")

def capture_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot_temp_dir = tempfile.gettempdir()  # Временная папка для сохранения скриншотов
    screenshot_path = os.path.join(screenshot_temp_dir, 'screenshot.png')
    
    screenshot.save(screenshot_path)
    
    try:
        with open(screenshot_path, 'rb') as photo:
            bot.send_photo(CHAT_ID, photo, caption="Скриншот экрана")
        os.remove(screenshot_path)
    except Exception:
        pass

def detect_motion():
    global motion_detection_active
    cap = None  # Инициализируем камеру как None

    while True:
        if motion_detection_active and cap is None:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise SystemExit("Ошибка: не удалось открыть камеру.")
            ret, prev_frame = cap.read()
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
            prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
            bot.send_message(CHAT_ID, "Камера включена.")

        if not motion_detection_active and cap is not None:
            cap.release()
            cap = None
            bot.send_message(CHAT_ID, "Камера выключена.")
            time.sleep(1)
            continue

        if motion_detection_active:
            pause_signal.wait()  # Ожидание, пока пауза не будет снята
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            delta_frame = cv2.absdiff(prev_gray, gray)
            thresh_frame = cv2.threshold(delta_frame, 30, 255, cv2.THRESH_BINARY)[1]
            thresh_frame = cv2.dilate(thresh_frame, None, iterations=2)

            contours, _ = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                if cv2.contourArea(contour) < 5000:
                    continue
                send_image_to_telegram(frame, "Движение обнаружено!")
                break

            prev_gray = gray
            time.sleep(2)
        else:
            time.sleep(1)


def send_image_to_telegram(image, caption):
    try:
        clean_old_temp_files()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_image_path = temp_file.name
            cv2.imwrite(temp_image_path, image)
            with open(temp_image_path, 'rb') as photo:
                bot.send_photo(CHAT_ID, photo, caption=caption)
            os.remove(temp_image_path)
    except Exception:
        pass

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    commands = """
Доступные команды:
0 - Перезагрузить ПК
00 - Завершить работу ПК
1 - Сделать скриншот экрана
2 - Запустить/остановить обнаружение движения
3 - Закрыть блокнот
4 - Поставить на паузу/возобновить работу
5 - Начать/остановить запись звука
напиши текст и он будет озвучен
"""
    bot.send_message(message.chat.id, commands)

# Обработчик других сообщений от Telegram
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global motion_detection_active, recording

    if message.text.lower() == "0":
        bot.send_message(message.chat.id, "Перезагружаю ПК.")
        reboot_pc()
    elif message.text.lower() == "00":
        bot.send_message(message.chat.id, "Завершаю работу ПК.")
        shutdown_pc()
    elif message.text.lower() == "1":
        bot.send_message(message.chat.id, "Делаю скриншот экрана.")
        capture_screenshot()
    elif message.text.lower() == "2":
        if not motion_detection_active:
            bot.send_message(message.chat.id, "Запускаю обнаружение движения.")
            motion_detection_active = True
        else:
            bot.send_message(message.chat.id, "Останавливаю обнаружение движения.")
            motion_detection_active = False
    elif message.text.lower() == "3":
        bot.send_message(message.chat.id, "Закрываю блокнот.")
        close_notepad()
    elif message.text.lower() == "4":
        if pause_signal.is_set():
            bot.send_message(message.chat.id, "Останавливаю работу.")
            pause_signal.clear()  # Ставим работу на паузу
        else:
            bot.send_message(message.chat.id, "Возобновляю работу.")
            pause_signal.set()  # Возобновляем выполнение кода
    elif message.text.lower() == "5":
        if not recording:
            bot.send_message(message.chat.id, "Начинаю запись звука.")
            recording = True
            threading.Thread(target=record_audio, daemon=True).start()
        else:
            bot.send_message(message.chat.id, "Останавливаю запись звука и отправляю файл.")
            recording = False
            time.sleep(2)  # Небольшая пауза, чтобы убедиться, что запись завершена
            send_audio_to_telegram()
    else:
            bot.send_message(message.chat.id, "Сообщение записано в блокнот и будет воспроизведено.")
            write_to_file(message.text)
            open_notepad()
            speak_text(message.text)  # Воспроизводим текст через колонки


if __name__ == "__main__":
    pause_signal.set()  # Код начинает выполнение
    threading.Thread(target=detect_motion, daemon=True).start()
    bot.polling(none_stop=True)
