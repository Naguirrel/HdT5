import simpy
import random
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

# Constantes para la simulación
RANDOM_SEED = 42
MAX_MEMORIA_PROCESO = 10
MIN_MEMORIA_PROCESO = 1
MAX_INSTRUCCIONES = 10
MIN_INSTRUCCIONES = 1
INSTRUCCIONES_POR_CICLO = 3  # Instrucciones que ejecuta el CPU por unidad de tiempo

# Lista para almacenar los tiempos de ejecución de cada proceso
tiempos_ejecucion = []

def proceso(env, nombre, RAM, CPU, intervalo_llegada, memoria_total, num_cpus, velocidad_cpu):
    # Simular el tiempo de llegada del proceso
    yield env.timeout(random.expovariate(1.0 / intervalo_llegada))
    tiempo_llegada = env.now
    
    # Estado NEW: solicitar memoria
    memoria_requerida = random.randint(MIN_MEMORIA_PROCESO, MAX_MEMORIA_PROCESO)
    instrucciones_totales = random.randint(MIN_INSTRUCCIONES, MAX_INSTRUCCIONES)
    
    print(f'{nombre} llega en t={tiempo_llegada:.2f}, requiere {memoria_requerida} de memoria y {instrucciones_totales} instrucciones')
    
    # Esperar hasta que haya suficiente memoria disponible
    yield RAM.get(memoria_requerida)
    print(f'{nombre} obtuvo {memoria_requerida} de memoria en t={env.now:.2f}, pasa a READY')
    
    # Ciclo principal del proceso hasta que termine sus instrucciones
    while instrucciones_totales > 0:
        # Estado READY: esperar por el CPU
        with CPU.request() as req:
            yield req
            print(f'{nombre} obtuvo CPU en t={env.now:.2f}, pasa a RUNNING')
            
            # Estado RUNNING: ejecutar instrucciones
            instrucciones_ejecutadas = min(velocidad_cpu, instrucciones_totales)
            yield env.timeout(1)  # Unidad de tiempo para ejecutar instrucciones
            instrucciones_totales -= instrucciones_ejecutadas
            
            print(f'{nombre} ejecutó {instrucciones_ejecutadas} instrucciones, quedan {instrucciones_totales}')
            
            # Determinar el siguiente estado
            if instrucciones_totales <= 0:
                # Estado TERMINATED
                print(f'{nombre} ha terminado en t={env.now:.2f}, libera {memoria_requerida} de memoria')
                RAM.put(memoria_requerida)
                tiempo_total = env.now - tiempo_llegada
                tiempos_ejecucion.append(tiempo_total)
                print(f'{nombre} tiempo total en el sistema: {tiempo_total:.2f}')
                break
            else:
                # Decidir si va a WAITING o vuelve a READY
                decision = random.randint(1, 21)
                if decision == 1:
                    # Estado WAITING (I/O)
                    print(f'{nombre} pasa a WAITING para I/O en t={env.now:.2f}')
                    tiempo_io = random.uniform(1, 3)  # Tiempo aleatorio para operaciones I/O
                    yield env.timeout(tiempo_io)
                    print(f'{nombre} termina I/O en t={env.now:.2f}, vuelve a READY')
                else:
                    # Volver a READY
                    print(f'{nombre} vuelve a READY en t={env.now:.2f}')

def ejecutar_simulacion(num_procesos, intervalo_llegada, memoria_total=100, num_cpus=1, velocidad_cpu=3, verbose=False):
    """
    Ejecuta la simulación con los parámetros especificados
    """
    # Reiniciar la lista de tiempos
    global tiempos_ejecucion
    tiempos_ejecucion = []
    
    # Configurar el entorno
    env = simpy.Environment()
    random.seed(RANDOM_SEED)
    
    # Recursos
    RAM = simpy.Container(env, init=memoria_total, capacity=memoria_total)
    CPU = simpy.Resource(env, capacity=num_cpus)
    
    # Crear procesos
    for i in range(num_procesos):
        env.process(proceso(env, f'Proceso {i}', RAM, CPU, intervalo_llegada, memoria_total, num_cpus, velocidad_cpu))
    
    # Ejecutar la simulación
    if verbose:
        print(f"\n--- Iniciando simulación con {num_procesos} procesos, intervalo {intervalo_llegada}, "
              f"memoria {memoria_total}, {num_cpus} CPU(s), velocidad {velocidad_cpu} ---\n")
    
    env.run()
    
    # Calcular estadísticas
    tiempo_promedio = np.mean(tiempos_ejecucion)
    desviacion_std = np.std(tiempos_ejecucion)
    
    if verbose:
        print(f"\n--- Resultados de la simulación ---")
        print(f"Tiempo promedio de ejecución: {tiempo_promedio:.2f}")
        print(f"Desviación estándar: {desviacion_std:.2f}")
    
    return tiempo_promedio, desviacion_std

def ejecutar_experimentos():
    """
    Ejecuta todos los experimentos requeridos y genera gráficas
    """
    cantidades_procesos = [25, 50, 100, 150, 200]
    intervalos = [10, 5, 1]
    
    # Configuraciones a probar
    configuraciones = [
        {"nombre": "Base", "memoria": 100, "cpus": 1, "velocidad": 3},
        {"nombre": "Memoria 200", "memoria": 200, "cpus": 1, "velocidad": 3},
        {"nombre": "CPU Rápido", "memoria": 100, "cpus": 1, "velocidad": 6},
        {"nombre": "2 CPUs", "memoria": 100, "cpus": 2, "velocidad": 3}
    ]
    
    resultados = defaultdict(lambda: defaultdict(dict))
    
    # Ejecutar todas las simulaciones
    for config in configuraciones:
        print(f"\n=== Configuración: {config['nombre']} ===")
        
        for intervalo in intervalos:
            print(f"\n== Intervalo de llegada: {intervalo} ==")
            tiempos_promedio = []
            desviaciones = []
            
            for num_procesos in cantidades_procesos:
                tiempo_promedio, desviacion = ejecutar_simulacion(
                    num_procesos=num_procesos,
                    intervalo_llegada=intervalo,
                    memoria_total=config['memoria'],
                    num_cpus=config['cpus'],
                    velocidad_cpu=config['velocidad'],
                    verbose=True
                )
                
                tiempos_promedio.append(tiempo_promedio)
                desviaciones.append(desviacion)
                resultados[config['nombre']][intervalo][num_procesos] = (tiempo_promedio, desviacion)
                
                print(f"Procesos: {num_procesos}, Tiempo promedio: {tiempo_promedio:.2f}, Desviación: {desviacion:.2f}")
            
            # Graficar resultados para esta configuración y este intervalo
            plt.figure(figsize=(10, 6))
            plt.errorbar(cantidades_procesos, tiempos_promedio, yerr=desviaciones, marker='o', capsize=5)
            plt.title(f'Tiempo promedio de ejecución - {config["nombre"]} (Intervalo: {intervalo})')
            plt.xlabel('Número de procesos')
            plt.ylabel('Tiempo promedio (unidades)')
            plt.grid(True)
            plt.savefig(f'resultado_{config["nombre"].replace(" ", "_")}_{intervalo}.png')
            plt.close()
    
    # Graficar comparativas para cada intervalo
    for intervalo in intervalos:
        plt.figure(figsize=(12, 8))
        
        for config in configuraciones:
            tiempos = [resultados[config['nombre']][intervalo][n][0] for n in cantidades_procesos]
            plt.plot(cantidades_procesos, tiempos, marker='o', label=config['nombre'])
            
        plt.title(f'Comparativa de configuraciones (Intervalo: {intervalo})')
        plt.xlabel('Número de procesos')
        plt.ylabel('Tiempo promedio (unidades)')
        plt.legend()
        plt.grid(True)
        plt.savefig(f'comparativa_intervalo_{intervalo}.png')
        plt.close()
    
    # Generar tabla comparativa
    print("\n=== Tabla Comparativa de Resultados ===")
    print("Configuración | Intervalo | 25 Proc. | 50 Proc. | 100 Proc. | 150 Proc. | 200 Proc.")
    print("-------------|-----------|----------|----------|-----------|-----------|----------")
    
    for config in configuraciones:
        for intervalo in intervalos:
            row = f"{config['nombre']:12} | {intervalo:9} | "
            for num_procesos in cantidades_procesos:
                tiempo, _ = resultados[config['nombre']][intervalo][num_procesos]
                row += f"{tiempo:8.2f} | "
            print(row)
    
    # Realizar análisis de resultados
    analizar_resultados(resultados, cantidades_procesos, intervalos, configuraciones)

def analizar_resultados(resultados, cantidades_procesos, intervalos, configuraciones):
    """
    Analiza los resultados y determina la mejor estrategia
    """
    # Encontrar la mejor configuración para cada carga de trabajo
    print("\n=== Análisis de Resultados ===")
    
    for intervalo in intervalos:
        print(f"\nIntervalo de llegada: {intervalo}")
        
        for num_procesos in cantidades_procesos:
            mejor_config = None
            mejor_tiempo = float('inf')
            
            for config in configuraciones:
                tiempo, _ = resultados[config['nombre']][intervalo][num_procesos]
                if tiempo < mejor_tiempo:
                    mejor_tiempo = tiempo
                    mejor_config = config['nombre']
            
            print(f"Para {num_procesos} procesos, la mejor configuración es: {mejor_config} (Tiempo: {mejor_tiempo:.2f})")
    
    # Análisis general
    print("\n=== Conclusión General ===")
    print("Basado en los resultados de las simulaciones, podemos concluir que:")
    
    # Analizar tendencias y determinar la mejor estrategia general
    # (El análisis específico se completará después de ejecutar las simulaciones)
    print("Se recomienda revisar las gráficas generadas para un análisis visual de los resultados.")

# Ejecutar todos los experimentos
if __name__ == "__main__":
    ejecutar_experimentos()