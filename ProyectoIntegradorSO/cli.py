from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt, Prompt
from rich.panel import Panel
from procesos import ProcessManager
from recursos import SystemResources
from planificador import SchedulerFactory, RoundRobinScheduler
from comunicacion import message_system, producer_consumer
console = Console()

class CLI:
    def __init__(self):
        self.process_manager = ProcessManager()
        self.resources = SystemResources()
        self.scheduler = None
        self.scheduler_algorithm = "fcfs"
        self.quantum = 2
        self.logs = []
        self._setup_scheduler()

    def _setup_scheduler(self):
        self.scheduler = SchedulerFactory.create_scheduler(
            self.scheduler_algorithm,
            self.process_manager,
            self.resources,
            self.quantum
        )

    def show_menu(self) -> None:
        """Muestra el menú principal"""
        console.print(f"\n[bold cyan]Simulador de SO[/bold cyan] - [yellow]{self.scheduler.name}[/yellow]",
                      justify="center")
        console.print(
            "1. Crear proceso\n"
            "2. Listar procesos\n"
            "3. Ver recursos\n"
            "4. Cambiar algoritmo\n"
            "5. Ejecutar simulación\n"
            "6. Suspender proceso\n"
            "7. Reanudar proceso\n"
            "8. Terminar proceso\n"
            "9. Ver logs\n"
            "10. Enviar mensaje entre procesos\n"
            "11. Ver mensajes de un proceso\n"
            "12. Simulación Productor-Consumidor\n"
            "0. Salir"
        )
        console.print(
            "[dim italic]Nota: Los valores entre paréntesis son valores recomendados, pero puedes introducir valores diferentes según tus necesidades.[/dim italic]")

    def create_process_interactive(self) -> None:
        try:
            console.print(
                "[italic]Los valores entre paréntesis son recomendados, pero puedes usar otros valores.[/italic]")
            priority = IntPrompt.ask("Prioridad [dim](Recomendado: 1-5)[/dim]", default=3)

            console.print(f"[dim]Memoria total: {self.resources.total_memory} MB[/dim]")
            console.print(f"[dim]Memoria disponible: {self.resources.available_memory} MB[/dim]")

            memory = IntPrompt.ask("Memoria a asignar (MB) [dim](Recomendado: 256)[/dim]", default=256)
            burst_time = IntPrompt.ask("Tiempo de CPU [dim](Recomendado: 5, puedes usar cualquier valor)[/dim]",
                                       default=5)

            if priority < 1:
                console.print("[yellow]⚠ Advertencia: La prioridad se ha ajustado al valor mínimo (1)[/yellow]")
                priority = 1

            if memory < 1:
                console.print(f"[yellow]⚠ Advertencia: La memoria se ha ajustado al valor mínimo (1 MB)[/yellow]")
                memory = 1

            if burst_time < 1:
                console.print("[yellow]⚠ Advertencia: El tiempo de CPU se ha ajustado al valor mínimo (1)[/yellow]")
                burst_time = 1

            # Verificar si hay memoria suficiente
            if memory > self.resources.available_memory:
                console.print(
                    f"[red]✗ No hay suficiente memoria disponible. Disponible: {self.resources.available_memory} MB[/red]")
                return

            new_process = self.process_manager.create_process(priority, memory, burst_time)

            success = self.resources.assign_memory(new_process.pid, memory)
            if not success:
                console.print(f"[red]✗ Error al asignar memoria al proceso[/red]")

                self.process_manager.processes.remove(new_process)
                self.process_manager.ready_queue.remove(new_process)
                return

            message_system.create_queue(new_process.pid)

            console.print(f"[green]✓ Proceso creado (PID: {new_process.pid})[/green]")
            console.print(f"[dim]Memoria restante: {self.resources.available_memory} MB[/dim]")
            self.logs.append(
                f"Proceso {new_process.pid} creado con prioridad {priority}, memoria {memory}MB y tiempo {burst_time}")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")

    def list_processes_table(self) -> None:
        table = Table(title="Procesos Activos")
        table.add_column("PID")
        table.add_column("Estado")
        table.add_column("Prioridad")
        table.add_column("Memoria (MB)")
        table.add_column("Tiempo restante")
        table.add_column("Mensajes")

        for p in self.process_manager.list_processes():
            state_color = {
                "ready": "blue",
                "running": "green",
                "waiting": "yellow",
                "terminated": "red"
            }.get(p.state, "white")

            msg_count = message_system.get_queue_size(p.pid)
            msg_display = f"[green]{msg_count}[/green]" if msg_count > 0 else "0"

            table.add_row(
                str(p.pid),
                f"[{state_color}]{p.state}[/{state_color}]",
                str(p.priority),
                str(p.memory),
                str(p.burst_time),
                msg_display
            )

        console.print(table)

        # Mostrar cola de procesos listos
        if self.process_manager.ready_queue:
            ready_pids = [str(p.pid) for p in self.process_manager.ready_queue if p.state == "ready"]
            if ready_pids:
                console.print(f"Cola de listos: {' → '.join(ready_pids)}")

    def show_resources(self) -> None:
        status = self.resources.get_resource_status()
        table = Table(title="Recursos del Sistema")
        table.add_column("Recurso")
        table.add_column("Estado")
        table.add_column("Detalles")

        cpu_status = status["CPU"]
        cpu_color = "green" if cpu_status == "Libre" else "red"

        memory_used = int(self.resources.total_memory) - int(self.resources.available_memory)
        memory_percentage = (memory_used / int(self.resources.total_memory)) * 100

        memory_color = "green"
        if memory_percentage > 75:
            memory_color = "red"
        elif memory_percentage > 50:
            memory_color = "yellow"

        table.add_row("CPU", f"[{cpu_color}]{cpu_status}[/{cpu_color}]", "1 núcleo")
        table.add_row(
            "Memoria",
            f"[{memory_color}]{self.resources.available_memory}/{self.resources.total_memory} MB libre[/{memory_color}]",
            f"Usado: {memory_used} MB ({memory_percentage:.1f}%)"
        )

        console.print(table)

    def change_algorithm(self) -> None:
        console.print("[bold]Algoritmos disponibles:[/bold]")
        console.print("1. FCFS (First-Come, First-Served)")
        console.print("2. SJF (Shortest Job First)")
        console.print("3. Prioridad")
        console.print("4. Round Robin")

        option = Prompt.ask("Seleccione un algoritmo", choices=["1", "2", "3", "4"])

        # Guardar el algoritmo anterior para liberar recursos si es necesario
        old_algorithm = self.scheduler_algorithm
        old_scheduler = self.scheduler

        if option == "1":
            self.scheduler_algorithm = "fcfs"
        elif option == "2":
            self.scheduler_algorithm = "sjf"
        elif option == "3":
            self.scheduler_algorithm = "priority"
        elif option == "4":
            self.scheduler_algorithm = "round_robin"
            console.print(
                "[italic]El quantum determina cuántos ciclos se ejecuta cada proceso antes de ser interrumpido.[/italic]")
            self.quantum = IntPrompt.ask(
                "Valor del quantum [dim](Recomendado: 2, puedes usar cualquier valor positivo)[/dim]", default=2)
            if self.quantum < 1:
                console.print("[yellow]⚠ Advertencia: El quantum se ha ajustado al valor mínimo (1)[/yellow]")
                self.quantum = 1

        # Configurar el nuevo planificador
        self._setup_scheduler()

        # Limpiar estado previo y reiniciar estados si es necesario
        self._reset_process_states()

        console.print(f"[green]✓ Algoritmo cambiado a: {self.scheduler.name}[/green]")
        self.logs.append(f"Algoritmo cambiado a {self.scheduler.name}")

    def _reset_process_states(self) -> None:
        # Asegurarse de que la CPU esté disponible para el nuevo algoritmo
        self.resources.cpu_available = True

        # Verificar si hay algún proceso en estado "running" y pasarlo a "ready"
        for process in self.process_manager.processes:
            if process.state == "running":
                process.state = "ready"
                self.logs.append(f"Proceso {process.pid} cambiado de running a ready al cambiar de algoritmo")

        # Reiniciar el proceso actual en el planificador
        if hasattr(self.scheduler, 'current_process'):
            self.scheduler.current_process = None

        # Si es Round Robin, reiniciar el contador de quantum
        if hasattr(self.scheduler, 'current_quantum'):
            self.scheduler.current_quantum = 0

    def run_simulation(self) -> None:

        console.print("[italic]Puedes especificar cualquier número de ciclos a ejecutar.[/italic]")
        cycles = IntPrompt.ask("Número de ciclos a ejecutar [dim](Recomendado: 5, puedes usar cualquier valor)[/dim]",
                               default=5)

        if cycles < 1:
            console.print("[yellow]⚠ Advertencia: El número de ciclos se ha ajustado al valor mínimo (1)[/yellow]")
            cycles = 1

        # Mostrar tabla de estado inicial
        console.print("\n[bold]Estado inicial (Ciclo 0):[/bold]")
        self.list_processes_table()
        self.show_resources()

        # Ejecutar ciclos uno por uno, mostrando detalles en cada paso
        for i in range(cycles):
            current_cycle = i + 1
            console.print(
                f"\n[bold cyan]Ciclo {current_cycle}/{cycles} - Tiempo global: {self.scheduler.time}[/bold cyan]")

            # Ejecutar un ciclo
            result = self.scheduler.execute_cycle()
            event_type = result.get("event")
            process = result.get("process")

            # Generar descripción detallada del evento
            event_desc = f"[yellow]→ Evento:[/yellow] "
            if event_type == "process_started":
                event_desc += f"Proceso {process.pid} iniciado (tiempo restante: {process.burst_time})"
            elif event_type == "process_running":
                event_desc += f"Proceso {process.pid} en ejecución (tiempo restante: {process.burst_time})"
            elif event_type == "process_completed":
                event_desc += f"Proceso {process.pid} completado"
            elif event_type == "process_preempted":
                event_desc += f"Proceso {process.pid} interrumpido por quantum (tiempo restante: {process.burst_time})"
            elif event_type == "idle":
                event_desc += "CPU inactiva"

            # Mostrar evento actual
            console.print(event_desc)

            # Si estamos usando Round Robin, mostrar información del quantum
            if isinstance(self.scheduler, RoundRobinScheduler) and process and event_type in ["process_running",
                                                                                              "process_started"]:
                console.print(
                    f"[dim]   Quantum actual: {self.scheduler.current_quantum}/{self.scheduler.quantum}[/dim]")

            # Mostrar estado actual después de cada ciclo
            console.print("\n[bold]Estado después del ciclo {0}:[/bold]".format(current_cycle))
            self.list_processes_table()
            self.show_resources()

            # Registrar en logs
            self._handle_simulation_event(result)

        console.print(f"\n[green]✓ Simulación completada: {current_cycle} ciclos ejecutados[/green]")

    def _handle_simulation_event(self, event_info: dict) -> None:
        event_type = event_info.get("event")

        if event_type == "process_started":
            process = event_info.get("process")
            self.logs.append(
                f"Ciclo {self.scheduler.time}: Proceso {process.pid} inició ejecución (tiempo restante: {process.burst_time})")

        elif event_type == "process_running":
            process = event_info.get("process")
            self.logs.append(
                f"Ciclo {self.scheduler.time}: Proceso {process.pid} en ejecución (tiempo restante: {process.burst_time})")

        elif event_type == "process_completed":
            process = event_info.get("process")
            self.logs.append(f"Ciclo {self.scheduler.time}: Proceso {process.pid} completado")

        elif event_type == "process_preempted":
            process = event_info.get("process")
            self.logs.append(
                f"Ciclo {self.scheduler.time}: Proceso {process.pid} interrumpido por quantum (tiempo restante: {process.burst_time})")

        elif event_type == "idle":
            self.logs.append(f"Ciclo {self.scheduler.time}: CPU inactiva")

    def suspend_process(self) -> None:
        pid = IntPrompt.ask("PID del proceso a suspender")

        process = next((p for p in self.process_manager.processes if p.pid == pid), None)
        if not process:
            console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
            return

        if process.state not in ["running", "ready"]:
            console.print(
                f"[red]✗ El proceso {pid} no está en ejecución o listo (estado actual: {process.state})[/red]")
            return

        # Si el proceso está ejecutándose, liberar la CPU
        if process.state == "running":
            self.resources.cpu_available = True
            # Si es el proceso actual del planificador, resetear
            if self.scheduler.current_process and self.scheduler.current_process.pid == pid:
                self.scheduler.current_process = None

        process.state = "waiting"
        console.print(f"[yellow]⏸ Proceso {pid} suspendido[/yellow]")
        self.logs.append(f"Proceso {pid} suspendido")

    def resume_process(self) -> None:
        pid = IntPrompt.ask("PID del proceso a reanudar")

        process = next((p for p in self.process_manager.processes if p.pid == pid), None)
        if not process:
            console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
            return

        if process.state != "waiting":
            console.print(f"[red]✗ El proceso {pid} no está suspendido (estado actual: {process.state})[/red]")
            return

        process.state = "ready"
        console.print(f"[green]▶ Proceso {pid} reanudado[/green]")
        self.logs.append(f"Proceso {pid} reanudado")

    def terminate_process(self) -> None:
        pid = IntPrompt.ask("PID del proceso a terminar")

        process = next((p for p in self.process_manager.processes if p.pid == pid), None)
        if not process:
            console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
            return

        if process.state == "terminated":
            console.print(f"[red]✗ El proceso {pid} ya está terminado[/red]")
            return

        # Si el proceso está ejecutándose, liberar la CPU
        if process.state == "running":
            self.resources.cpu_available = True
            # Si es el proceso actual del planificador, resetear
            if self.scheduler.current_process and self.scheduler.current_process.pid == pid:
                self.scheduler.current_process = None

        # Liberar memoria
        self.resources.release_memory(process.pid, process.memory)

        process.state = "terminated"
        console.print(f"[red]⏹ Proceso {pid} terminado forzadamente[/red]")
        console.print(
            f"[dim]Memoria liberada: {process.memory} MB. Memoria restante: {self.resources.available_memory} MB[/dim]")
        self.logs.append(f"Proceso {pid} terminado forzadamente")

    def show_logs(self) -> None:
        if not self.logs:
            console.print("[yellow]No hay eventos registrados[/yellow]")
            return

        # Crear tabla para mejor visualización
        table = Table(title="Registro de Eventos")
        table.add_column("#", style="dim")
        table.add_column("Evento")

        # Determinar cuántos logs mostrar
        max_logs = 15  # Mostrar más logs que antes
        start_idx = max(0, len(self.logs) - max_logs)

        for i, log in enumerate(self.logs[start_idx:], start=start_idx + 1):
            table.add_row(str(i), log)

        console.print(table)

        # Indicar si hay más logs
        if start_idx > 0:
            console.print(f"[dim]... {start_idx} eventos anteriores no mostrados[/dim]")

    def send_message(self) -> None:
        # Mostrar procesos activos
        active_processes = [p for p in self.process_manager.processes
                            if p.state != "terminated"]

        if len(active_processes) < 2:
            console.print("[red]✗ Se necesitan al menos dos procesos activos para enviar mensajes[/red]")
            return

        # Listar procesos para seleccionar
        console.print("[bold]Procesos disponibles:[/bold]")

        # Crear tabla para mejor visualización
        table = Table(title="Procesos Activos para Mensajes")
        table.add_column("PID")
        table.add_column("Estado")
        table.add_column("Mensajes pendientes")

        for p in active_processes:
            state_color = {
                "ready": "blue",
                "running": "green",
                "waiting": "yellow"
            }.get(p.state, "white")

            # Contar mensajes en la cola
            msg_count = message_system.get_queue_size(p.pid)
            msg_display = f"[green]{msg_count}[/green]" if msg_count > 0 else "0"

            table.add_row(
                str(p.pid),
                f"[{state_color}]{p.state}[/{state_color}]",
                msg_display
            )

        console.print(table)

        # Seleccionar proceso emisor
        sender_pid = IntPrompt.ask("PID del proceso emisor")
        sender = next((p for p in active_processes if p.pid == sender_pid), None)
        if not sender:
            console.print(f"[red]✗ No se encontró proceso con PID {sender_pid}[/red]")
            return

        # Seleccionar proceso receptor
        receiver_pid = IntPrompt.ask("PID del proceso receptor")
        receiver = next((p for p in active_processes if p.pid == receiver_pid), None)
        if not receiver:
            console.print(f"[red]✗ No se encontró proceso con PID {receiver_pid}[/red]")
            return

        # Introducir mensaje
        message = Prompt.ask("Mensaje")

        # Enviar mensaje
        result = message_system.send_message(sender_pid, receiver_pid, message)
        if result:
            console.print(f"[green]✓ Mensaje enviado de proceso {sender_pid} a proceso {receiver_pid}[/green]")
            self.logs.append(f"Mensaje enviado: {sender_pid} → {receiver_pid}")
        else:
            console.print(f"[red]✗ Error al enviar mensaje[/red]")

    def view_messages(self) -> None:
        pid = IntPrompt.ask("PID del proceso")

        process = next((p for p in self.process_manager.processes if p.pid == pid), None)
        if not process:
            console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
            return

        # Verificar si hay mensajes
        queue_size = message_system.get_queue_size(pid)
        if queue_size == 0:
            console.print(f"[yellow]El proceso {pid} no tiene mensajes[/yellow]")
            return

        # Mostrar mensajes
        console.print(f"[bold]Mensajes del proceso {pid}:[/bold]")

        table = Table(title=f"Cola de mensajes: Proceso {pid}")
        table.add_column("De")
        table.add_column("Mensaje")
        table.add_column("Acción", style="dim")

        # Recibir y mostrar todos los mensajes
        for _ in range(queue_size):
            message = message_system.receive_message(pid)
            if message:
                table.add_row(
                    str(message["sender"]),
                    message["content"],
                    "Mensaje leído y eliminado de la cola"
                )

        console.print(table)

    def run_producer_consumer(self) -> None:
        console.print("[bold]Simulación del problema Productor-Consumidor[/bold]")
        console.print("[italic]Este problema demuestra sincronización entre procesos usando semáforos.[/italic]")

        # Mostrar menú de opciones
        console.print("1. Registrar un proceso como productor")
        console.print("2. Registrar un proceso como consumidor")
        console.print("3. Producir un item")
        console.print("4. Consumir un item")
        console.print("5. Ver estado del buffer y semáforos")
        console.print("6. Ver logs de la simulación")
        console.print("7. Volver al menú principal")

        option = Prompt.ask("Seleccione una opción", choices=["1", "2", "3", "4", "5", "6", "7"])

        if option == "1":
            # Listar procesos activos
            active_processes = [p for p in self.process_manager.processes if p.state != "terminated"]
            if not active_processes:
                console.print("[red]✗ No hay procesos activos disponibles[/red]")
                return

            # Mostrar procesos para seleccionar
            console.print("[bold]Procesos disponibles:[/bold]")
            for p in active_processes:
                console.print(f"PID: {p.pid} - Estado: {p.state}")

            # Seleccionar proceso
            pid = IntPrompt.ask("PID del proceso a registrar como productor")
            process = next((p for p in active_processes if p.pid == pid), None)
            if not process:
                console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
                return

            # Registrar como productor
            producer_consumer.set_producer(pid)
            console.print(f"[green]✓ Proceso {pid} registrado como productor[/green]")

        elif option == "2":
            # Listar procesos activos
            active_processes = [p for p in self.process_manager.processes if p.state != "terminated"]
            if not active_processes:
                console.print("[red]✗ No hay procesos activos disponibles[/red]")
                return

            # Mostrar procesos para seleccionar
            console.print("[bold]Procesos disponibles:[/bold]")
            for p in active_processes:
                console.print(f"PID: {p.pid} - Estado: {p.state}")

            # Seleccionar proceso
            pid = IntPrompt.ask("PID del proceso a registrar como consumidor")
            process = next((p for p in active_processes if p.pid == pid), None)
            if not process:
                console.print(f"[red]✗ No se encontró proceso con PID {pid}[/red]")
                return

            # Registrar como consumidor
            producer_consumer.set_consumer(pid)
            console.print(f"[green]✓ Proceso {pid} registrado como consumidor[/green]")

        elif option == "3":
            # Verificar si hay un productor registrado
            producer_pid = producer_consumer.producer_pid
            if producer_pid is None:
                console.print("[yellow]⚠ No hay ningún proceso registrado como productor[/yellow]")
                console.print("[yellow]⚠ Utilice la opción 1 para registrar un productor primero[/yellow]")
                return

            # Verificar si el productor existe y está activo
            producer = next((p for p in self.process_manager.processes if p.pid == producer_pid), None)
            if not producer or producer.state == "terminated":
                console.print(f"[red]✗ El productor (PID {producer_pid}) ya no está disponible[/red]")
                return

            # Solicitar item a producir
            item = Prompt.ask("Item a producir")

            # Intentar producir
            result = producer_consumer.produce(producer_pid, item)
            if result:
                console.print(f"[green]✓ Item '{item}' producido correctamente por proceso {producer_pid}[/green]")

                # Actualizar registro
                self.logs.append(f"Productor {producer_pid} produjo item '{item}'")
            else:
                console.print(f"[yellow]⚠ No se pudo producir el item (buffer lleno o proceso bloqueado)[/yellow]")

                # Mostrar estado del buffer
                status = producer_consumer.get_buffer_status()
                console.print(
                    f"[dim]Estado del buffer: {len(status['buffer_content'])}/{status['buffer_size']} items[/dim]")

        elif option == "4":
            # Verificar si hay un consumidor registrado
            consumer_pid = producer_consumer.consumer_pid
            if consumer_pid is None:
                console.print("[yellow]⚠ No hay ningún proceso registrado como consumidor[/yellow]")
                console.print("[yellow]⚠ Utilice la opción 2 para registrar un consumidor primero[/yellow]")
                return

            # Verificar si el consumidor existe y está activo
            consumer = next((p for p in self.process_manager.processes if p.pid == consumer_pid), None)
            if not consumer or consumer.state == "terminated":
                console.print(f"[red]✗ El consumidor (PID {consumer_pid}) ya no está disponible[/red]")
                return

            # Intentar consumir
            item = producer_consumer.consume(consumer_pid)
            if item:
                console.print(f"[green]✓ Item '{item}' consumido correctamente por proceso {consumer_pid}[/green]")

                # Actualizar registro
                self.logs.append(f"Consumidor {consumer_pid} consumió item '{item}'")
            else:
                console.print(f"[yellow]⚠ No se pudo consumir ningún item (buffer vacío o proceso bloqueado)[/yellow]")

                # Mostrar estado del buffer
                status = producer_consumer.get_buffer_status()
                console.print(
                    f"[dim]Estado del buffer: {len(status['buffer_content'])}/{status['buffer_size']} items[/dim]")

        elif option == "5":
            status = producer_consumer.get_buffer_status()

            # Crear representación visual del buffer
            buffer_visual = "["
            for i in range(status["buffer_size"]):
                if i < len(status["buffer_content"]):
                    buffer_visual += f" [green]{status['buffer_content'][i]}[/green] "
                else:
                    buffer_visual += " □ "
            buffer_visual += "]"

            # Información sobre procesos registrados
            producer_info = f"PID {status['producer_pid']}" if status['producer_pid'] else "Ninguno"
            consumer_info = f"PID {status['consumer_pid']}" if status['consumer_pid'] else "Ninguno"

            # Información sobre semáforos
            mutex_info = f"Valor: {status['mutex_value']}"
            empty_info = f"Valor: {status['empty_slots']}"
            full_info = f"Valor: {status['full_slots']}"

            # Información sobre procesos bloqueados
            if status['mutex_waiting']:
                mutex_info += f" [yellow](Procesos bloqueados: {', '.join(map(str, status['mutex_waiting']))})[/yellow]"
            if status['empty_waiting']:
                empty_info += f" [yellow](Procesos bloqueados: {', '.join(map(str, status['empty_waiting']))})[/yellow]"
            if status['full_waiting']:
                full_info += f" [yellow](Procesos bloqueados: {', '.join(map(str, status['full_waiting']))})[/yellow]"

            console.print(Panel(
                f"[bold]Buffer (tamaño: {status['buffer_size']}):[/bold]\n"
                f"Items en buffer: {status['items_in_buffer']}\n"
                f"Buffer: {buffer_visual}\n\n"
                f"[bold]Semáforos:[/bold]\n"
                f"mutex: {mutex_info}\n"
                f"empty: {empty_info}\n"
                f"full: {full_info}\n\n"
                f"[bold]Procesos:[/bold]\n"
                f"Productor: {producer_info}\n"
                f"Consumidor: {consumer_info}",
                title="Estado del Productor-Consumidor",
                expand=False
            ))

        elif option == "6":
            logs = producer_consumer.get_logs()
            if not logs:
                console.print("[yellow]No hay eventos registrados en la simulación[/yellow]")
            else:
                # Crear tabla para mejor visualización
                table = Table(title="Eventos de Productor-Consumidor")
                table.add_column("#", style="dim")
                table.add_column("Evento")

                for i, log in enumerate(logs[-20:], start=max(1, len(logs) - 20)):
                    table.add_row(str(i), log)

                console.print(table)

                # Indicar si hay más eventos no mostrados
                if len(logs) > 20:
                    console.print(f"[dim]... {len(logs) - 20} eventos anteriores no mostrados[/dim]")