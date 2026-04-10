import json
import os

CONFIG_FILE = "config.json"

class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {
            "owon_port": "",
            "korad_port": "",
            "bg_color": "#0f0f0f",
            "font_color": "#00ff41", # Matrix green
            "accent_color": "#2196f3"
        }

    @staticmethod
    def save(config):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f)
