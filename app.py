import pandas as pd
import numpy as np

# 1. 读取数据
# 请替换为你本地的实际文件名
main_file = 'B0DNN8BWY8-US-Reviews-251224-531094.xlsx - B0DNN8BWY8-Review(760).csv'
good_tags_file = 'B0DNN8BWY8-US-Reviews-251224-531094.xlsx - 好评点.csv'
bad_tags_file = 'B0DNN8BWY8-US-Reviews-251224-531094.xlsx - 差评点.csv'

# 读取主文件
df_main = pd.read_csv(main_file)

# 读取标签库 (假设没有表头，第一列即为标签)
# 标签格式处理：将 "舒适/佩戴舒适" 拆分为 ["舒适", "佩戴舒适"]
def load_and_process_tags(file_path):
    raw_tags = pd.read_csv(file_path, header=None, names=['tag'])['tag'].dropna().astype(str).tolist()
    processed = []
    for tag in raw_tags:
        # 使用 '/' 拆分同义词，但保留原始标签作为最终打标结果
        keywords = [k.strip() for k in tag.split('/') if k.strip()]
        processed.append((tag, keywords))
    return processed

good_tags_processed = load_and_process_tags(good_tags_file)
bad_tags_processed = load_and_process_tags(bad_tags_file)

# 2. 定义打标函数
def get_tag(row):
    try:
        rating = float(row['星级'])
    except:
        return "" # 评分格式错误则不处理
    
    # 核心：使用【内容(翻译)】列进行匹配
    text = str(row['内容(翻译)']) if pd.notna(row['内容(翻译)']) else ""
    if not text:
        return ""
    
    target_list = []
    
    # 星级分流逻辑
    if rating >= 4:
        target_list = good_tags_processed
    elif rating <= 3:
        target_list = bad_tags_processed
    else:
        return ""
        
    # 关键词匹配
    for tag_label, keywords in target_list:
        # 只要评论中包含该标签下的【任意一个】关键词，即命中
        if any(kw in text for kw in keywords):
            return tag_label # 找到第一个匹配的标签即返回
            
    return "" # 无匹配则留空

# 3. 执行并保存
df_main['分析标签'] = df_main.apply(get_tag, axis=1)

# 保存为 CSV (utf-8-sig 防止中文乱码)
df_main.to_csv('tagged_reviews_result.csv', index=False, encoding='utf-8-sig')

print("打标完成！已保存为 tagged_reviews_result.csv")
