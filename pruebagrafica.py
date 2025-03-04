import simpy
import random
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import defaultdict
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import time

# Constantes para la simulación
RANDOM_SEED = 42
MAX_MEMORIA_PROCESO = 10
MIN_MEMORIA_PROCESO = 1
MAX_INSTRUCCIONES = 10
MIN_INSTRUCCIONES = 1

class SistemaOperativoSimulacion:
    def __init__(self):
        # Lista para almacenar los tiempos de ejecución de cada proceso
        self.tiempos_ejecucion = []
        self.resultados = defaultdict(lambda: defaultdict(dict))
        self.log_texto = ""
        self.simulacion_en_progreso = False
        
    def proceso(self, env, nombre, RAM, CPU, intervalo_llegada, instrucciones_por_ciclo):
        # Simular el tiempo de llegada del proceso
        yield env.timeout(random.expovariate(1.0 / intervalo_llegada))
        tiempo_llegada = env.now
        
        # Estado NEW: solicitar memoria
        memoria_requerida = random.randint(MIN_MEMORIA_PROCESO, MAX_MEMORIA_PROCESO)
        instrucciones_totales = random.randint(MIN_INSTRUCCIONES, MAX_INSTRUCCIONES)
        
        self.log(f'{nombre} llega en t={tiempo_llegada:.2f}, requiere {memoria_requerida} de memoria y {instrucciones_totales} instrucciones')
        
        # Esperar hasta que haya suficiente memoria disponible
        yield RAM.get(memoria_requerida)
        self.log(f'{nombre} obtuvo {memoria_requerida} de memoria en t={env.now:.2f}, pasa a READY')
        
        # Ciclo principal del proceso hasta que termine sus instrucciones
        while instrucciones_totales > 0:
            # Estado READY: esperar por el CPU
            with CPU.request() as req:
                yield req
                self.log(f'{nombre} obtuvo CPU en t={env.now:.2f}, pasa a RUNNING')
                
                # Estado RUNNING: ejecutar instrucciones
                instrucciones_ejecutadas = min(instrucciones_por_ciclo, instrucciones_totales)
                yield env.timeout(1)  # Unidad de tiempo para ejecutar instrucciones
                instrucciones_totales -= instrucciones_ejecutadas
                
                self.log(f'{nombre} ejecutó {instrucciones_ejecutadas} instrucciones, quedan {instrucciones_totales}')
                
                # Determinar el siguiente estado
                if instrucciones_totales <= 0:
                    # Estado TERMINATED
                    self.log(f'{nombre} ha terminado en t={env.now:.2f}, libera {memoria_requerida} de memoria')
                    RAM.put(memoria_requerida)
                    tiempo_total = env.now - tiempo_llegada
                    self.tiempos_ejecucion.append(tiempo_total)
                    self.log(f'{nombre} tiempo total en el sistema: {tiempo_total:.2f}')
                    break
                else:
                    # Decidir si va a WAITING o vuelve a READY
                    decision = random.randint(1, 21)
                    if decision == 1:
                        # Estado WAITING (I/O)
                        self.log(f'{nombre} pasa a WAITING para I/O en t={env.now:.2f}')
                        tiempo_io = random.uniform(1, 3)  # Tiempo aleatorio para operaciones I/O
                        yield env.timeout(tiempo_io)
                        self.log(f'{nombre} termina I/O en t={env.now:.2f}, vuelve a READY')
                    else:
                        # Volver a READY
                        self.log(f'{nombre} vuelve a READY en t={env.now:.2f}')

    def ejecutar_simulacion(self, num_procesos, intervalo_llegada, memoria_total=100, num_cpus=1, velocidad_cpu=3):
        """
        Ejecuta la simulación con los parámetros especificados
        """
        # Reiniciar la lista de tiempos
        self.tiempos_ejecucion = []
        
        # Configurar el entorno
        env = simpy.Environment()
        random.seed(RANDOM_SEED)
        
        # Recursos
        RAM = simpy.Container(env, init=memoria_total, capacity=memoria_total)
        CPU = simpy.Resource(env, capacity=num_cpus)
        
        # Crear procesos
        for i in range(num_procesos):
            env.process(self.proceso(env, f'Proceso {i}', RAM, CPU, intervalo_llegada, velocidad_cpu))
        
        # Ejecutar la simulación
        self.log(f"\n--- Iniciando simulación con {num_procesos} procesos, intervalo {intervalo_llegada}, "
                f"memoria {memoria_total}, {num_cpus} CPU(s), velocidad {velocidad_cpu} ---\n")
        
        env.run()
        
        # Calcular estadísticas
        tiempo_promedio = np.mean(self.tiempos_ejecucion)
        desviacion_std = np.std(self.tiempos_ejecucion)
        
        self.log(f"\n--- Resultados de la simulación ---")
        self.log(f"Tiempo promedio de ejecución: {tiempo_promedio:.2f}")
        self.log(f"Desviación estándar: {desviacion_std:.2f}")
        
        return tiempo_promedio, desviacion_std
    
    def ejecutar_experimentos(self, cantidades_procesos, intervalos, configuraciones, directorio_resultados="resultados"):
        """
        Ejecuta todos los experimentos requeridos y genera gráficas
        """
        self.simulacion_en_progreso = True
        
        # Crear directorio para resultados si no existe
        if not os.path.exists(directorio_resultados):
            os.makedirs(directorio_resultados)
        
        # Limpiar resultados anteriores
        self.resultados = defaultdict(lambda: defaultdict(dict))
        
        # Ejecutar todas las simulaciones
        for config in configuraciones:
            self.log(f"\n=== Configuración: {config['nombre']} ===")
            
            for intervalo in intervalos:
                self.log(f"\n== Intervalo de llegada: {intervalo} ==")
                tiempos_promedio = []
                desviaciones = []
                
                for num_procesos in cantidades_procesos:
                    tiempo_promedio, desviacion = self.ejecutar_simulacion(
                        num_procesos=num_procesos,
                        intervalo_llegada=intervalo,
                        memoria_total=config['memoria'],
                        num_cpus=config['cpus'],
                        velocidad_cpu=config['velocidad']
                    )
                    
                    tiempos_promedio.append(tiempo_promedio)
                    desviaciones.append(desviacion)
                    self.resultados[config['nombre']][intervalo][num_procesos] = (tiempo_promedio, desviacion)
                    
                    self.log(f"Procesos: {num_procesos}, Tiempo promedio: {tiempo_promedio:.2f}, Desviación: {desviacion:.2f}")
                
                # Graficar resultados para esta configuración y este intervalo
                plt.figure(figsize=(10, 6))
                plt.errorbar(cantidades_procesos, tiempos_promedio, yerr=desviaciones, marker='o', capsize=5)
                plt.title(f'Tiempo promedio de ejecución - {config["nombre"]} (Intervalo: {intervalo})')
                plt.xlabel('Número de procesos')
                plt.ylabel('Tiempo promedio (unidades)')
                plt.grid(True)
                plt.savefig(f'{directorio_resultados}/resultado_{config["nombre"].replace(" ", "_")}_{intervalo}.png')
                plt.close()
        
        # Graficar comparativas para cada intervalo
        for intervalo in intervalos:
            plt.figure(figsize=(12, 8))
            
            for config in configuraciones:
                tiempos = [self.resultados[config['nombre']][intervalo][n][0] for n in cantidades_procesos]
                plt.plot(cantidades_procesos, tiempos, marker='o', label=config['nombre'])
                
            plt.title(f'Comparativa de configuraciones (Intervalo: {intervalo})')
            plt.xlabel('Número de procesos')
            plt.ylabel('Tiempo promedio (unidades)')
            plt.legend()
            plt.grid(True)
            plt.savefig(f'{directorio_resultados}/comparativa_intervalo_{intervalo}.png')
            plt.close()
        
        # Generar tabla comparativa
        self.log("\n=== Tabla Comparativa de Resultados ===")
        self.log("Configuración | Intervalo | 25 Proc. | 50 Proc. | 100 Proc. | 150 Proc. | 200 Proc.")
        self.log("-------------|-----------|----------|----------|-----------|-----------|----------")
        
        for config in configuraciones:
            for intervalo in intervalos:
                row = f"{config['nombre']:12} | {intervalo:9} | "
                for num_procesos in cantidades_procesos:
                    tiempo, _ = self.resultados[config['nombre']][intervalo][num_procesos]
                    row += f"{tiempo:8.2f} | "
                self.log(row)
        
        # Realizar análisis de resultados
        self.analizar_resultados(cantidades_procesos, intervalos, configuraciones)
        
        self.simulacion_en_progreso = False
        self.log("\n=== Simulación completada ===")
        return self.log_texto

    def analizar_resultados(self, cantidades_procesos, intervalos, configuraciones):
        """
        Analiza los resultados y determina la mejor estrategia
        """
        # Encontrar la mejor configuración para cada carga de trabajo
        self.log("\n=== Análisis de Resultados ===")
        
        for intervalo in intervalos:
            self.log(f"\nIntervalo de llegada: {intervalo}")
            
            for num_procesos in cantidades_procesos:
                mejor_config = None
                mejor_tiempo = float('inf')
                
                for config in configuraciones:
                    tiempo, _ = self.resultados[config['nombre']][intervalo][num_procesos]
                    if tiempo < mejor_tiempo:
                        mejor_tiempo = tiempo
                        mejor_config = config['nombre']
                
                self.log(f"Para {num_procesos} procesos, la mejor configuración es: {mejor_config} (Tiempo: {mejor_tiempo:.2f})")
        
        # Análisis general
        self.log("\n=== Conclusión General ===")
        
        # Contar cuántas veces cada configuración fue la mejor
        conteo_mejores = defaultdict(int)
        for intervalo in intervalos:
            for num_procesos in cantidades_procesos:
                mejor_config = None
                mejor_tiempo = float('inf')
                
                for config in configuraciones:
                    tiempo, _ = self.resultados[config['nombre']][intervalo][num_procesos]
                    if tiempo < mejor_tiempo:
                        mejor_tiempo = tiempo
                        mejor_config = config['nombre']
                
                conteo_mejores[mejor_config] += 1
        
        # Encontrar la configuración que fue mejor más veces
        mejor_general = max(conteo_mejores.items(), key=lambda x: x[1])
        
        self.log(f"La configuración que ofreció mejores resultados en más escenarios fue: {mejor_general[0]} ({mejor_general[1]} veces)")
        
        # Análisis por carga de trabajo
        self.log("\nAnálisis por tipo de carga:")
        self.log("- Para cargas ligeras (pocos procesos, intervalos largos): " + 
                self.mejor_config_para_carga(configuraciones, intervalos=[10], procesos=[25, 50]))
        self.log("- Para cargas moderadas (procesos intermedios): " + 
                self.mejor_config_para_carga(configuraciones, intervalos=[5], procesos=[50, 100]))
        self.log("- Para cargas intensas (muchos procesos, intervalos cortos): " + 
                self.mejor_config_para_carga(configuraciones, intervalos=[1], procesos=[150, 200]))
        
        self.log("\nSe han generado gráficas comparativas en la carpeta de resultados.")

    def mejor_config_para_carga(self, configuraciones, intervalos, procesos):
        """
        Determina la mejor configuración para un tipo específico de carga
        """
        conteo = defaultdict(int)
        
        for intervalo in intervalos:
            for num_procesos in procesos:
                mejor_config = None
                mejor_tiempo = float('inf')
                
                for config in configuraciones:
                    tiempo, _ = self.resultados[config['nombre']][intervalo][num_procesos]
                    if tiempo < mejor_tiempo:
                        mejor_tiempo = tiempo
                        mejor_config = config['nombre']
                
                conteo[mejor_config] += 1
        
        mejor = max(conteo.items(), key=lambda x: x[1])
        return f"{mejor[0]} ({mejor[1]}/{len(intervalos)*len(procesos)} casos)"
    
    def log(self, mensaje):
        """
        Agrega un mensaje al log
        """
        self.log_texto += mensaje + "\n"


class SistemaOperativoGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Sistema Operativo de Tiempo Compartido")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)
        
        self.simulador = SistemaOperativoSimulacion()
        self.ultimo_directorio = "resultados"
        
        # Crear los tabs
        self.tab_control = ttk.Notebook(root)
        
        # Tab para configuraciones
        self.tab_config = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_config, text='Configuración')
        
        # Tab para resultados
        self.tab_resultados = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_resultados, text='Resultados')
        
        # Tab para visualización
        self.tab_visualizacion = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tab_visualizacion, text='Visualización')
        
        self.tab_control.pack(expand=1, fill='both')
        
        # Configurar los tabs
        self.configurar_tab_config()
        self.configurar_tab_resultados()
        self.configurar_tab_visualizacion()
    
    def configurar_tab_config(self):
        # Frame para parámetros generales
        frame_general = ttk.LabelFrame(self.tab_config, text="Parámetros generales")
        frame_general.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Directorio de resultados
        ttk.Label(frame_general, text="Directorio de resultados:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.directorio_var = tk.StringVar(value="resultados")
        ttk.Entry(frame_general, textvariable=self.directorio_var, width=30).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Frame para cantidades de procesos
        frame_procesos = ttk.LabelFrame(self.tab_config, text="Cantidades de procesos")
        frame_procesos.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        self.proceso_vars = []
        default_procesos = [25, 50, 100, 150, 200]
        
        for i, proc in enumerate(default_procesos):
            var = tk.IntVar(value=proc)
            self.proceso_vars.append(var)
            ttk.Label(frame_procesos, text=f"Cantidad {i+1}:").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            ttk.Entry(frame_procesos, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=5, sticky="w")
        
        # Frame para intervalos
        frame_intervalos = ttk.LabelFrame(self.tab_config, text="Intervalos de llegada")
        frame_intervalos.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        
        self.intervalo_vars = []
        default_intervalos = [10, 5, 1]
        
        for i, intervalo in enumerate(default_intervalos):
            var = tk.IntVar(value=intervalo)
            self.intervalo_vars.append(var)
            ttk.Label(frame_intervalos, text=f"Intervalo {i+1}:").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            ttk.Entry(frame_intervalos, textvariable=var, width=10).grid(row=i, column=1, padx=5, pady=5, sticky="w")
        
        # Frame para configuraciones
        frame_configs = ttk.LabelFrame(self.tab_config, text="Configuraciones a probar")
        frame_configs.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        
        # Configuración base
        ttk.Label(frame_configs, text="Configuración base:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.config_base_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_configs, variable=self.config_base_var).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Memoria aumentada
        ttk.Label(frame_configs, text="Memoria aumentada (200):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.config_memoria_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_configs, variable=self.config_memoria_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # CPU rápido
        ttk.Label(frame_configs, text="CPU rápido (6 inst/ciclo):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.config_cpu_rapido_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_configs, variable=self.config_cpu_rapido_var).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # 2 CPUs
        ttk.Label(frame_configs, text="2 CPUs:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.config_2cpus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_configs, variable=self.config_2cpus_var).grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        # Botón para iniciar simulación
        btn_frame = ttk.Frame(self.tab_config)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        self.btn_simular = ttk.Button(btn_frame, text="Iniciar simulación", command=self.iniciar_simulacion)
        self.btn_simular.pack(pady=10)
        
        # Barra de progreso
        self.progreso_var = tk.DoubleVar()
        self.progreso = ttk.Progressbar(btn_frame, variable=self.progreso_var, maximum=100)
        self.progreso.pack(fill='x', pady=10)
        
        # Configurar grid weights
        self.tab_config.columnconfigure(0, weight=1)
        self.tab_config.columnconfigure(1, weight=1)
        self.tab_config.rowconfigure(0, weight=1)
        self.tab_config.rowconfigure(1, weight=1)
    
    def configurar_tab_resultados(self):
        # Área de texto para el log
        self.log_text = scrolledtext.ScrolledText(self.tab_resultados, wrap=tk.WORD)
        self.log_text.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Botones para limpiar y guardar el log
        btn_frame = ttk.Frame(self.tab_resultados)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(btn_frame, text="Limpiar log", command=self.limpiar_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Guardar log", command=self.guardar_log).pack(side=tk.LEFT, padx=5)
    
    def configurar_tab_visualizacion(self):
        # Frame superior para controles
        frame_controles = ttk.Frame(self.tab_visualizacion)
        frame_controles.pack(fill='x', padx=10, pady=10)
        
        # Selector de gráfica
        ttk.Label(frame_controles, text="Seleccionar gráfica:").pack(side=tk.LEFT, padx=5)
        self.grafica_var = tk.StringVar()
        self.combo_graficas = ttk.Combobox(frame_controles, textvariable=self.grafica_var, state="readonly")
        self.combo_graficas.pack(side=tk.LEFT, padx=5)
        self.combo_graficas.bind("<<ComboboxSelected>>", self.mostrar_grafica_seleccionada)
        
        # Botón para actualizar lista de gráficas
        ttk.Button(frame_controles, text="Actualizar lista", command=self.actualizar_lista_graficas).pack(side=tk.LEFT, padx=5)
        
        # Frame para la gráfica
        self.frame_grafica = ttk.Frame(self.tab_visualizacion)
        self.frame_grafica.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Etiqueta inicial
        ttk.Label(self.frame_grafica, text="Seleccione una gráfica para visualizar").pack(expand=True)
    
    def iniciar_simulacion(self):
        # Recopilar parámetros
        cantidades_procesos = [var.get() for var in self.proceso_vars]
        intervalos = [var.get() for var in self.intervalo_vars]
        directorio = self.directorio_var.get()
        
        # Preparar configuraciones
        configuraciones = []
        
        if self.config_base_var.get():
            configuraciones.append({"nombre": "Base", "memoria": 100, "cpus": 1, "velocidad": 3})
        
        if self.config_memoria_var.get():
            configuraciones.append({"nombre": "Memoria 200", "memoria": 200, "cpus": 1, "velocidad": 3})
        
        if self.config_cpu_rapido_var.get():
            configuraciones.append({"nombre": "CPU Rápido", "memoria": 100, "cpus": 1, "velocidad": 6})
        
        if self.config_2cpus_var.get():
            configuraciones.append({"nombre": "2 CPUs", "memoria": 100, "cpus": 2, "velocidad": 3})
        
        if not configuraciones:
            messagebox.showerror("Error", "Seleccione al menos una configuración")
            return
        
        # Deshabilitar botón durante la simulación
        self.btn_simular.configure(state="disabled")
        self.progreso_var.set(0)
        
        # Crear directorio si no existe
        if not os.path.exists(directorio):
            os.makedirs(directorio)
        
        self.ultimo_directorio = directorio
        
        # Ejecutar simulación en un hilo separado
        threading.Thread(target=self.ejecutar_simulacion_thread, 
                         args=(cantidades_procesos, intervalos, configuraciones, directorio)).start()
    
    def ejecutar_simulacion_thread(self, cantidades_procesos, intervalos, configuraciones, directorio):
        # Iniciar simulación
        try:
            log_resultado = self.simulador.ejecutar_experimentos(
                cantidades_procesos, intervalos, configuraciones, directorio)
            
            # Actualizar UI en el hilo principal
            self.root.after(0, self.actualizar_log, log_resultado)
            self.root.after(0, self.simulacion_completada)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en la simulación: {str(e)}"))
            self.root.after(0, self.simulacion_completada)
        
        # Actualizar el progreso periódicamente
        while self.simulador.simulacion_en_progreso:
            self.root.after(100, self.actualizar_progreso)
            time.sleep(0.1)
    
    def actualizar_progreso(self):
        # Simular progreso
        if self.simulador.simulacion_en_progreso:
            valor_actual = self.progreso_var.get()
            if valor_actual < 99:
                self.progreso_var.set(valor_actual + 0.5)
    
    def simulacion_completada(self):
        self.btn_simular.configure(state="normal")
        self.progreso_var.set(100)
        self.actualizar_lista_graficas()
        # Cambiar a la pestaña de resultados
        self.tab_control.select(1)
    
    def actualizar_log(self, texto):
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, texto)
        self.log_text.see(tk.END)
    
    def limpiar_log(self):
        self.log_text.delete(1.0, tk.END)
    
    def guardar_log(self):
        texto = self.log_text.get(1.0, tk.END)
        with open(f"{self.ultimo_directorio}/log_simulacion.txt", "w") as f:
            f.write(texto)
        messagebox.showinfo("Información", f"Log guardado en {self.ultimo_directorio}/log_simulacion.txt")
    
    def actualizar_lista_graficas(self):
        # Buscar archivos de gráficas en el directorio
        directorio = self.ultimo_directorio
        if not os.path.exists(directorio):
            return
        
        archivos = [f for f in os.listdir(directorio) if f.endswith('.png')]
        self.combo_graficas['values'] = archivos
        
        if archivos:
            self.combo_graficas.current(0)
            self.mostrar_grafica_seleccionada(None)
    
    def mostrar_grafica_seleccionada(self, event):
        # Limpiar el frame
        for widget in self.frame_grafica.winfo_children():
            widget.destroy()
        
        # Obtener la gráfica seleccionada
        grafica = self.grafica_var.get()
        if not grafica:
            return
        
        # Cargar la imagen
        ruta_completa = os.path.join(self.ultimo_directorio, grafica)
        
        # Crear figura de matplotlib
        figura = plt.figure(figsize=(10, 6))
        canvas = FigureCanvasTkAgg(figura, master=self.frame_grafica)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=1)
        
        # Mostrar la imagen en la figura
        imagen = plt.imread(ruta_completa)
        plt.imshow(imagen)
        plt.axis('off')
        canvas.draw()


if __name__ == "__main__":
    root = tk.Tk()
    app = SistemaOperativoGUI(root)
    root.mainloop()