import os
import glob
import re
import pandas as pd
from collections import defaultdict

def parse_file(file_path):
    data = defaultdict(list)
    current_attack = None
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith("Attack:"):
                current_attack = line.split(": ")[1]
                data[current_attack] = defaultdict(list)
            elif line.startswith("Average "):
                metric = re.match(r"Average (\w+):", line).group(1)
                values = list(map(float, re.findall(r"\d+\.\d+", line)))
                data[current_attack][metric].append(values)
    return data

def process_folder_averages(input_folder):
    all_files = glob.glob(os.path.join(input_folder, "results_*.txt"))
    aggregated = defaultdict(lambda: defaultdict(list))
    attack_order = []  # Сохраняем порядок атак
    
    for file in all_files:
        file_data = parse_file(file)
        for attack, metrics in file_data.items():
            if attack not in attack_order:  # Сохраняем порядок появления атак
                attack_order.append(attack)
            for metric, values in metrics.items():
                aggregated[attack][metric].extend(values)
    
    return aggregated, attack_order

def collect_all_attacks(base_dir):
    all_attacks = set()
    folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    
    for folder in folders:
        input_folder = os.path.join(base_dir, folder)
        all_files = glob.glob(os.path.join(input_folder, "results_*.txt"))
        
        for file in all_files:
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith("Attack:"):
                        attack = line.split(": ")[1].strip()
                        all_attacks.add(attack)
    
    return sorted(all_attacks)

def calculate_metric_average(values):
    if not values:
        return None
    flat_values = [num for sublist in values for num in sublist]
    return sum(flat_values) / len(flat_values)

def generate_report(base_dir, attack_name, output_file):
    folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    report_data_no_attack = []
    report_data_selected_attack = []

    for folder in folders:
        input_folder = os.path.join(base_dir, folder)
        data, _ = process_folder_averages(input_folder)
        
        # Для таблицы без атак
        no_attack_psnr = calculate_metric_average(data.get("No attack", {}).get("PSNR", []))
        no_attack_ber = calculate_metric_average(data.get("No attack", {}).get("BER", []))
        report_data_no_attack.append({
            'Folder': folder,
            'PSNR': no_attack_psnr,
            'BER': no_attack_ber
        })
        
        # Для таблицы с выбранной атакой
        attack_psnr = calculate_metric_average(data.get(attack_name, {}).get("PSNR", []))
        attack_ber = calculate_metric_average(data.get(attack_name, {}).get("BER", []))
        report_data_selected_attack.append({
            'Folder': folder,
            'PSNR': attack_psnr,
            'BER': attack_ber
        })
    
    # Создаем DataFrame
    df_no_attack = pd.DataFrame(report_data_no_attack)
    df_attack = pd.DataFrame(report_data_selected_attack)
    
    # Сохраняем в Excel
    with pd.ExcelWriter(output_file) as writer:
        df_no_attack.to_excel(writer, sheet_name='No Attack', index=False)
        df_attack.to_excel(writer, sheet_name=attack_name, index=False)

def main_menu():
    print("Select operating mode:")
    print("1 - Calculating average values ​​by folders")
    print("2 - Generating Attack Reports")
    choice = input("Enter the number of the selected mode: ")
    
    base_dir = "data"
    output_dir = "results"
    os.makedirs(output_dir, exist_ok=True)
    
    if choice == '1':
        # Режим 1: существующая функциональность
        folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
        
        for folder in folders:
            input_folder = os.path.join(base_dir, folder)
            output_file = os.path.join(output_dir, f"average_{folder}.txt")
            aggregated, attack_order = process_folder_averages(input_folder)
            
            with open(output_file, 'w', encoding='utf-8') as out:
                for attack in attack_order:  # Используем сохраненный порядок атак
                    out.write(f"Attack: {attack}\n")
                    metrics = ["MSE", "PSNR", "NCC", "BER", "SSIM"]
                    for metric in metrics:
                        values = aggregated[attack].get(metric, [])
                        if not values:
                            # Если метрика отсутствует, записываем это в файл
                            out.write(f"Average {metric}: N/A\n")
                            continue
                        avg = [sum(col)/len(col) for col in zip(*values)]
                        avg_str = " ".join(f"{x:.6f}" for x in avg)
                        out.write(f"Average {metric}: {avg_str}\n")
                    out.write("\n")
        
        print("Mode 1: Average calculation completed")
    
    elif choice == '2':
        # Режим 2: генерация отчетов по атакам
        all_attacks = collect_all_attacks(base_dir)
        
        print("\nAvailable attacks:")
        for i, attack in enumerate(all_attacks, 1):
            print(f"{i}. {attack}")
        
        try:
            selection = int(input("\nEnter attack number: ")) - 1
            selected_attack = all_attacks[selection]
        except (ValueError, IndexError):
            print("Error: Invalid attack number entered")
            return
        
        output_file = os.path.join(output_dir, f"attack_report_{selected_attack}.xlsx")
        generate_report(base_dir, selected_attack, output_file)
        print(f"\nThe report is saved to file: {output_file}")
    
    else:
        print("Error: Incorrect mode selection")

if __name__ == "__main__":
    main_menu()