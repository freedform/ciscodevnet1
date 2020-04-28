from netmiko import ConnectHandler
from datetime import date
from os import path, makedirs


class CiscoClass:
    def __init__(self, device_info):
        """
        Конструктор класса принмает словарь параметров подключения,
        объявляем все необходимые переменные и иницируем подключение в устройству
        self.report основная переменная в которую пишут свои результаты все методы класса,
        которые запускаются через метод run_fn
        """

        self.hostname = device_info["hostname"]

        self.backup_dir = r"/path/to/backup/dir"

        conn_info = device_info["conn_info"]

        print(f"Connecting to {self.hostname}")
        try:
            self.ssh_conn = ConnectHandler(**conn_info)
            self.ssh_conn.enable()
        except Exception:
            raise Exception(f"Something wrong with {self.hostname}")

        self.ntp_server = "10.11.12.13"

        self.report = {"hostname": self.hostname}

    def run_fn(self, task_list):
        """
        Запуск всех методов по ключам словаря task_dict если присутствует all в task_list
        то запускаем все возможные методы
        иначе запуск производится только по конкретным что описаны в task_list
        """
        task_dict = {
            "backup": self.__backup_fn,
            "software": self.__software_fn,
            "cdp": self.__cdp_fn,
            "ntp": self.__ntp_fn,

        }
        if "all" in task_list:
            for fn in task_dict.keys():
                task_dict[fn]()
        else:
            for fn in task_list:
                task_dict[fn]()

    def report_fn(self):
        """
        Здесь производится форматирование self.report и его возврат
        """
        result = []
        for val in self.report.values():
            if type(val) is dict:
                result += val.values()
            else:
                result.append(val)

        return "|".join(result)

    def close_con(self):
        """
        Закрываем соединение иницированное в конструкторе
        """
        self.ssh_conn.disconnect()

    def __backup_fn(self):
        """
        Метод сбора конфигурации с устройства
        """
        backup = self.ssh_conn.send_command("show run")
        f_today = date.today().strftime("%d-%m-%Y")
        filename = "_".join([self.hostname, f_today])

        if not path.exists(self.backup_dir):
            makedirs(self.backup_dir)
        file_path = path.join(self.backup_dir, filename)

        with open(file_path, "w") as fl_w:
            fl_w.write(backup)

    def __cdp_fn(self):
        """
        Метод сбора иноформации о cdp
        """
        cdp = self.ssh_conn.send_command("show cdp neighbors detail")
        if "CDP is not enabled" in cdp:
            result = f"CDP is OFF, 0 peers"
        else:
            neighbor_count = 0
            for line in cdp.splitlines():
                if "Device ID:" in line:
                    neighbor_count += 1
            result = f"CDP is ON, {neighbor_count} peers"
        self.report["cdp"] = result

    def __ntp_fn(self):
        """
        Метод сбора иноформации о ntp
        """
        ntp = self.ssh_conn.send_command(f"ping {self.ntp_server}")
        if "!!!!!" in ntp:
            self.ssh_conn.send_config_set(f"ntp server {self.ntp_server}")
        else:
            print(f"NTP server {self.ntp_server} is unreachable from {self.hostname}")
        # self.ssh_conn.send_config_set(f"clock timezone GMT +0")

        ntp_status = self.ssh_conn.send_command("show ntp status")
        if "unsynchronized" in ntp_status:
            clock_status = "NTP not sync"
        elif "Clock is synchronized" in ntp_status:
            clock_status = "Clock in sync"
        else:
            clock_status = "Clock not sync"
        self.report["ntp"] = clock_status

    def __software_fn(self):
        """
        Метод сбора иноформации о прошивке и модели
        """
        version = self.ssh_conn.send_command("show version")
        image = model = None
        for line in version.splitlines():
            if line.startswith("System image file is"):
                image = line.split()[-1].strip('"')
            elif line.startswith("cisco"):
                model = line.split()[1]
            elif line.startswith("Cisco") and "processor" in line:
                model = line.split()[1]
            elif line.startswith("Cisco") and "memory" in line:
                model = line.split()[1]
        if "NPE" in image or "npe" in image:
            image_type = "NPE"
        else:
            image_type = "PE"
        self.report["facts"] = {"image": image, "model": model, "image_type": image_type}



