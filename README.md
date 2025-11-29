# Análise de Multiplicação de Matrizes em Arquiteturas Híbridas (P‑Cores / E‑Cores)

Este repositório contém o código‑fonte, scripts, dados e documentação
utilizados no estudo que avalia o desempenho computacional e o impacto
térmico de diferentes estratégias de paralelismo em Python --- numa CPU
híbrida com P‑Cores e E‑Cores. A multiplicação de matrizes é usada como
carga de trabalho CPU‑bound para comparar abordagens de paralelismo sob
distintas configurações de afinidade de CPU.

## Descrição do Projeto

O objetivo deste trabalho é investigar como a heterogeneidade de
hardware (núcleos "P" e "E") afeta o desempenho e a temperatura da CPU
para workloads intensivos em CPU, em diferentes estratégias de
paralelismo em Python:

-   **Multiprocessing** (Python 3.12) --- criação de processos filhos,
    usando Copy‑on‑Write (CoW).
-   **Dask** (Python 3.12) --- particionamento em blocos e escalonamento
    dinâmico de tarefas.
-   **Free‑Threading / Threading** (Python 3.14) --- paralelismo via
    threads após remoção do GIL, com memória compartilhada (Zero Copy).

O estudo analisa execução de multiplicação de matrizes de tamanhos
variados, sob diferentes cenários de afinidade de CPU (somente P‑Cores,
mistura de P + E, somente E, com e sem Hyper‑Threading), medindo tempo
de execução, eficiência e comportamento térmico.

## Principais Resultados

-   A estratégia com threads (Python 3.14, free‑threading) obteve os
    **menores tempos de execução em praticamente todos os cenários e
    tamanhos de matriz**, além de evidenciar **temperatura média
    significativamente menor** durante a execução intensiva.
-   O uso indiscriminado de E‑Cores em tarefas CPU‑bound pode se tornar
    um **gargalo de desempenho**, especialmente quando a divisão de
    trabalho não considera topologia da CPU.
-   O uso de escalonamento dinâmico (Dask) mitiga parte desse problema,
    priorizando núcleos mais potentes (P‑Cores) sempre que possível.
-   A topologia de CPU e a afinidade de núcleo são fatores determinantes
    para performance e eficiência térmica em workloads paralelos
    intensivos.

## Pré‑requisitos

-   Python 3.12 (multiprocessing e Dask) ou Python 3.14 com
    free‑threading.
-   numpy, dask, psutil, matplotlib.
-   Linux com suporte para *taskset* (opcional, recomendado).
-   Configuração adequada das variáveis de controle de paralelismo de
    bibliotecas BLAS/LAPACK.

## Reprodutibilidade

Para instalar a pilha de software basta executar os comandos:

	pip install -r requirements_py3.12.txt
	pip install -r requirements_py3.14t.txt
	sudo xargs apt-get install -y < system_packages.tx

## Autor

João Luiz Grave Gross\
Analista de Infraestrutura de TI\
Doutorando em Ciência da Computação
