import json
import random
import sqlite3
import uuid
import hashlib
import os
import copy
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI()
DB_PATH = Path("/data/save.db") if os.path.exists("/data") else Path("save.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                nickname TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                nickname TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                days INTEGER NOT NULL,
                money INTEGER NOT NULL,
                rep INTEGER NOT NULL,
                nerv INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL
            )
        """)

init_db()

# ---------------- ДАННЫЕ ----------------
def make_ticket(tid, title, desc, skill, reward, rep, time, sols=None, input_data=None):
    t = {"id": tid, "title": title, "desc": desc, "skill": skill, "reward": reward, "rep": rep, "time": time}
    if sols: t["sols"] = sols
    if input_data:
        t["input"] = True
        t["answer"] = input_data["answer"]
        t["hint"] = input_data["hint"]
    return t

TICKETS = [
    # ================= NETWORK (20) =================
    # 8 вариантов
    make_ticket("net1", "Нет интернета", "Бухгалтерия не может открыть 1С.", "network", 150, 2, 10, sols=[{"text": "Перезагрузить роутер", "ok": True}, {"text": "Переустановить Windows", "ok": False}, {"text": "Проверить кабель", "ok": False}]),
    make_ticket("net2", "Медленный Wi-Fi", "Плохо ловит в переговорной.", "network", 120, 2, 10, sols=[{"text": "Переставить точку доступа", "ok": True}, {"text": "Купить новый роутер", "ok": False}, {"text": "Проверить каналы", "ok": False}]),
    make_ticket("net3", "Проблема с VPN", "Удаленщик не может подключиться.", "network", 160, 2, 10, sols=[{"text": "Проверить фаервол", "ok": True}, {"text": "Сказать 'перезагрузите'", "ok": False}, {"text": "Проверить сертификаты", "ok": False}]),
    make_ticket("net4", "Шум в трубке", "IP-телефония с помехами.", "network", 180, 2, 15, sols=[{"text": "Проверить качество канала", "ok": True}, {"text": "Заменить телефоны", "ok": False}, {"text": "Настроить QoS", "ok": False}]),
    make_ticket("net5", "Сбой DHCP", "Сотрудники не получают IP-адреса.", "network", 160, 2, 15, sols=[{"text": "Проверить DHCP-сервер", "ok": True}, {"text": "Задать статические IP", "ok": False}, {"text": "Проверить пул", "ok": False}]),
    make_ticket("net6", "Мусорный трафик", "В сети замечен странный трафик.", "network", 280, 5, 20, sols=[{"text": "Проверить соединения", "ok": True}, {"text": "Перезагрузить роутер", "ok": False}, {"text": "Заблокировать IP", "ok": False}]),
    make_ticket("net7", "Проверка кабеля", "Нужно проверить витую пару.", "network", 90, 1, 10, sols=[{"text": "Использовать тестер", "ok": True}, {"text": "Заменить кабель", "ok": False}, {"text": "Переобжать коннекторы", "ok": False}]),
    make_ticket("net8", "Перегрузка канала", "Веб-сайт тормозит из-за нагрузки.", "network", 200, 3, 15, sols=[{"text": "Настроить трафик-шейпер", "ok": True}, {"text": "Отключить сервер", "ok": False}, {"text": "Добавить канал", "ok": False}]),
    # 12 кода
    make_ticket("net9", "Проверка DNS", "Не резолвится домен. Введите команду nslookup.", "network", 150, 2, 5, input_data={"answer": "nslookup google.com", "hint": "nslookup <домен>"}),
    make_ticket("net10", "Открытые порты", "Введите команду для просмотра открытых портов.", "network", 180, 2, 10, input_data={"answer": "netstat -tuln", "hint": "netstat -tuln"}),
    make_ticket("net11", "Пинг сервера", "Проверьте доступность 8.8.8.8 (4 пакета).", "network", 100, 1, 5, input_data={"answer": "ping -c 4 8.8.8.8", "hint": "ping -c 4 <ip>"}),
    make_ticket("net12", "Скачивание файла", "Скачайте файл по ссылке http://example.com/file.zip", "network", 150, 2, 10, input_data={"answer": "wget http://example.com/file.zip", "hint": "wget <url>"}),
    make_ticket("net13", "Смена MAC", "Смените MAC-адрес на eth0.", "network", 200, 3, 15, input_data={"answer": "macchanger -r eth0", "hint": "macchanger -r <интерфейс>"}),
    make_ticket("net14", "Проверка IP", "Покажите IP-адреса всех интерфейсов.", "network", 120, 2, 5, input_data={"answer": "ip a", "hint": "ip a"}),
    make_ticket("net15", "Маршрутизация", "Покажите таблицу маршрутизации.", "network", 160, 2, 10, input_data={"answer": "ip route", "hint": "ip route"}),
    make_ticket("net16", "Трассировка", "Проверьте маршрут до 8.8.8.8.", "network", 180, 3, 15, input_data={"answer": "traceroute 8.8.8.8", "hint": "traceroute <ip>"}),
    make_ticket("net17", "Слушающие порты", "Покажите только слушающие TCP-порты.", "network", 200, 3, 10, input_data={"answer": "ss -tln", "hint": "ss -tln"}),
    make_ticket("net18", "Статус сети", "Покажите статус сетевых интерфейсов.", "network", 100, 1, 5, input_data={"answer": "networkctl status", "hint": "networkctl status"}),
    make_ticket("net19", "ARP таблица", "Покажите ARP-таблицу.", "network", 140, 2, 10, input_data={"answer": "arp -a", "hint": "arp -a"}),
    make_ticket("net20", "Сброс сети", "Перезапустите сетевую службу.", "network", 220, 3, 15, input_data={"answer": "systemctl restart networking", "hint": "systemctl restart networking"}),

    # ================= SECURITY (20) =================
    # 8 вариантов
    make_ticket("sec1", "Фишинг", "Письмо от 'директора' с просьбой перевести деньги.", "security", 250, 5, 15, sols=[{"text": "Заблокировать отправителя", "ok": True}, {"text": "Перевести деньги", "ok": False}, {"text": "Проверить заголовки", "ok": False}]),
    make_ticket("sec2", "Утечка данных", "База клиентов попала в сеть.", "security", 400, 8, 30, sols=[{"text": "Проверить логи", "ok": True}, {"text": "Сменить пароли", "ok": False}, {"text": "Игнорировать", "ok": False}]),
    make_ticket("sec3", "Взлом почты", "Пароль от почты утек.", "security", 350, 6, 20, sols=[{"text": "Сменить пароль и 2FA", "ok": True}, {"text": "Ничего не делать", "ok": False}, {"text": "Проверить сессии", "ok": False}]),
    make_ticket("sec4", "Хакерская атака", "Уязвимость SQL-инъекции.", "security", 400, 7, 25, sols=[{"text": "Закрыть уязвимость", "ok": True}, {"text": "Оставить", "ok": False}, {"text": "Обновить CMS", "ok": False}]),
    make_ticket("sec5", "Шифровальщик", "Файлы зашифрованы.", "security", 500, 10, 30, sols=[{"text": "Отключить от сети", "ok": True}, {"text": "Заплатить выкуп", "ok": False}, {"text": "Восстановить из бэкапа", "ok": False}]),
    make_ticket("sec6", "Пиратский софт", "Установили нелицензионный Photoshop.", "security", 180, 4, 15, sols=[{"text": "Удалить и купить", "ok": True}, {"text": "Оставить", "ok": False}, {"text": "Проверить ПК", "ok": False}]),
    make_ticket("sec7", "Открыт порт", "На сервере открыт лишний порт.", "security", 180, 3, 15, sols=[{"text": "Настроить iptables", "ok": True}, {"text": "Выключить сервер", "ok": False}, {"text": "Использовать ufw", "ok": False}]),
    make_ticket("sec8", "Взлом Wi-Fi", "Брутфорс пароля от Wi-Fi.", "security", 220, 4, 20, sols=[{"text": "Включить WPA3", "ok": True}, {"text": "Отключить Wi-Fi", "ok": False}, {"text": "Проверить логи", "ok": False}]),
    # 12 кода
    make_ticket("sec9", "Права на скрипт", "Сделайте файл run.sh исполняемым.", "security", 170, 2, 8, input_data={"answer": "chmod +x run.sh", "hint": "chmod +x <файл>"}),
    make_ticket("sec10", "Смена прав", "Дайте права 777 папке /var/www.", "security", 160, 2, 10, input_data={"answer": "chmod 777 /var/www", "hint": "chmod 777 <путь>"}),
    make_ticket("sec11", "Поиск SUID", "Найдите файлы с битом SUID.", "security", 250, 4, 15, input_data={"answer": "find / -perm -4000", "hint": "find / -perm -4000"}),
    make_ticket("sec12", "Проверка хеша", "Вычислите SHA-256 для файла file.txt", "security", 150, 2, 10, input_data={"answer": "sha256sum file.txt", "hint": "sha256sum <файл>"}),
    make_ticket("sec13", "Блокировка IP", "Заблокируйте IP 1.2.3.4 через iptables.", "security", 200, 3, 15, input_data={"answer": "iptables -A INPUT -s 1.2.3.4 -j DROP", "hint": "iptables -A INPUT -s <ip> -j DROP"}),
    make_ticket("sec14", "Статус фаервола", "Проверьте статус ufw.", "security", 120, 2, 5, input_data={"answer": "ufw status", "hint": "ufw status"}),
    make_ticket("sec15", "Прослушивание", "Запустите прослушивание трафика на eth0.", "security", 280, 5, 20, input_data={"answer": "tcpdump -i eth0", "hint": "tcpdump -i <интерфейс>"}),
    make_ticket("sec16", "Проверка пользователей", "Покажите текущих пользователей в системе.", "security", 100, 1, 5, input_data={"answer": "who", "hint": "who"}),
    make_ticket("sec17", "История команд", "Покажите историю команд.", "security", 80, 1, 5, input_data={"answer": "history", "hint": "history"}),
    make_ticket("sec18", "Поиск паролей", "Найдите файлы с именем 'password'.", "security", 220, 4, 15, input_data={"answer": "find / -name '*password*'", "hint": "find / -name '*password*'"}),
    make_ticket("sec19", "Права папки", "Покажите права на папку /etc.", "security", 90, 1, 5, input_data={"answer": "ls -ld /etc", "hint": "ls -ld <путь>"}),
    make_ticket("sec20", "Смена владельца", "Сделайте пользователя root владельцем файла file.txt.", "security", 160, 2, 10, input_data={"answer": "chown root file.txt", "hint": "chown <пользователь> <файл>"}),

    # ================= WINDOWS (20) =================
    # 8 вариантов
    make_ticket("win1", "Забыл пароль", "Сотрудник не может войти в почту.", "windows", 80, 1, 5, sols=[{"text": "Сбросить через AD", "ok": True}, {"text": "Сказать 'не ко мне'", "ok": False}, {"text": "Проверить учетку", "ok": False}]),
    make_ticket("win2", "Обновление Windows", "Обновить ПК на 10 машинах.", "windows", 250, 3, 20, sols=[{"text": "Групповые политики", "ok": True}, {"text": "Обновлять вручную", "ok": False}, {"text": "Использовать WSUS", "ok": False}]),
    make_ticket("win3", "Потерян файл", "Удалили макет и очистили корзину.", "windows", 200, 3, 15, sols=[{"text": "Восстановить из бэкапа", "ok": True}, {"text": "Сказать, что пропал", "ok": False}, {"text": "Использовать Recuva", "ok": False}]),
    make_ticket("win4", "Завис компьютер", "Завис на логотипе Windows.", "windows", 150, 2, 15, sols=[{"text": "Безопасный режим", "ok": True}, {"text": "Ждать", "ok": False}, {"text": "Проверить диск", "ok": False}]),
    make_ticket("win5", "Нет звука", "Пропал звук в наушниках.", "windows", 50, 1, 5, sols=[{"text": "Проверить настройки", "ok": True}, {"text": "Купить новые", "ok": False}, {"text": "Переустановить драйвер", "ok": False}]),
    make_ticket("win6", "Неверное время", "Сбилось время на ПК.", "windows", 80, 1, 5, sols=[{"text": "Настроить NTP", "ok": True}, {"text": "Выставить вручную", "ok": False}, {"text": "Перезагрузить ПК", "ok": False}]),
    make_ticket("win7", "Тормозит 1С", "Медленная 1С.", "windows", 180, 3, 15, sols=[{"text": "Проверить нагрузку", "ok": True}, {"text": "Перезагрузить", "ok": False}, {"text": "Оптимизировать", "ok": False}]),
    make_ticket("win8", "Зависает Excel", "Excel вылетает.", "windows", 80, 1, 10, sols=[{"text": "Отключить надстройки", "ok": True}, {"text": "Переустановить", "ok": False}, {"text": "Проверить на вирусы", "ok": False}]),
    # 12 кода
    make_ticket("win9", "Проверка системы", "Запустите проверку целостности системных файлов.", "windows", 180, 3, 20, input_data={"answer": "sfc /scannow", "hint": "sfc /scannow"}),
    make_ticket("win10", "Сброс сети", "Сбросьте настройки сети через командную строку.", "windows", 150, 2, 10, input_data={"answer": "netsh winsock reset", "hint": "netsh winsock reset"}),
    make_ticket("win11", "Просмотр IP", "Покажите полную конфигурацию сети.", "windows", 100, 1, 5, input_data={"answer": "ipconfig /all", "hint": "ipconfig /all"}),
    make_ticket("win12", "Очистка DNS", "Очистите кэш DNS.", "windows", 80, 1, 5, input_data={"answer": "ipconfig /flushdns", "hint": "ipconfig /flushdns"}),
    make_ticket("win13", "Проверка диска", "Запустите проверку диска C на ошибки.", "windows", 200, 3, 25, input_data={"answer": "chkdsk C: /f", "hint": "chkdsk <диск> /f"}),
    make_ticket("win14", "Список процессов", "Покажите запущенные процессы.", "windows", 120, 2, 5, input_data={"answer": "tasklist", "hint": "tasklist"}),
    make_ticket("win15", "Убить процесс", "Завершите процесс notepad.exe.", "windows", 140, 2, 10, input_data={"answer": "taskkill /IM notepad.exe /F", "hint": "taskkill /IM <имя> /F"}),
    make_ticket("win16", "Просмотр служб", "Покажите список служб.", "windows", 100, 1, 5, input_data={"answer": "sc query", "hint": "sc query"}),
    make_ticket("win17", "Перезапуск службы", "Перезапустите службу spooler.", "windows", 180, 3, 10, input_data={"answer": "net stop spooler && net start spooler", "hint": "net stop <служба> && net start <служба>"}),
    make_ticket("win18", "Просмотр событий", "Откройте журнал событий (командой).", "windows", 160, 2, 10, input_data={"answer": "eventvwr", "hint": "eventvwr"}),
    make_ticket("win19", "Сетевые подключения", "Покажите сетевые подключения.", "windows", 110, 1, 5, input_data={"answer": "ncpa.cpl", "hint": "ncpa.cpl"}),
    make_ticket("win20", "Информация о системе", "Покажите информацию о системе.", "windows", 90, 1, 5, input_data={"answer": "systeminfo", "hint": "systeminfo"}),

    # ================= LINUX (20) =================
    # 8 вариантов
    make_ticket("lin1", "Бэкап падает", "Ночной бэкап падает.", "linux", 250, 4, 20, sols=[{"text": "Проверить место", "ok": True}, {"text": "Отключить", "ok": False}, {"text": "Проверить права", "ok": False}]),
    make_ticket("lin2", "Пароль root", "Сбросить пароль root.", "linux", 250, 4, 20, sols=[{"text": "Single-user", "ok": True}, {"text": "Переустановить", "ok": False}, {"text": "Использовать livecd", "ok": False}]),
    make_ticket("lin3", "Сбой БД", "База повреждена.", "linux", 300, 5, 25, sols=[{"text": "Восстановить из дампа", "ok": True}, {"text": "Удалить", "ok": False}, {"text": "Запустить repair", "ok": False}]),
    make_ticket("lin4", "Мусор в логах", "Логи переполнены.", "linux", 120, 2, 10, sols=[{"text": "Очистить", "ok": True}, {"text": "Отключить", "ok": False}, {"text": "Настроить ротацию", "ok": False}]),
    make_ticket("lin5", "Закончилось место", "Диск / переполнен.", "linux", 200, 3, 15, sols=[{"text": "Очистить логи", "ok": True}, {"text": "Удалить всё", "ok": False}, {"text": "Проверить место", "ok": False}]),
    make_ticket("lin6", "Ошибка Nginx", "Сайт не работает.", "linux", 220, 3, 15, sols=[{"text": "Перезапустить nginx", "ok": True}, {"text": "Перезагрузить сервер", "ok": False}, {"text": "Проверить конфиг", "ok": False}]),
    make_ticket("lin7", "Служба упала", "Служба не запускается.", "linux", 180, 2, 10, sols=[{"text": "Проверить статус и логи", "ok": True}, {"text": "Удалить службу", "ok": False}, {"text": "Переустановить", "ok": False}]),
    make_ticket("lin8", "Медленный сервер", "Высокая нагрузка на CPU.", "linux", 250, 4, 20, sols=[{"text": "Проверить процессы (top)", "ok": True}, {"text": "Перезагрузить", "ok": False}, {"text": "Купить новый", "ok": False}]),
    # 12 кода
    make_ticket("lin9", "Логи бэкапа", "Посмотрите 10 строк /var/log/backup.log.", "linux", 200, 3, 10, input_data={"answer": "tail -n 10 /var/log/backup.log", "hint": "tail -n 10 <файл>"}),
    make_ticket("lin10", "Статус Nginx", "Проверьте статус nginx.", "linux", 180, 2, 8, input_data={"answer": "systemctl status nginx", "hint": "systemctl status <служба>"}),
    make_ticket("lin11", "Свободное место", "Проверьте место на дисках.", "linux", 220, 3, 10, input_data={"answer": "df -h", "hint": "df -h"}),
    make_ticket("lin12", "Создать папку", "Создайте директорию /backup.", "linux", 120, 1, 5, input_data={"answer": "sudo mkdir /backup", "hint": "sudo mkdir <путь>"}),
    make_ticket("lin13", "Архивация", "Упакуйте /var/log в logs.tar.gz.", "linux", 250, 4, 15, input_data={"answer": "tar -czvf logs.tar.gz /var/log", "hint": "tar -czvf <архив> <папка>"}),
    make_ticket("lin14", "Поиск файла", "Найдите файл secret.txt.", "linux", 200, 3, 15, input_data={"answer": "find / -name secret.txt", "hint": "find / -name <имя>"}),
    make_ticket("lin15", "Права", "Покажите права на файл file.txt.", "linux", 90, 1, 5, input_data={"answer": "ls -l file.txt", "hint": "ls -l <файл>"}),
    make_ticket("lin16", "Память", "Покажите использование оперативной памяти.", "linux", 100, 1, 5, input_data={"answer": "free -h", "hint": "free -h"}),
    make_ticket("lin17", "Процессы", "Покажите топ-процессы по CPU.", "linux", 150, 2, 10, input_data={"answer": "top", "hint": "top"}),
    make_ticket("lin18", "Журнал", "Покажите последние 20 строк системного журнала.", "linux", 180, 2, 10, input_data={"answer": "journalctl -n 20", "hint": "journalctl -n 20"}),
    make_ticket("lin19", "Ядро", "Покажите версию ядра.", "linux", 80, 1, 5, input_data={"answer": "uname -r", "hint": "uname -r"}),
    make_ticket("lin20", "Пользователи", "Покажите список пользователей.", "linux", 110, 1, 5, input_data={"answer": "cat /etc/passwd", "hint": "cat /etc/passwd"}),

    # ================= HARDWARE (20) =================
    # 8 вариантов
    make_ticket("hw1", "Принтер не печатает", "Очередь есть, бумаги нет.", "hardware", 100, 1, 8, sols=[{"text": "Очистить очередь", "ok": True}, {"text": "Заменить картридж", "ok": False}, {"text": "Переустановить драйвер", "ok": False}]),
    make_ticket("hw2", "Синий экран", "BSOD.", "hardware", 200, 3, 15, sols=[{"text": "Проверить память", "ok": True}, {"text": "Купить новый", "ok": False}, {"text": "Посмотреть код", "ok": False}]),
    make_ticket("hw3", "Не работает мышь", "Беспроводная мышь.", "hardware", 50, 1, 3, sols=[{"text": "Заменить батарейку", "ok": True}, {"text": "Переустановить Windows", "ok": False}, {"text": "Переподключить USB", "ok": False}]),
    make_ticket("hw4", "Сервер не включается", "После скачка напряжения.", "hardware", 300, 5, 25, sols=[{"text": "Проверить БП", "ok": True}, {"text": "Заменить мат. плату", "ok": False}, {"text": "Проверить ИБП", "ok": False}]),
    make_ticket("hw5", "Пыльный сервер", "Гул из серверной.", "hardware", 140, 2, 12, sols=[{"text": "Заменить вентилятор", "ok": True}, {"text": "Закрыть дверь", "ok": False}, {"text": "Почистить", "ok": False}]),
    make_ticket("hw6", "Сбой RAID", "Диск вышел из строя.", "hardware", 300, 5, 20, sols=[{"text": "Заменить диск", "ok": True}, {"text": "Игнорировать", "ok": False}, {"text": "Пересборка", "ok": False}]),
    make_ticket("hw7", "Сброс BIOS", "Сбросить BIOS.", "hardware", 100, 1, 10, sols=[{"text": "Достать батарейку", "ok": True}, {"text": "Заменить материнку", "ok": False}, {"text": "Перемычка", "ok": False}]),
    make_ticket("hw8", "Медленный диск", "SSD тормозит.", "hardware", 150, 2, 15, sols=[{"text": "Проверить AHCI", "ok": True}, {"text": "Заменить диск", "ok": False}, {"text": "Обновить прошивку", "ok": False}]),
    # 12 кода
    make_ticket("hw9", "Проверка дисков", "Выведите список блочных устройств.", "hardware", 120, 2, 10, input_data={"answer": "lsblk", "hint": "lsblk"}),
    make_ticket("hw10", "Проверка SMART", "Проверьте SMART статус диска /dev/sda.", "hardware", 200, 3, 15, input_data={"answer": "smartctl -a /dev/sda", "hint": "smartctl -a <диск>"}),
    make_ticket("hw11", "Температура CPU", "Узнайте температуру процессора.", "hardware", 100, 1, 5, input_data={"answer": "sensors", "hint": "sensors"}),
    make_ticket("hw12", "Список PCI", "Покажите все PCI-устройства.", "hardware", 80, 1, 5, input_data={"answer": "lspci", "hint": "lspci"}),
    make_ticket("hw13", "Скорость диска", "Измерьте скорость записи на диск.", "hardware", 180, 3, 15, input_data={"answer": "dd if=/dev/zero of=test bs=1M count=1024", "hint": "dd if=/dev/zero of=test bs=1M count=1024"}),
    make_ticket("hw14", "USB устройства", "Покажите подключенные USB-устройства.", "hardware", 90, 1, 5, input_data={"answer": "lsusb", "hint": "lsusb"}),
    make_ticket("hw15", "Загрузка", "Покажите список устройств загрузки.", "hardware", 130, 2, 10, input_data={"answer": "efibootmgr", "hint": "efibootmgr"}),
    make_ticket("hw16", "Частота CPU", "Покажите частоту процессора.", "hardware", 100, 1, 5, input_data={"answer": "lscpu", "hint": "lscpu"}),
    make_ticket("hw17", "Память", "Покажите информацию о памяти.", "hardware", 110, 1, 5, input_data={"answer": "free -h", "hint": "free -h"}),
    make_ticket("hw18", "Ядро", "Покажите версию ядра.", "hardware", 80, 1, 5, input_data={"answer": "uname -r", "hint": "uname -r"}),
    make_ticket("hw19", "Сеть", "Покажите сетевые интерфейсы.", "hardware", 90, 1, 5, input_data={"answer": "ip link", "hint": "ip link"}),
    make_ticket("hw20", "Питание", "Покажите статус батареи (если есть).", "hardware", 70, 1, 5, input_data={"answer": "upower -i /org/freedesktop/UPower/devices/battery_BAT0", "hint": "upower -i <путь>"})
]

ITEMS = [
    {"id": "i3", "name": "☕ Кофемашина", "desc": "Восстанавливает нервы (+5)", "price": 800, "eff": {"nerv": 5}},
    {"id": "i2", "name": "🛡️ Антивирус", "desc": "Следующий провал по security не отнимет репутацию", "price": 1500, "eff": {"antivirus": 1}},
    {"id": "i8", "name": "💊 Антидепрессанты", "desc": "При падении нервов до 0 восстанавливает 20 (Одноразово)", "price": 1800, "eff": {"antidepressants": 1}},
    {"id": "i4", "name": "💾 Бэкап", "desc": "При падении репутации до 0 восстанавливает 20 (Одноразово)", "price": 2000, "eff": {"backup": 1}},
    {"id": "i6", "name": "🌐 Мощный роутер", "desc": "+2 network, +1 нерв за сетевые тикеты", "price": 2000, "eff": {"skill": "network", "val": 2}},
    {"id": "i5", "name": "🛠️ Набор инструментов", "desc": "+2 hardware, +10% к деньгам за железо", "price": 2500, "eff": {"skill": "hardware", "val": 2}},
    {"id": "i7", "name": "📱 Второй монитор", "desc": "+2 windows, +10% к деньгам за Windows", "price": 2500, "eff": {"skill": "windows", "val": 2}},
    {"id": "i1", "name": "🖥️ Новый сервер", "desc": "+1 сервер (+200₽ в день)", "price": 3000, "eff": {"srv": 1}}
]

def new_state():
    return {
        "nickname": "",
        "day": 1, "money": 500, "rep": 50, "nerv": 100,
        "servers_total": 0,
        "tickets": [], "ticket_idx": 0, "ticket_data": None,
        "used_tickets": [],
        "log": [], "game_over": None,
        "skills": {"network": 1, "windows": 1, "linux": 1, "security": 1, "hardware": 1},
        "antivirus": 0,
        "backup": 0,
        "antidepressants": 0,
        "hardware_bonus": 0,
        "windows_bonus": 0
    }

def apply_eff(state, eff):
    if not eff: return
    if "srv" in eff: state["servers_total"] += eff["srv"]
    if "rep" in eff: state["rep"] = max(0, min(100, state["rep"] + eff["rep"]))
    if "nerv" in eff: state["nerv"] = max(0, min(100, state["nerv"] + eff["nerv"]))
    if "antivirus" in eff: state["antivirus"] += 1
    if "backup" in eff: state["backup"] += 1
    if "antidepressants" in eff: state["antidepressants"] += 1
    if "skill" in eff:
        s = eff["skill"]
        state["skills"][s] = state["skills"].get(s, 1) + eff.get("val", 1)
        if s == "hardware": state["hardware_bonus"] = 1
        if s == "windows": state["windows_bonus"] = 1

def load_state(sid: str):
    with get_db() as conn:
        row = conn.execute("SELECT state FROM sessions WHERE id = ?", (sid,)).fetchone()
    return json.loads(row["state"]) if row else None

def save_state(sid: str, state: dict):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO sessions (id, state) VALUES (?, ?)", (sid, json.dumps(state)))

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>SysAdmin Simulator</title>
    <style>
        :root { 
            --bg: #0f0a1a; --panel: #1f1733; --border: #2d2148; 
            --accent: #8b5cf6; --text: #e9e4f5; --muted: #9a8fb5; 
            --ok: #34d399; --bad: #f87171; --gold: #fbbf24; 
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', sans-serif; 
            background: radial-gradient(circle at 20% 0%, #1e1338 0%, var(--bg) 60%); 
            color: var(--text); 
            min-height: 100vh; 
            display: flex; 
            justify-content: center; 
        }
        .app { width: 100%; max-width: 1600px; padding: 20px; display: flex; flex-direction: column; gap: 20px; min-height: 100vh; }
        .topbar { display: flex; align-items: center; gap: 24px; padding: 20px 24px; background: var(--panel); border: 1px solid var(--border); border-radius: 12px; flex-wrap: wrap; }
        .brand { font-weight: 800; font-size: 24px; color: #a78bfa; white-space: nowrap; }
        .brand span { color: var(--muted); }
        .stats { display: flex; gap: 32px; flex-wrap: wrap; flex: 1; font-size: 16px; }
        .stat { display: flex; flex-direction: column; }
        .stat-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-val { font-weight: 700; font-size: 18px; }
        .stat-val.ok { color: var(--ok); } .stat-val.bad { color: var(--bad); }
        .btn-top { background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 15px; transition: 0.2s; font-weight: 600; }
        .btn-top:hover { border-color: var(--accent); color: #a78bfa; background: rgba(139,92,246,0.1); }
        .btn-top.shop { border-color: var(--accent); color: #a78bfa; }
        .btn-top.leader { border-color: var(--gold); color: var(--gold); }
        .main { display: grid; grid-template-columns: 1fr 380px; gap: 20px; flex: 1; }
        .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 32px; display: flex; flex-direction: column; gap: 24px; height: 100%; min-height: 500px; }
        .panel h2 { font-size: 28px; color: #a78bfa; margin-bottom: 10px; }
        .panel-body { flex: 1; display: flex; flex-direction: column; gap: 16px;}
        .panel-body p { font-size: 18px; line-height: 1.6; margin-bottom: 12px; }
        .muted { color: var(--muted); }
        .actions { display: flex; flex-direction: column; gap: 12px; margin-top: 20px; }
        .btn-primary { background: linear-gradient(180deg, var(--accent), #6d3fd4); color: #fff; border: none; padding: 16px 24px; border-radius: 8px; font-weight: 600; font-size: 16px; cursor: pointer; transition: 0.2s; box-shadow: 0 4px 15px rgba(139,92,246,0.3); text-align: center; width: fit-content; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(139,92,246,0.4); }
        .btn-choice { display: block; width: 100%; text-align: left; background: rgba(139,92,246,0.08); border: 1px solid var(--border); color: var(--text); padding: 16px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; margin-bottom: 12px; transition: 0.15s; font-weight: 500; }
        .btn-choice:hover { border-color: var(--accent); background: rgba(139,92,246,0.18); transform: translateX(4px); }
        .btn-shop { display: flex; justify-content: space-between; align-items: center; width: 100%; background: rgba(139,92,246,0.08); border: 1px solid var(--border); color: var(--text); padding: 16px 24px; border-radius: 8px; cursor: pointer; font-size: 16px; margin-bottom: 12px; text-align: left; transition: 0.15s; }
        .btn-shop:hover { border-color: var(--accent); background: rgba(139,92,246,0.18); transform: translateX(4px); }
        .btn-shop .price { color: var(--gold); font-weight: 700; font-size: 18px; }
        .btn-shop .desc { color: var(--muted); font-size: 14px; display: block; margin-top: 4px; }
        .cmd-input { width: 100%; padding: 16px; background: #000; color: #34d399; border: 1px solid #444; border-radius: 8px; font-family: 'Consolas', monospace; font-size: 18px; outline: none; margin-bottom: 16px; }
        .cmd-input:focus { border-color: var(--accent); box-shadow: 0 0 10px rgba(139,92,246,0.3); }
        .sidebar { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 24px; height: 100%; }
        .sidebar h3 { font-size: 13px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; margin-top: 24px; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); padding-bottom: 6px;}
        .sidebar h3:first-child { margin-top: 0; }
        .skills { list-style: none; }
        .skills li { display: flex; justify-content: space-between; padding: 8px 0; font-size: 16px; border-bottom: 1px dashed rgba(139,92,246,0.2); }
        .skills li:last-child { border-bottom: none; }
        .skills .lvl { color: #a78bfa; font-weight: 700; font-size: 18px; }
        .log { list-style: none; font-size: 14px; max-height: 300px; overflow-y: auto; padding-right: 5px;}
        .log li { padding: 8px 0; border-bottom: 1px dashed var(--border); color: var(--muted); }
        .log li:last-child { border-bottom: none; }
        .leaderboard-table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 16px; }
        .leaderboard-table th, .leaderboard-table td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
        .leaderboard-table th { color: var(--muted); font-size: 13px; text-transform: uppercase; }
        .leaderboard-table tr:hover { background: rgba(139,92,246,0.05); }
        .status-win { color: var(--ok); font-weight: 700; }
        .status-lose { color: var(--bad); font-weight: 700; }
        .status-progress { color: var(--gold); font-weight: 700; }
        .status-ended { color: var(--muted); font-weight: 700; }
        .reg-input { width: 100%; padding: 16px; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 8px; font-size: 16px; outline: none; margin-bottom: 16px; }
        .reg-input:focus { border-color: var(--accent); }
        @media (max-width: 1000px) {
            .main { grid-template-columns: 1fr; }
            .sidebar { height: auto; }
        }
    </style>
</head>
<body>
    <div class="app">
        <header class="topbar">
            <div class="brand">🖥️ SYSADMIN<span>·SIM</span></div>
            <div class="stats" id="stats"></div>
            <button class="btn-top leader" onclick="showLeaderboard()">🏆 Рекорды</button>
            <button class="btn-top shop" onclick="showShop()">🛒 Магазин</button>
            <button class="btn-top" onclick="quitGame()">Выход</button>
        </header>
        <main class="main">
            <section class="panel">
                <h2 id="title">Загрузка...</h2>
                <div class="panel-body" id="body"></div>
                <div class="actions" id="actions"></div>
            </section>
            <aside class="sidebar">
                <h3>Профиль</h3>
                <div id="profile" style="margin-bottom:16px; font-weight:700; color:var(--accent); font-size:20px;">Гость</div>
                <h3>Навыки</h3>
                <ul class="skills" id="skills"></ul>
                <h3>Журнал</h3>
                <ul class="log" id="log"></ul>
            </aside>
        </main>
    </div>

    <script>
        let SID = localStorage.getItem('sysadmin_sid');
        let STATE = null;
        let USED_HINT = false;

        async function initGame() {
            if (!SID) {
                SID = Math.random().toString(36).substring(2, 15);
                localStorage.setItem('sysadmin_sid', SID);
            }
            const res = await fetch(`/api/state?sid=${SID}&nocache=${Date.now()}`);
            STATE = await res.json();
            updateUI(STATE);
            
            if (!STATE.nickname) {
                showAuth();
            } else if (STATE.game_over) {
                showGameOver();
            } else if (STATE.ticket_data) {
                renderTicket(STATE.ticket_data);
            } else {
                showWelcome();
            }
        }

        async function fetchAPI(url, method = 'GET', body = null) {
            try {
                const opts = { method, headers: { 'Content-Type': 'application/json' } };
                if (body) opts.body = JSON.stringify(body);
                const finalUrl = `${url}${url.includes('?') ? '&' : '?'}sid=${SID}&nocache=${Date.now()}`;
                const res = await fetch(finalUrl, opts);
                return res.ok ? await res.json() : null;
            } catch (e) {
                console.error(e);
                return null;
            }
        }

        function updateUI(state) {
            if (!state) return;
            STATE = state;
            
            document.getElementById('profile').textContent = state.nickname || 'Гость';
            
            document.getElementById('stats').innerHTML = `
                <div class="stat"><span class="stat-label">День</span><span class="stat-val">${state.day}</span></div>
                <div class="stat"><span class="stat-label">Деньги</span><span class="stat-val">${state.money}₽</span></div>
                <div class="stat"><span class="stat-label">Серверы</span><span class="stat-val">${state.servers_total}</span></div>
                <div class="stat"><span class="stat-label">Репутация</span><span class="stat-val ${state.rep < 30 ? 'bad' : 'ok'}">${state.rep}</span></div>
                <div class="stat"><span class="stat-label">Нервы</span><span class="stat-val ${state.nerv < 30 ? 'bad' : 'ok'}">${state.nerv}</span></div>
            `;
            document.getElementById('skills').innerHTML = `
                <li><span>network</span><span class="lvl">${state.skills.network}</span></li>
                <li><span>windows</span><span class="lvl">${state.skills.windows}</span></li>
                <li><span>linux</span><span class="lvl">${state.skills.linux}</span></li>
                <li><span>security</span><span class="lvl">${state.skills.security}</span></li>
                <li><span>hardware</span><span class="lvl">${state.skills.hardware}</span></li>
            `;
            document.getElementById('log').innerHTML = (state.log || []).slice(-10).reverse()
                .map(l => `<li>${l}</li>`).join('') || '<li class="muted">пусто</li>';
        }

        function setPanel(title, body, actions) {
            document.getElementById('title').textContent = title;
            document.getElementById('body').innerHTML = body;
            document.getElementById('actions').innerHTML = '';
            if (actions) {
                actions.forEach(act => {
                    const btn = document.createElement('button');
                    btn.textContent = act.text;
                    btn.className = act.class || 'btn-primary';
                    btn.onclick = act.onClick;
                    document.getElementById('actions').appendChild(btn);
                });
            }
        }

        function showAuth() {
            setPanel('Вход / Регистрация', 
                `<p class="muted">Введите никнейм и пароль.</p>
                 <input type="text" id="nick-input" class="reg-input" placeholder="Ваш никнейм..." maxlength="20">
                 <input type="password" id="pass-input" class="reg-input" placeholder="Пароль..." maxlength="30">
                 <p id="auth-error" style="color:var(--bad); display:none; margin-bottom:10px; font-size:16px;"></p>`,
                [{ text: 'Войти', onClick: authPlayer }]
            );
            setTimeout(() => document.getElementById('nick-input').focus(), 100);
        }

        async function authPlayer() {
            const nick = document.getElementById('nick-input').value.trim();
            const pass = document.getElementById('pass-input').value.trim();
            const err = document.getElementById('auth-error');
            
            if (!nick || !pass) { 
                err.textContent = "Заполните оба поля!"; 
                err.style.display = 'block';
                return; 
            }
            
            const r = await fetchAPI('/api/auth', 'POST', { nickname: nick, password: pass });
            if (!r) { err.textContent = "Ошибка сервера."; err.style.display = 'block'; return; }
            
            if (!r.ok) {
                err.textContent = r.error || "Ошибка авторизации";
                err.style.display = 'block';
                return;
            }
            
            updateUI(r.state);
            showWelcome();
        }

        function showWelcome() {
            if (!STATE.nickname) { showAuth(); return; }
            setPanel(`Добро пожаловать, ${STATE.nickname}!`, 
                '<p class="muted">Вы — системный администратор.</p><p>Нажмите «Начать день», чтобы приступить к работе.</p>',
                [{ text: 'Начать день', onClick: startDay }]
            );
        }

        function showGameOver() {
            let title = 'Игра окончена';
            let desc = '';
            
            if (STATE.game_over === 'win') {
                title = '🏆 Победа!';
                desc = `<p>Вы продержались все 30 дней и спасли компанию от IT-апокалипсиса!</p>
                        <p class="muted">Ваш результат занесен в таблицу рекордов.</p>`;
            } else if (STATE.game_over === 'rep') {
                title = 'Уволен';
                desc = `<p>Ваша репутация упала до нуля. Директор вызвал вас «на ковёр».</p>`;
            } else if (STATE.game_over === 'nerves') {
                title = 'Выгорание';
                desc = `<p>Ваши нервы сдали. Пора в отпуск — на неопределённый срок.</p>`;
            } else {
                title = 'Игра окончена';
                desc = `<p>Ваши статы упали до нуля. Вас уволили.</p>`;
            }

            desc += `<p class="muted">Дней пройдено: ${STATE.day} | Деньги: ${STATE.money}₽ | Репутация: ${STATE.rep} | Нервы: ${STATE.nerv}</p>`;

            setPanel(title, desc, [
                { text: '🏆 Рекорды', onClick: showLeaderboard, class: 'btn-primary' },
                { text: 'Сыграть снова', onClick: newGame, class: 'btn-primary' }
            ]);
        }

        async function startDay() {
            if (!STATE.nickname) { showAuth(); return; }
            const r = await fetchAPI('/api/start_day', 'POST');
            if (!r || !r.state) return;
            updateUI(r.state);
            if (r.state.ticket_data) {
                USED_HINT = false;
                renderTicket(r.state.ticket_data);
            } else {
                showEndDay();
            }
        }

        function renderTicket(t) {
            USED_HINT = false;
            let repDisplay = t.rep;
            if (t.input) repDisplay += 1; // Если задача с кодом, показываем +1 бонус
            let html = `<p>${t.desc}</p><p class="muted">Награда: ${t.reward}₽ | Репутация: +${repDisplay} | Время: ${t.time} мин</p>`;
            if (t.input) {
                html += `<div style="margin-top:20px; width:100%;">
                    <input type="text" id="cmd-input" class="cmd-input" placeholder="Введите команду..." autocomplete="off">
                    <div style="display:flex; gap:12px;">
                        <button class="btn-primary" onclick="submitCommand()">Выполнить</button>
                        <button class="btn-primary" style="background:transparent; border:1px solid var(--border); box-shadow:none;" onclick="showHint()">Подсказка</button>
                    </div>
                    <p id="hint-text" style="color:var(--gold); margin-top:16px; display:none; font-size:16px;">💡 ${t.hint}</p>
                </div>`;
                
                setPanel(t.title, html, []);
                
                setTimeout(() => {
                    const inp = document.getElementById('cmd-input');
                    if (inp) {
                        inp.focus();
                        inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') submitCommand(); });
                    }
                }, 100);
            } else {
                let actions = t.sols.map((sol, i) => ({
                    text: sol.text, class: 'btn-choice', onClick: () => answerTicket(i)
                }));
                setPanel(t.title, html, actions);
            }
        }

        function showHint() {
            USED_HINT = true;
            const h = document.getElementById('hint-text');
            if (h) h.style.display = 'block';
        }

        async function submitCommand() {
            const cmd = document.getElementById('cmd-input').value.trim();
            if (!cmd) return;
            
            const r = await fetchAPI('/api/ticket', 'POST', { answer: cmd, used_hint: USED_HINT });
            if (!r || !r.state) return;
            updateUI(r.state);
            
            if (r.state.game_over) return showGameOver();
            
            if (r.state.ticket_data) {
                USED_HINT = false;
                renderTicket(r.state.ticket_data);
            } else {
                showEndDay();
            }
        }

        async function answerTicket(idx) {
            const r = await fetchAPI('/api/ticket', 'POST', { idx, used_hint: USED_HINT });
            if (!r || !r.state) return;
            updateUI(r.state);
            
            if (r.state.game_over) return showGameOver();
            
            if (r.state.ticket_data) {
                USED_HINT = false;
                renderTicket(r.state.ticket_data);
            } else {
                showEndDay();
            }
        }

        function showEndDay() {
            setPanel('Рабочий день окончен', '<p>Все тикеты на сегодня решены.</p>', [
                { text: 'В магазин', onClick: showShop, class: 'btn-primary' },
                { text: 'Следующий день', onClick: endDay, class: 'btn-primary' }
            ]);
        }

        async function endDay() {
            if (!STATE.nickname) { showAuth(); return; }
            const r = await fetchAPI('/api/end_day', 'POST');
            if (!r || !r.state) return;
            updateUI(r.state);
            
            if (r.state.game_over) {
                showGameOver();
            } else {
                if (r.state.ticket_data) {
                    USED_HINT = false;
                    renderTicket(r.state.ticket_data);
                } else {
                    showEndDay();
                }
            }
        }

        async function showShop() {
            if (!STATE.nickname) { showAuth(); return; }
            const r = await fetchAPI('/api/shop');
            if (!r) return;
            let html = `<p class="muted">У вас ${r.money}₽ на счету. | Серверы: ${STATE.servers_total} (Доход: +${STATE.servers_total * 200}₽/день)</p>`;
            let actions = r.items.map(it => ({
                text: it.name, class: 'btn-shop',
                html: `<div><strong>${it.name}</strong><span class="desc">${it.desc}</span></div><div class="price">${it.price}₽</div>`,
                onClick: () => buyItem(it.id)
            }));
            actions.push({ text: 'Вернуться', onClick: () => {
                if (STATE.ticket_data) renderTicket(STATE.ticket_data);
                else showEndDay();
            }, class: 'btn-primary' });
            
            document.getElementById('title').textContent = '🛒 Магазин';
            document.getElementById('body').innerHTML = html;
            const actDiv = document.getElementById('actions');
            actDiv.innerHTML = '';
            actions.forEach(act => {
                const btn = document.createElement('button');
                if (act.html) btn.innerHTML = act.html; else btn.textContent = act.text;
                btn.className = act.class; btn.onclick = act.onClick;
                actDiv.appendChild(btn);
            });
        }

        async function buyItem(id) {
            if (!STATE.nickname) { showAuth(); return; }
            const r = await fetchAPI('/api/buy', 'POST', { id });
            if (!r) return;
            if (!r.ok) { alert(r.error || "Недостаточно денег!"); return; }
            updateUI(r.state);
            showShop();
        }

        async function showLeaderboard() {
            if (!STATE.nickname) { showAuth(); return; }
            const r = await fetchAPI('/api/leaderboard');
            if (!r) return;
            
            let html = `<p class="muted">Топ-10 лучших результатов.</p>`;
            
            if (r.length === 0) {
                html += `<p class="muted">Пока нет рекордов. Сыграйте игру до конца!</p>`;
            } else {
                html += `<table class="leaderboard-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Никнейм</th>
                            <th>Дата</th>
                            <th>Дней</th>
                            <th>Деньги</th>
                            <th>Репутация</th>
                            <th>Нервы</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>`;
                r.forEach((row, i) => {
                    let statusClass = 'status-progress';
                    if (row.status === 'Победа') statusClass = 'status-win';
                    if (row.status === 'Проигрыш') statusClass = 'status-lose';
                    if (row.status === 'Завершено') statusClass = 'status-ended';
                    
                    html += `<tr>
                        <td>${i + 1}</td>
                        <td>${row.nickname}</td>
                        <td>${row.date}</td>
                        <td>${row.days}</td>
                        <td>${row.money}₽</td>
                        <td>${row.rep}</td>
                        <td>${row.nerv}</td>
                        <td class="${statusClass}">${row.status}</td>
                    </tr>`;
                });
                html += `</tbody></table>`;
            }
            
            setPanel('🏆 Таблица рекордов', html, [
                { text: 'Вернуться', onClick: () => {
                    if (STATE.game_over) showGameOver();
                    else if (STATE.ticket_data) renderTicket(STATE.ticket_data);
                    else showWelcome();
                }, class: 'btn-primary' }
            ]);
        }

        function quitGame() {
            if (STATE && STATE.nickname) {
                const data = new Blob([JSON.stringify({ sid: SID })], { type: 'application/json' });
                navigator.sendBeacon('/api/quit?sid=' + SID, data);
            }
            localStorage.removeItem('sysadmin_sid');
            setTimeout(() => location.reload(), 100);
        }

        function newGame() {
            localStorage.removeItem('sysadmin_sid');
            location.reload();
        }

        window.addEventListener('beforeunload', function (e) {
            if (STATE && STATE.nickname && !STATE.game_over) {
                const data = new Blob([JSON.stringify({ sid: SID })], { type: 'application/json' });
                navigator.sendBeacon('/api/quit?sid=' + SID, data);
            }
        });

        window.onload = initGame;
    </script>
</body>
</html>
"""

def generate_unique_tickets(state):
    by_skill = {"network": [], "windows": [], "linux": [], "security": [], "hardware": []}
    for t in TICKETS:
        by_skill[t["skill"]].append(t)
    
    # Выбираем 3 категории
    categories = random.sample(["network", "windows", "linux", "security", "hardware"], k=3)
    picked = []
    
    for cat in categories:
        available = [t for t in by_skill[cat] if t["id"] not in state.get("used_tickets", [])]
        if not available:
            available = by_skill[cat]
            
        # Разделяем на "выбор" и "код"
        sols_pool = [t for t in available if "sols" in t]
        input_pool = [t for t in available if "input" in t]
        
        # Гарантируем, что попадется хотя бы 1 с кодом, если это возможно
        if cat == categories[0] and input_pool:
            t = random.choice(input_pool)
        elif cat == categories[1] and sols_pool:
            t = random.choice(sols_pool)
        else:
            t = random.choice(available)
            
        picked.append(t)
        state["used_tickets"].append(t["id"])
    
    if len(state["used_tickets"]) > 50:
        state["used_tickets"] = state["used_tickets"][-50:]
    
    return [t["id"] for t in picked]

def save_to_leaderboard(nickname, state, status):
    now = datetime.now().strftime("%d.%m")
    with get_db() as conn:
        row = conn.execute("SELECT * FROM leaderboard WHERE nickname = ?", (nickname,)).fetchone()
        
        if row:
            old = dict(row)
            is_better = (state["day"] > old["days"]) or \
                        (state["day"] == old["days"] and state["money"] > old["money"]) or \
                        (state["day"] == old["days"] and state["money"] == old["money"] and state["rep"] > old["rep"])
            
            if old["status"] == "Победа":
                return
            
            if is_better or status in ["Завершено", "Проигрыш"]:
                conn.execute("""
                    UPDATE leaderboard 
                    SET date=?, days=?, money=?, rep=?, nerv=?, status=?
                    WHERE nickname=?
                """, (now, state["day"], state["money"], state["rep"], state["nerv"], status, nickname))
        else:
            conn.execute("""
                INSERT INTO leaderboard (nickname, date, days, money, rep, nerv, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (nickname, now, state["day"], state["money"], state["rep"], state["nerv"], status))

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(HTML_PAGE, headers={"Cache-Control": "no-store"})

@app.get("/api/state")
async def get_state(request: Request, sid: str = None):
    if not sid: sid = str(uuid.uuid4())
    state = load_state(sid)
    if not state:
        state = new_state()
        save_state(sid, state)
    return JSONResponse(state, headers={"Cache-Control": "no-store"})

@app.post("/api/auth")
async def auth(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False, "error": "Сессия не найдена"})
    
    body = await request.json()
    nickname = body.get("nickname", "").strip()
    password = body.get("password", "").strip()
    
    if not nickname or not password:
        return JSONResponse({"ok": False, "error": "Ник и пароль обязательны"})
    
    p_hash = hash_password(password)
    
    with get_db() as conn:
        acc = conn.execute("SELECT password_hash FROM accounts WHERE nickname = ?", (nickname,)).fetchone()
        
        if acc:
            if acc["password_hash"] != p_hash:
                return JSONResponse({"ok": False, "error": "Неверный пароль"})
        else:
            conn.execute("INSERT INTO accounts (nickname, password_hash) VALUES (?, ?)", (nickname, p_hash))
    
    state["nickname"] = nickname
    save_state(sid, state)
    
    save_to_leaderboard(nickname, state, "В процессе")
    
    return JSONResponse({"ok": True, "state": state}, headers={"Cache-Control": "no-store"})

@app.post("/api/quit")
async def quit_game(request: Request, sid: str = None):
    state = load_state(sid)
    if state and state.get("nickname"):
        if not state.get("game_over"):
            save_to_leaderboard(state["nickname"], state, "Завершено")
    return JSONResponse({"ok": True})

@app.get("/api/leaderboard")
async def get_leaderboard():
    with get_db() as conn:
        rows = conn.execute("SELECT nickname, date, days, money, rep, nerv, status FROM leaderboard ORDER BY days DESC, money DESC LIMIT 10").fetchall()
    return JSONResponse([dict(r) for r in rows], headers={"Cache-Control": "no-store"})

@app.post("/api/start_day")
async def start_day(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False})

    if state.get("game_over"):
        return JSONResponse({"ok": False, "state": state})

    state["log"] = []
    state["tickets"] = generate_unique_tickets(state)
    state["ticket_idx"] = 0
    
    first_id = state["tickets"][0]
    first_ticket = next((x for x in TICKETS if x["id"] == first_id), None)
    
    if first_ticket:
        first_ticket = copy.deepcopy(first_ticket)
        if "sols" in first_ticket:
            random.shuffle(first_ticket["sols"])
        state["ticket_data"] = first_ticket
    
    save_state(sid, state)
    return JSONResponse({"ok": True, "state": state}, headers={"Cache-Control": "no-store"})

@app.post("/api/ticket")
async def answer_ticket(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False})
    
    if state.get("game_over"):
        return JSONResponse({"ok": False, "state": state})
    
    body = await request.json()
    idx = body.get("idx")
    user_answer = body.get("answer")
    used_hint = body.get("used_hint", False)
    
    if state["ticket_idx"] < len(state["tickets"]):
        tid = state["tickets"][state["ticket_idx"]]
        current_ticket = state.get("ticket_data")
        
        is_correct = False
        
        if current_ticket:
            if current_ticket.get("input"):
                expected = current_ticket["answer"].lower().strip()
                if user_answer and user_answer.lower().strip() == expected:
                    is_correct = True
            else:
                if idx is not None and "sols" in current_ticket and 0 <= idx < len(current_ticket["sols"]):
                    if current_ticket["sols"][idx]["ok"]:
                        is_correct = True

        if is_correct:
            reward = current_ticket["reward"]
            if current_ticket["skill"] == "hardware" and state.get("hardware_bonus"): reward = int(reward * 1.1)
            if current_ticket["skill"] == "windows" and state.get("windows_bonus"): reward = int(reward * 1.1)
            
            state["money"] += reward
            
            # --- ИЗМЕНЕНИЕ БАЛАНСА ---
            rep_gain = current_ticket["rep"]
            if current_ticket.get("input"):
                rep_gain += 1  # +1 репутации за кодовые задачи
                
            rep_penalty = 2 if (used_hint and current_ticket.get("input")) else 0 # -2 за подсказку
            
            state["rep"] = min(100, state["rep"] + rep_gain - rep_penalty)
            
            nerv_gain = 1
            if current_ticket["skill"] == "network" and state.get("skills", {}).get("network", 0) >= 3:
                nerv_gain += 1
            state["nerv"] = min(100, state["nerv"] + nerv_gain)
            
            if "skill" in current_ticket:
                skill_name = current_ticket["skill"]
                state["skills"][skill_name] = state["skills"].get(skill_name, 1) + 1
                state["log"].append(f"🎓 Навык {skill_name} повышен!")
            
            log_msg = f"✅ {current_ticket['title']} — решено (+{reward}₽, +{rep_gain} реп)"
            if rep_penalty > 0:
                log_msg += f" (штраф за подсказку: -{rep_penalty} реп)"
            state["log"].append(log_msg)
        else:
            # --- БЛОК ПРОВАЛА ---
            if current_ticket["skill"] == "security" and state.get("antivirus", 0) > 0:
                state["antivirus"] -= 1
                state["log"].append(f"🛡️ Антивирус сработал! Провал по security без потери репутации.")
                state["nerv"] = max(0, state["nerv"] - 3)
            else:
                state["rep"] = max(0, state["rep"] - current_ticket["rep"])
                state["nerv"] = max(0, state["nerv"] - 3)
                state["log"].append(f"❌ {current_ticket['title']} — провал (-{current_ticket['rep']} реп, -3 нерва)")
        
        state["ticket_idx"] += 1
        
        if state["ticket_idx"] < len(state["tickets"]):
            next_id = state["tickets"][state["ticket_idx"]]
            next_ticket = next((x for x in TICKETS if x["id"] == next_id), None)
            
            if next_ticket:
                next_ticket = copy.deepcopy(next_ticket)
                if "sols" in next_ticket:
                    random.shuffle(next_ticket["sols"])
                state["ticket_data"] = next_ticket
            else:
                state["ticket_data"] = None
        else:
            state["ticket_data"] = None
    
    # Проверка на конец игры
    if state["rep"] <= 0:
        if state.get("backup", 0) > 0:
            state["backup"] -= 1
            state["rep"] = 20
            state["log"].append("💾 Бэкап сработал! Репутация восстановлена до 20.")
        else:
            state["game_over"] = "lose"
            state["log"].append("💀 Вы потеряли репутацию. Игра окончена.")
            if state.get("nickname"): save_to_leaderboard(state["nickname"], state, "Проигрыш")

    if state["nerv"] <= 0:
        if state.get("antidepressants", 0) > 0:
            state["antidepressants"] -= 1
            state["nerv"] = 20
            state["log"].append("💊 Антидепрессанты сработали! Нервы восстановлены до 20.")
        else:
            state["game_over"] = "lose"
            state["log"].append("💀 Вы выгорели. Игра окончена.")
            if state.get("nickname"): save_to_leaderboard(state["nickname"], state, "Проигрыш")
    
    save_state(sid, state)
    return JSONResponse({"ok": True, "state": state}, headers={"Cache-Control": "no-store"})

@app.get("/api/shop")
async def get_shop(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False})
    return JSONResponse({"items": ITEMS, "money": state["money"]}, headers={"Cache-Control": "no-store"})

@app.post("/api/buy")
async def buy(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False})
    body = await request.json()
    item_id = body.get("id")
    item = next((x for x in ITEMS if x["id"] == item_id), None)
    if not item: return JSONResponse({"ok": False, "error": "Товар не найден"})
    if state["money"] < item["price"]: return JSONResponse({"ok": False, "error": "Недостаточно денег!"})
    state["money"] -= item["price"]
    apply_eff(state, item["eff"])
    state["log"].append(f"✅ Куплено: {item['name']}")
    save_state(sid, state)
    return JSONResponse({"ok": True, "state": state}, headers={"Cache-Control": "no-store"})

@app.post("/api/end_day")
async def end_day(request: Request, sid: str = None):
    state = load_state(sid)
    if not state: return JSONResponse({"ok": False})
    
    if state.get("game_over"):
        return JSONResponse({"ok": False, "state": state})
        
    state["day"] += 1
    state["nerv"] = min(100, state["nerv"] + 1)
    
    server_income = state["servers_total"] * 200
    if server_income > 0:
        state["money"] += server_income
        state["log"].append(f"💰 Доход с серверов: +{server_income}₽")
    
    state["log"].append(f"🌅 Наступил день {state['day']}!")
    
    if state["rep"] <= 0: 
        if state.get("backup", 0) > 0:
            state["backup"] -= 1
            state["rep"] = 20
            state["log"].append("💾 Бэкап сработал! Репутация восстановлена.")
        else:
            state["game_over"] = "lose"
            state["log"].append("💀 Вы потеряли репутацию. Игра окончена.")
            if state.get("nickname"): save_to_leaderboard(state["nickname"], state, "Проигрыш")
            
    elif state["nerv"] <= 0: 
        if state.get("antidepressants", 0) > 0:
            state["antidepressants"] -= 1
            state["nerv"] = 20
            state["log"].append("💊 Антидепрессанты сработали! Нервы восстановлены.")
        else:
            state["game_over"] = "lose"
            state["log"].append("💀 Вы выгорели. Игра окончена.")
            if state.get("nickname"): save_to_leaderboard(state["nickname"], state, "Проигрыш")
            
    elif state["day"] > 30: 
        state["game_over"] = "win"
        
    if state.get("nickname") and not state.get("game_over"):
        save_to_leaderboard(state["nickname"], state, "В процессе")
    elif state.get("nickname") and state["game_over"] == "win":
        save_to_leaderboard(state["nickname"], state, "Победа")
    
    state["tickets"] = generate_unique_tickets(state)
    state["ticket_idx"] = 0
    first_id = state["tickets"][0]
    first_ticket = next((x for x in TICKETS if x["id"] == first_id), None)
    
    if first_ticket:
        first_ticket = copy.deepcopy(first_ticket)
        if "sols" in first_ticket:
            random.shuffle(first_ticket["sols"])
        state["ticket_data"] = first_ticket
    
    save_state(sid, state)
    return JSONResponse({"ok": True, "state": state}, headers={"Cache-Control": "no-store"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)