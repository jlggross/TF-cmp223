import concurrent.futures
import os
import sys
import time
import getpass
import numpy as np
import pandas as pd
from datetime import datetime

# --------------------------------------
# CONFIGURATION

# Threads de baixo nível em 1 para que o Python (ou BLAS) 
# não tente paralelizar internamente, a aplicação controla o paralelismo.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

MATRIX_SIZE = 2000  # size of NxN matrices

CPU_SETS = {
    "1-T": [0],
    "2-T": [0, 2],
    "2-T-HP": [0, 1],
    "4-T": [0, 2, 4, 6],
    "4-T-HP": [0, 1, 2, 3],
    "8-T": [0, 2, 4, 6, 8, 10, 12, 14],
    "8-T-HP": [0, 1, 2, 3, 4, 5, 6, 7],    
}

NUM_RUNS = 2   # runs per CPU set
GOVERNOR = "performance"
IDLE_TIME = 1  # segundos entre execuções

# Variáveis globais (matrizes)
# Em threading, elas são compartilhadas nativamente (Shared Memory)
A_global = None
B_global = None

# --------------------------------------
# Safety check
def safety_check(cpu_ids):
    if MATRIX_SIZE % len(cpu_ids) != 0:
        print(f"Error: MATRIX_SIZE ({MATRIX_SIZE}) is not divisible by number of workers ({len(cpu_ids)}).")
        sys.exit(1)

# --------------------------------------
# Governor configuration (Mantido igual, pois é comando de SO)
def set_governor(governor: str):
    password = getpass.getpass("Sudo password: ")
    bash_command = f"""
    for cpu_file in $(ls -v /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor); do
        cpu_name=$(basename $(dirname $(dirname $cpu_file)))
        echo "{governor}" | sudo tee $cpu_file > /dev/null
        current_gov=$(cat $cpu_file)
        echo "$cpu_name: $current_gov"
    done
    """
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

# --------------------------------------
# Worker task (Threading Version)
def worker_thread_task(args):
    row_index, chunk_size, cpu_ids = args
    
    # Identifica qual worker "lógico" é este com base na linha
    worker_id = row_index // chunk_size
    target_cpu = cpu_ids[worker_id]
    
    # --- DEFINIR AFINIDADE DA THREAD ---
    # No Linux, os.sched_setaffinity(0, ...) aplica-se à thread chamadora (LWP)
    # Isso garante que esta thread Python rode APENAS no núcleo especificado.
    try:
        os.sched_setaffinity(0, {target_cpu})
    except Exception as e:
        print(f"Erro ao definir afinidade na thread para CPU {target_cpu}: {e}")

    # Acesso direto à memória compartilhada (Zero Copy)
    start_row = row_index
    end_row = row_index + chunk_size
    
    # Slicing em numpy cria uma "view", não copia dados, o que é muito eficiente
    A_chunk = A_global[start_row:end_row, :]
    
    # Cálculo
    # Nota: Ao usar Python 3.14, np.dot libera o GIL internamente 
    # permitindo paralelismo real mesmo em Python < 3.13.
    return np.dot(A_chunk, B_global)

# --------------------------------------
# Main execution loop
if __name__ == "__main__":
    
    # Verificação de versão apenas informativa
    print(f"Executando em Python {sys.version}")
    # Em Python 3.14 experimental, podemos verificar se o GIL está desabilitado:
    try:
        # sys._is_gil_enabled() é esperado nas builds 3.13+/3.14 free-threaded
        gil_status = sys._is_gil_enabled() 
        print(f"GIL Ativo: {gil_status}")
    except AttributeError:
        print("Status do GIL: Desconhecido (API sys._is_gil_enabled não encontrada)")

    print("Passo 1: Configurar governor")
    set_governor(GOVERNOR)
    
    results = [] 
    
    # Inicializa as matrizes globais
    # Em threading, não precisamos nos preocupar com fork/spawn, apenas alocamos.
    print("Alocando matrizes...")
    A_global = np.random.rand(MATRIX_SIZE, MATRIX_SIZE).astype(np.float64)
    B_global = np.random.rand(MATRIX_SIZE, MATRIX_SIZE).astype(np.float64)
    
    print("Passo 2: Execuções (Threading Mode)")
    for run in range(1, NUM_RUNS + 1):        
        for label, cores in CPU_SETS.items():
            safety_check(cores)
            
            governor = get_governor(cores[0])
            chunk_size = MATRIX_SIZE // len(cores)
            
            # Tarefas
            tasks = [(i*chunk_size, chunk_size, cores) for i in range(len(cores))]

            start_time = time.time()
            
            # ThreadPoolExecutor substitui mp.Pool
            # max_workers=len(cores) cria exatamente uma thread por núcleo desejado
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(cores)) as executor:
                # executor.map funciona similar ao pool.map, mantendo a ordem
                C_chunks = list(executor.map(worker_thread_task, tasks))
            
            # Combinação de resultados
            C = np.vstack(C_chunks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            results.append({
                "Run": run,
                "Scenario": label,
                "CPUs_used": cores,
                "Governor": governor,
                "Time_sec": total_time,
                "Result_shape": C.shape
            })
            
            print(f"Run {run} | {label}: {cores} | Governor: {governor} | Time: {total_time:.4f}s")

            print(f"Aguardando {IDLE_TIME} segundos...\n")
            time.sleep(IDLE_TIME)
            
    df_results = pd.DataFrame(results)
    pd.set_option('display.width', 1000)
    df_reduced = df_results[["Run", "Scenario", "Governor", "Time_sec"]]
    df_sorted = df_reduced.sort_values(by="Scenario", ascending=False)
    print("\nResumo em DataFrame:\n", df_sorted)
    
    now = datetime.now()
    filename = (
    f"{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}_THREADING_"
    f"matrix{MATRIX_SIZE}_numruns{NUM_RUNS}_{GOVERNOR}.csv"
    )
    df_results.to_csv(filename, index=False)
    print(f"\nResultados salvos em: {filename}")
