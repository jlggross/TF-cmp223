#!/bin/bash

# Cabeçalho da tabela
printf "%-6s %-15s %-15s %-15s %-15s %-15s %-15s\n" "CPU" "base_freq(kHz)" "cpu_info_max" "cpu_info_min" "scaling_max" "scaling_min" "governor/driver"

# Loop por núcleos de 0 a 27
for i in $(seq 0 27); do
    cpu="/sys/devices/system/cpu/cpu$i"

    # Verifica se o diretório existe
    [[ ! -d $cpu ]] && continue

    # Arquivos de interesse
    base_freq_file="$cpu/cpufreq/base_frequency"
    info_max_file="$cpu/cpufreq/cpuinfo_max_freq"
    info_min_file="$cpu/cpufreq/cpuinfo_min_freq"
    scaling_max_file="$cpu/cpufreq/scaling_max_freq"
    scaling_min_file="$cpu/cpufreq/scaling_min_freq"
    driver_file="$cpu/cpufreq/scaling_driver"
    governor_file="$cpu/cpufreq/scaling_governor"

    # Ler conteúdo (verifica se o arquivo existe)
    base_freq=$( [[ -f $base_freq_file ]] && cat $base_freq_file || echo "N/A" )
    info_max=$( [[ -f $info_max_file ]] && cat $info_max_file || echo "N/A" )
    info_min=$( [[ -f $info_min_file ]] && cat $info_min_file || echo "N/A" )
    scaling_max=$( [[ -f $scaling_max_file ]] && cat $scaling_max_file || echo "N/A" )
    scaling_min=$( [[ -f $scaling_min_file ]] && cat $scaling_min_file || echo "N/A" )
    driver=$( [[ -f $driver_file ]] && cat $driver_file || echo "N/A" )
    governor=$( [[ -f $governor_file ]] && cat $governor_file || echo "N/A" )

    # Imprimir linha da tabela
    printf "%-6s %-15s %-15s %-15s %-15s %-15s %-7s / %-7s\n" \
        "$i" "$base_freq" "$info_max" "$info_min" "$scaling_max" "$scaling_min" "$governor" "$driver"
done

