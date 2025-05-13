import queue
import time
import threading
from typing import Dict, Any, List, Optional, Union, Tuple

class MessageQueue:
    """
    Sistema de mensajes entre procesos.
    Implementa comunicación por paso de mensajes, donde cada proceso tiene su
    propia cola de mensajes y puede enviar/recibir mensajes a/de otros procesos.
    """

    def __init__(self):
        self.process_queues = {}  # Diccionario de colas para cada proceso
        self.message_id_counter = 0  # Contador global de IDs de mensajes

    def create_queue(self, pid: int) -> None:
        if pid not in self.process_queues:
            self.process_queues[pid] = queue.Queue()

    def remove_queue(self, pid: int) -> None:
        if pid in self.process_queues:
            del self.process_queues[pid]

    def send_message(self, sender_pid: int, receiver_pid: int, message: str) -> bool:

        if sender_pid not in self.process_queues:
            return False

        if receiver_pid not in self.process_queues:
            return False

        self.message_id_counter += 1

        formatted_message = {
            "id": self.message_id_counter,
            "sender": sender_pid,
            "content": message,
            "timestamp": time.time()
        }
        self.process_queues[receiver_pid].put(formatted_message)
        return True

    def receive_message(self, pid: int, blocking: bool = False) -> Optional[Dict[str, Any]]:
        # Verificar si el proceso tiene una cola
        if pid not in self.process_queues:
            return None

        try:
            if not blocking and self.process_queues[pid].empty():
                return None

            return self.process_queues[pid].get(block=blocking)
        except queue.Empty:
            return None

    def peek_message(self, pid: int) -> Optional[Dict[str, Any]]:
        if pid not in self.process_queues or self.process_queues[pid].empty():
            return None
        queue_items = list(self.process_queues[pid].queue)
        if queue_items:
            return queue_items[0]
        return None

    def get_queue_size(self, pid: int) -> int:
        if pid not in self.process_queues:
            return 0
        return self.process_queues[pid].qsize()


class Semaphore:
    def __init__(self, initial_value: int = 1, name: str = "unnamed"):

        self.value = initial_value
        self.name = name
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
        # Lista de PIDs de procesos esperando en este semáforo
        self.waiting_processes = []
        # Lista para registrar eventos
        self.operations_log = []

    def wait(self, pid: int) -> bool:
        with self.lock:
            if self.value <= 0:
                self.waiting_processes.append(pid)
                self.operations_log.append(f"Proceso {pid} bloqueado en semáforo '{self.name}' (valor: {self.value})")
                return False

            self.value -= 1
            self.operations_log.append(f"Proceso {pid} adquirió semáforo '{self.name}' (nuevo valor: {self.value})")
            return True

    def signal(self, pid: int) -> List[int]:

        with self.lock:
            self.value += 1
            self.operations_log.append(f"Proceso {pid} liberó semáforo '{self.name}' (nuevo valor: {self.value})")

            woken_processes = []
            if self.waiting_processes:
                woken_pid = self.waiting_processes.pop(0)
                woken_processes.append(woken_pid)
                self.operations_log.append(f"Proceso {woken_pid} despertado del semáforo '{self.name}'")

            return woken_processes

    def get_value(self) -> int:
        with self.lock:
            return self.value

    def get_waiting_processes(self) -> List[int]:
        with self.lock:
            return self.waiting_processes.copy()

    def get_logs(self) -> List[str]:
        with self.lock:
            return self.operations_log.copy()


class ProducerConsumer:
    def __init__(self, buffer_size: int = 5):
        self.buffer_size = buffer_size
        self.buffer = []

        self.mutex = Semaphore(1, "mutex")  # Exclusión mutua para acceder al buffer
        self.empty = Semaphore(buffer_size, "empty")  # Espacios vacíos
        self.full = Semaphore(0, "full")  # Espacios llenos

        self.producer_pid = None
        self.consumer_pid = None

        self.logs = []

    def set_producer(self, pid: int) -> None:
        self.producer_pid = pid
        self.logs.append(f"Proceso {pid} registrado como productor")

    def set_consumer(self, pid: int) -> None:
        self.consumer_pid = pid
        self.logs.append(f"Proceso {pid} registrado como consumidor")

    def produce(self, pid: int, item: str) -> bool:
        if self.producer_pid is not None and pid != self.producer_pid:
            self.logs.append(f"Error: El proceso {pid} no está registrado como productor")
            return False

        if not self.empty.wait(pid):
            self.logs.append(f"Productor {pid} bloqueado: buffer lleno")
            return False

        if not self.mutex.wait(pid):
            # Si no puede obtener mutex, devuelve el permiso de "empty"
            self.empty.signal(pid)
            self.logs.append(f"Productor {pid} bloqueado: no pudo obtener acceso exclusivo al buffer")
            return False

        self.buffer.append(item)
        self.logs.append(f"Productor {pid}: item '{item}' producido → buffer: {len(self.buffer)}/{self.buffer_size}")

        self.mutex.signal(pid)
        self.full.signal(pid)

        return True

    def consume(self, pid: int) -> Optional[str]:
        # Verificar si el proceso está registrado como consumidor
        if self.consumer_pid is not None and pid != self.consumer_pid:
            self.logs.append(f"Error: El proceso {pid} no está registrado como consumidor")
            return None

        # Intentar adquirir el semáforo "full" (¿hay items disponibles?)
        if not self.full.wait(pid):
            self.logs.append(f"Consumidor {pid} bloqueado: buffer vacío")
            return None

        # Intentar adquirir el semáforo de exclusión mutua
        if not self.mutex.wait(pid):
            self.full.signal(pid)
            self.logs.append(f"Consumidor {pid} bloqueado: no pudo obtener acceso exclusivo al buffer")
            return None

        # Sección crítica: Retira el item del buffer
        item = self.buffer.pop(0)
        self.logs.append(f"Consumidor {pid}: item '{item}' consumido → buffer: {len(self.buffer)}/{self.buffer_size}")

        # Liberar mutex
        self.mutex.signal(pid)

        # Incrementar semáforo "empty"
        self.empty.signal(pid)

        return item

    def get_buffer_status(self) -> Dict[str, Any]:
        return {
            "buffer_size": self.buffer_size,
            "items_in_buffer": len(self.buffer),
            "buffer_content": self.buffer.copy(),
            "empty_slots": self.empty.get_value(),
            "full_slots": self.full.get_value(),
            "mutex_value": self.mutex.get_value(),
            "producer_pid": self.producer_pid,
            "consumer_pid": self.consumer_pid,
            "empty_waiting": self.empty.get_waiting_processes(),
            "full_waiting": self.full.get_waiting_processes(),
            "mutex_waiting": self.mutex.get_waiting_processes()
        }

    def get_logs(self) -> List[str]:
        semaphore_logs = (
                self.mutex.get_logs() +
                self.empty.get_logs() +
                self.full.get_logs()
        )
        all_logs = self.logs + semaphore_logs
        return all_logs


# Sistema de comunicación global
message_system = MessageQueue()
producer_consumer = ProducerConsumer(buffer_size=5)