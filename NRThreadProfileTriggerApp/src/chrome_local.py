from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome

class LocalChrome(Chrome):
    def __init__(self):
        __options = Options()
        __options.add_argument(f'--window-size={1280}x{1024}')
        __options.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        super().__init__(options=__options)

