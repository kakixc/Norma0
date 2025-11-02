import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from telethon import TelegramClient, events
import threading
import json
import os

# Configuration file
CONFIG_FILE = 'bot_config.json'

# Global variables
is_running = {}
client = None
loop = None


def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        'api_id': '',
        'api_hash': '',
        'phone': '',
        'delay': 0.15,
        'stata_enabled': True  # Добавлено: значение по умолчанию
    }


def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


async def toggle_loop(chat_id, delay, stata_enabled):
    """Toggle loop for 0/1 messages with stata every 10 seconds"""
    current_value = 0
    start_time = asyncio.get_event_loop().time()
    last_stata_time = start_time

    while is_running.get(chat_id, False):
        try:
            current_time = asyncio.get_event_loop().time()

            # Check if 10 seconds passed for stata (only if enabled)
            if stata_enabled and current_time - last_stata_time >= 10:
                stata_msg = await client.send_message(chat_id, "стата дня")
                log_message(f"[Chat {chat_id}] Sent: стата дня (STATA)")

                await asyncio.sleep(0.1)
                await client.delete_messages(chat_id, stata_msg.id)
                log_message(f"[Chat {chat_id}] Deleted: стата дня (STATA)")

                last_stata_time = current_time
                await asyncio.sleep(delay)

            # Send regular 0/1 message
            message = await client.send_message(chat_id, str(current_value))
            log_message(f"[Chat {chat_id}] Sent: {current_value}")

            await asyncio.sleep(delay)
            await client.delete_messages(chat_id, message.id)
            log_message(f"[Chat {chat_id}] Deleted: {current_value}")

            current_value = 1 - current_value
            await asyncio.sleep(delay)

        except Exception as e:
            log_message(f"Error in toggle loop for chat {chat_id}: {e}")
            is_running[chat_id] = False
            break

    log_message(f"[Chat {chat_id}] Toggle stopped")


def log_message(message):
    """Add message to log text widget"""
    if hasattr(log_message, 'text_widget'):
        log_message.text_widget.insert(tk.END, message + '\n')
        log_message.text_widget.see(tk.END)


async def handle_message(event):
    """Handle incoming messages"""
    message_text = event.message.text.strip().lower()
    chat_id = event.chat_id
    delay = float(delay_var.get())

    # Использование значения из переменной флажка
    stata_enabled = stata_var.get() == 1

    log_message(f"[DEBUG] Received message: '{message_text}'")

    if message_text == 'норма 0':
        await event.delete()

        if is_running.get(chat_id, False):
            log_message(f"[Chat {chat_id}] Already running")
            return

        log_message(f"[Chat {chat_id}] Starting toggle...")
        log_message(f"[Chat {chat_id}] Stata is {'enabled' if stata_enabled else 'disabled'}")

        is_running[chat_id] = True
        # ИСПРАВЛЕНИЕ 1: Передан обязательный аргумент stata_enabled
        asyncio.create_task(toggle_loop(chat_id, delay, stata_enabled=stata_enabled))

    elif message_text == 'норма стоп':
        await event.delete()

        if is_running.get(chat_id, False):
            is_running[chat_id] = False
            log_message(f"[Chat {chat_id}] Stopping toggle...")
        else:
            log_message(f"[Chat {chat_id}] Not running")


async def start_bot(api_id, api_hash, phone, password):
    """Start the Telegram bot"""
    global client

    try:
        client = TelegramClient('session_name', api_id, api_hash)

        @client.on(events.NewMessage(outgoing=True))
        async def message_handler(event):
            await handle_message(event)

        await client.start(
            phone=phone,
            password=password if password else None
        )

        log_message("=" * 50)
        log_message("Bot started successfully!")
        log_message("Commands:")
        log_message("  'норма 0' - Start toggle")
        log_message("  'норма стоп' - Stop toggle")
        log_message("=" * 50)

        await client.run_until_disconnected()

    except Exception as e:
        log_message(f"Error: {e}")
        messagebox.showerror("Error", str(e))


def run_bot_thread(api_id, api_hash, phone, password):
    """Run bot in separate thread"""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot(api_id, api_hash, phone, password))


def start_button_click():
    """Handle start button click"""
    api_id = api_id_entry.get().strip()
    api_hash = api_hash_entry.get().strip()
    phone = phone_entry.get().strip()
    password = password_entry.get().strip()
    delay = delay_entry.get().strip()
    stata_enabled_val = stata_var.get() == 1  # Получаем значение флажка

    if not api_id or not api_hash or not phone:
        messagebox.showerror("Error", "Please fill in API ID, API Hash, and Phone!")
        return

    try:
        api_id = int(api_id)
        float(delay)
    except ValueError:
        messagebox.showerror("Error", "API ID must be a number and Delay must be a decimal!")
        return

    # Save config, включая состояние флажка
    config = {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone,
        'delay': float(delay),
        'stata_enabled': stata_enabled_val
    }
    save_config(config)

    # Disable start button and entries
    start_btn.config(state='disabled')
    api_id_entry.config(state='disabled')
    api_hash_entry.config(state='disabled')
    phone_entry.config(state='disabled')
    password_entry.config(state='disabled')
    delay_entry.config(state='disabled')
    stata_check.config(state='disabled')  # Отключаем флажок
    stop_btn.config(state='normal')

    # Start bot in separate thread
    bot_thread = threading.Thread(target=run_bot_thread, args=(api_id, api_hash, phone, password), daemon=True)
    bot_thread.start()

    log_message("Starting bot...")


def stop_button_click():
    """Handle stop button click"""
    global client, loop

    if client:
        # Stop all running toggles
        for chat_id in list(is_running.keys()):
            is_running[chat_id] = False

        if loop and client:
            # ИСПРАВЛЕНИЕ 2: Изменен способ вызова disconnect из другого потока
            def disconnect_task():
                # Создаем задачу для отключения
                asyncio.ensure_future(client.disconnect())

            try:
                loop.call_soon_threadsafe(disconnect_task)
            except RuntimeError as e:
                log_message(f"Error disconnecting bot: {e}")

        log_message("Stopping bot...")
        client = None  # Очищаем клиента

    # Enable start button and entries
    start_btn.config(state='normal')
    api_id_entry.config(state='normal')
    api_hash_entry.config(state='normal')
    phone_entry.config(state='normal')
    password_entry.config(state='normal')
    delay_entry.config(state='normal')
    stata_check.config(state='normal')  # Включаем флажок
    stop_btn.config(state='disabled')


def create_gui():
    """Create the GUI"""
    global api_id_entry, api_hash_entry, phone_entry, password_entry, delay_entry
    global start_btn, stop_btn, delay_var, stata_var, stata_check

    root = tk.Tk()
    root.title("Telegram UserBot Norma0 Controller by @kaktusi_top")
    root.geometry("700x650")  # Немного увеличим высоту для новой опции
    root.resizable(False, False)

    # Load config
    config = load_config()
    delay_var = tk.StringVar(value=str(config.get('delay', 0.15)))
    stata_var = tk.IntVar(value=config.get('stata_enabled', True))  # Добавлено: переменная для флажка

    # Main frame
    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Configuration section
    config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
    config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

    # API ID
    ttk.Label(config_frame, text="API ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
    api_id_entry = ttk.Entry(config_frame, width=50)
    api_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
    api_id_entry.insert(0, config.get('api_id', ''))

    # API Hash
    ttk.Label(config_frame, text="API Hash:").grid(row=1, column=0, sticky=tk.W, pady=5)
    api_hash_entry = ttk.Entry(config_frame, width=50)
    api_hash_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
    api_hash_entry.insert(0, config.get('api_hash', ''))

    # Phone
    ttk.Label(config_frame, text="Phone:").grid(row=2, column=0, sticky=tk.W, pady=5)
    phone_entry = ttk.Entry(config_frame, width=50)
    phone_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
    phone_entry.insert(0, config.get('phone', ''))

    # Password (2FA)
    ttk.Label(config_frame, text="Password (2FA):").grid(row=3, column=0, sticky=tk.W, pady=5)
    password_entry = ttk.Entry(config_frame, width=50, show="*")
    password_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

    # Delay
    ttk.Label(config_frame, text="Delay (sec):").grid(row=4, column=0, sticky=tk.W, pady=5)
    delay_entry = ttk.Entry(config_frame, width=50, textvariable=delay_var)
    delay_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)

    # STATA Checkbox (Новый элемент)
    stata_check = ttk.Checkbutton(config_frame, text="Включить 'стата дня' (каждые 10s)", variable=stata_var)
    stata_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

    config_frame.columnconfigure(1, weight=1)

    # Commands section
    commands_frame = ttk.LabelFrame(main_frame, text="Available Commands", padding="10")
    commands_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

    # Обновленное описание команд
    commands_text = """• норма 0 - запустить набор нормы (писать в группу) (0/1 + опционально 'стата дня')
• норма стоп - Остановить"""

    ttk.Label(commands_frame, text=commands_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)

    # Control buttons
    button_frame = ttk.Frame(main_frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))

    start_btn = ttk.Button(button_frame, text="Start Bot", command=start_button_click, width=15)
    start_btn.grid(row=0, column=0, padx=5)

    stop_btn = ttk.Button(button_frame, text="Stop Bot", command=stop_button_click, width=15, state='disabled')
    stop_btn.grid(row=0, column=1, padx=5)

    # Log section
    log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
    log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

    log_text = scrolledtext.ScrolledText(log_frame, width=80, height=20, wrap=tk.WORD)
    log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # Store text widget for logging
    log_message.text_widget = log_text

    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(3, weight=1)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)

    # Footer
    footer_frame = ttk.Frame(main_frame)
    footer_frame.grid(row=4, column=0, columnspan=2, pady=(10, 0))

    footer_label = ttk.Label(footer_frame, text="Создал @kaktusi_top(PXL)",
                             font=('Arial', 9, 'italic'), foreground='gray')
    footer_label.grid(row=0, column=0)

    log_message("Bot ready. Enter your credentials and click 'Start Bot'.")
    log_message("Get API credentials from: https://my.telegram.org")

    root.mainloop()


if __name__ == '__main__':
    create_gui()
