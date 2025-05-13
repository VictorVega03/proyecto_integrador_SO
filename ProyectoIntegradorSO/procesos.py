class Process:
    def __init__(self, pid: int, priority: int, memory: int, burst_time: int):
        self.pid = pid
        self.state = "ready"
        self.priority = priority
        self.memory = memory
        self.burst_time = burst_time
        self.resources = []
        self.arrival_time = 0

class ProcessManager:
    def __init__(self):
        self.processes = []
        self.ready_queue = []

    def create_process(self, priority: int, memory: int, burst_time: int) -> Process:

        pid = len(self.processes) + 1
        new_process = Process(pid, priority, memory, burst_time)
        self.processes.append(new_process)
        self.ready_queue.append(new_process)
        return new_process

    def list_processes(self) -> list[Process]:
        return self.processes

    def get_process_by_pid(self, pid: int) -> Process:
        for process in self.processes:
            if process.pid == pid:
                return process

        return None

    def terminate_process(self, pid: int) -> bool:
        process = self.get_process_by_pid(pid)

        if process and process.state != "terminated":
            process.state = "terminated"
            return True

        return False