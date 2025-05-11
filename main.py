import os
import glob
import re
import pandas as pd
from collections import defaultdict
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

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

def generate_report(base_dir, attack_names, output_file):
    folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    reports_data = {attack: [] for attack in attack_names}
    report_data_no_attack = []

    for folder in folders:
        input_folder = os.path.join(base_dir, folder)
        data, _ = process_folder_averages(input_folder)
        
        # Для таблицы без атак (всегда добавляем)
        no_attack_psnr = calculate_metric_average(data.get("No attack", {}).get("PSNR", []))
        no_attack_ber = calculate_metric_average(data.get("No attack", {}).get("BER", []))
        report_data_no_attack.append({
            'Folder': folder,
            'PSNR': no_attack_psnr,
            'BER': no_attack_ber
        })
        
        # Для каждой выбранной атаки
        for attack_name in attack_names:
            attack_psnr = calculate_metric_average(data.get(attack_name, {}).get("PSNR", []))
            attack_ber = calculate_metric_average(data.get(attack_name, {}).get("BER", []))
            reports_data[attack_name].append({
                'Folder': folder,
                'PSNR': attack_psnr,
                'BER': attack_ber
            })
    
    # Сохраняем в Excel
    with pd.ExcelWriter(output_file) as writer:
        # Сначала записываем No attack
        df_no_attack = pd.DataFrame(report_data_no_attack)
        df_no_attack.to_excel(writer, sheet_name='No Attack', index=False)
        
        # Затем все выбранные атаки
        for attack_name in attack_names:
            df_attack = pd.DataFrame(reports_data[attack_name])
            df_attack.to_excel(writer, sheet_name=attack_name, index=False)

def show_attack_selector(all_attacks, base_dir, output_dir):
    # Создаем основное окно
    root = tk.Tk()
    root.title("Select Attacks")
    root.geometry("400x600")  # Увеличиваем высоту окна
    
    # Создаем основной фрейм
    main_frame = ttk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)
    
    # Заголовок
    ttk.Label(main_frame, text="Select attacks to include in the report:", 
              font=('Helvetica', 10, 'bold')).pack(pady=10)
    
    # Создаем фрейм для прокручиваемого содержимого
    scroll_frame = ttk.Frame(main_frame)
    scroll_frame.pack(fill=tk.BOTH, expand=1)
    
    # Создаем холст с полосой прокрутки
    canvas = tk.Canvas(scroll_frame)
    scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
    
    # Создаем фрейм внутри холста для чекбоксов
    checkbox_frame = ttk.Frame(canvas)
    
    # Настраиваем прокрутку
    checkbox_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    # Размещаем элементы прокрутки
    canvas.create_window((0, 0), window=checkbox_frame, anchor="nw", width=canvas.winfo_reqwidth())
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Размещаем холст и полосу прокрутки
    canvas.pack(side="left", fill=tk.BOTH, expand=1)
    scrollbar.pack(side="right", fill="y")
    
    # Настраиваем прокрутку колесиком мыши
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    # Переменные для хранения состояния чекбоксов
    var_dict = {}
    
    # Создаем чекбоксы для каждой атаки
    for attack in all_attacks:
        var = tk.BooleanVar()
        var_dict[attack] = var
        ttk.Checkbutton(checkbox_frame, text=attack, variable=var).pack(anchor='w', padx=20, pady=2)
    
    def process_selection():
        selected_attacks = [attack for attack, var in var_dict.items() if var.get()]
        if not selected_attacks:
            messagebox.showwarning("Warning", "Please select at least one attack!")
            return
            
        output_file = os.path.join(output_dir, f"attack_report_multiple.xlsx")
        generate_report(base_dir, selected_attacks, output_file)
        messagebox.showinfo("Success", f"Report saved to: {output_file}")
        root.destroy()
    
    def select_all():
        for var in var_dict.values():
            var.set(True)
    
    def deselect_all():
        for var in var_dict.values():
            var.set(False)
    
    # Создаем нижний фрейм для кнопок (вне области прокрутки)
    bottom_frame = ttk.Frame(main_frame)
    bottom_frame.pack(fill=tk.X, pady=10)
    
    # Кнопки управления
    button_frame = ttk.Frame(bottom_frame)
    button_frame.pack()
    
    ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Deselect All", command=deselect_all).pack(side=tk.LEFT, padx=5)
    
    # Кнопка генерации отчета
    ttk.Button(main_frame, text="Generate Report", 
              command=process_selection).pack(pady=10)
    
    # Запускаем главный цикл
    root.mainloop()

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
        # Режим 2: генерация отчетов по атакам через GUI
        all_attacks = collect_all_attacks(base_dir)
        show_attack_selector(all_attacks, base_dir, output_dir)
    
    else:
        print("Error: Incorrect mode selection")

if __name__ == "__main__":
    main_menu()