import streamlit as st
import pandas as pd
import io

# --- 页面配置 ---
st.set_page_config(page_title="评论自动打标工具 (修复版)", layout="wide", page_icon="🏷️")

# --- 状态管理 ---
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df_main' not in st.session_state:
    st.session_state.df_main = None
if 'df_good' not in st.session_state:
    st.session_state.df_good = None
if 'df_bad' not in st.session_state:
    st.session_state.df_bad = None

# --- 核心分析函数 (已修复匹配逻辑) ---
def analyze_reviews(df_main, df_good, df_bad, col_review, col_rating):
    # 1. 准备标签库
    # 这里我们不做简单的 tolist()，而是预处理，把 "A/B" 拆分成关键词列表
    def process_tags(df):
        raw_tags = df.iloc[:, 0].dropna().astype(str).tolist()
        processed = []
        for tag in raw_tags:
            # 将标签按 '/' 拆分，去除首尾空格
            # 例如: "舒适/佩戴舒适" -> keywords: ["舒适", "佩戴舒适"]
            keywords = [k.strip() for k in tag.split('/') if k.strip()]
            if keywords:
                # 存入元组: (原始标签名, [关键词1, 关键词2...])
                processed.append((tag, keywords))
        return processed

    good_tags_processed = process_tags(df_good)
    bad_tags_processed = process_tags(df_bad)
    
    # 2. 定义单行打标逻辑
    def get_tag(row):
        # 获取评论内容，转为字符串
        content = str(row[col_review]) if pd.notna(row[col_review]) else ""
        
        # 获取星级 (容错处理)
        try:
            rating = float(row[col_rating])
        except:
            return None 

        matched_tag = None
        target_list = []

        # 星级分流
        if rating >= 4:
            target_list = good_tags_processed
        elif rating <= 3:
            target_list = bad_tags_processed
        else:
            return None 

        # --- 增强版匹配逻辑 ---
        # 遍历每一个标签组
        for original_label, keywords in target_list:
            # 检查该标签下的【任意一个】关键词是否出现在评论中
            for kw in keywords:
                if kw in content:
                    matched_tag = original_label
                    return matched_tag # 找到一个就立刻返回，不再继续找
        
        return None

    # 3. 执行
    df_result = df_main.copy()
    df_result['分析标签'] = df_result.apply(get_tag, axis=1)
    
    return df_result, None

# --- 主界面 ---
st.title("🏷️ 评论自动打标神器 (增强匹配版)")
st.info("💡 修复说明：已优化算法。现在标签如 '舒适/佩戴舒适' 会自动拆分为 '舒适' 或 '佩戴舒适' 进行匹配，确保能打上标签。")

# 文件上传
uploaded_file = st.file_uploader("上传 Excel 文件 (包含3个Sheet)", type=['xlsx'], key="uploader")

# 数据加载
if uploaded_file:
    try:
        if not st.session_state.data_loaded:
            xls = pd.ExcelFile(uploaded_file)
            if len(xls.sheet_names) < 3:
                st.error("❌ 文件必须包含至少3个Sheet (数据, 好评, 差评)")
            else:
                st.session_state.df_main = pd.read_excel(xls, sheet_name=0)
                st.session_state.df_good = pd.read_excel(xls, sheet_name=1)
                st.session_state.df_bad = pd.read_excel(xls, sheet_name=2)
                st.session_state.data_loaded = True
                st.rerun()
    except Exception as e:
        st.error(f"读取失败: {e}")

# 重置逻辑
if not uploaded_file and st.session_state.data_loaded:
    st.session_state.data_loaded = False
    st.session_state.df_main = None
    st.rerun()

# 分析区
if st.session_state.data_loaded and st.session_state.df_main is not None:
    df = st.session_state.df_main
    cols = df.columns.tolist()
    
    st.write("---")
    c1, c2 = st.columns(2)
    
    # 智能选择列名 (优先找 '翻译' 或 '内容')
    # 你的文件里有 '内容(翻译)'，我们会优先匹配它
    idx_review = next((i for i, c in enumerate(cols) if any(x in str(c) for x in ['翻译', '内容', 'review'])), 0)
    col_review = c1.selectbox("选择【评论内容】列", cols, index=idx_review, key="sel_rev")
    
    idx_rating = next((i for i, c in enumerate(cols) if any(x in str(c) for x in ['星', 'Rating'])), 0)
    col_rating = c2.selectbox("选择【星级】列", cols, index=idx_rating, key="sel_rate")

    if st.button("🚀 开始打标", type="primary"):
        with st.spinner("正在拆分关键词并匹配..."):
            res, err = analyze_reviews(
                st.session_state.df_main,
                st.session_state.df_good,
                st.session_state.df_bad,
                col_review,
                col_rating
            )
            
            if err:
                st.error(err)
            else:
                # 统计结果
                count = res['分析标签'].notna().sum()
                st.success(f"打标完成！共有 **{count}** 条评论成功匹配到标签。")
                
                # 预览前10行有标签的数据
                st.write("结果预览 (仅展示已打标数据):")
                st.dataframe(res[res['分析标签'].notna()].head())
                
                # 下载
                out = io.BytesIO()
                res.to_csv(out, index=False, encoding='utf-8-sig')
                st.download_button("📥 下载结果 CSV", out, "tagged_result.csv", "text/csv")
