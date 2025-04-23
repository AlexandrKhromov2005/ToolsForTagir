import os
import glob
import re
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

def process_folder(input_folder, output_folder):
    all_files = glob.glob(os.path.join(input_folder, "results_*.txt"))
    
    if not all_files:
        print(f"Файлы не найдены в {input_folder}")
        return

    aggregated = defaultdict(lambda: defaultdict(list))

    for file in all_files:
        file_data = parse_file(file)
        for attack, metrics in file_data.items():
            for metric, values in metrics.items():
                aggregated[attack][metric].extend(values)

    folder_name = os.path.basename(input_folder)
    output_file = os.path.join(output_folder, f"average_{folder_name}.txt")

    with open(output_file, 'w', encoding='utf-8') as out:
        for attack in sorted(aggregated.keys()):
            out.write(f"Attack: {attack}\n")
            for metric in ["MSE", "PSNR", "NCC", "BER", "SSIM"]:
                values = aggregated[attack].get(metric, [])
                if not values:
                    continue
                avg = [sum(col)/len(col) for col in zip(*values)]
                avg_str = " ".join(f"{x:.6f}" for x in avg)
                out.write(f"Average {metric}: {avg_str}\n")
            out.write("\n")

def main():
    base_dir = "data"
    output_dir = "results"
    
    # Создаем папку results, если ее нет
    os.makedirs(output_dir, exist_ok=True)
    
    # Получаем список всех подпапок в data
    folders = [
        d for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]
    
    if not folders:
        print("Папки для обработки не найдены в директории 'data'")
        return

    for folder in folders:
        input_folder = os.path.join(base_dir, folder)
        print(f"Обработка папки: {input_folder}")
        process_folder(input_folder, output_dir)
    
    print("\nОбработка завершена. Результаты сохранены в папку 'results'")

if __name__ == "__main__":
    main()