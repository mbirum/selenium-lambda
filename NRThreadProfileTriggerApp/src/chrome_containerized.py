from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Chrome

class ContainerizedChrome(Chrome):
    def __init__(self):
        __options = Options()
        __options.add_argument('--headless')
        __options.add_argument('--no-sandbox')
        __options.add_argument('--start-maximized')
        __options.add_argument('--start-fullscreen')
        __options.add_argument('--single-process')
        __options.add_argument('--disable-dev-shm-usage')
        __options.binary_location = "/usr/local/bin/headless-chromium"
        service_log_path = "/usr/src/app/clogs/chromedriver.log"
        service_args = ['--verbose']
        super().__init__('/usr/local/bin/chromedriver', options=__options, service_args=service_args, service_log_path=service_log_path)