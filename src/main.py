import tkinter as tk
from tkinter import ttk
import threading
import queue
from pydantic import BaseModel, Field, ValidationError
from pydantic.dataclasses import dataclass
from typing import Callable
from rich import print
from pynput import keyboard

from iris_cli import (
    iris_cli,
    DEFAULT_BRIGHT,
    DEFAULT_TEMP,
    reset_cli,
    BRIGHT_RANGE,
    TEMP_RANGE,
)


def get_type(value):
    return str(type(value))[8:-2]


class AppStateInfo(BaseModel):
    """State info"""

    temperature: int = Field(ge=TEMP_RANGE[0], le=TEMP_RANGE[1])
    brightness: int = Field(ge=BRIGHT_RANGE[0], le=BRIGHT_RANGE[1])


APP_STALE_UPDATE_INTERVAL = 50  # ms


class SliderApp:
    """Class to create a temperature and brightness slider app"""

    def __init__(
        self, root: tk.Tk, gui_q: queue.Queue, key_q: queue.Queue, state: AppStateInfo
    ) -> None:
        self.gui_queue: queue.Queue = gui_q
        self.key_queue: queue.Queue = key_q

        self.root = root
        self.root.title("Temperature and Brightness Control")

        # Initialize StringVars for labels
        self.temperature_label_var = tk.StringVar(
            value=f"Temperature: {state.temperature} K"
        )
        self.brightness_label_var = tk.StringVar(
            value=f"Brightness: {state.brightness} %"
        )

        # Initialize IntVars for sliders
        self.temperature_value = tk.IntVar(value=state.temperature)
        self.brightness_value = tk.IntVar(value=state.brightness)
        self.__make_sliders()
        self.__process_gui_queue()

    def __process_gui_queue(self):
        """recieving messages from the gui queue made by keyboard"""

        data: AppStateInfo = None
        try:
            while True:
                # data that is passed to gui key
                data = self.gui_queue.get_nowait()
                self.state = data
                # if data is fetched it should applied first and then proceed
                self.on_brightness_change(val=data.brightness, update=False)
                self.on_temperature_change(val=data.temperature, update=False)
                self.update_iris()
        except queue.Empty:
            pass
        except ValidationError:
            pass

        self.root.after(APP_STALE_UPDATE_INTERVAL, self.__process_gui_queue)

    def __make_sliders(self):
        """Temperature and brightness sliders"""
        root = self.root

        # Reset Button
        reset_button = ttk.Button(root, text="Reset", command=self.reset)
        reset_button.pack(pady=10)

        # Create and place the temperature label
        temperature_label = ttk.Label(root, textvariable=self.temperature_label_var)
        temperature_label.pack(pady=10)

        # Create and place the temperature slider
        temperature_slider = ttk.Scale(
            root,
            from_=TEMP_RANGE[0],
            to=TEMP_RANGE[1],
            orient="horizontal",
            variable=self.temperature_value,
            command=self.on_temperature_change,
            length=500,
        )
        temperature_slider.pack(pady=10, padx=10)

        # Create and place the brightness label
        brightness_label = ttk.Label(root, textvariable=self.brightness_label_var)
        brightness_label.pack(pady=10)

        # Create and place the brightness slider
        brightness_slider = ttk.Scale(
            root,
            from_=10,
            to=100,
            orient="horizontal",
            variable=self.brightness_value,
            command=self.on_brightness_change,
            length=350,
        )
        brightness_slider.pack(pady=10, padx=10)

    def on_temperature_change(self, _=None, val: int | None = None, update=True):
        """Function to update the temperature label when the slider value changes"""
        if val:
            self.temperature_value.set(val)
        temperature_value = self.temperature_value.get()
        self.temperature_label_var.set(f"Temperature: {temperature_value} K")
        if update:
            self.update_iris()

    def on_brightness_change(self, _=None, val: int | None = None, update=True):
        """Function to update the brightness label when the slider value changes"""
        if val:
            self.brightness_value.set(val)
        brightness_value = self.brightness_value.get()
        self.brightness_label_var.set(f"Brightness: {brightness_value} %")
        if update:
            self.update_iris()

    def update_iris(self):
        temp = self.temperature_value.get()
        bright = self.brightness_value.get()
        iris_cli(temp, bright)
        try:
            self.key_queue.put(AppStateInfo(brightness=bright, temperature=temp))
        except ValidationError:
            pass

    def reset(self):
        """Reset with default temperature and brightness"""
        self.temperature_value.set(DEFAULT_TEMP)
        self.brightness_value.set(DEFAULT_BRIGHT)
        self.on_temperature_change()
        self.on_brightness_change()
        reset_cli()


class KeboardShortcut:
    """Handling Keyboard Shortcuts and synchronizing with gui"""

    def __init__(self, key_q, gui_q, state: AppStateInfo) -> None:
        self.key_queue: queue.Queue = key_q
        self.gui_queue: queue.Queue = gui_q
        self.state = state

        self.brigh_step = 5
        self.temp_step = 100

        self.hotkeys: list[tuple[tuple[str], Callable] | None] = []
        self.pressed_keys = []  # stack
        self.__register_control_hotkeys()

        self.MODIFIER_KEYS = ["ctrl", "alt", "shift"]
        self.__process_key_queue()

    def start_listener(self):

        with keyboard.Listener(
            on_press=self.__on_press, on_release=self.__on_release
        ) as listener:
            listener.join()

    def __on_press(self, key: keyboard.KeyCode | keyboard.Key):
        """on press"""

        """
        To keep the logic of our app simple(fow now) we will have some restrictions
        - Only support hotkeys of max length 3
        - No consecutive multiple key press allowed
        - We will only take ctrl, alt, shift as modifier keys, so that the keys after them can
          pe parsed without order. Example: "ctrl+alt+9" and "alt+ctrl+9" will be same
        - add a unsubscribe method to remove the listener
        - the left and right variants of the modifier keys will be treated as same.
          but if implicitly provided which variant is pressed, then it will be considered
        """
        key_name = ""
        if isinstance(key, keyboard.KeyCode):
            key_name = key.char
            # if len(self.pressed_keys) != 0 and self.pressed_keys[-1] != key_name:
            # self.pressed_keys.append(key_name)
        elif isinstance(key, keyboard.Key):
            key_name = key.name
        to_append_key = True
        if len(self.pressed_keys) > 0 and self.pressed_keys[-1] == key_name:
            to_append_key = False
        if to_append_key:
            self.pressed_keys.append(key_name)

        # print(f"[yellow]pressed[/], {key_name}, {self.pressed_keys}")
        for items in self.hotkeys:
            if not items:
                continue
            [hotkey, callback] = items
            if len(hotkey) != len(self.pressed_keys):
                continue
            hotkey_name = "+".join(hotkey)
            for i, h_key in enumerate(hotkey):
                h_key_sep = self.seprate_key_types(h_key)
                p_key_sep = self.seprate_key_types(self.pressed_keys[i])
                if len(h_key_sep.modifiers_keys) != len(p_key_sep.modifiers_keys):
                    break
                elif (
                    h_key_sep.modifiers_keys != p_key_sep.modifiers_keys
                    or h_key_sep.other_keys != p_key_sep.other_keys
                ):
                    break
            else:
                # will run if no break
                callback(hotkey_name)
                pass

    def __on_release(self, key):
        """on release"""

        key_name = ""
        try:
            key_name = key.char
        except AttributeError:
            key_name = key.name
        if len(self.pressed_keys) != 0:
            self.pressed_keys.pop()
        if len(self.pressed_keys) > 3:
            self.pressed_keys.clear()
        # print(f"[red]released[/], {key_name}, {self.pressed_keys}")

    def __process_key_queue(self):
        """recieving messages from the keyboard queue made by the gui"""

        data: AppStateInfo = None
        try:
            while True:
                # here we only nned to keep the state in sync
                data = self.key_queue.get_nowait()
                self.state = data
        except queue.Empty:
            pass
        except ValidationError:
            pass

        # run this function every 100ms
        timer = threading.Timer(
            APP_STALE_UPDATE_INTERVAL / 1000, self.__process_key_queue
        )
        timer.daemon = True
        timer.start()

    def seprate_key_types(self, hotkey_str: str):
        """Parses the key string and classifies them into modifier keys and other keys"""

        @dataclass
        class HotKey_Data:
            modifiers_keys: list[str]
            other_keys: list[str]

        res = HotKey_Data([], [])

        keys = hotkey_str.split("+")
        for key in keys:
            is_modifier = False
            for mod_key in self.MODIFIER_KEYS:
                if key.startswith(mod_key):
                    main_key = key[: len(mod_key)]
                    if len(key) != len(mod_key):
                        other_half = key[len(mod_key) :]
                        if other_half not in ("_r", "_l"):
                            continue
                    res.modifiers_keys.append(main_key)
                    is_modifier = True
            if not is_modifier:
                res.other_keys.append(key)
        return res

    def register_hotkey(self, hotkey_str: str, callback: Callable[[str], None]):
        """Register a hotkey with a callback."""

        @dataclass
        class EventInfo:
            hotkey: str
            event_id: int
            unsubscribe: Callable[[], None]

        keys = hotkey_str.split("+")
        self.hotkeys.append((tuple(keys), callback))

        index = len(self.hotkeys) - 1

        def unsub():
            self.hotkeys[index] = None

        return EventInfo(hotkey_str, index, unsub)

    def __register_control_hotkeys(self):
        def update_state():
            try:
                self.gui_queue.put(AppStateInfo(**self.state.model_dump()))
            except ValidationError as e:
                pass

        def bright_up(hotkey_name):
            # print("bright up")
            self.state.brightness += self.brigh_step
            update_state()

        def bright_down(hotkey_name):
            # print("bright down")
            self.state.brightness -= self.brigh_step
            update_state()

        def temp_up(hotkey_name):
            # print("temp up")
            self.state.temperature += self.temp_step
            update_state()

        def temp_down(hotkey_name):
            # print("temp down")
            self.state.temperature -= self.temp_step
            update_state()

        self.register_hotkey("alt+9", temp_up)
        self.register_hotkey("alt+8", temp_down)
        self.register_hotkey("alt+f9", bright_up)
        self.register_hotkey("alt+f8", bright_down)


if __name__ == "__main__":
    try:
        # reset_cli()  # This might change in future if we want to tsave

        INITIAL_STATE = AppStateInfo(
            temperature=DEFAULT_TEMP, brightness=DEFAULT_BRIGHT
        )
        app_root = tk.Tk()
        gui_queue = queue.Queue()
        key_queue = queue.Queue()

        app = SliderApp(app_root, gui_q=gui_queue, key_q=key_queue, state=INITIAL_STATE)
        key_obj = KeboardShortcut(gui_q=gui_queue, key_q=key_queue, state=INITIAL_STATE)

        th = threading.Thread(target=key_obj.start_listener)
        th.daemon = True
        # daemon threads exit when main thread exits
        th.start()

        app_root.mainloop()
        # pylint: disable=broad-exception-caught
    except Exception as e:
        print(e)
    finally:
        reset_cli()
