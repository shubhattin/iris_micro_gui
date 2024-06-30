import tkinter as tk
from tkinter import ttk
import threading

from pynput import keyboard

from iris_cli import iris_cli, DEFAULT_BRIGHT, DEFAULT_TEMP, reset_cli


class SliderApp:
    """Class to create a temperature and brightness slider app"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Temperature and Brightness Control")

        # Initialize StringVars for labels
        self.temperature_label_var = tk.StringVar(
            value=f"Temperature: {DEFAULT_TEMP} K"
        )
        self.brightness_label_var = tk.StringVar(
            value=f"Brightness: {DEFAULT_BRIGHT} %"
        )

        # Initialize IntVars for sliders
        self.temperature_value = tk.IntVar(value=DEFAULT_TEMP)
        self.brightness_value = tk.IntVar(value=DEFAULT_BRIGHT)
        self.make_sliders()

    def make_sliders(self):
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
            from_=1000,
            to=10000,
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

    def on_temperature_change(self, _=None):
        """Function to update the temperature label when the slider value changes"""
        temperature_value = self.temperature_value.get()
        self.temperature_label_var.set(f"Temperature: {temperature_value} K")
        iris_cli(self.temperature_value.get(), self.brightness_value.get())

    def on_brightness_change(self, _=None):
        """Function to update the brightness label when the slider value changes"""
        brightness_value = self.brightness_value.get()
        self.brightness_label_var.set(f"Brightness: {brightness_value} %")
        iris_cli(self.temperature_value.get(), self.brightness_value.get())

    def reset(self):
        """Reset with default temperature and brightness"""
        self.temperature_value.set(DEFAULT_TEMP)
        self.brightness_value.set(DEFAULT_BRIGHT)
        self.on_temperature_change()
        self.on_brightness_change()
        reset_cli()


class KeboardShortcut:
    """Handling Keyboard Shortcuts and synchronizing with gui"""

    def __init__(self) -> None:
        self.ctrl_pressed = False

        self.brigh_step = 5
        self.temp_step = 100

    def on_press(self, key):
        """on press"""

        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True

            if self.ctrl_pressed:
                if key == keyboard.Key.f8:
                    print("Decrease")
                elif key == keyboard.Key.f9:
                    print("Increase")
        except AttributeError:
            pass

    def on_release(self, key):
        """on release"""
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = False
        except AttributeError:
            pass

    def start_listener(self):
        """start"""
        with keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        ) as listener:
            listener.join()


if __name__ == "__main__":
    try:
        reset_cli()  # This might change in future if we want to tsave
        app_root = tk.Tk()
        app = SliderApp(app_root)

        key_obj = KeboardShortcut()
        th = threading.Thread(target=key_obj.start_listener)

        th.daemon = True
        th.start()
        app_root.mainloop()
        # pylint: disable=broad-exception-caught
    except Exception as e:
        pass
    finally:
        reset_cli()
