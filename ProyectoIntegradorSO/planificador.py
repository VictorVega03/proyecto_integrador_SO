import time
from procesos import Process, ProcessManager
from recursos import SystemResources

class Scheduler:
    def __init__(self, process_manager: ProcessManager, resources: SystemResources):
        self.process_manager = process_manager
        self.resources = resources
        self.current_process = None
        self.name = "Base Scheduler"
        self.time = 0

    def select_next_process(self) -> Process:
        raise NotImplementedError("Este método debe ser implementado por las subclases")

    def execute_cycle(self) -> dict:
        self.time += 1

        # Si no hay proceso en ejecución, selecciona uno nuevo
        if self.current_process is None or self.current_process.state != "running":
            next_process = self.select_next_process()
            if next_process and self.resources.cpu_available:
                # Asigna CPU al proceso
                self.resources.cpu_available = False
                next_process.state = "running"
                self.current_process = next_process
                return {"event": "process_started", "process": next_process}
            else:
                # Si no hay proceso disponible o la CPU no está disponible
                return {"event": "idle"}

        # Si hay un proceso en ejecución, reduce su tiempo de CPU
        if self.current_process and self.current_process.state == "running":
            self.current_process.burst_time -= 1

            # Si el proceso ha terminado
            if self.current_process.burst_time <= 0:
                self.current_process.state = "terminated"
                self.resources.cpu_available = True  # Liberar CPU
                self.resources.release_memory(self.current_process.pid, self.current_process.memory)
                result = {"event": "process_completed", "process": self.current_process}
                self.current_process = None
                return result

            return {"event": "process_running", "process": self.current_process}
        self.resources.cpu_available = True
        return {"event": "idle"}


class FCFSScheduler(Scheduler):
    def __init__(self, process_manager: ProcessManager, resources: SystemResources):
        super().__init__(process_manager, resources)
        self.name = "First-Come, First-Served (FCFS)"

    def select_next_process(self) -> Process:
        for process in self.process_manager.ready_queue:
            if process.state == "ready":
                return process
        return None

class SJFScheduler(Scheduler):
    def __init__(self, process_manager: ProcessManager, resources: SystemResources):
        super().__init__(process_manager, resources)
        self.name = "Shortest Job First (SJF)"

    def select_next_process(self) -> Process:
        if not self.process_manager.ready_queue:
            return None

        ready_processes = [p for p in self.process_manager.ready_queue if p.state == "ready"]
        if not ready_processes:
            return None

        return min(ready_processes, key=lambda p: p.burst_time)


class PriorityScheduler(Scheduler):
    def __init__(self, process_manager: ProcessManager, resources: SystemResources):
        super().__init__(process_manager, resources)
        self.name = "Priority Scheduler"

    def select_next_process(self) -> Process:
        if not self.process_manager.ready_queue:
            return None

        ready_processes = [p for p in self.process_manager.ready_queue if p.state == "ready"]
        if not ready_processes:
            return None

        return min(ready_processes, key=lambda p: p.priority)


class RoundRobinScheduler(Scheduler):
    def __init__(self, process_manager: ProcessManager, resources: SystemResources, quantum: int = 2):
        super().__init__(process_manager, resources)
        self.name = f"Round Robin (Quantum: {quantum})"
        self.quantum = max(1, quantum)  # Asegurarse de que quantum sea al menos 1
        self.current_quantum = 0

    def select_next_process(self) -> Process:
        if not self.process_manager.ready_queue:
            return None

        if self.current_process and self.current_process.state == "running" and self.current_quantum >= self.quantum:
            self.current_process.state = "ready"

            if self.current_process in self.process_manager.ready_queue:
                self.process_manager.ready_queue.remove(self.current_process)
                self.process_manager.ready_queue.append(self.current_process)
            else:
                self.process_manager.ready_queue.append(self.current_process)
            self.resources.cpu_available = True
            self.current_quantum = 0
            self.current_process = None

        for process in self.process_manager.ready_queue:
            if process.state == "ready":
                self.current_quantum = 0
                return process

        return None

    def execute_cycle(self) -> dict:
        self.time += 1

        if self.current_process is None or self.current_process.state != "running":
            next_process = self.select_next_process()
            if next_process and self.resources.cpu_available:
                # Asigna CPU al proceso
                self.resources.cpu_available = False
                next_process.state = "running"
                self.current_process = next_process
                self.current_quantum = 0
                return {"event": "process_started", "process": next_process}
            else:
                # Si no hay proceso disponible o la CPU no está disponible
                return {"event": "idle"}

        # Si hay un proceso en ejecución
        if self.current_process and self.current_process.state == "running":
            # Incrementar quantum usado
            self.current_quantum += 1

            # Reducir tiempo de CPU del proceso
            self.current_process.burst_time -= 1

            # Si el proceso ha terminado
            if self.current_process.burst_time <= 0:
                self.current_process.state = "terminated"
                self.resources.cpu_available = True
                self.resources.release_memory(self.current_process.pid, self.current_process.memory)
                result = {"event": "process_completed", "process": self.current_process}
                self.current_process = None
                self.current_quantum = 0
                return result

            # Si el proceso ha agotado su quantum pero no ha terminado
            if self.current_quantum >= self.quantum:
                process_to_preempt = self.current_process
                process_to_preempt.state = "ready"
                self.resources.cpu_available = True

                # Verificar si el proceso está en la cola antes de manipularlo
                if process_to_preempt in self.process_manager.ready_queue:
                    self.process_manager.ready_queue.remove(process_to_preempt)
                    self.process_manager.ready_queue.append(process_to_preempt)
                else:
                    self.process_manager.ready_queue.append(process_to_preempt)

                result = {"event": "process_preempted", "process": process_to_preempt}
                self.current_process = None
                self.current_quantum = 0
                return result

            # Si el proceso sigue ejecutándose sin haber agotado su quantum
            return {"event": "process_running", "process": self.current_process}

        self.resources.cpu_available = True
        return {"event": "idle"}

    def set_quantum(self, quantum: int) -> None:
        self.quantum = max(1, quantum)
        self.name = f"Round Robin (Quantum: {self.quantum})"
        self.current_quantum = 0


class SchedulerFactory:
    @staticmethod
    def create_scheduler(algorithm: str, process_manager: ProcessManager,
                         resources: SystemResources, quantum: int = 2) -> Scheduler:
        algorithm = algorithm.lower()

        if algorithm == 'fcfs':
            return FCFSScheduler(process_manager, resources)
        elif algorithm == 'sjf':
            return SJFScheduler(process_manager, resources)
        elif algorithm == 'priority':
            return PriorityScheduler(process_manager, resources)
        elif algorithm == 'round_robin':
            return RoundRobinScheduler(process_manager, resources, quantum)
        else:
            raise ValueError(f"Algoritmo desconocido: {algorithm}")