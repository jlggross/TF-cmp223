
import multiprocessing as mp
import psutil
import getpass
import os
import sys
import time
import numpy as np
import pandas as pd
from datetime import datetime

# --------------------------------------
# CONFIGURATION

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

MATRIX_SIZE = 1000  # size of NxN matrices
CPU_SETS = {
    "p-cores 1 thread": [0, 2, 4, 6, 8, 10, 12, 14], # p-cores (8 cores, 1 thread per core)
    "p-cores 2 threads": [0, 1, 2, 3, 4, 5, 6, 7], # p-cores (4 cores, 2 threads per core)
    "p-cores & e-cores 50-50": [0, 2, 4, 6, 16, 17, 18, 19], # p-cores e e-cores (4 cores p-core, 4 cores e-core)
    "e-cores": [16, 17, 18, 19, 20, 21, 22, 23] # e-cores (8 cores, 1 thread per core)
}
NUM_RUNS = 5   # runs per CPU set
GOVERNOR = "performance"
IDLE_TIME = 1  # segundos entre execuções

# Variáveis globais (matrizes) para serem herdadas pelos workers
A_global = None
B_global = None

# --------------------------------------
# Safety check
def safety_check(cpu_ids):
    if MATRIX_SIZE % len(cpu_ids) != 0:
        print(f"Error: MATRIX_SIZE ({MATRIX_SIZE}) is not divisible by number of workers ({len(cpu_ids)}).")
        sys.exit(1)

# --------------------------------------
# Governor configuration
def set_governor(governor: str):
    """
    Altera o CPU governor de todos os núcleos para o valor especificado.

    Parâmetros:
        governor (str): nome do governor (ex.: "performance", "powersave", "schedutil").
    """
    password = getpass.getpass("Sudo password: ")

    # Interpolamos o valor do parâmetro governor dirTempetamente no comando bash
    bash_command = f"""
    for cpu_file in $(ls -v /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor); do
        cpu_name=$(basename $(dirname $(dirname $cpu_file)))

        echo "{governor}" | sudo tee $cpu_file > /dev/null

        current_gov=$(cat $cpu_file)
        echo "$cpu_name: $current_gov"
    done
    """

    # Usa sudo -S para aceitar senha via stdin
    command = f'echo "{password}" | sudo -S bash -c \'{bash_command}\''
    os.system(command)    

# --------------------------------------
# Governor detection
def get_governor(cpu_id):
    path = f"/sys/devices/system/cpu/cpu{cpu_id}/cpufreq/scaling_governor"
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "N/A"

# Worker task: Acessa as matrizes globais
def worker_task_global(args):
    row_index, chunk_size, cpu_ids = args
    worker_id = row_index // chunk_size # Calcula um ID simples para o worker

    # Define a afinidade
    p = psutil.Process(os.getpid())
    p.cpu_affinity([cpu_ids[worker_id]])

    # Pega o chunk da matriz A global
    start_row = row_index
    end_row = row_index + chunk_size
    A_chunk = A_global[start_row:end_row, :]

    # Calcula usando a matriz B global (que foi herdada, não copiada)
    return np.dot(A_chunk, B_global)

# --------------------------------------
# Main execution loop
if __name__ == "__main__":

    print("Passo 1: Configurar governor")
    set_governor(GOVERNOR)

    results = []  # lista para armazenar resultados      

    print("Passo 2: Execuções")
    for run in range(1, NUM_RUNS + 1):        
        for label, cores in CPU_SETS.items():
            # Garantir que o workload será dividido igualmente
            safety_check(cores)

            # Garantir que o governor está correto
            governor = get_governor(cores[0])

            # Inicializa as matrizes globais
            A_global = np.random.rand(MATRIX_SIZE, MATRIX_SIZE).astype(np.float64)
            B_global = np.random.rand(MATRIX_SIZE, MATRIX_SIZE).astype(np.float64)

            # Split A into chunks by rows
            chunk_size = MATRIX_SIZE // len(cores)

            # Tarefas agora contêm apenas índices, muito leves
            tasks = [(i*chunk_size, chunk_size, cores) for i in range(len(cores))]

            start_time = time.time()

            # Criação do pool. Matrizes herdadas por fork()
            with mp.Pool(processes=len(cores)) as pool:
                C_chunks = pool.map(worker_task_global, tasks)

            # Combinação de resultados
            C = np.vstack(C_chunks)

            end_time = time.time()
            total_time = end_time - start_time

            # salva os dados em um dataFrame
            results.append({
                "Run": run,
                "Scenario": label,
                "CPUs_used": cores,
                "Governor": governor,
                "Time_sec": total_time,
                "Result_shape": C.shape
            })

            print(f"Run {run} | {label}: {cores} | Governor: {governor} | Time: {total_time}")

            # Idle para estabilizar
            print(f"Aguardando {IDLE_TIME} segundos para estabilização...\n")
            time.sleep(IDLE_TIME)

    # cria dataframe com todos os resultados
    df_results = pd.DataFrame(results)
    pd.set_option('display.width', 1000) # Evita quebra de linha do print do df  
    df_reduced = df_results[["Run", "Scenario", "Governor", "Time_sec"]]
    df_sorted = df_reduced.sort_values(by="Scenario", ascending=False)
    print("\nResumo em DataFrame:\n", df_sorted)

    # salvar em CSV
    now = datetime.now()
    data_str = now.strftime("%Y%m%d") # formato aaaammdd
    hora_str = now.strftime("%H%M%S") # formato hhmmss
    filename = (
    f"{data_str}_{hora_str}_matrix{MATRIX_SIZE}_"
        f"numruns{NUM_RUNS}_{GOVERNOR}.csv"
    )
    df_results.to_csv(filename, index=False)
    print(f"\nResultados salvos em: {filename}")           

