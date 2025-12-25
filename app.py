import streamlit as st
import pandas as pd
import io

# --- 页面基础设置 ---
st.set_page_config(page_title="电商评论自动打标工具", layout="wide", page_icon="🏷️")

# --- 初始化 Session State (缓存状态) ---
# 这步至关重要，防止每次点击按钮都重新读取文件，从而解决 removeChild 错误
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df_main' not in st.session_state:
    st.session_state.df_main = None
if 'df_good' not in st.session_state:
    st.session_state.df_good = None
if 'df_bad' not in st.session_state:
    st.session_state.df_bad = None

# --- 核心分析函数 ---
def analyze_reviews(df_main, df_good, df_bad, col_review, col_rating):
    """
    根据星级分流，分别匹配好评库和差评库
    """
    try:
        # 1. 准备标签库 (转为列表并过滤空值)
        good_tags = df_good.iloc[:, 0].dropna().astype(str).tolist()
        bad_tags = df_bad.iloc[:, 0].dropna().astype(str).tolist()
        
        # 2. 定义单行处理逻辑
        def get_tag(row):
            content = str(row[col_review]) if pd.notna(row[col_review]) else ""
            try:
                rating = float(row[col_rating])
            except:
                return None 

            matched_tag = None
            target_tags = []

            # 星级分流
            if rating >= 4:
                target_tags = good_tags
            elif rating <= 3:
                target_tags = bad_tags
            else:
                return None 

            # 关键词匹配
            for tag in target_tags:
                if tag in content:
                    matched_tag = tag
                    break 
            return matched_tag

        # 3. 应用逻辑
        df_result = df_main.copy()
        df_result['分析标签'] = df_result.apply(get_tag, axis=1)
        return df_result, None
        
    except Exception as e:
        return None, str(e)

# --- 界面显示 ---
st.title("🏷️ 亚马逊/电商评论自动打标神器")
st.markdown("""
**使用说明：** 请上传 Excel (.xlsx) 文件，需包含 3 个 Sheet：
1. **数据源** (评论+星级) | 2. **好评库** | 3. **差评库**
""")

# --- 文件上传区 ---
# 给 file_uploader 加一个 key，保持状态稳定
uploaded_file = st.file_uploader("请上传 Excel 文件", type=['xlsx'], key="file_uploader")

# --- 数据加载逻辑 (核心修复部分) ---
if uploaded_file:
    try:
        # 只有当文件发生变化，或者数据还没加载时，才读取 Excel
        # 这样可以避免频繁读取导致的 DOM 错误
        if not st.session_state.data_loaded:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            
            if len(sheet_names) < 3:
                st.error(f"❌ 文件格式错误：检测到只有 {len(sheet_names)} 个Sheet。")
            else:
                # 读取数据存入 session_state
                st.session_state.df_main = pd.read_excel(xls, sheet_name=0)
                st.session_state.df_good = pd.read_excel(xls, sheet_name=1)
                st.session_state.df_bad = pd.read_excel(xls, sheet_name=2)
                st.session_state.data_loaded = True
                # 强制刷新一次页面以更新状态
                st.rerun() 
    except Exception as e:
        st.error(f"读取文件失败: {e}")

# 如果用户更换了文件（点击了X），重置状态
if not uploaded_file and st.session_state.data_loaded:
    st.session_state.data_loaded = False
    st.session_state.df_main = None
    st.rerun()

# --- 分析配置区 (只有数据加载成功后才显示) ---
if st.session_state.data_loaded and st.session_state.df_main is not None:
    
    st.success(f"✅ 文件已加载！包含 {len(st.session_state.df_main)} 条数据。")
    st.write("---")
    
    df_main = st.session_state.df_main
    all_columns = df_main.columns.tolist()

    col1, col2 = st.columns(2)
    
    with col1:
        # 智能预选列名
        default_review = next((i for i, c in enumerate(all_columns) if any(x in str(c).lower() for x in ['内容', '评论', 'review', 'content', 'body'])), 0)
        # 增加 key 参数，确保组件唯一性
        selected_review_col = st.selectbox("选择【评论内容】列：", all_columns, index=default_review, key="sel_review")
    
    with col2:
        default_rating = next((i for i, c in enumerate(all_columns) if any(x in str(c).lower() for x in ['星', '分', 'rating', 'star'])), 0)
        selected_rating_col = st.selectbox("选择【星级/评分】列：", all_columns, index=default_rating, key="sel_rating")

    # --- 按钮区 ---
    if st.button("🚀 开始自动打标", type="primary", key="btn_start"):
        with st.spinner('正在分析中...'):
            result_df, err = analyze_reviews(
                st.session_state.df_main, 
                st.session_state.df_good, 
                st.session_state.df_bad, 
                selected_review_col, 
                selected_rating_col
            )
            
            if err:
                st.error(f"分析出错: {err}")
            else:
                # 统计
                tagged_count = result_df['分析标签'].notna().sum()
                st.info(f"分析完成！成功打标 **{tagged_count}** 条。")
                
                # 预览
                st.dataframe(result_df.head())
                
                # 下载
                output = io.BytesIO()
                result_df.to_csv(output, index=False, encoding='utf-8-sig')
                output.seek(0)
                
                st.download_button(
                    label="📥 下载 CSV 结果",
                    data=output,
                    file_name="Review_Analysis_Result.csv",
                    mime="text/csv"
                )
