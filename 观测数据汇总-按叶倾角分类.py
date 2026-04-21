import pandas as pd
import os
import re
from pathlib import Path

# ================= 配置区域 =================

# 1. 设置根目录 (现在是 result2 这一级)
base_result_dir = r"E:\LESS-project\Artical-retry\complex sence\Clumping\Random\result"

# 2. 定义你要处理的子文件夹名称列表
# 只需要在这里修改或增加名字，脚本就会自动循环处理
target_scenes = [
    "Spherical",
    "Erectophile",
    "Planophile",
    # "Plagiophile", # 如果有其他的，继续加在这里
    # "Extremophile"
]

# 3. 定义输出文件名 (每个子文件夹内都会生成一个同名的汇总文件)
combined_csv_name = "combined_simulation_results_with_LAI.csv"


# ================= 核心处理函数 =================
def process_scene_folder(target_dir):
    """
    处理单个场景文件夹的函数
    :param target_dir: 具体的文件夹路径 (例如 .../Spherical)
    """
    print(f"\n{'=' * 10} 正在处理场景: {os.path.basename(target_dir)} {'=' * 10}")

    output_csv_path = os.path.join(target_dir, combined_csv_name)
    all_dataframes = []

    # 1. 递归搜索 CSV 文件
    csv_files = list(Path(target_dir).rglob('*.csv'))

    # 过滤掉以前生成的汇总文件，防止重复读取
    csv_files = [f for f in csv_files if f.name != combined_csv_name]

    if not csv_files:
        print(f"⚠️  跳过: 在 {target_dir} 中未找到 CSV 文件。")
        return

    print(f"📂 找到 {len(csv_files)} 个文件，开始提取...")

    for file_path in csv_files:
        try:
            file_name = file_path.name
            # 获取父文件夹名 (可能用于提取 LAI)
            parent_folder_name = file_path.parent.name

            # === A. 提取 Cab ===
            cab_match = re.search(r'_Cab([\d.]+)', file_name, re.IGNORECASE)
            if not cab_match:
                # print(f"  - 跳过: {file_name} 无 Cab 信息") # 减少刷屏，暂时注释
                continue
            cab_value = float(cab_match.group(1))

            # === B. 提取 LAI ===
            lai_match = re.search(r'LAI([\d.]+)', file_name, re.IGNORECASE)
            if lai_match:
                lai_value = float(lai_match.group(1))
            else:
                # 尝试从父文件夹名提取
                lai_match_parent = re.search(r'LAI([\d.]+)', parent_folder_name, re.IGNORECASE)
                if lai_match_parent:
                    lai_value = float(lai_match_parent.group(1))
                else:
                    lai_value = None  # 标记为 NaN

            # === C. 读取并添加列 ===
            df = pd.read_csv(file_path)
            if df.empty: continue

            # 插入元数据列
            # 注意：这里的 Scene 默认使用当前处理的文件夹名 (如 Spherical)
            df['Scene'] = os.path.basename(target_dir)
            df['Cab'] = cab_value
            df['LAI'] = lai_value

            all_dataframes.append(df)

        except Exception as e:
            print(f"❌ 处理文件 {file_path.name} 出错: {e}")

    # 2. 合并数据
    if not all_dataframes:
        print("  - 没有有效数据可合并。")
        return

    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # === D. 列名修复与重排 ===
    if 'Sun_Zenith' in combined_df.columns:
        combined_df.rename(columns={'Sun_Zenith': 'SZA'}, inplace=True)

    band_cols = [col for col in combined_df.columns if col.startswith('Band_')]

    if band_cols:
        band_cols.sort(key=lambda x: int(x.split('_')[1]))

        rename_dict = {}
        # 假设前两列是角度
        if len(band_cols) >= 1: rename_dict[band_cols[0]] = 'VZA'
        if len(band_cols) >= 2: rename_dict[band_cols[1]] = 'VAA'

        # 映射波长 (起始 410nm)
        spectral_cols = band_cols[2:]
        start_wavelength = 410
        new_spectral_names = [str(i) for i in range(start_wavelength, start_wavelength + len(spectral_cols))]
        rename_dict.update(dict(zip(spectral_cols, new_spectral_names)))

        combined_df.rename(columns=rename_dict, inplace=True)

        # 排序列
        id_cols = ['Scene', 'Cab', 'LAI', 'SZA', 'VZA', 'VAA']
        final_id_cols = [c for c in id_cols if c in combined_df.columns]
        other_cols = [c for c in combined_df.columns if c not in final_id_cols and c not in new_spectral_names]

        final_columns = final_id_cols + other_cols + new_spectral_names
        combined_df = combined_df[final_columns]

    # 3. 保存
    try:
        combined_df.to_csv(output_csv_path, index=False)
        print(f"✅ 成功！已保存: {output_csv_path}")
        print(f"   行数: {len(combined_df)}")
    except Exception as e:
        print(f"❌ 保存失败: {e}")


# ================= 主程序入口 =================

if __name__ == "__main__":
    print(f"开始批量处理，根目录: {base_result_dir}")

    # 循环遍历列表中的文件夹
    for scene_name in target_scenes:
        # 拼接完整路径: .../result2/Spherical
        full_scene_path = os.path.join(base_result_dir, scene_name)

        # 检查文件夹是否存在
        if os.path.exists(full_scene_path):
            process_scene_folder(full_scene_path)
        else:
            print(f"\n❌ 警告: 文件夹不存在，跳过: {full_scene_path}")

    print("\n所有任务处理完毕！")