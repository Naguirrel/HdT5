import simpy
import random
import numpy as np
import matplotlib.pyplot as plt

def proceso(env, nombre, ram, cpu, instrucciones, tiempos):
    llegada = env.now
    memoria_requerida = random.randint(1, 10)
    
    # Solicitar memoria
    yield ram.get(memoria_requerida)
    
    # Pasa a Ready
    while instrucciones > 0:
        with cpu.request() as req:
            yield req
            yield env.timeout(1)  # Unidad de tiempo del CPU
            instrucciones -= min(3, instrucciones)
            
            if instrucciones > 0 and random.randint(1, 21) == 1:
                yield env.timeout(3)  # Simula operación de I/O
    
    # Regresar memoria
    yield ram.put(memoria_requerida)
    tiempos.append(env.now - llegada)

def correr_simulacion(num_procesos, intervalo):
    random.seed(42)
    env = simpy.Environment()
    ram = simpy.Container(env, init=100, capacity=100)
    cpu = simpy.Resource(env, capacity=1)
    tiempos = []
    
    def generar_procesos():
        for i in range(num_procesos):
            env.process(proceso(env, f'Proceso-{i}', ram, cpu, random.randint(1, 10), tiempos))
            yield env.timeout(random.expovariate(1.0 / intervalo))
    
    env.process(generar_procesos())
    env.run()
    return (np.mean(tiempos) if tiempos else 0, np.std(tiempos) if tiempos else 0)

def ejecutar_pruebas():
    procesos = [25, 50, 100, 150, 200]
    intervalos = [10, 5, 1]
    resultados = {}
    
    for intervalo in intervalos:
        tiempos_medios = []
        desviaciones = []
        for num in procesos:
            resultado = correr_simulacion(num, intervalo)
            if isinstance(resultado, tuple) and len(resultado) == 2:
                promedio, desviacion = resultado
            else:
                promedio, desviacion = 0, 0
            tiempos_medios.append(promedio)
            desviaciones.append(desviacion)
        resultados[intervalo] = (procesos, tiempos_medios, desviaciones)
        
        # Graficar resultados
        plt.plot(procesos, tiempos_medios, marker='o', label=f'Intervalo {intervalo}')
    
    plt.xlabel('Número de procesos')
    plt.ylabel('Tiempo promedio en sistema')
    plt.title('Tiempo promedio vs Número de procesos')
    plt.legend()
    plt.grid()
    plt.show()
    return resultados

ejecutar_pruebas()