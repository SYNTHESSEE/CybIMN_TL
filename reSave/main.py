"""
Кибериммунный подход к разработке. Задача "Светофор"

Вам предлагается доработать упрощённый прототип системы управления светофором с учётом принципов конструктивной безопасности (кибериммунный подход). В данной задаче светофор рассматривается как набор функциональных компонентов, которые взаимодействуют строго через «монитор безопасности» (SecurityMonitor).  
Монитор безопасности выступает «центральным пропускным пунктом»: он принимает все сообщения от компонентов, проверяет их на соответствие заданной политике безопасности и либо передаёт адресату, либо блокирует.
О задаче  
Указанная задача направлена на реализацию базовой компетенции федерального государственного образовательного стандарта высшего образования БК-3 - способность применять языки, методы и инструментальные средства программирования для решения задач профессиональной деятельности.  

Необходимо показать, каким образом можно ограничивать и контролировать взаимодействие различных частей программы (подсистем) с помощью монитора безопасности, а также корректно реализовывать допустимые режимы работы светофора и блокировать потенциально аварийные.
Светофор - это, на первый взгляд, очень простая система, но она оказывает критическое влияние на безопасность дорожного движения.
"""

from dataclasses import dataclass
from queue import Queue, Empty
from threading import Thread
from time import sleep
import json


"""
 Простая реализация выбранной политики архитектуры

В рамках задачи реализуется политика архитектуры, показанная на рис. 1.

Рис. 1. Политика архитектуры (https://raw.githubusercontent.com/cyberimmunity-edu/cyberimmune-systems-example-traffic-light-jupyter-notebook/refs/heads/master/images/tl-archpol-0.02.png)

Рис. 1. Политика архитектуры светофора

1. Есть несколько функциональных компонентов (сущности 1-4) и монитор безопасности, который будет контролировать их взаимодействие, в том числе реализовывать контроль конфигураций светофора (сущность №5 на архитектурной диаграмме)
2. Определены политики безопасности
3. Написан модуль ControlSystem моделирующий запрос на изменение режима для проверки работы всех элементов

- В качестве интерфейса взаимодействия использованы очереди сообщений, у каждой сущности есть своя «персональная» очередь, ассоциированная с ней
- Компоненты 1-4 отправляют сообщения только в очередь monitor сущности SecurityMonitor
- SecurityMonitor проверяет сообщения на соответствие политикам безопасности, в случае положительного решения перенаправляет сообщение в очередь соответствующей сущности

В коде сущности названы следующим образом
1. Связь - CitySystemConnector
2. Система управления светофора - ControlSystem
3. Управление светодиодами - LightsGPIO
4. Система диагностики - SelfDiagnosticsSystem

Логика контроля режимов светофора (компонент №5 на рис. 1) реализована в виде политики безопасности в мониторе безопасности (эту логику нужно будет дополнить в задании 5).  

Рис. 2. Политика архитектуры с именами классов (https://raw.githubusercontent.com/cyberimmunity-edu/cyberimmune-systems-example-traffic-light-jupyter-notebook/refs/heads/master/images/tl-archpol-code.png)

Рис. 2. Политика архитектуры с именами классов
"""

"""
Очередь событий для монитора безопасности: все запросы от сущностей друг к другу должны отправляться только в неё
"""
monitor_events_queue = Queue()

"""
Формат сообщений
"""


@dataclass
class Event:
    source: str       # отправитель
    destination: str  # получатель
    operation: str    # чего хочет (запрашиваемое действие)
    parameters: str   # с какими параметрами


"""
Монитор безопасности
"""

"""
Ниже в методе _check_policies можно увидеть пример политики безопасности:

python
if event.source == "ControlSystem" \
        and event.destination == "LightsGPIO" \
        and event.operation == "set_mode" \
        and self._check_mode(event.operation):
    authorized = True
            

В этом примере проверяется отправитель сообщения, получатель, запрашиваемая операция а также параметры операции. Это максимально строгий вариант, и в зависимости от ситуации количество проверок можно уменьшить.
В мониторе безопасности осуществляется контролируемая блокировка противоречащих полотикам взаимодействий между сущностями.
"""


# формат управляющих команд для монитора
@dataclass
class ControlEvent:
    operation: str


# список разрешенных сочетаний сигналов светофора (эту логику нужно будет изменить в заданиях 2,3)
# любые сочетания, отсутствующие в этом списке, запрещены
traffic_lights_allowed_configurations = [
    {"direction_1": "red", "direction_2": "green"},
    {"direction_1": "red", "direction_2": "red"},
    {"direction_1": "red", "direction_2": "yellow"},
    {"direction_1": "yellow", "direction_2": "yellow"},
    {"direction_1": "off", "direction_2": "off"},
    {"direction_1": "green", "direction_2": "red"},
    {"direction_1": "green", "direction_2": "yellow"},
]


class ModeChecker:
    """Простой помощник для проверки допустимости конфигураций светофора."""

    def __init__(self, allowed_configurations):
        self._allowed = allowed_configurations

    def is_allowed(self, mode_str: str) -> bool:
        try:
            mode = json.loads(mode_str)
            print(f"[монитор] проверяем конфигурацию {mode}")
            return mode in self._allowed
        except Exception:
            return False


# Класс, реализующий поведение монитора безопасности
class Monitor(Thread):

    def __init__(self, events_q: Queue):
        # вызываем конструктор базового класса
        super().__init__()
        self._events_q = events_q  # очередь событий для монитора (входящие сообщения)
        self._control_q = Queue()  # очередь управляющих команд (например, для остановки монитора)
        self._entity_queues = {}   # словарь очередей известных монитору сущностей
        self._force_quit = False   # флаг завершения работы монитора
        self._mode_checker = ModeChecker(traffic_lights_allowed_configurations)

    # регистрация очереди новой сущности
    def add_entity_queue(self, entity_id: str, queue: Queue):
        print(f"[монитор] регистрируем сущность {entity_id}")
        self._entity_queues[entity_id] = queue

    # проверка политик безопасности
    def _check_policies(self, event) -> bool:
        print(f"[монитор] обрабатываем событие {event}")

        # default deny: всё, что не разрешено, запрещено по умолчанию!
        authorized = False

        # проверка на входе, что это экземпляр класса Event,
        # т.е. имеет ожидаемый формат
        if not isinstance(event, Event):
            return False

        #
        #  политики безопасности
        #

        # пример политики безопасности
        if event.source == "ControlSystem" \
                and event.destination == "LightsGPIO" \
                and event.operation == "set_mode" \
                and self._mode_checker.is_allowed(event.parameters):
            authorized = True

        if authorized is False:
            print("[монитор] событие не разрешено политиками безопасности")
        return authorized

    # выполнение разрешённого запроса
    # метод должен вызываться только после проверки политик безопасности
    def _proceed(self, event: Event) -> bool:
        print(f"[монитор] отправляем запрос {event}")
        try:
            # найдём очередь получателя события
            dst_q: Queue = self._entity_queues[event.destination]
            # и положим запрос в эту очередь
            dst_q.put(event)
            return True
        except Exception as e:
            # например, запрос пришёл от или для неизвестной сущности
            print(f"[монитор] ошибка выполнения запроса {e}")
            return False

    # публичный метод для тестов: проверка политик и маршрутизация одного события
    def authorize_and_route(self, event) -> bool:
        authorized = self._check_policies(event)
        if not authorized:
            return False

        if not isinstance(event, Event):
            return False

        if event.destination not in self._entity_queues:
            print("[монитор] неизвестная сущность-получатель")
            return False

        routed = self._proceed(event)
        return routed

    # основной код работы монитора безопасности
    def run(self):
        print("[монитор] старт")

        # в цикле проверяет наличие новых событий,
        # выход из цикла по флагу _force_quit
        while self._force_quit is False:
            event = None
            try:
                # ожидание сделано неблокирующим,
                # чтобы можно было завершить работу монитора,
                # не дожидаясь нового сообщения
                event = self._events_q.get_nowait()
                # сюда попадаем только в случае получение события,
                # теперь нужно проверить политики безопасности
                self.authorize_and_route(event)
            except Empty:
                # сюда попадаем, если новых сообщений ещё нет,
                # в таком случае немного подождём
                sleep(0.5)
            except Exception as e:
                # что-то пошло не так, выведем сообщение об ошибке
                print(f"[монитор] ошибка обработки {e}, {event}")
            self._check_control_q()
        print("[монитор] завершение работы")

    # запрос на остановку работы монитора безопасности для завершения работы
    # может вызываться вне процесса монитора
    def stop(self):
        # поскольку монитор работает в отдельном процессе,
        # запрос помещается в очередь, которая проверяется из процесса монитора
        request = ControlEvent(operation="stop")
        self._control_q.put(request)

    # проверка наличия новых управляющих команд
    def _check_control_q(self):
        try:
            request: ControlEvent = self._control_q.get_nowait()
            print(f"[монитор] проверяем запрос {request}")
            if isinstance(request, ControlEvent) and request.operation == "stop":
                # поступил запрос на остановку монитора, поднимаем "красный флаг"
                self._force_quit = True
        except Empty:
            # никаких команд не поступило, ну и ладно
            pass


"""
Сущность ControlSystem

Эта сущность (Система управления светофора) отправляет сообщение для другой сущности (LightsGPIO)
"""


class ControlSystem(Thread):

    def __init__(self, monitor_queue: Queue):
        # вызываем конструктор базового класса
        super().__init__()
        # мы знаем только очередь монитора безопасности для взаимодействия с другими сущностями
        # прямая отправка сообщений в другую сущность запрещена в концепции FLASK
        self.monitor_queue = monitor_queue
        # создаём собственную очередь, в которую монитор сможет положить сообщения для этой сущности
        self._own_queue = Queue()

    # выдаёт собственную очередь для взаимодействия
    def entity_queue(self):
        return self._own_queue

    # основной код сущности
    def run(self):
        print(f"[{self.__class__.__name__}] старт")
        print(f"[{self.__class__.__name__}] отправляем тестовый запрос")

        # (эту логику нужно будет изменить в задании 1)
        mode = {"direction_1": "green", "direction_2": "red"}

        # запрос для сущности WorkerB - "скажи hello"
        event = Event(
            source=self.__class__.__name__,
            destination="LightsGPIO",
            operation="set_mode",
            parameters=json.dumps(mode),
        )

        self.monitor_queue.put(event)
        print(f"[{self.__class__.__name__}] завершение работы")


"""
Сущность LightsGPIO

Эта сущность (Система управления светодиодами) ждёт входящее сообщение в течение заданного периода времени, и если получает - обрабатывает и завершает работу или выходит по таймауту. (эту логику нужно будет изменить в задании 4)
"""


class LightsGPIO(Thread):

    def __init__(self, monitor_queue: Queue):
        # вызываем конструктор базового класса
        super().__init__()
        # мы знаем только очередь монитора безопасности для взаимодействия с другими сущностями
        # прямая отправка сообщений в другую сущность запрещена в концепции FLASK
        self.monitor_queue = monitor_queue
        # создаём собственную очередь, в которую монитор сможет положить сообщения для этой сущности
        self._own_queue = Queue()
        # состояние для дидактики и тестов
        self.current_mode = None

    def entity_queue(self):
        return self._own_queue

    # основной код сущности
    def run(self):
        print(f"[{self.__class__.__name__}] старт")
        attempts = 10
        while attempts > 0:
            try:
                event: Event = self._own_queue.get_nowait()
                if event.operation == "set_mode":
                    print(
                        f"[{self.__class__.__name__}] {event.source} запрашивает изменение режима {event.parameters}"
                    )
                    print(f"[{self.__class__.__name__}] новый режим: {event.parameters}!")
                    try:
                        self.current_mode = json.loads(event.parameters)
                    except Exception:
                        self.current_mode = None
                    if self.current_mode is not None:
                        self._print_terminal_state(self.current_mode)
                    break
            except Empty:
                sleep(0.2)
                attempts -= 1
        print(f"[{self.__class__.__name__}] завершение работы")

    def _print_terminal_state(self, mode: dict) -> None:
        icons = {
            "red": "🔴",
            "yellow": "🟡",
            "green": "🟢",
            "off": "⚫",
        }
        d1 = icons.get(mode.get("direction_1", "off"), "⚪")
        d2 = icons.get(mode.get("direction_2", "off"), "⚪")
        print(f"[{self.__class__.__name__}] состояние: direction_1 {d1}  direction_2 {d2}")


"""
Дополнительные сущности (заглушки) для полноты архитектуры.
Используются при тестировании политик направлений, но не участвуют в демонстрации.
"""


class CitySystemConnector(Thread):

    def __init__(self, monitor_queue: Queue):
        super().__init__()
        self.monitor_queue = monitor_queue
        self._own_queue = Queue()

    def entity_queue(self):
        return self._own_queue

    def run(self):
        print(f"[{self.__class__.__name__}] старт")
        print(f"[{self.__class__.__name__}] завершение работы")


class SelfDiagnosticsSystem(Thread):

    def __init__(self, monitor_queue: Queue):
        super().__init__()
        self.monitor_queue = monitor_queue
        self._own_queue = Queue()

    def entity_queue(self):
        return self._own_queue

    def run(self):
        print(f"[{self.__class__.__name__}] старт")
        print(f"[{self.__class__.__name__}] завершение работы")




def _build_system():
    monitor = Monitor(monitor_events_queue)
    control_system = ControlSystem(monitor_events_queue)
    lights_gpio = LightsGPIO(monitor_events_queue)
    return monitor, control_system, lights_gpio


def _register_entities(monitor: Monitor, control_system: ControlSystem, lights_gpio: LightsGPIO):
    monitor.add_entity_queue(control_system.__class__.__name__, control_system.entity_queue())
    monitor.add_entity_queue(lights_gpio.__class__.__name__, lights_gpio.entity_queue())


def run_demo() -> None:
    """
    Инициализируем монитор и сущности
    """
    monitor, control_system, lights_gpio = _build_system()

    """
    регистрируем очереди сущностей в мониторе
    """
    _register_entities(monitor, control_system, lights_gpio)

    """
    Запускаем всё
    """

    """
    Ожидаемая последовательность событий

    Диаграмма последовательности вызовов (https://www.plantuml.com/plantuml/png/dPBVIiCm6CNlynIvdtk1NSZ02n4KXJr1w886-cUqcR0xgoBpIdoJLgqhtRg-mfStygJPM3js9OLyoPTpVia97ITQn7eU-6o6gZmr4w7c5r6euyYVB18j0ouIxhb6JpIHtZnMUd4JXKf7iPK5RjgJNQlx1vrStbtTMeNVhXZR0VdmV6yQ34QSQjhI5sNcWrE5QMrUgQHlysAUq7oZqcxyq1hbW6KxG8S5KWEBPHMe5MLeOBa6uHd4YWbVSs1JQg1OKktEF3ATSTI2Vk7Os6b6AupGerctn3uM5WWfn_OAxGRGr4OogTtktjCzmt3utyZ2q-fHQBb_JrSEv177oHigRB1E2ChOL1vxfPz8ZWjdBhv9ELn5Bw_vfFf4L2fFlZsEtkBBpNjxWH8mkyHWbbZbC1TCXbCsne1Vxmy0)
    """

    monitor.start()
    control_system.start()
    lights_gpio.start()

    """
    Теперь останавливаем
    """
    sleep(2)
    monitor.stop()

    control_system.join()
    lights_gpio.join()
    monitor.join()


def main() -> None:
    run_demo()

"""
 Заключение

В этом блокноте продемонстрирован базовый функционал контролируемого изменения режима работы светофора. 

В примере не реализованы некоторые сущности и большая часть логики работы светофора, которую можно предположить по архитектурной диаграмме. Попробуйте проделать это самостоятельно в соответствии с заданиями.
"""

"""
 Задания

Уровень "Начальный"

1. Измените режим на недопустимый (два зелёных).  
   В коде ControlSystem измените запрос на установку недопустимого режима (оба направления «green»). Убедитесь, что при выполнении всех ячеек монитор безопасности (Monitor или ModeChecker) блокирует такое сообщение.  
   Баллы: 1

2. Разрешите режим «мигающий жёлтый» (yellow_blinking).  
   Измените политики безопасности так, чтобы дополнительно стал разрешен режим с мигающим жёлтым ("yellow_blinking") для обоих направлений одновременно. Убедитесь, что теперь этот режим пропускается системой (то есть не блокируется).  
   Баллы: 3

Уровень "Продвинутый"

3. Добавьте политики безопасности для дополнительных секций со стрелками.  
   Обновите в список разрешённых конфигураций светофора в traffic_lights_allowed_configurations (либо соответствующую структуру в Monitor или ModeChecker) так, чтобы система дополнительно поддерживала режимы с двумя боковыми секциями поворота (налево/направо) для каждого из обоих направлений, и учитывала эти сигналы в процессе проверки (например добавить разрешенную конфигурацию {"direction_1": "green", "direction_1_left": "green", "direction_1_right": "green", "direction_2": "red", "direction_2_right": "green"} и др.).  
   Баллы: 6

4. Измените код сущностей, чтобы они работали произвольное время пока не получат команду «stop».  
   Внесите изменения в код сущностей, чтобы они не завершались автоматически по таймеру (как это сейчас сделано в блокноте), а работали на протяжении всего выполнения программы, пока не получат команду «stop» (по аналогии как это реализовано в мониторе безопасности).  
   Сделайте так, чтобы:  
   - ControlSystem генерировал различные команды раз в 3 секунды.  
   - ModeChecker, LightsGPIO, ControlSystem и Monitor завершали работу только после получения команды stop.  
   - Установить таймер выполнения программы на 60 секунд sleep(60) после чего должна выполняться команда stop.  
   Баллы: 7

5. Разделите класс Monitor на два класса: Monitor и ModeChecker.  
   - Перенесите логику проверки режимов из Monitor в отдельный класс ModeChecker, а в Monitor оставьте только контроль взаимодействия между компонентами (проверку отправителя, получателя, типа запроса и пр.).
   - Обновите политики в Monitor так, чтобы он пропускал сообщение set_mode лишь от ControlSystem к ModeChecker и от ModeChecker к LightsGPIO.
   Баллы: 8
"""

"""
Примечания к оформлению решения

- Итоговое решение оформляется как проект с файлом main.py (логика и демонстрация).
- Проект можно запускать из консоли: python main.py.
- Для проверки используйте pytest -q.
- Отдельно основные-тесты: pytest -q tests/test_ipc_policies.py tests/test_mode_checker.py
- Отдельно тесты заданий: pytest -q tests/test_student_tasks.py
- Основные тесты показывают, что базовая логика не сломана.
- Тесты заданий проверяют корректность реализации пунктов 1–5 (часть из них изначально красные).
- Также могут быть дополнительные тесты, которых нет в этом репозитории, для итоговой проверки.
"""


if __name__ == "__main__":
    main()

