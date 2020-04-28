import argparse
import yaml
from multiprocessing import Process
from cisco_class import CiscoClass
from os import path


def arg_parser():
    """ Функция обработки аргументов командной стороки, принимает пока
    -i путь к инвентарному файлу
    -с имена таксов, количество и названия строго фиксировано и определено в choices
    работает только связка -i <filename> -c task name
    :return:
    """
    input_parser = argparse.ArgumentParser()
    input_parser.add_argument('-i', '--inventory',
                              action='store',
                              nargs=1
                              )
    input_parser.add_argument('-c', '--collect',
                              action='store',
                              nargs="+",
                              choices=["backup", "cdp", "ntp", "software", "all"]
                              )

    output_parser = input_parser.parse_args()
    out = vars(output_parser)

    if out["inventory"] and out["collect"]:
        inv = out["inventory"][0]
        collect = out["collect"]
        run_task(inv, collect)
    else:
        print("Noting to do")


def cisco_connect(device, task):
    """
    Функция подключения к устройствам, определяет класс CiscoClass, далее вызывается метод run_fn, который получает
    список тасков
    после выполнения соединения закрываются через метод close_con
    ну и вывод на экран того что удалось собрать
    """
    cisco = CiscoClass(device)
    cisco.run_fn(task)
    cisco.close_con()
    print(cisco.report_fn())


def run_task(yaml_inventory, task):
    """
    Проверка существования инвентарного файла, а также проверка наличия ключа devices.
    Далее форки процессов для каждого уствройства в каждом процесс вызов функции cisco_connect
    """
    if not path.exists(yaml_inventory):
        raise Exception(f"INVENTORY FILE <{yaml_inventory}> does not exist")
    inventory = yaml.safe_load(open(yaml_inventory))
    devices = inventory.get("devices")
    if devices:
        procs = []
        for device in devices:
            proc_instance = Process(target=cisco_connect, args=(device, task))
            procs.append(proc_instance)
        for proc in procs:
            proc.start()
        for proc in procs:
            proc.join()

    else:
        print(f"No devices in {yaml_inventory}")


if __name__ == "__main__":
    arg_parser()
