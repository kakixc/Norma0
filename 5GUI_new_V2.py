import asyncio
import tkinter as tk
from tkinter import scrolledtext, messagebox
from telethon import TelegramClient, events
import threading
import json
import os
from tkinter import PhotoImage

CONFIG_FILE = 'bot_config.json'

# Global variables
is_running = {}
is_stata_running = {}
custom_commands = {}
client = None
loop = None
DELAY = 0.15
current_theme = 'dark'

# Themes
THEMES = {
    'dark': {
        'bg': '#1c1c1e',
        'card': '#2c2c2e',
        'input': '#3a3a3c',
        'text': '#ffffff',
        'secondary': '#98989d',
        'accent': '#0a84ff',
        'red': '#ff453a',
        'gray': '#48484a',
        'green': '#32d74b'
    },
    'light': {
        'bg': '#f5f5f7',
        'card': '#ffffff',
        'input': '#e5e5ea',
        'text': '#1d1d1f',
        'secondary': '#6e6e73',
        'accent': '#007aff',
        'red': '#ff3b30',
        'gray': '#d1d1d6',
        'green': '#34c759'
    }
}


def get_theme():
    return THEMES[current_theme]


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            global current_theme
            current_theme = config.get('theme', 'dark')
            return config
    return {
        'api_id': '',
        'api_hash': '',
        'phone': '',
        'password': '',
        'delay': 0.15,
        'theme': 'dark',
        'show_progress': True,
        'custom_commands': []
    }


def save_config(config):
    config['theme'] = current_theme
    config['custom_commands'] = [cmd for cmd in custom_commands.values()]
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def log_message(msg):
    if hasattr(log_message, 'widget'):
        log_message.widget.config(state='normal')
        log_message.widget.insert(tk.END, msg + '\n')
        log_message.widget.see(tk.END)
        log_message.widget.config(state='disabled')


async def toggle_loop(chat_id, count=None):
    current_value = 0
    sent_count = 0
    show_progress = show_progress_var.get()
    progress_msg = None

    try:
        while is_running.get(chat_id, False):
            # Show progress message
            if show_progress and count and sent_count == 0:
                progress_msg = await client.send_message(chat_id, f"Выполняется... (0/{count})")

            message = await client.send_message(chat_id, str(current_value))
            sent_count += 1

            # Update progress
            if show_progress and count and progress_msg:
                try:
                    await client.edit_message(chat_id, progress_msg, f"Выполняется... ({sent_count}/{count})")
                except:
                    pass

            await asyncio.sleep(DELAY)
            await client.delete_messages(chat_id, message.id)

            current_value = 1 - current_value
            await asyncio.sleep(DELAY)

            # Check if reached count
            if count and sent_count >= count:
                break

            # Check if stopped
            if not is_running.get(chat_id, False):
                break

    except Exception as e:
        log_message(f"Error in toggle_loop: {e}")
    finally:
        # Cleanup progress message
        if progress_msg and show_progress:
            try:
                await client.delete_messages(chat_id, progress_msg.id)
            except:
                pass

        is_running[chat_id] = False
        log_message(f"✓ Completed {sent_count} messages in chat {chat_id}")


async def stata_loop(chat_id):
    while is_stata_running.get(chat_id, False):
        try:
            message = await client.send_message(chat_id, "стата дня")
            await asyncio.sleep(0.1)
            await client.delete_messages(chat_id, message.id)
            await asyncio.sleep(10)
        except Exception as e:
            log_message(f"Error in stata_loop: {e}")
            is_stata_running[chat_id] = False
            break


async def send_custom_command(chat_id, text, delete_after):
    try:
        message = await client.send_message(chat_id, text)
        if delete_after > 0:
            await asyncio.sleep(delete_after)
            await client.delete_messages(chat_id, message.id)
    except Exception as e:
        log_message(f"Error in send_custom_command: {e}")


async def send_custom_loop(chat_id, text, delete_after, count):
    """Send `text` count times with DELAY; delete each message if delete_after > 0."""
    sent = 0
    try:
        while sent < count and is_running.get(chat_id, False):
            msg = await client.send_message(chat_id, text)
            sent += 1

            if delete_after > 0:
                # Schedule deletion after delete_after seconds
                await asyncio.sleep(delete_after)
                try:
                    await client.delete_messages(chat_id, msg.id)
                except:
                    pass
            else:
                await asyncio.sleep(DELAY)

            # Small pause between sends
            await asyncio.sleep(DELAY)

            # Check if stopped
            if not is_running.get(chat_id, False):
                break

    except Exception as e:
        log_message(f"Error in send_custom_loop: {e}")

    log_message(f"✓ Sent custom command {sent} times in chat {chat_id}")
    is_running[chat_id] = False


async def handle_outgoing_message(event):
    """Handle messages sent by the user"""
    message_text = event.message.text.strip()
    chat_id = event.chat_id

    # Convert to lowercase for command matching
    message_lower = message_text.lower()

    # Handle stop commands first
    if message_lower == 'норма стоп':
        await event.delete()
        if is_running.get(chat_id, False):
            is_running[chat_id] = False
            log_message(f"✓ Stopped toggle in chat {chat_id}")
        return

    elif message_lower == 'кастом стоп':
        await event.delete()
        if is_running.get(chat_id, False):
            is_running[chat_id] = False
            log_message(f"✓ Stopped custom commands in chat {chat_id}")
        return

    # Handle normal commands
    if message_lower.startswith('норма '):
        await event.delete()
        parts = message_text.split()
        if len(parts) >= 2:
            try:
                count = int(parts[1])
                if count > 0:
                    if not is_running.get(chat_id, False):
                        is_running[chat_id] = True
                        asyncio.create_task(toggle_loop(chat_id, count))
                        log_message(f"✓ Started toggle with {count} messages in chat {chat_id}")
                    return
            except:
                pass

    elif message_lower == 'норма':
        await event.delete()
        # Default to 1 message if no count specified
        if not is_running.get(chat_id, False):
            is_running[chat_id] = True
            asyncio.create_task(toggle_loop(chat_id, 1))
            log_message(f"✓ Started toggle with 1 message in chat {chat_id}")

    elif message_lower == 'стата старт':
        await event.delete()
        if not is_stata_running.get(chat_id, False):
            is_stata_running[chat_id] = True
            asyncio.create_task(stata_loop(chat_id))
            log_message(f"✓ Started stata in chat {chat_id}")

    elif message_lower == 'стата стоп':
        await event.delete()
        if is_stata_running.get(chat_id, False):
            is_stata_running[chat_id] = False
            log_message(f"✓ Stopped stata in chat {chat_id}")

    # Custom commands
    for cmd_id, cmd in custom_commands.items():
        trigger = cmd['trigger'].lower().strip()
        if message_lower == trigger or message_lower.startswith(trigger + ' '):
            await event.delete()

            # Parse count from message if provided
            parts = message_text.split()
            parsed_count = 0
            if len(parts) >= 2 and parts[0].lower() == trigger and parts[1].isdigit():
                parsed_count = int(parts[1])

            # Decide final count
            repeats = int(cmd.get('repeats', 0))
            if parsed_count > 0:
                count_to_send = parsed_count
            elif repeats > 0:
                count_to_send = repeats
            else:
                count_to_send = 1

            # Send command
            if count_to_send == 1:
                await send_custom_command(chat_id, cmd['text'], cmd.get('delete_after', 0))
                log_message(f"✓ Sent custom '{trigger}' once in chat {chat_id}")
            else:
                if not is_running.get(chat_id, False):
                    is_running[chat_id] = True
                    asyncio.create_task(
                        send_custom_loop(chat_id, cmd['text'], cmd.get('delete_after', 0), count_to_send))
                    log_message(f"✓ Started custom '{trigger}' x{count_to_send} in chat {chat_id}")
            break


async def start_bot(api_id, api_hash, phone, password):
    global client, DELAY

    try:
        client = TelegramClient('session_name', api_id, api_hash)

        # Handle outgoing messages (commands sent by user)
        @client.on(events.NewMessage(outgoing=True))
        async def outgoing_handler(event):
            await handle_outgoing_message(event)

        if password:
            await client.start(phone=phone, password=password)
        else:
            await client.start(
                phone=phone,
                code_callback=lambda: show_input_dialog("Verification", "Enter code from Telegram"),
                password_callback=lambda: show_input_dialog("2FA Password", "Enter your 2FA password")
            )

        log_message("=" * 40)
        log_message("✓ Bot started successfully!")
        log_message("=" * 40)

        await client.run_until_disconnected()

    except Exception as error:
        log_message(f"✗ Error: {str(error)}")


def run_bot_thread(api_id, api_hash, phone, password, delay):
    global loop, DELAY
    DELAY = delay
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot(api_id, api_hash, phone, password))


def start_button_click():
    api_id = api_id_entry.get().strip()
    api_hash = api_hash_entry.get().strip()
    phone = phone_entry.get().strip()
    password = password_entry.get().strip()
    delay = delay_entry.get().strip()

    if not api_id or not api_hash or not phone:
        messagebox.showerror("Error", "Fill in API ID, API Hash, and Phone!")
        return

    try:
        api_id_int = int(api_id)
        delay_float = float(delay)
    except ValueError:
        messagebox.showerror("Error", "Invalid API ID or Delay!")
        return

    theme = get_theme()

    config = {
        'api_id': api_id,
        'api_hash': api_hash,
        'phone': phone,
        'password': password,
        'delay': delay_float,
        'show_progress': show_progress_var.get(),
        'custom_commands': [cmd for cmd in custom_commands.values()]
    }
    save_config(config)

    start_btn.config(state='disabled', bg=theme['gray'])
    stop_btn.config(state='normal', bg=theme['red'])

    for entry in [api_id_entry, api_hash_entry, phone_entry, password_entry, delay_entry]:
        entry.config(state='disabled')

    threading.Thread(target=run_bot_thread, args=(api_id_int, api_hash, phone, password, delay_float),
                     daemon=True).start()
    log_message("▶ Starting bot...")


def stop_button_click():
    global client, loop

    # Stop all running loops
    for chat_id in list(is_running.keys()):
        is_running[chat_id] = False
    for chat_id in list(is_stata_running.keys()):
        is_stata_running[chat_id] = False

    # Disconnect client
    if client:
        try:
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(client.disconnect(), loop)
        except:
            pass

    theme = get_theme()
    start_btn.config(state='normal', bg=theme['accent'])
    stop_btn.config(state='disabled', bg=theme['gray'])

    for entry in [api_id_entry, api_hash_entry, phone_entry, password_entry, delay_entry]:
        entry.config(state='normal')

    log_message("⬛ Bot stopped")


def show_input_dialog(title, prompt):
    """Show input dialog"""
    theme = get_theme()
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("400x180")
    dialog.configure(bg=theme['card'])
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    x = (dialog.winfo_screenwidth() // 2) - 200
    y = (dialog.winfo_screenheight() // 2) - 90
    dialog.geometry(f'400x180+{x}+{y}')

    tk.Label(dialog, text=prompt, bg=theme['card'], fg=theme['text'],
             font=('Segoe UI', 13, 'bold')).pack(pady=(25, 20))

    var = tk.StringVar()
    entry = tk.Entry(dialog, bg=theme['input'], fg=theme['text'], insertbackground=theme['accent'],
                     relief='flat', font=('Segoe UI', 12), bd=0, textvariable=var,
                     justify='center')
    entry.pack(padx=40, fill='x', ipady=10)
    entry.focus()

    if 'password' in title.lower():
        entry.config(show='●')

    result = {'value': None}

    def submit():
        result['value'] = var.get().strip()
        dialog.destroy()

    entry.bind('<Return>', lambda e: submit())

    tk.Button(dialog, text="Submit", command=submit, bg=theme['accent'], fg='#ffffff',
              relief='flat', font=('Segoe UI', 11, 'bold'), padx=30, pady=8,
              cursor='hand2', borderwidth=0).pack(pady=20)

    dialog.wait_window()
    return result['value']


def toggle_theme():
    global current_theme
    current_theme = 'light' if current_theme == 'dark' else 'dark'
    apply_theme()
    config = load_config()
    save_config(config)


def apply_theme():
    theme = get_theme()
    root.configure(bg=theme['bg'])

    # Update all widgets
    for widget_type, widgets in all_widgets.items():
        if widget_type == 'header':
            widgets.configure(bg=theme['bg'])
        elif widget_type == 'main':
            widgets.configure(bg=theme['bg'])
        elif widget_type == 'left':
            widgets.configure(bg=theme['bg'])
        elif widget_type == 'right':
            widgets.configure(bg=theme['bg'])
        elif 'card' in widget_type:
            widgets.configure(bg=theme['card'])

    # Update labels
    for label in all_widgets.get('labels', []):
        parent_bg = theme['card'] if str(label.master) in str(all_widgets.get('config_card', '')) else theme['bg']
        label.configure(bg=parent_bg, fg=theme['text'])

    # Update entries
    for entry in [api_id_entry, api_hash_entry, phone_entry, password_entry, delay_entry]:
        entry.configure(bg=theme['input'], fg=theme['text'], insertbackground=theme['accent'])

    # Update listbox and log
    commands_listbox.configure(bg=theme['input'], fg=theme['text'], selectbackground=theme['accent'])
    log_message.widget.configure(bg=theme['input'], fg=theme['text'])

    # Update buttons
    if start_btn['state'] == 'disabled':
        start_btn.configure(bg=theme['gray'])
    else:
        start_btn.configure(bg=theme['accent'])

    if stop_btn['state'] == 'disabled':
        stop_btn.configure(bg=theme['gray'])
    else:
        stop_btn.configure(bg=theme['red'])


    # Update custom command buttons
    for btn in all_widgets.get('custom_buttons', []):
        btn_text = btn.cget('text')
        if btn_text == "Add":
            btn.configure(bg=theme['accent'])
        elif btn_text == "Delete":
            btn.configure(bg=theme['red'])


def add_custom_command():


    theme = get_theme()
    dialog = tk.Toplevel(root)
    dialog.title("Add Command")
    dialog.geometry("450x600")
    dialog.configure(bg=theme['card'])
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    # Центрирование диалогового окна
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
    y = (dialog.winfo_screenheight() // 2) - (400 // 2)
    dialog.geometry(f"450x600+{x}+{y}")



    tk.Label(dialog, text="Add Custom Command", bg=theme['card'], fg=theme['text'],
             font=('Segoe UI', 17, 'bold')).pack(pady=(30, 25))

    def create_field(label_text, default=''):
        frame = tk.Frame(dialog, bg=theme['card'])
        frame.pack(fill='x', padx=35, pady=8)

        tk.Label(frame, text=label_text, bg=theme['card'], fg=theme['secondary'],
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 5))

        entry = tk.Entry(frame, bg=theme['input'], fg=theme['text'],
                         insertbackground=theme['accent'],
                         relief='flat', font=('Segoe UI', 11), bd=0)
        entry.pack(fill='x', ipady=10)
        if default:
            entry.insert(0, default)
        return entry

    trigger_entry = create_field("Trigger")
    text_entry = create_field("Text to send")
    delete_entry = create_field("Delete after (seconds, 0 = don't)", "0")
    repeats_entry = create_field("Repeats (0 = single send)", "0")

    def save():
        trigger = trigger_entry.get().strip()
        text = text_entry.get().strip()

        if not trigger or not text:
            messagebox.showerror("Error", "Fill in all fields!")
            return

        try:
            delete_after = float(delete_entry.get().strip())
            repeats = int(repeats_entry.get().strip())
            if repeats < 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Invalid delete time or repeats!")
            return

        cmd_id = max(custom_commands.keys()) + 1 if custom_commands else 0
        custom_commands[cmd_id] = {
            'trigger': trigger,
            'text': text,
            'delete_after': delete_after,
            'repeats': repeats
        }
        update_commands_list()

        # Save config with updated commands
        config = load_config()
        save_config(config)

        dialog.destroy()
        log_message(f"✓ Added: {trigger} → {text} (repeats: {repeats}, delete: {delete_after}s)")

    btn_frame = tk.Frame(dialog, bg=theme['card'])
    btn_frame.pack(pady=20)

    tk.Button(btn_frame, text="Cancel", command=dialog.destroy, bg=theme['gray'],
              fg='#ffffff', relief='flat', font=('Segoe UI', 11), padx=25, pady=8,
              cursor='hand2', borderwidth=0).pack(side='left', padx=5)

    tk.Button(btn_frame, text="Add", command=save, bg=theme['accent'], fg='#ffffff',
              relief='flat', font=('Segoe UI', 11, 'bold'), padx=25, pady=8,
              cursor='hand2', borderwidth=0).pack(side='left', padx=5)


def delete_custom_command():
    sel = commands_listbox.curselection()
    if not sel:
        messagebox.showwarning("Warning", "Select a command!")
        return

    idx = sel[0]
    cmd_id = list(custom_commands.keys())[idx]
    cmd = custom_commands[cmd_id]

    if messagebox.askyesno("Confirm", f"Delete '{cmd['trigger']}'?"):
        del custom_commands[cmd_id]
        update_commands_list()

        # Save config with updated commands
        config = load_config()
        save_config(config)

        log_message(f"✗ Deleted: {cmd['trigger']}")


def update_commands_list():
    commands_listbox.delete(0, tk.END)
    for cmd in custom_commands.values():
        info = []
        if cmd.get('repeats', 0) > 0:
            info.append(f"x{cmd['repeats']}")
        if cmd.get('delete_after', 0) > 0:
            info.append(f"del:{cmd['delete_after']}s")
        info_str = " (" + ", ".join(info) + ")" if info else ""
        commands_listbox.insert(tk.END, f"{cmd['trigger']} → {cmd['text']}{info_str}")


def create_gui():
    global api_id_entry, api_hash_entry, phone_entry, password_entry, delay_entry
    global start_btn, stop_btn, theme_btn, commands_listbox, root
    global all_widgets, show_progress_var


    root = tk.Tk()
    root.title("Norma0_V2_control")
    root.geometry("1000x900")
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (1000 // 2)
    y = (root.winfo_screenheight() // 2) - (900 // 2)
    root.geometry(f"1000x900+{x}+{y}")
    try:
        # Замените "logo.png" на путь к вашему файлу
        logo_image = PhotoImage(file="icon.png")
        root.iconphoto(False, logo_image)
    except Exception as e:
        print(f"Не удалось загрузить логотип: {e}")
    theme = get_theme()
    root.configure(bg=theme['bg'])
    root.resizable(False, False)

    config = load_config()
    show_progress_var = tk.BooleanVar(value=config.get('show_progress', True))

    all_widgets = {
        'labels': [],
        'custom_buttons': []
    }

    for i, cmd in enumerate(config.get('custom_commands', [])):
        custom_commands[i] = cmd

    # Header







    header = tk.Frame(root, bg=theme['bg'])
    header.pack(fill='x', pady=(20, 15), padx=25)
    all_widgets['header'] = header

    title_label = tk.Label(header, text="Norma0_V2_control", bg=theme['bg'], fg=theme['text'],
                           font=('Segoe UI', 26, 'bold'))
    title_label.pack(side='left')
    all_widgets['labels'].append(title_label)

    def open_instructions():
        import webbrowser
        webbrowser.open("https://github.com/kakixc/Norma0/blob/main/README.md")

    instructions_btn = tk.Button(header, text="📖 Instructions",
                                 command=open_instructions, bg=theme['bg'], fg=theme['accent'],
                                 relief='flat', font=('Segoe UI', 11), padx=15, pady=5,
                                 cursor='hand2', borderwidth=0)
    instructions_btn.pack(side='right', padx=(0, 10))


    # Main
    main = tk.Frame(root, bg=theme['bg'])
    main.pack(fill='both', expand=True, padx=25)
    all_widgets['main'] = main

    # Left
    left = tk.Frame(main, bg=theme['bg'])
    left.pack(side='left', fill='both', expand=True, padx=(0, 12))
    all_widgets['left'] = left

    # Config
    config_card = tk.Frame(left, bg=theme['card'])
    config_card.pack(fill='x', pady=(0, 12))
    all_widgets['config_card'] = config_card

    config_label = tk.Label(config_card, text="Configuration", bg=theme['card'], fg=theme['text'],
                            font=('Segoe UI', 15, 'bold'))
    config_label.pack(anchor='w', padx=18, pady=(15, 10))
    all_widgets['labels'].append(config_label)

    def create_input(label):
        f = tk.Frame(config_card, bg=theme['card'])
        f.pack(fill='x', padx=18, pady=4)

        label_widget = tk.Label(f, text=label, bg=theme['card'], fg=theme['secondary'],
                                font=('Segoe UI', 9))
        label_widget.pack(anchor='w', pady=(0, 3))
        all_widgets['labels'].append(label_widget)

        e = tk.Entry(f, bg=theme['input'], fg=theme['text'],
                     insertbackground=theme['accent'],
                     relief='flat', font=('Segoe UI', 10), bd=0)
        e.pack(fill='x', ipady=8)
        return e

    api_id_entry = create_input("API ID")
    api_id_entry.insert(0, config.get('api_id', ''))

    api_hash_entry = create_input("API Hash")
    api_hash_entry.insert(0, config.get('api_hash', ''))

    phone_entry = create_input("Phone")
    phone_entry.insert(0, config.get('phone', ''))

    password_entry = create_input("Password (2FA - optional)")
    password_entry.insert(0, config.get('password', ''))
    password_entry.config(show='●')

    delay_entry = create_input("Delay (seconds)")
    delay_entry.insert(0, str(config.get('delay', 0.15)))

    # Show progress checkbox
    check_frame = tk.Frame(config_card, bg=theme['card'])
    check_frame.pack(fill='x', padx=18, pady=8)

    progress_check = tk.Checkbutton(check_frame, text='Показывать "Выполняется..." в чате',
                                    variable=show_progress_var, bg=theme['card'], fg=theme['text'],
                                    selectcolor=theme['input'], activebackground=theme['card'],
                                    font=('Segoe UI', 9))
    progress_check.pack(anchor='w')
    all_widgets['labels'].append(progress_check)

    tk.Frame(config_card, bg=theme['card'], height=8).pack()

    # Buttons
    btns = tk.Frame(left, bg=theme['bg'])
    btns.pack(pady=12)

    start_btn = tk.Button(btns, text="Start", command=start_button_click,
                          bg=theme['accent'], fg='#ffffff', relief='flat',
                          font=('Segoe UI', 12, 'bold'), padx=32, pady=9,
                          cursor='hand2', borderwidth=0)
    start_btn.pack(side='left', padx=4)

    stop_btn = tk.Button(btns, text="Stop", command=stop_button_click,
                         bg=theme['gray'], fg='#ffffff', relief='flat',
                         font=('Segoe UI', 12, 'bold'), padx=32, pady=9,
                         cursor='hand2', state='disabled', borderwidth=0)
    stop_btn.pack(side='left', padx=4)

    # Built-in
    builtin = tk.Frame(left, bg=theme['card'])
    builtin.pack(fill='x')
    all_widgets['builtin'] = builtin

    builtin_label = tk.Label(builtin, text="Built-in Commands", bg=theme['card'], fg=theme['text'],
                             font=('Segoe UI', 13, 'bold'))
    builtin_label.pack(anchor='w', padx=18, pady=(12, 8))
    all_widgets['labels'].append(builtin_label)

    cmds = """норма [число] - набрать норму. число количество сообщений
норма - отправить 1 сообщение
норма стоп - остановить норму
кастом стоп - остановить кастомные команды
стата старт - запустить стату
стата стоп - остановить стату"""

    cmds_label = tk.Label(builtin, text=cmds, bg=theme['card'], fg=theme['text'],
                          font=('Segoe UI', 9), justify='left')
    cmds_label.pack(anchor='w', padx=18, pady=(0, 12))
    all_widgets['labels'].append(cmds_label)

    # Right
    right = tk.Frame(main, bg=theme['bg'])
    right.pack(side='right', fill='both', expand=True)
    all_widgets['right'] = right

    # Custom
    custom = tk.Frame(right, bg=theme['card'])
    custom.pack(fill='both', expand=True, pady=(0, 12))
    all_widgets['custom'] = custom

    custom_label = tk.Label(custom, text="Custom Commands", bg=theme['card'], fg=theme['text'],
                            font=('Segoe UI', 15, 'bold'))
    custom_label.pack(anchor='w', padx=18, pady=(15, 10))
    all_widgets['labels'].append(custom_label)

    listbox_frame = tk.Frame(custom, bg=theme['input'])
    listbox_frame.pack(fill='both', expand=True, padx=18, pady=(0, 10))

    scrollbar = tk.Scrollbar(listbox_frame)
    scrollbar.pack(side='right', fill='y')

    commands_listbox = tk.Listbox(listbox_frame, bg=theme['input'], fg=theme['text'],
                                  relief='flat', font=('Segoe UI', 9),
                                  yscrollcommand=scrollbar.set,
                                  selectbackground=theme['accent'],
                                  selectforeground='#ffffff',
                                  bd=0, highlightthickness=0)
    commands_listbox.pack(side='left', fill='both', expand=True, padx=10, pady=10)
    scrollbar.config(command=commands_listbox.yview)

    update_commands_list()

    cmd_btns = tk.Frame(custom, bg=theme['card'])
    cmd_btns.pack(pady=(0, 12))

    add_btn = tk.Button(cmd_btns, text="Add", command=add_custom_command,
                        bg=theme['accent'], fg='#ffffff', relief='flat',
                        font=('Segoe UI', 10, 'bold'), padx=20, pady=7,
                        cursor='hand2', borderwidth=0)
    add_btn.pack(side='left', padx=4)
    all_widgets['custom_buttons'].append(add_btn)

    delete_btn = tk.Button(cmd_btns, text="Delete", command=delete_custom_command,
                           bg=theme['red'], fg='#ffffff', relief='flat',
                           font=('Segoe UI', 10, 'bold'), padx=20, pady=7,
                           cursor='hand2', borderwidth=0)
    delete_btn.pack(side='left', padx=4)
    all_widgets['custom_buttons'].append(delete_btn)

    # Log
    log_card = tk.Frame(right, bg=theme['card'])
    log_card.pack(fill='both', expand=True)
    all_widgets['log_card'] = log_card

    log_label = tk.Label(log_card, text="Log", bg=theme['card'], fg=theme['text'],
                         font=('Segoe UI', 13, 'bold'))
    log_label.pack(anchor='w', padx=18, pady=(12, 8))
    all_widgets['labels'].append(log_label)

    log_text = scrolledtext.ScrolledText(log_card, bg=theme['input'], fg=theme['text'],
                                         relief='flat', font=('Consolas', 9), wrap='word',
                                         bd=0, highlightthickness=0, state='disabled')
    log_text.pack(fill='both', expand=True, padx=18, pady=(0, 12))

    log_message.widget = log_text

    # Footer
    footer_label = tk.Label(root, text="Сделал PXL. тг:@kaktusi_top", bg=theme['bg'],
                            fg=theme['secondary'], font=('Segoe UI', 9))
    footer_label.pack(pady=(3, 15))
    all_widgets['labels'].append(footer_label)

    log_message("Ready. Get API: https://my.telegram.org")

    # Footer
    footer_frame = tk.Frame(root, bg=theme['bg'])
    footer_frame.pack(pady=(0, 15))

    # Ссылка на GitHub
    def open_github():
        import webbrowser
        webbrowser.open("https://github.com/kakixc/Norma0")

    github_label = tk.Label(footer_frame, text="GitHub Repository", bg=theme['bg'],
                            fg=theme['accent'], font=('Segoe UI', 9), cursor="hand2")
    github_label.pack(pady=(0, 0))
    github_label.bind("<Button-1>", lambda e: open_github())
    github_label.pack(pady=(0, 0), anchor='n')


    def open_site():
        import webbrowser
        webbrowser.open("https://kakixc.github.io/Norma0/")

    github_label = tk.Label(footer_frame, text="Site", bg=theme['bg'],
                            fg=theme['accent'], font=('Segoe UI', 9), cursor="hand2")
    github_label.pack(pady=(0, 0))
    github_label.bind("<Button-1>", lambda e: open_site())
    github_label.pack(pady=(0, 0), anchor='n')
    root.mainloop()


if __name__ == '__main__':
    create_gui()